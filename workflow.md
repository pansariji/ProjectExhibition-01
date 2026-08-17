# LocalDrop System Architecture and Workflow

LocalDrop is a local network peer-to-peer file and folder sharing application built with Python and CustomTkinter. It enables direct, secure transfers between laptops and mobile devices on the same Wi-Fi network without requiring cloud servers, internet access, or third-party user accounts.

---

# Modular Codebase Structure

The application is organized into clean, dedicated Python packages and modules:

- **.gitignore**: Excludes Python bytecode caches (`__pycache__`, `*.pyc`), virtual environments (`.venv/`), PyInstaller build outputs (`build/`, `dist/`), OS files (`.DS_Store`, `Thumbs.db`), received files (`Downloads/`), and temporary zip archives (`*.zip`).
- **config.py**: Holds all global configuration tokens, network ports (UDP 50025, Web 8080), theme colors (Warm Cream Retro-Tech palette), chunk sizes, and default paths.
- **utils.py**: Contains network IP discovery, 4-digit passcode generation, human-readable file size formatting, and QR code image generation.
- **p2p/ Package**: 
  - `p2p/client.py`: Handles laptop discovery via UDP broadcast and direct TCP socket file/folder streaming.
  - `p2p/server.py`: Manages UDP broadcast listening, passcode validation, and incoming TCP data reception.
- **web/ Package**: 
  - `web/templates.py`: Contains HTML, CSS, and JavaScript templates served to mobile devices.
  - `web/server.py`: Implements HTTP web server handlers, WebReceiver for mobile uploads, and WebSender for mobile downloads.
- **ui/ Package**:
  - `ui/home_frame.py`: Renders the main dashboard, hero card, feature badges, and primary action buttons.
  - `ui/receive_frame.py`: Manages the Receive view with Mobile QR and Laptop Passcode tabs.
  - `ui/send_frame.py`: Manages the Send view with file/folder selection, Mobile QR, and Laptop Passcode tabs.
- **main.py**: The main entry point that initializes CustomTkinter and controls view transitions.

---

# Networking Protocols and Transfer Modes

LocalDrop supports two distinct modes of operation depending on the target device type.

## Mode 1: Laptop to Laptop (P2P Passcode Pairing)

This mode allows two computers running LocalDrop to discover each other and transfer data automatically over local sockets without requiring IP address entry.

### Discovery Stage (UDP Broadcast & Automatic Subnet Unicast Scan)
- Protocol: UDP (port 50025) & TCP (default port 50026).
- The receiving laptop generates a random 4-digit passcode, binds TCP server to port 50026, and listens on UDP port 50025.
- **Standard Discovery (UDP Broadcast):** The sending laptop sends a broadcast packet containing `LOCALDROP_DISCOVER:passcode` to `255.255.255.255` and local subnet broadcast.
- **Enterprise / Campus Wi-Fi Mode (Fast Parallel ARP + TCP + UDP Subnet Engine):**
  - Enterprise Wi-Fi networks (such as VIT Bhopal) block UDP Broadcast packets (`255.255.255.255`) and turn on AP Isolation.
  - If UDP Broadcast gets no response within 0.8 seconds, LocalDrop automatically switches to the **Fast Parallel Subnet & ARP Engine**:
    1. **ARP Cache Inspection**: Parses system `arp -a` cache to instantly locate active local neighbor IPs across all subnets/VLANs.
    2. **Multi-Threaded Dual Probing**: Dispatches 60 concurrent worker threads sending parallel UDP unicast probes and TCP probes directly to `DEFAULT_P2P_PORT` (50026).
  - When the matching receiver responds, discovery completes automatically.
- **Emergency Manual IP Fallback & Hotspot Alternative:**
  - If university router AP Isolation completely blocks inter-device packets, the user can:
    1. Enter the Receiver IP into the **Receiver IP (Optional)** input box.
    2. Use **Mobile QR Mode** over port 8080.
    3. Turn on a **Mobile Hotspot** on either device (100% bulletproof bypass for campus Wi-Fi AP Isolation running at 50+ MB/s).

### Data Transfer Stage (TCP Streaming)
- Protocol: Direct TCP socket stream.
- Binary Headers: Python's `struct` module serializes metadata headers including item type flags ('F' for single file, 'D' for directory), folder names, entry counts, relative paths, and sizes.
- Chunked Data Stream: File contents are read and transmitted in 8 KB chunks. This keeps memory consumption minimal regardless of file or folder size.
- Directory Reconstruction: For folder transfers, LocalDrop recursively walks the directory structure, sends empty directory markers and relative file paths, and recreates the full folder tree inside the recipient's Downloads folder.

---

## Mode 2: Mobile Browser Web Sharing (Zero-Install QR Code)

This mode allows smartphones (iOS and Android) to exchange files with a laptop through a web browser, requiring no app installation on the phone.

### Connection Stage (QR Code)
- Protocol: HTTP over TCP (default port 8080).
- LocalDrop determines the laptop's local IP address and launches an HTTP server.
- It generates a QR code containing the web server URL (for example, `http://192.168.1.5:8080`).
- Scanning the QR code opens the mobile interface directly in Safari or Chrome.

### Mobile to Laptop Uploads (Web Receiver)
- The laptop serves an embedded HTML5 web application with drag-and-drop file selection and folder picker support (`webkitdirectory`).
- Mobile browsers send files via HTTP POST requests to `/upload` with a custom `X-Relative-Path` header specifying the file's relative path within a directory structure.
- The laptop HTTP handler parses the header, creates necessary parent directories in the Downloads folder, and streams incoming payload bytes directly to disk.

### Laptop to Mobile Downloads (Web Sender)
- Single Files: Tapping download sends an HTTP GET request to `/download`. The laptop serves the file with an `application/octet-stream` header.
- Folder Downloads: Since mobile browsers cannot directly download uncompressed folder trees, LocalDrop dynamically creates a `.zip` archive in a temporary directory using Python's `shutil` module, serving the zipped directory for a single-tap download.

---

# Technology Stack Summary

- **User Interface**: Python CustomTkinter (Light mode, Warm Cream Editorial Retro-Tech theme).
- **Desktop Discovery**: Python socket module using UDP Broadcast on port 50025.
- **Desktop Data Transfer**: Python socket and struct modules using binary TCP streams.
- **Mobile Web Server**: Python http.server and socketserver hosting HTTP endpoints on port 8080.
- **QR Code Rendering**: qrcode and Pillow (PIL) libraries.
- **Mobile Web Interface**: HTML5, CSS3, JavaScript XHR with upload progress tracking.
- **Archive Generation**: Python shutil and tempfile modules for ZIP archive creation.