# LocalDrop

LocalDrop is a local network peer-to-peer file and folder sharing tool built with Python and Tkinter. It allows laptops and mobile devices on the same Wi-Fi network to transfer files and complete folder structures securely without needing external cloud services.

## Features
- **Bidirectional Zero-Install Web Sharing (QR Code)**:
  - **Upload to Laptop**: Scan the QR code displayed in the Laptop's Receive mode to upload files or full folder trees from mobile browsers (iPhone or Android).
  - **Download from Laptop**: Scan the QR code displayed in the Laptop's Send mode to download selected files or auto-zipped folder archives directly to your phone.
- **Passcode-based Laptop-to-Laptop Pairing**: Simplifies app-to-app connection using a 4-digit passcode instead of typing IP addresses.
- **Local Network (LAN)**: Transfers files and folders entirely over the local network for maximum speed and privacy.
- **File & Folder Support**: Transfer individual files or complete directory structures with nested subfolders while preserving folder hierarchy (`webkitdirectory` & `.zip` stream support).
- **Large File Support**: Files are streamed in chunks, supporting arbitrarily large files and folders without loading them entirely into memory.
- **Progress Tracking**: Real-time progress bar and overall transfer speed (MB/s).
- **Simple GUI**: Easy-to-use Tkinter interface with tabbed modes for both Sending and Receiving.

## Prerequisites
- Python 3.x
- Optional dependencies for QR code display:
  ```bash
  pip install qrcode pillow
  ```

## How to Run

1. Open a terminal or command prompt in the project directory.
2. Run the main application:
   ```bash
   python main.py
   ```

### 📱 Sharing with Mobile via QR Code (Zero-Install)
- **To Receive from Mobile:** Click **Receive File / Folder** -> select **📱 Mobile (QR Code)** -> Scan the QR code with phone camera -> Upload files or folders from your phone!
- **To Send to Mobile:** Click **Send File / Folder** -> select a file or folder -> select **📱 Mobile (QR Code)** -> Scan the QR code with phone camera -> Tap **Download** on your phone!

### 💻 Laptop-to-Laptop Transfer (Passcode Mode)
- **On Receiver Laptop:** Click **Receive File / Folder** -> select **💻 Laptop (Passcode)** tab to view 4-digit passcode.
- **On Sender Laptop:** Click **Send File / Folder** -> select file/folder -> select **💻 Laptop (Passcode)** tab -> enter passcode -> click **Send Now**.

---

## How it Works (Technical Architecture)

LocalDrop combines three networking modes to achieve seamless cross-device sharing without cloud servers or manual IP setup:

### 1. Zero-Install Mobile Web Server (HTTP + QR Code)
- **QR Code Generation**: Uses `qrcode` and `Pillow` to encode `http://<laptop_local_ip>:8080` into a QR image displayed on the Tkinter canvas.
- **Web Receiver (`POST /upload`)**: Python's `http.server` hosts an embedded mobile HTML5 Web App. Uses `webkitdirectory` to capture relative directory paths (`X-Relative-Path`) and reconstructs nested folder trees on disk inside `Downloads/`.
- **Web Sender (`GET /download`)**: Displays a mobile download interface. For single files, streams raw file bytes. For folders, dynamically packages the directory into a `.zip` archive on-the-fly for single-tap mobile downloads.

### 2. UDP Discovery (Passcode System for Laptops)
- **Receiver**: Generates a random 4-digit passcode and listens for UDP broadcast packets on port 50025.
- **Sender**: Broadcasts a UDP packet to the local subnet containing the passcode (e.g., `LOCALDROP_DISCOVER:1234`).
- **Pairing**: Receiver replies with its IP address and dynamic TCP port (`LOCALDROP_ACCEPT:56789`).

### 3. TCP File & Folder Protocol
- **Header Flags**: Transmits `'F'` for single files or `'D'` for directory trees.
- **Directory Manifest**: Sends entry counts, aggregate size, relative path metadata, and streams chunked file data (16 KB chunks).
- **Disk Reconstruction**: Recreates missing directory trees and streams data directly to disk.
