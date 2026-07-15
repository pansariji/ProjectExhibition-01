import socket
import random
import os

def get_local_ip():
    """
    Attempts to find the local IP address of the machine by connecting to a public DNS.
    This doesn't actually send data, it just sets up the socket to read the local IP.
    """
    try:
        # 10.255.255.255 is a non-routable address, but it forces the socket
        # to pick the active local network interface.
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
        s.close()
    except Exception:
        IP = '127.0.0.1'
    return IP

def generate_passcode():
    """Generates a random 4-digit passcode as a string."""
    return f"{random.randint(0, 9999):04d}"

def format_size(size_in_bytes):
    """Formats a byte count into a human-readable string (KB, MB, GB)."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} PB"
