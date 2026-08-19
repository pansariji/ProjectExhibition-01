import http.server
import socketserver
import threading
import urllib.parse
import os
import time
import shutil
import tempfile
import zipfile

import config
from utils import get_local_ip, format_size
from web.templates import MOBILE_UPLOAD_HTML_PAGE, MOBILE_DOWNLOAD_HTML_PAGE

class DropItHTTPHandler(http.server.BaseHTTPRequestHandler):
    """
    HTTP request handler serving mobile web interfaces for uploading files/folders
    to the laptop or downloading shared items from the laptop.
    """
    def log_message(self, format, *args):
        """Suppresses default HTTP server stdout logging."""
        pass

    def send_cors_headers(self):
        """Adds CORS and cache headers for universal browser compatibility (Brave, Opera, Chrome, Safari)."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Relative-Path, Content-Type, Content-Length')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')

    def do_OPTIONS(self):
        """Handles HTTP OPTIONS preflight requests sent by privacy-focused browsers like Brave and Opera."""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        """Handles HTTP GET requests for rendering web pages or streaming downloads."""
        # Web Receiver Mode (Mobile browser uploads files to Laptop)
        if hasattr(self.server, 'web_receiver'):
            if self.path == '/' or self.path == '/index.html':
                self.send_response(200)
                self.send_cors_headers()
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(MOBILE_UPLOAD_HTML_PAGE.encode('utf-8'))
            else:
                self.send_error(404, "Not Found")
                
        # Web Sender Mode (Mobile browser downloads shared file/zip from Laptop)
        elif hasattr(self.server, 'web_sender'):
            ws = self.server.web_sender
            
            # Wait for background folder compression if in progress
            while ws.running and not ws.ready:
                time.sleep(0.1)

            if not ws.running or not ws.ready or not ws.serve_path:
                self.send_error(503, "Archive compression in progress. Please refresh in a moment.")
                return

            if self.path == '/' or self.path == '/index.html':
                item_name = os.path.basename(ws.target_filename)
                item_size = format_size(ws.file_size)
                icon = "📦" if ws.is_dir else "📄"
                item_type = "Folder (.zip)" if ws.is_dir else "File"

                page = MOBILE_DOWNLOAD_HTML_PAGE.replace("{{ICON}}", icon)\
                                                .replace("{{ITEM_NAME}}", item_name)\
                                                .replace("{{ITEM_SIZE}}", item_size)\
                                                .replace("{{ITEM_TYPE}}", item_type)
                
                self.send_response(200)
                self.send_cors_headers()
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(page.encode('utf-8'))

            elif self.path == '/download':
                try:
                    file_path = ws.serve_path
                    filename = os.path.basename(ws.target_filename)

                    self.send_response(200)
                    self.send_cors_headers()
                    self.send_header('Content-type', 'application/octet-stream')
                    self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                    self.send_header('Content-Length', str(ws.file_size))
                    self.end_headers()

                    sent = 0
                    start_time = time.time()
                    last_update = start_time
                    last_sent = 0

                    with open(file_path, 'rb') as f:
                        while sent < ws.file_size and ws.running:
                            chunk = f.read(config.CHUNK_SIZE_WEB)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            sent += len(chunk)

                            now = time.time()
                            if now - last_update > 0.1:
                                ws.notify_progress(sent, ws.file_size, now - last_update, sent - last_sent)
                                last_update = now
                                last_sent = sent

                    ws.notify_progress(ws.file_size, ws.file_size, max(time.time() - start_time, 0.001), ws.file_size - last_sent)
                    ws.notify_complete(True)

                except Exception as e:
                    ws.notify_complete(False)
                    self.send_error(500, f"Download Error: {e}")
            else:
                self.send_error(404, "Not Found")

    def do_POST(self):
        """Handles HTTP POST requests for receiving mobile file uploads."""
        if hasattr(self.server, 'web_receiver') and self.path == '/upload':
            try:
                raw_relpath = self.headers.get('X-Relative-Path', '')
                rel_path = urllib.parse.unquote(raw_relpath) if raw_relpath else "uploaded_file"
                content_len = int(self.headers.get('Content-Length', 0))

                downloads_dir = self.server.web_receiver.downloads_dir
                parts = rel_path.split('/')
                target_path = os.path.join(downloads_dir, *parts)

                os.makedirs(os.path.dirname(target_path), exist_ok=True)

                received = 0
                start_time = time.time()
                last_update = start_time
                last_received = 0

                with open(target_path, 'wb') as f:
                    while received < content_len and self.server.web_receiver.running:
                        chunk_size = min(config.CHUNK_SIZE_WEB, content_len - received)
                        chunk = self.rfile.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        received += len(chunk)

                        now = time.time()
                        if now - last_update > 0.1:
                            self.server.web_receiver.notify_progress(rel_path, received, content_len, now - last_update, received - last_received)
                            last_update = now
                            last_received = received

                self.server.web_receiver.notify_progress(rel_path, content_len, content_len, max(time.time() - start_time, 0.001), content_len - last_received)
                self.server.web_receiver.notify_complete(target_path)

                self.send_response(200)
                self.send_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "ok"}')

            except Exception as e:
                self.send_error(500, f"Server Error: {e}")
        else:
            self.send_error(404, "Not Found")


class WebReceiver:
    """
    HTTP Web Receiver server enabling mobile browser users to upload files/folders directly to the laptop.
    """
    def __init__(self, port=config.DEFAULT_WEB_PORT, on_status_callback=None, on_progress_callback=None, on_complete_callback=None):
        self.port = port
        self.on_status = on_status_callback
        self.on_progress = on_progress_callback
        self.on_complete = on_complete_callback
        
        self.local_ip = get_local_ip()
        self.url = f"http://{self.local_ip}:{self.port}"
        
        self.running = False
        self.httpd = None
        
        self.downloads_dir = config.DOWNLOADS_DIR
        if not os.path.exists(self.downloads_dir):
            os.makedirs(self.downloads_dir)

    def start(self):
        """Starts the HTTP server on an available port in a background daemon thread."""
        self.running = True
        socketserver.TCPServer.allow_reuse_address = True
        while self.running:
            try:
                self.httpd = socketserver.TCPServer(('0.0.0.0', self.port), DropItHTTPHandler)
                self.httpd.web_receiver = self
                break
            except OSError:
                self.port += 1
                self.url = f"http://{self.local_ip}:{self.port}"
                
        if self.on_status:
            self.on_status(f"Web Receiver active at {self.url}")
            
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def stop(self):
        """Shuts down the HTTP server."""
        self.running = False
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass

    def notify_progress(self, rel_path, received, total, elapsed, bytes_diff):
        """Reports transfer progress percentage and speed metrics."""
        now = time.time()
        if not hasattr(self, '_start_time') or received <= bytes_diff:
            self._start_time = now
            self._peak_bytes_sec = 0.0

        self._last_total_received = received
        self._last_total = total
        total_elapsed = max(now - self._start_time, 0.001)
        cur_bytes_sec = (bytes_diff / elapsed) if elapsed > 0 else 0
        avg_bytes_sec = (received / total_elapsed) if total_elapsed > 0 else 0
        self._peak_bytes_sec = max(getattr(self, '_peak_bytes_sec', 0.0), cur_bytes_sec)

        if self.on_progress:
            percent = (received / total * 100) if total > 0 else 100.0
            cur_speed_str = f"{format_size(cur_bytes_sec)}/s"
            avg_speed_str = f"{format_size(avg_bytes_sec)}/s"
            peak_speed_str = f"{format_size(self._peak_bytes_sec)}/s"
            size_info_str = f"{format_size(received)} / {format_size(total)}"
            self.on_progress(percent, cur_speed_str, avg_speed_str, peak_speed_str, size_info_str)
        if self.on_status:
            self.on_status(f"Receiving {rel_path} ({format_size(received)} / {format_size(total)})")

    def notify_complete(self, filepath):
        """Triggers transfer completion callbacks."""
        if self.on_progress:
            now = time.time()
            total_elapsed = max(now - getattr(self, '_start_time', now), 0.001)
            rec = getattr(self, '_last_total_received', 0)
            tot = getattr(self, '_last_total', 0)
            final_avg = rec / total_elapsed if total_elapsed > 0 else 0
            peak_str = f"{format_size(getattr(self, '_peak_bytes_sec', 0.0))}/s"
            size_str = f"{format_size(rec)} / {format_size(tot)}" if tot > 0 else "--"
            self.on_progress(100.0, "Done", f"{format_size(final_avg)}/s", peak_str, size_str)
        if self.on_status:
            self.on_status(f"Saved: {os.path.basename(filepath)}")
        if self.on_complete:
            self.on_complete(True, filepath)


class WebSender:
    """
    HTTP Web Sender server enabling mobile browser users to download shared files/folders from the laptop.
    Automatically compresses shared folders into temporary ZIP archives in a background thread to keep GUI smooth.
    """
    def __init__(self, shared_path, port=config.DEFAULT_WEB_PORT, on_status_callback=None, on_progress_callback=None, on_complete_callback=None):
        self.shared_path = shared_path
        self.port = port
        self.on_status = on_status_callback
        self.on_progress = on_progress_callback
        self.on_complete = on_complete_callback

        self.local_ip = get_local_ip()
        self.url = f"http://{self.local_ip}:{self.port}"

        self.running = False
        self.ready = False
        self.httpd = None
        self.temp_zip_path = None

        self.is_dir = os.path.isdir(shared_path)

        if self.is_dir:
            base_name = os.path.basename(os.path.normpath(shared_path))
            self.target_filename = f"{base_name}.zip"
            self.serve_path = None
            self.file_size = 0
            self.ready = False
        else:
            self.serve_path = shared_path
            self.target_filename = os.path.basename(shared_path)
            self.file_size = os.path.getsize(shared_path)
            self.ready = True

    def start(self):
        """Starts the HTTP server serving the shared asset on an available port."""
        self.running = True
        socketserver.TCPServer.allow_reuse_address = True
        while self.running:
            try:
                self.httpd = socketserver.TCPServer(('0.0.0.0', self.port), DropItHTTPHandler)
                self.httpd.web_sender = self
                break
            except OSError:
                self.port += 1
                self.url = f"http://{self.local_ip}:{self.port}"

        if self.is_dir:
            def _prepare_zip():
                if self.on_status:
                    self.on_status("Packaging folder for mobile web sharing...")
                try:
                    base_name = os.path.basename(os.path.normpath(self.shared_path))
                    temp_dir = tempfile.gettempdir()
                    zip_path = os.path.join(temp_dir, f"dropit_{base_name}.zip")
                    
                    # Create uncompressed ZIP container (ZIP_STORED) at raw disk speed (~10x-50x faster)
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_STORED) as zipf:
                        for root, dirs, files in os.walk(self.shared_path):
                            for file in files:
                                abs_path = os.path.join(root, file)
                                rel_path = os.path.relpath(abs_path, self.shared_path)
                                zipf.write(abs_path, rel_path)

                    self.temp_zip_path = zip_path
                    self.serve_path = self.temp_zip_path
                    self.file_size = os.path.getsize(self.temp_zip_path)
                    self.ready = True
                    if self.on_status:
                        self.on_status(f"Sharing via Web at {self.url}")
                except Exception as e:
                    if self.on_status:
                        self.on_status(f"Zip Error: {e}")

            threading.Thread(target=_prepare_zip, daemon=True).start()
        else:
            if self.on_status:
                self.on_status(f"Sharing via Web at {self.url}")

        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def stop(self):
        """Shuts down the HTTP server and removes any temporary ZIP archive created for directory sharing."""
        self.running = False
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass
        if self.temp_zip_path and os.path.exists(self.temp_zip_path):
            try:
                os.remove(self.temp_zip_path)
            except Exception:
                pass

    def notify_progress(self, sent, total, elapsed, bytes_diff):
        """Reports transfer progress percentage and transfer speed metrics."""
        now = time.time()
        if not hasattr(self, '_start_time') or sent <= bytes_diff:
            self._start_time = now
            self._peak_bytes_sec = 0.0

        self._last_sent = sent
        total_elapsed = max(now - self._start_time, 0.001)
        cur_bytes_sec = (bytes_diff / elapsed) if elapsed > 0 else 0
        avg_bytes_sec = (sent / total_elapsed) if total_elapsed > 0 else 0
        self._peak_bytes_sec = max(getattr(self, '_peak_bytes_sec', 0.0), cur_bytes_sec)

        if self.on_progress:
            percent = (sent / total * 100) if total > 0 else 100.0
            cur_speed_str = f"{format_size(cur_bytes_sec)}/s"
            avg_speed_str = f"{format_size(avg_bytes_sec)}/s"
            peak_speed_str = f"{format_size(self._peak_bytes_sec)}/s"
            size_info_str = f"{format_size(sent)} / {format_size(total)}"
            self.on_progress(percent, cur_speed_str, avg_speed_str, peak_speed_str, size_info_str)
        if self.on_status:
            self.on_status(f"Sending {self.target_filename} ({format_size(sent)} / {format_size(total)})")

    def notify_complete(self, success):
        """Triggers transfer completion callbacks."""
        if self.on_progress and success:
            now = time.time()
            total_elapsed = max(now - getattr(self, '_start_time', now), 0.001)
            sent = getattr(self, '_last_sent', self.file_size)
            final_avg = sent / total_elapsed if total_elapsed > 0 else 0
            peak_str = f"{format_size(getattr(self, '_peak_bytes_sec', 0.0))}/s"
            size_str = f"{format_size(sent)} / {format_size(self.file_size)}"
            self.on_progress(100.0, "Done", f"{format_size(final_avg)}/s", peak_str, size_str)
        if self.on_status:
            self.on_status("Transfer complete!" if success else "Transfer failed.")
        if self.on_complete:
            self.on_complete(success)
            self.on_complete(success)

