# utils/helpers.py

import re
import subprocess
from datetime import datetime, timezone, timedelta

# --- ANSI Color Codes for Terminal Output ---
class Colors:
    """A class to hold ANSI color codes for beautifying terminal output."""
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"

# --- Text Manipulation ---
def clean_text(text: str) -> str:
    """Removes null bytes and other non-printable characters from a string."""
    if not isinstance(text, str):
        return ""
    return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", text)

def is_primarily_chinese(text: str) -> bool:
    """Checks if a string contains Chinese characters."""
    return True if re.search(r"[\u4e00-\u9fff]", text) else False

# --- Time and Date ---
def get_local_time_str() -> str:
    """Returns the current time as a formatted string for the GMT+8 timezone."""
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")

# --- System Interaction ---
def safe_notification(title: str, message: str):
    """Sends a desktop notification without crashing if the command fails."""
    try:
        subprocess.run(
            ["notify-send", title, message, "-a", "AI Core Modular", "-t", "4000"],
            check=True,
            capture_output=True,
        )
    except Exception:
        # Silently fail if notify-send is not available or errors out
        pass
