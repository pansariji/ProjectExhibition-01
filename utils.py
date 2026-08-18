import socket
import random
import os
import config

def get_local_ip():
    """
    Determines the local IP address of the active network interface.
    Creates a temporary datagram socket toward a public IP range to resolve
    the primary network interface IP without transmitting actual network data.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        pass

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return '127.0.0.1'

def generate_passcode():
    """
    Generates a random 4-digit numeric passcode formatted as a zero-padded string.
    Used for pairing laptop-to-laptop transfers.
    """
    return f"{random.randint(0, 9999):04d}"

def format_size(size_in_bytes):
    """
    Converts a byte count into a formatted human-readable string (B, KB, MB, GB, TB).
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} PB"

def generate_qr_image(url):
    """
    Generates a PIL Image containing a QR code for mobile browser connections.
    Converts output to RGB color space to ensure compatibility with CustomTkinter images.
    """
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
        img = qr.make_image(fill_color=config.COLOR_TEXT_PRIMARY, back_color=config.COLOR_CARD)
        return img.convert('RGB')
    except Exception as e:
        print(f"Failed to generate QR code image: {e}")
        return None

