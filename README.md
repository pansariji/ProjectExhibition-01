# LocalDrop

LocalDrop is a local network peer-to-peer file and folder sharing application built with Python and CustomTkinter. It allows laptops and mobile devices on the same Wi-Fi network to transfer files and complete folder structures securely without needing external cloud services.

## Features
- **Warm Cream Retro-Tech Editorial UI**: Powered by CustomTkinter with rounded paper cards, Space Grotesk and Consolas typography, smooth progress tracking, and a warm cream aesthetic.
- **Bidirectional Zero-Install Web Sharing (QR Code)**:
  - **Upload to Laptop**: Scan the QR code displayed in the Laptop Receive mode to upload files or full folder trees from mobile browsers (iPhone or Android).
  - **Download from Laptop**: Scan the QR code displayed in the Laptop Send mode to download selected files or auto-zipped folder archives directly to your phone.
- **Passcode-based Laptop-to-Laptop Pairing**: Simplifies app-to-app connection using a 4-digit passcode instead of typing IP addresses.
- **Local Network (LAN)**: Transfers files and folders entirely over the local network for maximum speed and privacy.
- **File and Folder Support**: Transfer individual files or complete directory structures with nested subfolders while preserving folder hierarchy (`webkitdirectory` and `.zip` stream support).
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

### Mobile Sharing via QR Code (Zero-Install)
- **To Receive from Mobile:** Click **Receive File or Folder**, select **Mobile QR**, scan the QR code with your phone camera, and upload files or folders from your phone browser.
- **To Send to Mobile:** Click **Send File or Folder**, select a file or folder, select **Mobile QR**, scan the QR code with your phone camera, and tap **Download** on your phone.

### Laptop-to-Laptop Transfer (Passcode Mode)
- **On Receiver Laptop:** Click **Receive File or Folder** and select **Laptop Passcode** tab to view the 4-digit passcode and Receiver IP.
- **On Sender Laptop:** Click **Send File or Folder**, select file or folder, select **Laptop Passcode** tab, enter the passcode, and click **Send Now**.
- **College / Campus Wi-Fi Networks (e.g. VIT Bhopal):**
  - Enterprise Wi-Fi routers block UDP Broadcast packets (`255.255.255.255`) and enable Client Isolation.
  - LocalDrop uses a **Fast Parallel Subnet & ARP Engine** (multi-threaded TCP & UDP probes on port `50026` + system `arp -a` cache inspection) to find peers automatically.
  - **Fallback Options if Subnet Scan Fails**:
    1. **Receiver IP Direct Entry**: Type the Receiver IP (displayed on the Receive screen) into the **Receiver IP (Optional)** field on the Sender screen.
    2. **Mobile QR Mode**: Switch to the **Mobile QR** tab to transfer files via any web browser over port `8080`.
    3. **Mobile Hotspot**: Turn on a Mobile Hotspot on either device (100% reliable bulletproof bypass for campus Wi-Fi AP Isolation running at 50+ MB/s).

---

## Codebase Architecture

LocalDrop is structured as a clean, modular Python application:

```
PE1/
├── .gitignore            # Git exclusion rules (pycache, virtualenvs, Downloads, build outputs)
├── config.py             # Central configuration (Colors, Theme Tokens, Ports, Chunk Sizes, Paths)
├── utils.py              # Utility functions (IP discovery, Passcode, Byte formatting, QR generation)
├── p2p/                  # Laptop-to-Laptop P2P Transfer Engine
│   ├── __init__.py
│   ├── client.py         # P2P Sender (UDP discovery + TCP file/folder streaming)
│   └── server.py         # P2P Receiver (UDP discovery responder + TCP reception)
├── web/                  # Mobile Web Server Module
│   ├── __init__.py
│   ├── server.py         # WebReceiver, WebSender, HTTP Request Handlers
│   └── templates.py      # Mobile HTML/CSS/JS interface templates
├── ui/                   # CustomTkinter UI Views and Components
│   ├── __init__.py
│   ├── home_frame.py     # Home Screen View (Hero card, routing badge, feature tags, action buttons)
│   ├── receive_frame.py  # Receive Screen View (Mobile QR tab and Laptop Passcode tab)
│   └── send_frame.py     # Send Screen View (File/Folder picker, QR tab and Passcode tab)
├── main.py               # Application entry point (~55 lines)
├── README.md             # Project overview and setup instructions
└── workflow.md           # In-depth technical architecture and networking protocol documentation
```
