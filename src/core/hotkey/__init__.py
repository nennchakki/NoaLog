# Hotkey management module
# Handles global hotkey registration using pynput

from .hotkey_manager import HotkeyManager, normalize_key_name, key_to_string

__all__ = ["HotkeyManager", "normalize_key_name", "key_to_string"]
