Here is a complete, easy-to-understand breakdown of how **LocalDrop** works under the hood, including the exact technologies, networking protocols, and connection workflows it uses.

---

# High-Level Architecture Overview

LocalDrop operates entirely within your **Local Area Network (LAN)** (e.g., your home or office Wi-Fi). No files or data ever leave your Wi-Fi router or go to any cloud server.

LocalDrop uses **two distinct modes of communication**:

1. **Laptop-to-Laptop Mode**: Uses **UDP Broadcast** for automatic device discovery + **TCP Sockets** for direct, high-speed file streaming.
2. **Mobile-to-Laptop / Laptop-to-Mobile Mode**: Uses **HTTP Server** + **QR Codes**, allowing any smartphone (iPhone/Android) to connect via its native Web Browser without installing any app.

---

#  Mode 1: Laptop-to-Laptop (P2P Passcode Transfer)

How do two laptops find each other on Wi-Fi without typing IP addresses?

```
[ Sender Laptop ]                                         [ Receiver Laptop ]
       │                                                         │
       │─── 1. UDP Broadcast ("LOCALDROP_DISCOVER:1234") ───────►│ (Listens on UDP 50025)
       │                                                         │
       │◄── 2. UDP Response  ("LOCALDROP_ACCEPT:56789") ─────────│ (Replies with IP & TCP Port)
       │                                                         │
       │═══ 3. Direct TCP Connection (Port 56789) ──────────────►│ (Streams file/folder bytes)
```

### 1. Discovery Phase (UDP Protocol)
* **Protocol**: **UDP (User Datagram Protocol)** on port `50025`.
* **How it works**:
  - The Receiver Laptop generates a random 4-digit passcode (e.g., `1234`) and listens on UDP port `50025`.
  - The Sender Laptop types `1234` and sends a **UDP Broadcast** packet to `255.255.255.255` (a special address that shouts to *all* devices on the Wi-Fi): `"LOCALDROP_DISCOVER:1234"`.
  - Every device on the Wi-Fi receives the UDP packet, but only the Receiver Laptop matching passcode `1234` answers back: `"LOCALDROP_ACCEPT:<dynamic_tcp_port>"`.
  - Now, the Sender Laptop instantly knows the Receiver's IP address and TCP port!

### 2. Data Transfer Phase (TCP Protocol)
* **Protocol**: **TCP (Transmission Control Protocol)**.
* **Why TCP?**: Unlike UDP, TCP guarantees 100% reliable, error-free delivery of every single byte in exact order.
* **Header Serialization**:
  - The Sender packs metadata (File vs. Folder flag `'F'` or `'D'`, file names, subfolder relative paths, and sizes) into binary headers using Python's `struct` module (`struct.pack('>I', name_len)` and `struct.pack('>Q', total_bytes)`).
* **Chunked Streaming**:
  - Files are read in **8 KB / 16 KB chunks** (`socket.sendall`) and written directly to disk on the receiver end inside `Downloads/`. This ensures even a 10 GB file uses almost no RAM!

---

#  Mode 2: Mobile-to-Laptop & Laptop-to-Mobile (QR Code Web Server)

How does a phone transfer files without installing an app?

```
[ Laptop ]                                                 [ Mobile Phone ]
    │                                                            │
    │─── 1. Displays QR Code (http://192.168.1.5:8080) ─────────►│ (Scans with Camera)
    │                                                            │
    │◄── 2. HTTP GET /  (Requests Web Page) ────────────────────│ (Browser opens web UI)
    │                                                            │
    │◄── 3. HTTP POST /upload  OR  HTTP GET /download ──────────►│ (Uploads/Downloads Data)
```

### 1. QR Code & Web Server Initialization
* **Protocol**: **HTTP over TCP** (default port `8080`).
* **Technologies**: Python's `http.server`, `socketserver`, `qrcode`, and `Pillow`.
* **How it works**:
  - LocalDrop finds the laptop's local Wi-Fi IP address (e.g., `192.168.1.5`).
  - It generates a QR code image encoding `http://192.168.1.5:8080`.
  - Scanning the QR code with an iPhone or Android camera opens the laptop's built-in web server in Safari or Chrome.

### 2. Mobile-to-Laptop Upload (Receiving Mode)
* **Web UI**: Embedded HTML5 + CSS + JavaScript web application served directly from Python string templates.
* **Folder Hierarchy (`webkitdirectory`)**:
  - HTML5 `<input type="file" webkitdirectory>` allows mobile users to select entire folder trees.
  - The mobile browser attaches a custom HTTP Header `X-Relative-Path: MyFolder/Photos/beach.jpg` to each upload request.
* **HTTP POST**: The phone sends HTTP `POST /upload` requests. The Python server parses `X-Relative-Path`, automatically recreates nested folders on disk, and streams the file contents into `Downloads/`.

### 3. Laptop-to-Mobile Download (Sending Mode)
* **Single File**: Mobile opens `GET /download` $\rightarrow$ Laptop responds with `Content-Type: application/octet-stream` and streams file bytes.
* **Folder Packaging (`.zip`)**:
  - Mobile browsers cannot download raw folders natively.
  - When a laptop user shares a folder, Python's `shutil.make_archive` zips the folder on-the-fly in a background temp directory.
  - Tapping **Download** on the phone downloads `MyFolder.zip` cleanly!

---

#  Summary of Technologies & Protocols Used

| Feature / Task | Technology / Library | Protocol / Format |
| :--- | :--- | :--- |
| **GUI Interface** | Python `tkinter` (`ttk`, `Notebook`, `PIL/ImageTk`) | Desktop Native UI |
| **Laptop Discovery** | Python `socket` | **UDP Broadcast** (Port `50025`) |
| **Laptop P2P Transfer** | Python `socket` + `struct` | **TCP Stream** (Binary Metadata Headers) |
| **Mobile Web Server** | Python `http.server` & `socketserver` | **HTTP / 1.1** (Port `8080`) |
| **QR Code Encoding** | `qrcode` & `Pillow` (PIL) | QR Matrix Code (URL string) |
| **Mobile UI & Drag-Drop** | HTML5, CSS3 Glassmorphism, JavaScript XHR | Responsive Web App |
| **Folder Reconstruction** | HTML5 `webkitdirectory` & HTTP Headers | `X-Relative-Path` Header |
| **On-the-fly Zip Packaging**| Python `shutil` & `tempfile` | `.zip` Archive Stream |