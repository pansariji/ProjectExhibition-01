# HTML Web Interface served to mobile browsers for UPLOADING (Laptop Receiving) - Warm Cream Retro-Tech Theme
MOBILE_UPLOAD_HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DropIt - Upload to Laptop</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Space Mono', monospace;
            background-color: #f3efe6;
            color: #1c1917;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 24px 16px;
        }
        .card {
            background-color: #faf7f0;
            border: 1px solid #e2dcd0;
            box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.04);
            border-radius: 20px;
            padding: 36px 28px;
            width: 100%;
            max-width: 440px;
            text-align: center;
        }
        .tag-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background-color: #eae4d7;
            color: #15803d;
            font-family: 'Space Mono', monospace;
            font-weight: 700;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 6px 14px;
            border-radius: 100px;
            border: 1px solid #d8d0c0;
            margin-bottom: 20px;
        }
        .tag-pill::before {
            content: '((o))';
            font-size: 10px;
        }
        h1 {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 32px;
            font-weight: 700;
            letter-spacing: -1px;
            margin-bottom: 6px;
            color: #1c1917;
        }
        p.subtitle {
            font-size: 13px;
            color: #78716c;
            font-weight: 400;
            margin-bottom: 30px;
        }
        .btn-group {
            display: flex;
            flex-direction: column;
            gap: 14px;
            margin-bottom: 24px;
        }
        .btn {
            background-color: #1c1917;
            color: #f3efe6;
            border: 1px solid #1c1917;
            border-radius: 100px;
            padding: 16px 24px;
            font-family: 'Space Grotesk', sans-serif;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            text-decoration: none;
            box-shadow: 0px 2px 6px rgba(0,0,0,0.1);
        }
        .btn:active {
            transform: scale(0.98);
        }
        .btn-secondary {
            background-color: #faf7f0;
            color: #1c1917;
            border: 1px solid #d8d0c0;
            box-shadow: none;
        }
        .btn-secondary:hover {
            background-color: #eae4d7;
        }
        input[type="file"] { display: none; }
        .drop-zone {
            border: 2px dashed #d8d0c0;
            border-radius: 16px;
            padding: 24px 16px;
            margin-bottom: 20px;
            background-color: #f3efe6;
            transition: border-color 0.2s ease;
        }
        .drop-zone.active {
            border-color: #15803d;
            background-color: #e8f5e9;
        }
        .progress-box {
            display: none;
            margin-top: 20px;
            text-align: left;
            border-top: 1px solid #e2dcd0;
            padding-top: 20px;
        }
        .progress-bar-bg {
            background-color: #e2dcd0;
            border-radius: 100px;
            height: 10px;
            margin: 12px 0;
            overflow: hidden;
        }
        .progress-bar-fill {
            background-color: #15803d;
            height: 100%;
            width: 0%;
            border-radius: 100px;
            transition: width 0.1s linear;
        }
        .status-text {
            font-size: 12px;
            font-weight: 700;
            color: #1c1917;
        }
        .speed-text {
            font-size: 12px;
            font-weight: 700;
            color: #15803d;
            float: right;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="tag-pill">LAN ROUTE ACTIVE</div>
        <h1>DropIt</h1>
        <p class="subtitle">Upload files directly to laptop</p>

        <div class="drop-zone" id="dropZone">
            <div class="btn-group">
                <button class="btn" onclick="document.getElementById('fileInput').click()">
                    📄 Select File(s)
                </button>
                <button class="btn btn-secondary" onclick="document.getElementById('folderInput').click()">
                    📁 Select Folder
                </button>
            </div>
            <p style="font-size: 11px; color: #78716c;">or drag & drop anywhere inside</p>
        </div>

        <input type="file" id="fileInput" multiple onchange="handleSelection(this.files)">
        <input type="file" id="folderInput" webkitdirectory directory multiple onchange="handleSelection(this.files)">

        <div class="progress-box" id="progressBox">
            <span class="status-text" id="statusLabel">Preparing transfer...</span>
            <span class="speed-text" id="speedLabel">0 KB/s</span>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" id="progressBar"></div>
            </div>
            <div style="font-size: 11px; color: #78716c; margin-top: 4px;" id="countLabel"></div>
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
                        if (xhr.status === 200) {
                            uploadedBytes += file.size;
                            let percent = totalBytes > 0 ? (uploadedBytes / totalBytes) * 100 : 100;
                            document.getElementById('progressBar').style.width = percent.toFixed(1) + '%';
                            resolve();
                        } else reject(new Error('Upload failed'));
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

# HTML Web Interface served to mobile browsers for DOWNLOADING (Laptop Sending) - Warm Cream Retro-Tech Theme
MOBILE_DOWNLOAD_HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DropIt - Download File</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Space Mono', monospace;
            background-color: #f3efe6;
            color: #1c1917;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 24px 16px;
        }
        .card {
            background-color: #faf7f0;
            border: 1px solid #e2dcd0;
            box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.04);
            border-radius: 20px;
            padding: 36px 28px;
            width: 100%;
            max-width: 440px;
            text-align: center;
        }
        .tag-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background-color: #eae4d7;
            color: #15803d;
            font-family: 'Space Mono', monospace;
            font-weight: 700;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 6px 14px;
            border-radius: 100px;
            border: 1px solid #d8d0c0;
            margin-bottom: 20px;
        }
        .tag-pill::before {
            content: '((o))';
            font-size: 10px;
        }
        h1 {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 32px;
            font-weight: 700;
            letter-spacing: -1px;
            margin-bottom: 6px;
            color: #1c1917;
        }
        p.subtitle {
            font-size: 13px;
            color: #78716c;
            font-weight: 400;
            margin-bottom: 24px;
        }
        .file-card {
            background-color: #f3efe6;
            border: 1px solid #d8d0c0;
            border-radius: 16px;
            padding: 24px 16px;
            margin-bottom: 28px;
            word-break: break-all;
        }
        .file-icon {
            font-size: 40px;
            margin-bottom: 10px;
        }
        .file-name {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 18px;
            font-weight: 700;
            color: #1c1917;
            margin-bottom: 4px;
        }
        .file-size {
            font-size: 13px;
            font-weight: 700;
            color: #15803d;
        }
        .btn {
            background-color: #1c1917;
            color: #f3efe6;
            border: 1px solid #1c1917;
            border-radius: 100px;
            padding: 18px 24px;
            font-family: 'Space Grotesk', sans-serif;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            text-decoration: none;
            width: 100%;
            box-shadow: 0px 4px 12px rgba(0,0,0,0.1);
        }
        .btn:active {
            transform: scale(0.98);
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="tag-pill">DOWNLOAD READY</div>
        <h1>DropIt</h1>
        <p class="subtitle">Download shared item to your device</p>

        <div class="file-card">
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
