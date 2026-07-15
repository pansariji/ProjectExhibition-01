import socket
import threading
import struct
import os
import time

from utils import get_local_ip, format_size

class Receiver:
    def __init__(self, passcode, on_status_callback, on_progress_callback, on_complete_callback):
        self.passcode = passcode
        self.on_status = on_status_callback
        self.on_progress = on_progress_callback
        self.on_complete = on_complete_callback
        
        self.udp_port = 50025
        self.local_ip = get_local_ip()
        
        self.running = False
        self.tcp_server_socket = None
        self.udp_socket = None
        self.tcp_port = 0
        
        self.downloads_dir = os.path.join(os.getcwd(), "Downloads")
        if not os.path.exists(self.downloads_dir):
            os.makedirs(self.downloads_dir)

    def start(self):
        """Starts the TCP and UDP servers."""
        self.running = True
        
        # Start TCP server
        self.tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server_socket.bind(('0.0.0.0', 0)) # Bind to any free port
        self.tcp_server_socket.listen(1)
        self.tcp_port = self.tcp_server_socket.getsockname()[1]
        
        self.on_status(f"Listening on TCP port {self.tcp_port}")
        
        # Start TCP thread
        threading.Thread(target=self._tcp_listener, daemon=True).start()
        
        # Start UDP listener thread
        threading.Thread(target=self._udp_listener, daemon=True).start()
        
        self.on_status(f"Waiting for Sender with passcode {self.passcode}...")

    def stop(self):
        """Stops all servers."""
        self.running = False
        if self.tcp_server_socket:
            try:
                self.tcp_server_socket.close()
            except:
                pass
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass

    def _udp_listener(self):
        """Listens for UDP broadcast packets from the Sender."""
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Allow reusing addresses and enable broadcasting
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Bind to all interfaces on the discovery port
            self.udp_socket.bind(('0.0.0.0', self.udp_port))
            
            while self.running:
                # Wait for broadcast
                data, addr = self.udp_socket.recvfrom(1024)
                message = data.decode('utf-8').strip()
                
                # Check if it's a valid LocalDrop discovery message
                if message.startswith("LOCALDROP_DISCOVER:"):
                    received_passcode = message.split(":")[1]
                    if received_passcode == self.passcode:
                        self.on_status(f"Sender found at {addr[0]}. Responding...")
                        # Reply with the TCP port to connect to
                        response = f"LOCALDROP_ACCEPT:{self.tcp_port}"
                        self.udp_socket.sendto(response.encode('utf-8'), addr)
                        # We found a sender, but we keep listening in case the first response was dropped.
                        # The sender will connect via TCP and that's when the actual transfer starts.
        except Exception as e:
            if self.running:
                self.on_status(f"UDP Error: {e}")

    def _tcp_listener(self):
        """Handles incoming TCP file transfers."""
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
        """Handles the actual file data reception from a connected sender."""
        try:
            # 1. Receive filename length (4 bytes, unsigned int)
            raw_namelen = self._recvall(client_sock, 4)
            if not raw_namelen:
                return
            name_len = struct.unpack('>I', raw_namelen)[0]
            
            # 2. Receive filename
            filename = self._recvall(client_sock, name_len).decode('utf-8')
            
            # 3. Receive file size (8 bytes, unsigned long long)
            raw_filesize = self._recvall(client_sock, 8)
            file_size = struct.unpack('>Q', raw_filesize)[0]
            
            self.on_status(f"Receiving file: {filename} ({format_size(file_size)})")
            
            # 4. Receive file data in chunks
            filepath = os.path.join(self.downloads_dir, filename)
            received_bytes = 0
            
            start_time = time.time()
            last_update_time = start_time
            last_received_bytes = 0
            
            with open(filepath, 'wb') as f:
                while received_bytes < file_size and self.running:
                    # Read in chunks of 8192 bytes
                    chunk_size = min(8192, file_size - received_bytes)
                    chunk = client_sock.recv(chunk_size)
                    if not chunk:
                        break # Connection closed early
                    f.write(chunk)
                    received_bytes += len(chunk)
                    
                    # Update progress every ~0.1 seconds to not overwhelm the GUI
                    current_time = time.time()
                    if current_time - last_update_time > 0.1:
                        percent = (received_bytes / file_size) * 100
                        # Calculate speed
                        elapsed = current_time - last_update_time
                        bytes_sec = (received_bytes - last_received_bytes) / elapsed
                        speed_str = f"{format_size(bytes_sec)}/s"
                        
                        self.on_progress(percent, speed_str)
                        
                        last_update_time = current_time
                        last_received_bytes = received_bytes

            if received_bytes == file_size:
                self.on_progress(100.0, "Done")
                self.on_status(f"Transfer complete. Saved to Downloads folder.")
                self.on_complete(True, filepath)
            else:
                self.on_status(f"Transfer incomplete or interrupted.")
                self.on_complete(False, None)
                
        except Exception as e:
            self.on_status(f"Transfer error: {e}")
            self.on_complete(False, None)
        finally:
            client_sock.close()

    def _recvall(self, sock, n):
        """Helper function to strictly receive exactly n bytes or return None if EOF is hit."""
        data = bytearray()
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
        return data
