import os

# CustomTkinter Appearance Settings
APPEARANCE_MODE = "Light"
COLOR_THEME = "blue"

# Visual Theme Tokens (Warm Cream Editorial Palette)
COLOR_BG = "#f3efe6"            # Main application background
COLOR_CARD = "#faf7f0"          # Card surface background
COLOR_CARD_ALT = "#eae4d7"      # Secondary card fill
COLOR_BORDER = "#e2dcd0"        # Card border color
COLOR_TEXT_PRIMARY = "#1c1917"  # High-contrast primary text
COLOR_TEXT_MUTED = "#78716c"    # Secondary muted text
COLOR_GREEN = "#15803d"         # Active routing and success status indicator
COLOR_GREEN_HOVER = "#166534"   # Hover state for green buttons

# Button Styling Tokens
COLOR_BTN_PRIMARY_BG = "#1c1917"   # Primary button background
COLOR_BTN_PRIMARY_FG = "#f3efe6"   # Primary button text color
COLOR_BTN_PRIMARY_HOVER = "#2b2623"# Primary button hover state

COLOR_BTN_SEC_BG = "#faf7f0"       # Secondary button background
COLOR_BTN_SEC_FG = "#1c1917"       # Secondary button text color
COLOR_BTN_SEC_HOVER = "#eae4d7"   # Secondary button hover state

# Networking Protocol Constants
DEFAULT_UDP_PORT = 50025    # Port for UDP broadcast discovery
DEFAULT_P2P_PORT = 50026    # Default starting port for TCP peer transfers
DEFAULT_WEB_PORT = 8080     # Default starting port for mobile web sharing
CHUNK_SIZE_P2P = 8192       # Buffer chunk size for peer-to-peer TCP transfers (8 KB)
CHUNK_SIZE_WEB = 16384      # Buffer chunk size for mobile HTTP web transfers (16 KB)

# Application Metadata and Default Storage
APP_TITLE = "DropIt"
APP_VERSION = "2.0"
WINDOW_GEOMETRY = "500x670"
DOWNLOADS_DIR = os.path.join(os.getcwd(), "Downloads")

