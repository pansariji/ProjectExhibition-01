import socket
import threading
import struct
import os
import time

import config
from utils import get_local_ip, format_size

class Receiver:
    def __init__(self, passcode, on_status_callback, on_progress_callback, on_complete_callback):
        self.passcode = passcode
        self.on_status = on_status_callback
        self.on_progress = on_progress_callback
        self.on_complete = on_complete_callback
        
        self.udp_port = config.DEFAULT_UDP_PORT
        self.local_ip = get_local_ip()
        
        self.running = False
        self.tcp_server_socket = None
        self.udp_socket = None
        self.tcp_port = 0
        
        self.downloads_dir = config.DOWNLOADS_DIR
        if not os.path.exists(self.downloads_dir):
            os.makedirs(self.downloads_dir)

    def start(self):
        """Starts TCP and UDP servers."""
        self.running = True
        
        self.tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server_socket.bind(('0.0.0.0', 0))  # Bind to any free port
        self.tcp_server_socket.listen(1)
        self.tcp_port = self.tcp_server_socket.getsockname()[1]
        
        self.on_status(f"Listening on TCP port {self.tcp_port}")
        
        threading.Thread(target=self._tcp_listener, daemon=True).start()
        threading.Thread(target=self._udp_listener, daemon=True).start()
        
        self.on_status(f"Waiting for Sender with passcode {self.passcode}...")

    def stop(self):
        """Stops all servers."""
        self.running = False
        if self.tcp_server_socket:
            try:
                self.tcp_server_socket.close()
            except Exception:
                pass
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except Exception:
                pass

    def _udp_listener(self):
        """Listens for UDP discovery broadcast packets."""
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.udp_socket.bind(('0.0.0.0', self.udp_port))
            
            while self.running:
                data, addr = self.udp_socket.recvfrom(1024)
                message = data.decode('utf-8').strip()
                
                if message.startswith("LOCALDROP_DISCOVER:"):
                    received_passcode = message.split(":")[1]
                    if received_passcode == self.passcode:
                        self.on_status(f"Sender found at {addr[0]}. Responding...")
                        response = f"LOCALDROP_ACCEPT:{self.tcp_port}"
                        self.udp_socket.sendto(response.encode('utf-8'), addr)
        except Exception as e:
            if self.running:
                self.on_status(f"UDP Error: {e}")

    def _tcp_listener(self):
        """Handles incoming TCP connections."""
        try:
            while self.running:
                client_sock, addr = self.tcp_server_socket.accept()
                if not self.running:
                    break
                
                self.on_status(f"Connected by {addr[0]}")
                threading.Thread(target=self._handle_client, args=(client_sock,), daemon=True).start()
        except Exception as e:
            if self.running:
                self.on_status(f"TCP Error: {e}")

    def _handle_client(self, client_sock):
        """Handles file/folder data reception."""
        try:
            raw_flag = self._recvall(client_sock, 1)
            if not raw_flag:
                return
            flag = raw_flag.decode('utf-8')

            if flag == 'D':
                # Receive folder name length & name
                raw_namelen = self._recvall(client_sock, 4)
                if not raw_namelen:
                    return
                name_len = struct.unpack('>I', raw_namelen)[0]
                foldername = self._recvall(client_sock, name_len).decode('utf-8')

                # Total size & entry count
                raw_totalsize = self._recvall(client_sock, 8)
                total_size = struct.unpack('>Q', raw_totalsize)[0]

                raw_entrycount = self._recvall(client_sock, 4)
                entry_count = struct.unpack('>I', raw_entrycount)[0]

                self.on_status(f"Receiving folder: {foldername} ({format_size(total_size)}, {entry_count} items)")

                dest_folder = os.path.join(self.downloads_dir, foldername)
                os.makedirs(dest_folder, exist_ok=True)

                total_received_bytes = 0
                start_time = time.time()
                last_update_time = start_time
                last_received_bytes = 0

                for _ in range(entry_count):
                    if not self.running:
                        break

                    raw_etype = self._recvall(client_sock, 1)
                    if not raw_etype:
                        break
                    entry_type = raw_etype.decode('utf-8')

                    raw_rel_len = self._recvall(client_sock, 4)
                    if not raw_rel_len:
                        break
                    rel_len = struct.unpack('>I', raw_rel_len)[0]

                    rel_path = self._recvall(client_sock, rel_len).decode('utf-8')
                    parts = rel_path.split('/')
                    target_path = os.path.join(dest_folder, *parts)

                    if entry_type == 'D':
                        os.makedirs(target_path, exist_ok=True)
                    elif entry_type == 'F':
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)

                        raw_fsize = self._recvall(client_sock, 8)
                        if not raw_fsize:
                            break
                        fsize = struct.unpack('>Q', raw_fsize)[0]

                        received_file_bytes = 0
                        with open(target_path, 'wb') as f:
                            while received_file_bytes < fsize and self.running:
                                chunk_size = min(config.CHUNK_SIZE_P2P, fsize - received_file_bytes)
                                chunk = client_sock.recv(chunk_size)
                                if not chunk:
                                    break
                                f.write(chunk)
                                len_chunk = len(chunk)
                                received_file_bytes += len_chunk
                                total_received_bytes += len_chunk

                                current_time = time.time()
                                if current_time - last_update_time > 0.1:
                                    percent = (total_received_bytes / total_size * 100) if total_size > 0 else 100.0
                                    elapsed = current_time - last_update_time
                                    bytes_sec = (total_received_bytes - last_received_bytes) / elapsed if elapsed > 0 else 0
                                    speed_str = f"{format_size(bytes_sec)}/s"
                                    self.on_progress(percent, speed_str)
                                    last_update_time = current_time
                                    last_received_bytes = total_received_bytes

                if self.running:
                    self.on_progress(100.0, "Done")
                    self.on_status(f"Folder transfer complete. Saved to Downloads/{foldername}")
                    self.on_complete(True, dest_folder)
                else:
                    self.on_status("Transfer interrupted.")
                    self.on_complete(False, None)

            elif flag == 'F':
                # Receive filename length & name
                raw_namelen = self._recvall(client_sock, 4)
                if not raw_namelen:
                    return
                name_len = struct.unpack('>I', raw_namelen)[0]
                filename = self._recvall(client_sock, name_len).decode('utf-8')

                # Receive file size
                raw_filesize = self._recvall(client_sock, 8)
                file_size = struct.unpack('>Q', raw_filesize)[0]

                self.on_status(f"Receiving file: {filename} ({format_size(file_size)})")

                filepath = os.path.join(self.downloads_dir, filename)
                received_bytes = 0

                start_time = time.time()
                last_update_time = start_time
                last_received_bytes = 0

                with open(filepath, 'wb') as f:
                    while received_bytes < file_size and self.running:
                        chunk_size = min(config.CHUNK_SIZE_P2P, file_size - received_bytes)
                        chunk = client_sock.recv(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        received_bytes += len(chunk)

                        current_time = time.time()
                        if current_time - last_update_time > 0.1:
                            percent = (received_bytes / file_size * 100) if file_size > 0 else 100.0
                            elapsed = current_time - last_update_time
                            bytes_sec = (received_bytes - last_received_bytes) / elapsed if elapsed > 0 else 0
                            speed_str = f"{format_size(bytes_sec)}/s"

                            self.on_progress(percent, speed_str)
                            last_update_time = current_time
                            last_received_bytes = received_bytes

                if received_bytes == file_size:
                    self.on_progress(100.0, "Done")
                    self.on_status("Transfer complete. Saved to Downloads folder.")
                    self.on_complete(True, filepath)
                else:
                    self.on_status("Transfer incomplete or interrupted.")
                    self.on_complete(False, None)
            else:
                self.on_status("Unknown transfer format received.")
                self.on_complete(False, None)

        except Exception as e:
            self.on_status(f"Transfer error: {e}")
            self.on_complete(False, None)
        finally:
            client_sock.close()

    def _recvall(self, sock, n):
        """Helper to strictly receive n bytes."""
        data = bytearray()
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
        return data
