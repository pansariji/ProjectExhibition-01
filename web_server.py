import http.server
import socketserver
import threading
import urllib.parse
import os
import time
import json
import shutil
import tempfile
from utils import get_local_ip, format_size

# HTML Web Interface served to mobile browsers for UPLOADING (Laptop Receiving)
MOBILE_UPLOAD_HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LocalDrop - Upload to Laptop</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #f8fafc;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .card {
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            padding: 32px 24px;
            width: 100%;
            max-width: 420px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
            text-align: center;
        }
        h1 {
            font-size: 26px;
            font-weight: 700;
            margin-bottom: 8px;
            background: linear-gradient(90deg, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        p.subtitle {
            font-size: 14px;
            color: #94a3b8;
            margin-bottom: 30px;
        }
        .btn-group {
            display: flex;
            flex-direction: column;
            gap: 14px;
            margin-bottom: 24px;
        }
        .btn {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: #fff;
            border: none;
            border-radius: 14px;
            padding: 16px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
            text-decoration: none;
        }
        .btn:hover, .btn:active {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(37, 99, 235, 0.5);
        }
        .btn-folder {
            background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%);
            box-shadow: 0 4px 12px rgba(109, 40, 217, 0.3);
        }
        input[type="file"] { display: none; }
        .drop-zone {
            border: 2px dashed rgba(255, 255, 255, 0.2);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 24px;
            background: rgba(15, 23, 42, 0.4);
        }
        .drop-zone.active {
            border-color: #38bdf8;
            background: rgba(56, 189, 248, 0.1);
        }
        .progress-box {
            display: none;
            margin-top: 20px;
            text-align: left;
        }
        .progress-bar-bg {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            height: 12px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-bar-fill {
            background: linear-gradient(90deg, #38bdf8, #4f46e5);
            height: 100%;
            width: 0%;
            transition: width 0.1s linear;
        }
        .status-text {
            font-size: 13px;
            color: #cbd5e1;
            margin-top: 6px;
        }
        .speed-text {
            font-size: 12px;
            color: #38bdf8;
            float: right;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>LocalDrop</h1>
        <p class="subtitle">Upload Files & Folders to Laptop</p>

        <div class="drop-zone" id="dropZone">
            <div class="btn-group">
                <button class="btn" onclick="document.getElementById('fileInput').click()">
                    📄 Select File(s)
                </button>
                <button class="btn btn-folder" onclick="document.getElementById('folderInput').click()">
                    📁 Select Folder
                </button>
            </div>
            <p style="font-size: 12px; color: #64748b;">Or drag and drop items here</p>
        </div>

        <input type="file" id="fileInput" multiple onchange="handleSelection(this.files)">
        <input type="file" id="folderInput" webkitdirectory directory multiple onchange="handleSelection(this.files)">

        <div class="progress-box" id="progressBox">
            <span class="status-text" id="statusLabel">Preparing...</span>
            <span class="speed-text" id="speedLabel">0 KB/s</span>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" id="progressBar"></div>
            </div>
            <div style="font-size: 12px; color: #94a3b8;" id="countLabel"></div>
        </div>
    </div>

    <script>
        const dropZone = document.getElementById('dropZone');

        ['dragenter', 'dragover'].forEach(name => {
            dropZone.addEventListener(name, (e) => { e.preventDefault(); dropZone.classList.add('active'); });
        });
        ['dragleave', 'drop'].forEach(name => {
            dropZone.addEventListener(name, (e) => { e.preventDefault(); dropZone.classList.remove('active'); });
        });

        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) handleSelection(files);
        });

        async function handleSelection(fileList) {
            if (!fileList || fileList.length === 0) return;
            const files = Array.from(fileList);

            document.getElementById('progressBox').style.display = 'block';
            
            let totalBytes = files.reduce((acc, f) => acc + f.size, 0);
            let uploadedBytes = 0;
            let startTime = Date.now();
            let lastTime = startTime;
            let lastUploaded = 0;

            for (let i = 0; i < files.length; i++) {
                let file = files[i];
                let relPath = file.webkitRelativePath || file.name;

                document.getElementById('statusLabel').textContent = `Uploading (${i + 1}/${files.length}): ${file.name}`;
                document.getElementById('countLabel').textContent = `${i + 1} of ${files.length} items processed`;

                await new Promise((resolve, reject) => {
                    let xhr = new XMLHttpRequest();
                    xhr.open('POST', '/upload', true);
                    xhr.setRequestHeader('X-Relative-Path', encodeURIComponent(relPath));

                    xhr.upload.onprogress = (e) => {
                        let currentUploaded = uploadedBytes + e.loaded;
                        let percent = totalBytes > 0 ? (currentUploaded / totalBytes) * 100 : 100;
                        document.getElementById('progressBar').style.width = percent.toFixed(1) + '%';

                        let now = Date.now();
                        if (now - lastTime > 300) {
                            let elapsed = (now - lastTime) / 1000;
                            let bytesSec = (currentUploaded - lastUploaded) / elapsed;
                            document.getElementById('speedLabel').textContent = formatSize(bytesSec) + '/s';
                            lastTime = now;
                            lastUploaded = currentUploaded;
                        }
                    };

                    xhr.onload = () => {
                        if (xhr.status === 200) resolve();
                        else reject(new Error('Upload failed'));
                    };
                    xhr.onerror = () => reject(new Error('Network error'));
                    xhr.send(file);
                });

                uploadedBytes += file.size;
            }

            document.getElementById('progressBar').style.width = '100%';
            document.getElementById('statusLabel').textContent = '✅ Transfer Complete!';
            document.getElementById('speedLabel').textContent = 'Done';
        }

        function formatSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
    </script>
</body>
</html>
"""

# HTML Web Interface served to mobile browsers for DOWNLOADING (Laptop Sending)
MOBILE_DOWNLOAD_HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LocalDrop - Download File</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #f8fafc;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .card {
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            padding: 32px 24px;
            width: 100%;
            max-width: 420px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
            text-align: center;
        }
        h1 {
            font-size: 26px;
            font-weight: 700;
            margin-bottom: 8px;
            background: linear-gradient(90deg, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        p.subtitle {
            font-size: 14px;
            color: #94a3b8;
            margin-bottom: 24px;
        }
        .file-info {
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 24px;
            word-break: break-all;
        }
        .file-icon {
            font-size: 40px;
            margin-bottom: 10px;
        }
        .file-name {
            font-size: 18px;
            font-weight: 600;
            color: #f8fafc;
            margin-bottom: 6px;
        }
        .file-size {
            font-size: 13px;
            color: #38bdf8;
        }
        .btn {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: #fff;
            border: none;
            border-radius: 14px;
            padding: 16px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
            text-decoration: none;
            width: 100%;
        }
        .btn:hover, .btn:active {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(16, 185, 129, 0.5);
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>LocalDrop</h1>
        <p class="subtitle">Download Item from Laptop</p>

        <div class="file-info">
            <div class="file-icon">{{ICON}}</div>
            <div class="file-name">{{ITEM_NAME}}</div>
            <div class="file-size">{{ITEM_SIZE}}</div>
        </div>

        <a class="btn" href="/download" download>
            📥 Download {{ITEM_TYPE}}
        </a>
    </div>
</body>
</html>
"""

class LocalDropHTTPHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        # Receiver Mode (Mobile Uploads to Laptop)
        if hasattr(self.server, 'web_receiver'):
            if self.path == '/' or self.path == '/index.html':
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(MOBILE_UPLOAD_HTML_PAGE.encode('utf-8'))
            else:
                self.send_error(404, "Not Found")
                
        # Sender Mode (Mobile Downloads from Laptop)
        elif hasattr(self.server, 'web_sender'):
            ws = self.server.web_sender
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
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(page.encode('utf-8'))

            elif self.path == '/download':
                try:
                    file_path = ws.serve_path
                    filename = os.path.basename(ws.target_filename)

                    self.send_response(200)
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
                            chunk = f.read(16384)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            sent += len(chunk)

                            now = time.time()
                            if now - last_update > 0.1:
                                ws.notify_progress(sent, ws.file_size, now - last_update, sent - last_sent)
                                last_update = now
                                last_sent = sent

                    ws.notify_complete(True)

                except Exception as e:
                    ws.notify_complete(False)
                    self.send_error(500, f"Download Error: {e}")
            else:
                self.send_error(404, "Not Found")

    def do_POST(self):
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
                        chunk_size = min(16384, content_len - received)
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

                self.server.web_receiver.notify_complete(target_path)

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "ok"}')

            except Exception as e:
                self.send_error(500, f"Server Error: {e}")
        else:
            self.send_error(404, "Not Found")

class WebReceiver:
    def __init__(self, port=8080, on_status_callback=None, on_progress_callback=None, on_complete_callback=None):
        self.port = port
        self.on_status = on_status_callback
        self.on_progress = on_progress_callback
        self.on_complete = on_complete_callback
        
        self.local_ip = get_local_ip()
        self.url = f"http://{self.local_ip}:{self.port}"
        
        self.running = False
        self.httpd = None
        
        self.downloads_dir = os.path.join(os.getcwd(), "Downloads")
        if not os.path.exists(self.downloads_dir):
            os.makedirs(self.downloads_dir)

    def start(self):
        self.running = True
        while self.running:
            try:
                self.httpd = socketserver.TCPServer(('0.0.0.0', self.port), LocalDropHTTPHandler)
                self.httpd.web_receiver = self
                break
            except OSError:
                self.port += 1
                self.url = f"http://{self.local_ip}:{self.port}"
                
        if self.on_status:
            self.on_status(f"Web Receiver active at {self.url}")
            
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def stop(self):
        self.running = False
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except:
                pass

    def notify_progress(self, rel_path, received, total, elapsed, bytes_diff):
        if self.on_progress:
            percent = (received / total * 100) if total > 0 else 100.0
            bytes_sec = (bytes_diff / elapsed) if elapsed > 0 else 0
            speed_str = f"{format_size(bytes_sec)}/s"
            self.on_progress(percent, speed_str)
        if self.on_status:
            self.on_status(f"Receiving {rel_path} ({format_size(received)} / {format_size(total)})")

    def notify_complete(self, filepath):
        if self.on_status:
            self.on_status(f"Saved: {os.path.basename(filepath)}")
        if self.on_complete:
            self.on_complete(True, filepath)


class WebSender:
    def __init__(self, shared_path, port=8080, on_status_callback=None, on_progress_callback=None, on_complete_callback=None):
        self.shared_path = shared_path
        self.port = port
        self.on_status = on_status_callback
        self.on_progress = on_progress_callback
        self.on_complete = on_complete_callback

        self.local_ip = get_local_ip()
        self.url = f"http://{self.local_ip}:{self.port}"

        self.running = False
        self.httpd = None
        self.temp_zip_path = None

        self.is_dir = os.path.isdir(shared_path)

        if self.is_dir:
            base_name = os.path.basename(os.path.normpath(shared_path))
            temp_dir = tempfile.gettempdir()
            zip_base = os.path.join(temp_dir, f"localdrop_{base_name}")
            self.temp_zip_path = shutil.make_archive(zip_base, 'zip', shared_path)
            self.serve_path = self.temp_zip_path
            self.target_filename = f"{base_name}.zip"
            self.file_size = os.path.getsize(self.temp_zip_path)
        else:
            self.serve_path = shared_path
            self.target_filename = os.path.basename(shared_path)
            self.file_size = os.path.getsize(shared_path)

    def start(self):
        self.running = True
        while self.running:
            try:
                self.httpd = socketserver.TCPServer(('0.0.0.0', self.port), LocalDropHTTPHandler)
                self.httpd.web_sender = self
                break
            except OSError:
                self.port += 1
                self.url = f"http://{self.local_ip}:{self.port}"

        if self.on_status:
            self.on_status(f"Sharing via Web at {self.url}")

        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def stop(self):
        self.running = False
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except:
                pass
        if self.temp_zip_path and os.path.exists(self.temp_zip_path):
            try:
                os.remove(self.temp_zip_path)
            except:
                pass

    def notify_progress(self, sent, total, elapsed, bytes_diff):
        if self.on_progress:
            percent = (sent / total * 100) if total > 0 else 100.0
            bytes_sec = (bytes_diff / elapsed) if elapsed > 0 else 0
            speed_str = f"{format_size(bytes_sec)}/s"
            self.on_progress(percent, speed_str)
        if self.on_status:
            self.on_status(f"Sending {self.target_filename} ({format_size(sent)} / {format_size(total)})")

    def notify_complete(self, success):
        if self.on_status:
            self.on_status("Transfer complete!" if success else "Transfer failed.")
        if self.on_complete:
            self.on_complete(success)


def generate_qr_image(url):
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=5,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        return img
    except Exception as e:
        print(f"Failed to generate QR code image: {e}")
        return None
