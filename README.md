# LocalDrop

LocalDrop is a local network peer-to-peer file sharing tool built with Python and Tkinter. It allows two laptops on the same Wi-Fi network to discover each other using a passcode and transfer files securely without needing external cloud services.

## Features
- **Passcode-based pairing**: Simplifies the connection process by using a 4-digit passcode instead of typing IP addresses.
- **Local Network (LAN)**: Transfers files entirely over the local network for speed and privacy.
- **Large File Support**: Files are streamed in chunks, supporting arbitrarily large files without loading them entirely into memory.
- **Progress Tracking**: Real-time progress bar and transfer speed (MB/s).
- **Simple GUI**: Easy-to-use Tkinter interface.

## Prerequisites
- Python 3.x
- No external dependencies required (uses built-in `socket`, `threading`, and `tkinter` modules).

## How to Run

1. Open a terminal or command prompt.
2. Navigate to the directory containing the LocalDrop files.
3. Run the main application:
   ```bash
   python3 main.py
   ```
4. **On the Receiving Computer:**
   - Click "Receive Files".
   - You will be shown a 4-digit passcode. Keep this screen open.
5. **On the Sending Computer:**
   - Run `python3 main.py` on the second computer.
   - Click "Send Files".
   - Select a file you want to transfer.
   - Enter the 4-digit passcode displayed on the receiver's screen.
   - Click "Send".

The file will be transferred and saved in a `Downloads` folder created in the same directory as the script on the receiving computer.

## How it Works (For Viva/Academic Review)

LocalDrop uses a combination of UDP (User Datagram Protocol) and TCP (Transmission Control Protocol) to achieve seamless file transfer without manual IP configuration.

### 1. UDP Discovery (The Passcode System)
- **Receiver**: When set to receive mode, the app generates a random 4-digit passcode and starts listening for UDP broadcast packets on a specific port (50025).
- **Sender**: When sending a file, the app broadcasts a UDP packet to the entire local subnet containing the passcode (e.g., `LOCALDROP_DISCOVER:1234`).
- **Pairing**: If the receiver hears this broadcast and the passcode matches its generated passcode, it replies directly to the sender with its IP address and a dynamically assigned TCP port (e.g., `LOCALDROP_ACCEPT:56789`).

*Why UDP?* UDP supports broadcasting, allowing the sender to shout to all devices on the network "Who has this passcode?" without knowing the receiver's IP address in advance.

### 2. TCP File Transfer
- **Connection**: Once the sender receives the receiver's IP and TCP port from the UDP response, it establishes a dedicated TCP connection.
- **Protocol**: The sender transmits the filename length, the filename itself, and the total file size as headers.
- **Streaming**: The sender reads the file in small chunks (e.g., 8192 bytes) and sends them over the TCP socket. The receiver writes these chunks to disk as they arrive.

*Why TCP?* TCP is connection-oriented and guarantees delivery, order, and error-checking. This ensures the file is transferred reliably without data corruption or missing bytes.

### 3. Threading
Both the sender and receiver use Python's `threading` module to run the networking operations in the background. If this were run on the main thread, the Tkinter GUI would freeze and become unresponsive while waiting for a connection or during a long file transfer.
