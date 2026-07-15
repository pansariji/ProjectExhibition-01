import socket
import threading
import struct
import os
import time

from utils import format_size

class Sender:
    def __init__(self, on_status_callback, on_progress_callback, on_complete_callback):
        self.on_status = on_status_callback
        self.on_progress = on_progress_callback
        self.on_complete = on_complete_callback
        self.udp_port = 50025
        self.running = False
        
    def cancel(self):
        """Cancels the transfer."""
        self.running = False

    def discover_and_send(self, filepath, passcode):
        """Starts a background thread to discover the receiver and send the file."""
        self.running = True
        threading.Thread(target=self._discover_and_send_thread, args=(filepath, passcode), daemon=True).start()

    def _discover_and_send_thread(self, filepath, passcode):
        """Threaded function to perform discovery and transfer."""
        receiver_ip = None
        receiver_tcp_port = None
        
        # 1. UDP Discovery
        self.on_status(f"Searching for receiver with passcode {passcode}...")
        
        try:
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            udp_socket.settimeout(5.0) # 5 second timeout for discovery
            
            # Get local IP and bind to it to force routing broadcast through the active interface on macOS
            from utils import get_local_ip
            local_ip = get_local_ip()
            if local_ip != '127.0.0.1':
                try:
                    udp_socket.bind((local_ip, 0))
                except Exception as bind_err:
                    print(f"Warning: Failed to bind UDP socket to local IP {local_ip}: {bind_err}")
            
            # Broadcast the discovery message
            message = f"LOCALDROP_DISCOVER:{passcode}"
            # Broadcast to 255.255.255.255 (limited broadcast)
            udp_socket.sendto(message.encode('utf-8'), ('255.255.255.255', self.udp_port))
            
            # Also broadcast to the subnet-directed broadcast address (e.g. 192.168.1.255) as a fallback
            if local_ip != '127.0.0.1' and '.' in local_ip:
                try:
                    parts = local_ip.split('.')
                    subnet_broadcast = '.'.join(parts[:-1]) + '.255'
                    udp_socket.sendto(message.encode('utf-8'), (subnet_broadcast, self.udp_port))
                except Exception:
                    pass
            
            # Wait for a response
            data, addr = udp_socket.recvfrom(1024)
            response = data.decode('utf-8').strip()
            
            if response.startswith("LOCALDROP_ACCEPT:"):
                receiver_ip = addr[0]
                receiver_tcp_port = int(response.split(":")[1])
                self.on_status(f"Receiver found at {receiver_ip}. Connecting...")
            else:
                self.on_status("Received malformed response from receiver.")
                self.on_complete(False)
                return
                
        except socket.timeout:
            self.on_status("Error: No device found with that passcode (timeout).")
            self.on_complete(False)
            return
        except Exception as e:
            self.on_status(f"Discovery Error: {e}")
            self.on_complete(False)
            return
        finally:
            udp_socket.close()

        if not self.running:
            return

        # 2. TCP File Transfer
        try:
            # Get file info
            filename = os.path.basename(filepath)
            file_size = os.path.getsize(filepath)
            
            tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_socket.connect((receiver_ip, receiver_tcp_port))
            
            # Send filename length (4 bytes)
            encoded_name = filename.encode('utf-8')
            tcp_socket.sendall(struct.pack('>I', len(encoded_name)))
            
            # Send filename
            tcp_socket.sendall(encoded_name)
            
            # Send file size (8 bytes)
            tcp_socket.sendall(struct.pack('>Q', file_size))
            
            self.on_status(f"Sending {filename} ({format_size(file_size)})...")
            
            sent_bytes = 0
            start_time = time.time()
            last_update_time = start_time
            last_sent_bytes = 0
            
            # Stream the file
            with open(filepath, 'rb') as f:
                while sent_bytes < file_size and self.running:
                    # Read 8192 bytes at a time
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    
                    tcp_socket.sendall(chunk)
                    sent_bytes += len(chunk)
                    
                    # Update progress every ~0.1s
                    current_time = time.time()
                    if current_time - last_update_time > 0.1:
                        percent = (sent_bytes / file_size) * 100
                        
                        elapsed = current_time - last_update_time
                        bytes_sec = (sent_bytes - last_sent_bytes) / elapsed
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
            except:
                pass
