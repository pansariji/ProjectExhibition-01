# DropIt Architecture & Networking Workflow Specification

DropIt is a modular, zero-cloud peer-to-peer file and folder sharing application built with Python, CustomTkinter, and HTTP/TCP networking. It enables high-speed transfers between computers and mobile devices connected to the same local network without third-party servers or external cloud connectivity.

---

## 🏛️ Codebase Module Organization

The application is structured into decoupled, single-responsibility modules:

- **`config.py`**: Central configuration store defining visual tokens (Warm Cream Editorial Palette), default ports (UDP `50025`, P2P `50026`, Web `8080`), buffer chunk sizes (`65536` bytes), and system storage paths.
- **`utils.py`**: Helper utilities providing LAN IP auto-detection, 4-digit numeric passcode generation, byte size formatting, QR code rendering, and PyInstaller asset path resolution (`get_resource_path`).
- **`p2p/` Package**:
  - **`p2p/client.py`**: P2P Sender engine executing UDP broadcast discovery and TCP socket file/folder streaming.
  - **`p2p/server.py`**: P2P Receiver engine managing UDP discovery responses, passcode validation, and incoming TCP socket binary streams.
- **`web/` Package**:
  - **`web/server.py`**: Embedded HTTP server (`DropItHTTPHandler`, `WebReceiver`, `WebSender`) with preflight OPTIONS and CORS header compliance.
  - **`web/templates.py`**: Mobile HTML5, CSS3, and JavaScript templates for zero-install browser uploads and downloads.
- **`ui/` Package**:
  - **`ui/home_frame.py`**: Renders the main dashboard, hero brand card, and route navigation buttons.
  - **`ui/receive_frame.py`**: Manages reception workflow for Mobile QR and Laptop Passcode modes.
  - **`ui/send_frame.py`**: Manages send workflow for File/Folder selection, Mobile QR, and Laptop Passcode modes.
- **`main.py`**: Application entry point controlling CustomTkinter initialization, window icons, and view frame switching.

---

## 📡 Networking Protocols & Operation Modes

### Mode 1: Laptop-to-Laptop Transfer (P2P Passcode Pairing)

This mode handles direct laptop-to-laptop transfers using TCP socket streams over local network ports.

#### 1. Discovery Phase (UDP Broadcast)
- **Receiver State**: Generates a 4-digit passcode, starts a TCP listener on port `50026`, and binds a UDP socket to port `50025`.
- **Sender State**: Transmits a UDP broadcast packet (`DROPIT_DISCOVER:passcode`) to `255.255.255.255`.
- **Response**: When the receiver's UDP listener detects a matching passcode, it returns `DROPIT_ACCEPT` containing its local IP address.

#### 2. Enterprise / Campus Wi-Fi AP Isolation Handling
- Enterprise Wi-Fi routers often drop UDP broadcast packets and block peer scanning between wireless stations.
- **Direct Unicast Bypass**: DropIt allows entering the Receiver IP directly in the Sender screen, bypassing UDP broadcast discovery entirely and connecting via unicast TCP.

#### 3. Binary Data Transfer Phase (TCP Socket Stream)
- **Protocol Headers**: Metadata is serialized using Python's `struct` module:
  - Item Type Flag (`'F'` for single file, `'D'` for directory).
  - Item Name & Total Byte Size.
  - Subfolder Entry Count & Relative Path strings.
- **High-Throughput Chunking**: File contents stream in **64 KB (`65536` bytes)** chunks.
- **Directory Hierarchy Reconstruction**: DropIt recursively traverses directories, sends relative folder markers, and recreates nested folder trees inside the recipient's `Downloads` folder.

---

### Mode 2: Mobile Browser Web Sharing (Zero-Install QR Code)

This mode allows any mobile device (iOS/Android) to exchange files with a laptop through a standard web browser without installing an app.

#### 1. Connection Phase (QR Code)
- DropIt resolves the laptop's LAN IP address, initializes an HTTP server on port `8080`, and generates a QR code pointing to `http://<LAPTOP_IP>:8080`.
- Scanning the QR code opens the DropIt mobile web interface in Chrome, Brave, Opera, Safari, or Firefox.

#### 2. Universal Browser & CORS Compliance
- **CORS Headers**: All HTTP responses include `Access-Control-Allow-Origin: *` to prevent privacy-focused browsers (Brave Shields, Opera) from blocking local IP requests.
- **Preflight OPTIONS Handler**: Implements `do_OPTIONS` to handle browser preflight checks before processing file uploads.

#### 3. Mobile to Laptop Uploads (Web Receiver)
- Mobile browsers post files to `/upload` using JavaScript `XMLHttpRequest` with custom `X-Relative-Path` headers.
- DropIt streams the incoming request body directly to disk, creating nested subdirectories automatically.

#### 4. Laptop to Mobile Downloads (Web Sender)
- **Single File Download**: Streams the file via HTTP GET to `/download` with an `application/octet-stream` header.
- **Folder Download**: Dynamically compresses directory trees into a temporary ZIP archive using Python's `shutil` module, enabling single-tap folder downloads on mobile devices.

---

## ⚡ Performance Optimization & Memory Management

- **Chunked Socket I/O**: Operating on 64 KB buffer chunks minimizes Python function call overhead and allows local Wi-Fi / Hotspot transfers to peak at **50–90 MB/s**.
- **Constant Memory Footprint**: Files are streamed directly between disk and network sockets, ensuring RAM usage remains flat regardless of transferred file size (e.g. 50 MB or 20 GB).
- **Sub-Millisecond Progress Dispatch**: Forces explicit 100% progress events upon transfer completion to guarantee smooth UI progress bar representation on instant small file transfers.

---

## ⚙️ Automated CI/CD & Build Pipeline

DropIt integrates GitHub Actions (`.github/workflows/build.yml`) for automated building:
1. **Runner Environment**: Windows Server 2022 runner VM.
2. **Dependency Resolution**: Installs dependencies from `requirements.txt`.
3. **PyInstaller Packaging**: Executes `pyinstaller --onefile --windowed` bundling static assets (`assets/logo.ico`, `assets/logo.png`).
4. **Artifact Distribution**: Uploads the resulting `DropIt.exe` binary directly to GitHub Release artifacts.