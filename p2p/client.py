import socket
import threading
import struct
import os
import time
import subprocess
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
from utils import format_size, get_local_ip

def get_arp_ips():
    """Parses the system ARP table to find active local network IPs."""
    active_ips = set()
    try:
        output = subprocess.check_output("arp -a", shell=True, stderr=subprocess.DEVNULL).decode('utf-8', errors='ignore')
        matches = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', output)
        for ip in matches:
            if not ip.startswith(('255.', '224.', '127.', '0.')):
                active_ips.add(ip)
    except Exception:
        pass
    return list(active_ips)

class Sender:
    def __init__(self, on_status_callback, on_progress_callback, on_complete_callback):
        self.on_status = on_status_callback
        self.on_progress = on_progress_callback
        self.on_complete = on_complete_callback
        self.udp_port = config.DEFAULT_UDP_PORT
        self.running = False
        
    def cancel(self):
        """Cancels the transfer."""
        self.running = False

    def discover_and_send(self, filepath, passcode, target_ip=None):
        """Starts a background thread to discover the receiver and send the file."""
        self.running = True
        threading.Thread(target=self._discover_and_send_thread, args=(filepath, passcode, target_ip), daemon=True).start()

    def _discover_receiver(self, passcode, target_ip=None):
        if target_ip:
            return target_ip, config.DEFAULT_P2P_PORT

        self.on_status(f"Searching for passcode {passcode} on Wi-Fi...")
        message = f"LOCALDROP_DISCOVER:{passcode}".encode('utf-8')
        local_ip = get_local_ip()

        # Phase 1: UDP Broadcast
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_socket.settimeout(0.8)
        
        if local_ip != '127.0.0.1':
            try:
                udp_socket.bind((local_ip, 0))
            except Exception:
                pass

        try:
            udp_socket.sendto(message, ('255.255.255.255', self.udp_port))
            if local_ip != '127.0.0.1' and '.' in local_ip:
                parts = local_ip.split('.')
                subnet_broadcast = '.'.join(parts[:-1]) + '.255'
                udp_socket.sendto(message, (subnet_broadcast, self.udp_port))
            
            data, addr = udp_socket.recvfrom(1024)
            response = data.decode('utf-8').strip()
            if response.startswith("LOCALDROP_ACCEPT:"):
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

        # Phase 2: Parallel ARP Cache + TCP/UDP Subnet Probing (Campus Wi-Fi Mode)
        if local_ip != '127.0.0.1' and '.' in local_ip:
            self.on_status(f"Campus Wi-Fi Mode: Probing ARP table & subnet for passcode {passcode}...")
            
            candidate_ips = set(get_arp_ips())
            parts = local_ip.split('.')
            subnet_prefix = '.'.join(parts[:3])
            for i in range(1, 255):
                candidate_ips.add(f"{subnet_prefix}.{i}")
            
            candidate_ips.discard(local_ip)
            found_target = [None, None]
            
            def probe_ip(ip):
                if not self.running or found_target[0]:
                    return
                # Send UDP probe
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.settimeout(0.2)
                    s.sendto(message, (ip, self.udp_port))
                    data, addr = s.recvfrom(1024)
                    res = data.decode('utf-8').strip()
                    s.close()
                    if res.startswith("LOCALDROP_ACCEPT:"):
                        port = int(res.split(":")[1])
                        found_target[0] = addr[0]
                        found_target[1] = port
                        return
                except Exception:
                    pass

                # If UDP unicast blocked, probe default TCP P2P port directly
                try:
                    ts = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    ts.settimeout(0.2)
                    if ts.connect_ex((ip, config.DEFAULT_P2P_PORT)) == 0:
                        ts.close()
                        found_target[0] = ip
                        found_target[1] = config.DEFAULT_P2P_PORT
                        return
                    ts.close()
                except Exception:
                    pass

            with ThreadPoolExecutor(max_workers=60) as executor:
                futures = [executor.submit(probe_ip, ip) for ip in candidate_ips]
                for future in as_completed(futures):
                    if found_target[0]:
                        break

            if found_target[0]:
                return found_target[0], found_target[1]

        return None, None

    def _discover_and_send_thread(self, filepath, passcode, target_ip=None):
        """Threaded function to perform discovery and transfer."""
        receiver_ip, receiver_tcp_port = self._discover_receiver(passcode, target_ip)
        
        if not receiver_ip or not receiver_tcp_port:
            self.on_status("College Wi-Fi Notice: Discovery failed (UDP Broadcast blocked).")
            self.on_complete(False, "DISCOVERY_FAILED")
            return

        self.on_status(f"Receiver found at {receiver_ip}. Connecting...")

        if not self.running:
            return

        # 2. TCP Transfer
        try:
            is_directory = os.path.isdir(filepath)
            tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_socket.connect((receiver_ip, receiver_tcp_port))

            if is_directory:
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

                # Directory Flag Header
                tcp_socket.sendall(b'D')

                encoded_foldername = foldername.encode('utf-8')
                tcp_socket.sendall(struct.pack('>I', len(encoded_foldername)))
                tcp_socket.sendall(encoded_foldername)

                tcp_socket.sendall(struct.pack('>Q', total_bytes))
                tcp_socket.sendall(struct.pack('>I', len(entries)))

                self.on_status(f"Sending folder {foldername} ({format_size(total_bytes)}, {len(entries)} items)...")

                total_sent_bytes = 0
                start_time = time.time()
                last_update_time = start_time
                last_sent_bytes = 0

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
                # Single File Transfer
                filename = os.path.basename(filepath)
                file_size = os.path.getsize(filepath)

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
