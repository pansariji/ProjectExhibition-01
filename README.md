# LocalDrop

LocalDrop is a local network peer-to-peer file and folder sharing tool built with Python and **CustomTkinter**. It allows laptops and mobile devices on the same Wi-Fi network to transfer files and complete folder structures securely without needing external cloud services.

## Features
- **Modern Dark UI**: Powered by `CustomTkinter` with rounded cards, smooth progress tracking, and clean dark mode theme.
- **Bidirectional Zero-Install Web Sharing (QR Code)**:
  - **Upload to Laptop**: Scan the QR code displayed in the Laptop's Receive mode to upload files or full folder trees from mobile browsers (iPhone or Android).
  - **Download from Laptop**: Scan the QR code displayed in the Laptop's Send mode to download selected files or auto-zipped folder archives directly to your phone.
- **Passcode-based Laptop-to-Laptop Pairing**: Simplifies app-to-app connection using a 4-digit passcode instead of typing IP addresses.
- **Local Network (LAN)**: Transfers files and folders entirely over the local network for maximum speed and privacy.
- **File & Folder Support**: Transfer individual files or complete directory structures with nested subfolders while preserving folder hierarchy (`webkitdirectory` & `.zip` stream support).
- **Large File Support**: Files are streamed in chunks, supporting arbitrarily large files and folders without loading them entirely into memory.

## Prerequisites
- Python 3.x
- Required dependencies:
  ```bash
  pip install customtkinter qrcode pillow
  ```

## How to Run

1. Open a terminal or command prompt in the project directory.
2. Run the main application:
   ```bash
   python main.py
   ```

### 📱 Sharing with Mobile via QR Code (Zero-Install)
- **To Receive from Mobile:** Click **Receive File or Folder** -> select **📱 Mobile (QR Code)** -> Scan the QR code with phone camera -> Upload files or folders from your phone!
- **To Send to Mobile:** Click **Send File or Folder** -> select a file or folder -> select **📱 Mobile (QR Code)** -> Scan the QR code with phone camera -> Tap **Download** on your phone!

### 💻 Laptop-to-Laptop Transfer (Passcode Mode)
- **On Receiver Laptop:** Click **Receive File or Folder** -> select **💻 Laptop (Passcode)** tab to view 4-digit passcode.
- **On Sender Laptop:** Click **Send File or Folder** -> select file/folder -> select **💻 Laptop (Passcode)** tab -> enter passcode -> click **Send Now**.

---

## Technical Architecture

LocalDrop combines three networking modes to achieve seamless cross-device sharing without cloud servers or manual IP setup:

### 1. Modern Desktop GUI (`customtkinter`)
- CustomTkinter dark mode theme (`ctk.set_appearance_mode("Dark")`).
- Tabbed navigation cards (`CTkTabview`), smooth progress bars (`CTkProgressBar`), and dynamic PIL image rendering (`CTkImage`).

### 2. Zero-Install Mobile Web Server (HTTP + QR Code)
- **QR Code Generation**: Uses `qrcode` and `Pillow` to encode `http://<laptop_local_ip>:8080` into a QR image.
- **Web Receiver (`POST /upload`)**: Python's `http.server` hosts an embedded mobile HTML5 Web App. Uses `webkitdirectory` to capture relative directory paths (`X-Relative-Path`) and reconstructs nested folder trees on disk inside `Downloads/`.
- **Web Sender (`GET /download`)**: Displays a mobile download interface. For single files, streams raw file bytes. For folders, dynamically packages the directory into a `.zip` archive on-the-fly for single-tap mobile downloads.

### 3. UDP Discovery & TCP Streaming (Laptop-to-Laptop)
- **UDP Broadcast**: Passcode discovery on port 50025.
- **TCP Data Streaming**: Binary header serialization (`struct`), chunked byte streaming, and relative folder tree reconstruction.
