import os

# CustomTkinter Appearance Settings
APPEARANCE_MODE = "Light"
COLOR_THEME = "blue"

# Theme Palette Constants (Warm Cream / Oatmeal Retro-Tech Editorial)
COLOR_BG = "#f3efe6"            # Warm Cream / Oatmeal Paper
COLOR_CARD = "#faf7f0"          # Warm Soft Off-White Card
COLOR_CARD_ALT = "#eae4d7"      # Subtle Neutral Fill
COLOR_BORDER = "#e2dcd0"        # Soft Warm Border
COLOR_TEXT_PRIMARY = "#1c1917"  # Deep Charcoal
COLOR_TEXT_MUTED = "#78716c"    # Warm Taupe / Muted Gray
COLOR_GREEN = "#15803d"         # Retro Emerald Green (Active/Routing)
COLOR_GREEN_HOVER = "#166534"

COLOR_BTN_PRIMARY_BG = "#1c1917"   # Charcoal Pill Button
COLOR_BTN_PRIMARY_FG = "#f3efe6"   # Cream Text
COLOR_BTN_PRIMARY_HOVER = "#2b2623"

COLOR_BTN_SEC_BG = "#faf7f0"
COLOR_BTN_SEC_FG = "#1c1917"
COLOR_BTN_SEC_HOVER = "#eae4d7"

# Network & Protocol Constants
DEFAULT_UDP_PORT = 50025
DEFAULT_P2P_PORT = 50026
DEFAULT_WEB_PORT = 8080
CHUNK_SIZE_P2P = 8192
CHUNK_SIZE_WEB = 16384

# Application Metadata & Default Paths
APP_TITLE = "LocalDrop"
APP_VERSION = "2.0"
WINDOW_GEOMETRY = "500x670"
DOWNLOADS_DIR = os.path.join(os.getcwd(), "Downloads")
