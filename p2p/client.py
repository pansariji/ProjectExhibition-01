import socket
import threading
import struct
import os
import time

import config
from utils import format_size, get_local_ip

class Sender:
    """
    Handles peer-to-peer file and folder transmission from the sender client.
    Performs UDP broadcast discovery using a 4-digit passcode or connects
    directly to a specified target IP, then streams data over a binary TCP socket.
    """
    def __init__(self, on_status_callback, on_progress_callback, on_complete_callback):
        self.on_status = on_status_callback
        self.on_progress = on_progress_callback
        self.on_complete = on_complete_callback
        self.udp_port = config.DEFAULT_UDP_PORT
        self.running = False
        
    def cancel(self):
        """Cancels an active or pending transfer operation."""
        self.running = False

    def discover_and_send(self, filepath, passcode, target_ip=None):
        """Starts a background thread to discover the receiver and stream payload data."""
        self.running = True
        threading.Thread(
            target=self._discover_and_send_thread, 
            args=(filepath, passcode, target_ip), 
            daemon=True
        ).start()

    def _discover_receiver(self, passcode, target_ip=None):
        """
        Discovers the receiver laptop IP address. If a manual target_ip is provided,
        it bypasses UDP broadcast and connects directly.
        """
        if target_ip:
            return target_ip, config.DEFAULT_P2P_PORT

        self.on_status(f"Searching for passcode {passcode} on local network...")
        message = f"DROPIT_DISCOVER:{passcode}".encode('utf-8')
        local_ip = get_local_ip()

        # Create UDP socket for broadcast discovery
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_socket.settimeout(1.0)
        
        if local_ip != '127.0.0.1':
            try:
                udp_socket.bind((local_ip, 0))
            except Exception:
                pass

        try:
            # Broadcast discovery message to global and subnet broadcast addresses
            udp_socket.sendto(message, ('255.255.255.255', self.udp_port))
            if local_ip != '127.0.0.1' and '.' in local_ip:
                parts = local_ip.split('.')
                subnet_broadcast = '.'.join(parts[:-1]) + '.255'
                udp_socket.sendto(message, (subnet_broadcast, self.udp_port))
            
            data, addr = udp_socket.recvfrom(1024)
            response = data.decode('utf-8').strip()
            if response.startswith("DROPIT_ACCEPT:"):
                tcp_port = int(response.split(":")[1])
                udp_socket.close()
                return addr[0], tcp_port
        except socket.timeout:
            pass
        finally:
            try:
                udp_socket.close()
            except Exception:
                pass

        return None, None

    def _discover_and_send_thread(self, filepath, passcode, target_ip=None):
        """Worker thread performing receiver discovery and chunked TCP streaming."""
        receiver_ip, receiver_tcp_port = self._discover_receiver(passcode, target_ip)
        
        if not receiver_ip or not receiver_tcp_port:
            self.on_status("Discovery failed. Network UDP Broadcast may be blocked.")
            self.on_complete(False, "DISCOVERY_FAILED")
            return

        self.on_status(f"Receiver found at {receiver_ip}. Connecting...")

        if not self.running:
            return

        # Establish TCP socket connection
        try:
            is_directory = os.path.isdir(filepath)
            tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_socket.connect((receiver_ip, receiver_tcp_port))

            if is_directory:
                # Directory Transfer Mode
                base_dir = os.path.abspath(filepath)
                foldername = os.path.basename(base_dir) or "Folder"

                entries = []
                total_bytes = 0
                for root, dirs, files in os.walk(base_dir):
                    rel_root = os.path.relpath(root, base_dir)
                    if rel_root == ".":
                        rel_root = ""

                    for d in dirs:
                        dir_abs = os.path.join(root, d)
                        if not os.listdir(dir_abs):
                            rel_dir = os.path.join(rel_root, d).replace('\\', '/')
                            entries.append(('D', rel_dir, None, 0))

                    for f in files:
                        file_abs = os.path.join(root, f)
                        rel_file = os.path.join(rel_root, f).replace('\\', '/')
                        try:
                            fsize = os.path.getsize(file_abs)
                        except OSError:
                            fsize = 0
                        total_bytes += fsize
                        entries.append(('F', rel_file, file_abs, fsize))

                # Send Directory Flag Header ('D')
                tcp_socket.sendall(b'D')

                # Send folder name length and folder name
                encoded_foldername = foldername.encode('utf-8')
                tcp_socket.sendall(struct.pack('>I', len(encoded_foldername)))
                tcp_socket.sendall(encoded_foldername)

                # Send total byte size and entry count
                tcp_socket.sendall(struct.pack('>Q', total_bytes))
                tcp_socket.sendall(struct.pack('>I', len(entries)))

                self.on_status(f"Sending folder {foldername} ({format_size(total_bytes)}, {len(entries)} items)...")

                total_sent_bytes = 0
                start_time = time.time()
                last_update_time = start_time
                last_sent_bytes = 0

                # Iterate and stream directory entries
                for entry_type, rel_path, abs_path, fsize in entries:
                    if not self.running:
                        break

                    tcp_socket.sendall(entry_type.encode('utf-8'))

                    encoded_rel_path = rel_path.encode('utf-8')
                    tcp_socket.sendall(struct.pack('>I', len(encoded_rel_path)))
                    tcp_socket.sendall(encoded_rel_path)

                    if entry_type == 'F':
                        tcp_socket.sendall(struct.pack('>Q', fsize))

                        with open(abs_path, 'rb') as f:
                            sent_for_file = 0
                            while sent_for_file < fsize and self.running:
                                chunk = f.read(min(config.CHUNK_SIZE_P2P, fsize - sent_for_file))
                                if not chunk:
                                    break
                                tcp_socket.sendall(chunk)
                                len_chunk = len(chunk)
                                sent_for_file += len_chunk
                                total_sent_bytes += len_chunk

                                current_time = time.time()
                                if current_time - last_update_time > 0.1:
                                    percent = (total_sent_bytes / total_bytes * 100) if total_bytes > 0 else 100.0
                                    elapsed = current_time - last_update_time
                                    bytes_sec = (total_sent_bytes - last_sent_bytes) / elapsed if elapsed > 0 else 0
                                    speed_str = f"{format_size(bytes_sec)}/s"
                                    self.on_progress(percent, speed_str)
                                    last_update_time = current_time
                                    last_sent_bytes = total_sent_bytes

                if self.running:
                    self.on_progress(100.0, "Done")
                    self.on_status("Folder transfer complete!")
                    self.on_complete(True)
                else:
                    self.on_status("Transfer canceled.")
                    self.on_complete(False)

            else:
                # Single File Transfer Mode
                filename = os.path.basename(filepath)
                file_size = os.path.getsize(filepath)

                # Send Single File Flag Header ('F')
                tcp_socket.sendall(b'F')

                encoded_name = filename.encode('utf-8')
                tcp_socket.sendall(struct.pack('>I', len(encoded_name)))
                tcp_socket.sendall(encoded_name)

                tcp_socket.sendall(struct.pack('>Q', file_size))

                self.on_status(f"Sending {filename} ({format_size(file_size)})...")

                sent_bytes = 0
                start_time = time.time()
                last_update_time = start_time
                last_sent_bytes = 0

                with open(filepath, 'rb') as f:
                    while sent_bytes < file_size and self.running:
                        chunk = f.read(config.CHUNK_SIZE_P2P)
                        if not chunk:
                            break
                        tcp_socket.sendall(chunk)
                        sent_bytes += len(chunk)

                        current_time = time.time()
                        if current_time - last_update_time > 0.1:
                            percent = (sent_bytes / file_size * 100) if file_size > 0 else 100.0
                            elapsed = current_time - last_update_time
                            bytes_sec = (sent_bytes - last_sent_bytes) / elapsed if elapsed > 0 else 0
                            speed_str = f"{format_size(bytes_sec)}/s"
                            self.on_progress(percent, speed_str)
                            last_update_time = current_time
                            last_sent_bytes = sent_bytes

                if sent_bytes == file_size:
                    self.on_progress(100.0, "Done")
                    self.on_status("Transfer complete!")
                    self.on_complete(True)
                else:
                    self.on_status("Transfer canceled.")
                    self.on_complete(False)

        except Exception as e:
            self.on_status(f"Transfer Error: {e}")
            self.on_complete(False)
        finally:
            try:
                tcp_socket.close()
            except Exception:
                pass

