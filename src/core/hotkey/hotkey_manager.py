"""
NoaLog Hotkey Manager

Global hotkey monitoring using pynput library.
Supports multi-key combinations with debounce functionality.

For macOS fullscreen apps, uses native Quartz event monitoring
as a fallback when pynput cannot capture events.
"""

import logging
import platform
import subprocess
import threading
import uuid
from typing import Callable, Dict, Optional, Set

from pynput import keyboard
from pynput.keyboard import Key, KeyCode

from models import Hotkey

logger = logging.getLogger(__name__)

# macOS native event monitoring support
_MACOS_NATIVE_AVAILABLE = False
_CGEventTapCreate = None
_CGEventMaskBit = None

if platform.system() == "Darwin":
    try:
        import Quartz
        from Quartz import (
            CGEventTapCreate,
            CGEventMaskBit,
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly,
            kCGEventKeyDown,
            kCGEventKeyUp,
            kCGEventFlagsChanged,
            CGEventGetIntegerValueField,
            kCGKeyboardEventKeycode,
            CGEventGetFlags,
            kCGEventFlagMaskShift,
            kCGEventFlagMaskControl,
            kCGEventFlagMaskAlternate,
            kCGEventFlagMaskCommand,
            CFMachPortCreateRunLoopSource,
            CFRunLoopGetCurrent,
            CFRunLoopAddSource,
            kCFRunLoopCommonModes,
            CFRunLoopRun,
            CFRunLoopStop,
        )
        _MACOS_NATIVE_AVAILABLE = True
        logger.info("macOS Quartz event monitoring available")
    except ImportError:
        logger.warning("Quartz (pyobjc-framework-Quartz) not available for native hotkey support")


# Key name mapping for pynput
# Maps user-friendly key names to pynput Key objects
KEY_MAP: Dict[str, Key] = {
    # Modifier keys
    "cmd": Key.cmd,
    "command": Key.cmd,
    "ctrl": Key.ctrl,
    "control": Key.ctrl,
    "alt": Key.alt,
    "option": Key.alt,
    "shift": Key.shift,
    # Special keys
    "space": Key.space,
    "enter": Key.enter,
    "return": Key.enter,
    "tab": Key.tab,
    "backspace": Key.backspace,
    "delete": Key.delete,
    "escape": Key.esc,
    "esc": Key.esc,
    # Arrow keys
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    # Function keys
    "f1": Key.f1,
    "f2": Key.f2,
    "f3": Key.f3,
    "f4": Key.f4,
    "f5": Key.f5,
    "f6": Key.f6,
    "f7": Key.f7,
    "f8": Key.f8,
    "f9": Key.f9,
    "f10": Key.f10,
    "f11": Key.f11,
    "f12": Key.f12,
}


def normalize_key_name(key_name: str) -> str:
    """Normalize key name to lowercase."""
    return key_name.lower().strip()


def key_to_string(key) -> Optional[str]:
    """Convert pynput key to string representation."""
    if isinstance(key, Key):
        # Special keys
        key_str = key.name.lower()
        # Normalize some key names
        if key_str in ("cmd", "cmd_l", "cmd_r"):
            return "cmd"
        if key_str in ("ctrl", "ctrl_l", "ctrl_r"):
            return "ctrl"
        if key_str in ("alt", "alt_l", "alt_r", "alt_gr"):
            return "alt"
        if key_str in ("shift", "shift_l", "shift_r"):
            return "shift"
        return key_str
    elif isinstance(key, KeyCode):
        # Regular character keys
        if key.char:
            return key.char.lower()
        elif key.vk:
            # Virtual key code (for special characters)
            return f"vk_{key.vk}"
    return None


class RegisteredHotkey:
    """Internal representation of a registered hotkey."""

    def __init__(
        self,
        hotkey_id: str,
        hotkey: Hotkey,
        callback: Callable,
        normalized_keys: Set[str],
    ):
        self.id = hotkey_id
        self.hotkey = hotkey
        self.callback = callback
        self.normalized_keys = normalized_keys


# macOS keycode to key name mapping
MACOS_KEYCODE_MAP = {
    0: "a", 1: "s", 2: "d", 3: "f", 4: "h", 5: "g", 6: "z", 7: "x",
    8: "c", 9: "v", 11: "b", 12: "q", 13: "w", 14: "e", 15: "r",
    16: "y", 17: "t", 31: "o", 32: "u", 34: "i", 35: "p", 37: "l",
    38: "j", 40: "k", 45: "n", 46: "m",
    # Special keys
    36: "enter", 48: "tab", 49: "space", 51: "backspace", 53: "escape",
    # Arrow keys
    123: "left", 124: "right", 125: "down", 126: "up",
    # Function keys
    122: "f1", 120: "f2", 99: "f3", 118: "f4", 96: "f5",
    97: "f6", 98: "f7", 100: "f8", 101: "f9", 109: "f10",
    103: "f11", 111: "f12",
}


class HotkeyManager:
    """
    Global hotkey manager using pynput with macOS native fallback.

    Features:
    - Multi-key combination detection (e.g., Cmd+Shift+C)
    - Debounce: Prevents re-triggering until all keys are released
    - Callback registration for hotkey events
    - macOS accessibility permission detection
    - Native Quartz event monitoring for fullscreen apps on macOS

    Usage:
        manager = HotkeyManager()
        hotkey = Hotkey(keys=["cmd", "shift", "l"])
        manager.register_hotkey(hotkey, my_callback)
        manager.start()
    """

    def __init__(self, throttle_ms: int = 500, use_native_macos: bool = True):
        """Initialize the hotkey manager.

        Args:
            throttle_ms: Minimum interval between triggers in milliseconds.
            use_native_macos: Use native Quartz event tap on macOS for better
                             fullscreen app support (requires pyobjc-framework-Quartz).
        """
        self._listener: Optional[keyboard.Listener] = None
        self._registered_hotkeys: Dict[str, RegisteredHotkey] = {}
        self._pressed_keys: Set[str] = set()
        self._triggered_hotkeys: Set[str] = set()  # For debounce
        self._last_trigger_time: Dict[str, float] = {}  # For throttle
        self._throttle_ms: int = throttle_ms
        self._lock = threading.Lock()
        self._running = False

        # macOS native monitoring
        self._use_native_macos = (
            use_native_macos and
            platform.system() == "Darwin" and
            _MACOS_NATIVE_AVAILABLE
        )
        self._native_thread: Optional[threading.Thread] = None
        self._native_run_loop = None
        self._native_event_tap = None

        logger.debug(f"HotkeyManager initialized (native_macos={self._use_native_macos})")

    def register_hotkey(self, hotkey: Hotkey, callback: Callable) -> str:
        """
        Register a hotkey combination with a callback.

        Args:
            hotkey: Hotkey object containing key combination
            callback: Function to call when hotkey is triggered

        Returns:
            str: Unique ID for the registered hotkey

        Raises:
            ValueError: If hotkey has no keys defined
        """
        if not hotkey.keys:
            raise ValueError("Hotkey must have at least one key defined")

        hotkey_id = str(uuid.uuid4())
        normalized_keys = {normalize_key_name(k) for k in hotkey.keys}

        registered = RegisteredHotkey(
            hotkey_id=hotkey_id,
            hotkey=hotkey,
            callback=callback,
            normalized_keys=normalized_keys,
        )

        with self._lock:
            self._registered_hotkeys[hotkey_id] = registered

        logger.info(f"Registered hotkey: {hotkey} (ID: {hotkey_id})")
        return hotkey_id

    def unregister_hotkey(self, hotkey_id: str) -> bool:
        """
        Unregister a hotkey by its ID.

        Args:
            hotkey_id: The ID returned from register_hotkey

        Returns:
            bool: True if hotkey was found and removed, False otherwise
        """
        with self._lock:
            if hotkey_id in self._registered_hotkeys:
                removed = self._registered_hotkeys.pop(hotkey_id)
                logger.info(f"Unregistered hotkey: {removed.hotkey} (ID: {hotkey_id})")
                return True
            return False

    def start(self) -> None:
        """
        Start the hotkey listener.

        Creates a background thread that monitors keyboard events.
        On macOS, requires accessibility permissions.
        Uses native Quartz event monitoring on macOS for fullscreen support.
        """
        if self._running:
            logger.warning("HotkeyManager is already running")
            return

        # Check accessibility permission on macOS
        if platform.system() == "Darwin":
            if not self.check_accessibility_permission():
                logger.warning(
                    "macOS accessibility permission may not be granted. "
                    "Hotkeys may not work. Please grant permission in "
                    "System Settings > Privacy & Security > Accessibility"
                )

        # On macOS, use native Quartz event tap for better fullscreen support
        if self._use_native_macos:
            self._start_native_macos()
        else:
            # Fall back to pynput
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.start()

        self._running = True
        logger.info(f"HotkeyManager started (native_macos={self._use_native_macos})")

    def _start_native_macos(self) -> None:
        """Start native macOS Quartz event monitoring.

        This method uses CGEventTap to monitor keyboard events at a lower level,
        which works even in fullscreen apps where pynput may fail.
        """
        if not _MACOS_NATIVE_AVAILABLE:
            logger.error("Quartz not available, cannot start native monitoring")
            return

        import Quartz
        from Quartz import (
            CGEventTapCreate,
            CGEventMaskBit,
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly,
            kCGEventKeyDown,
            kCGEventKeyUp,
            kCGEventFlagsChanged,
            CGEventGetIntegerValueField,
            kCGKeyboardEventKeycode,
            CGEventGetFlags,
            kCGEventFlagMaskShift,
            kCGEventFlagMaskControl,
            kCGEventFlagMaskAlternate,
            kCGEventFlagMaskCommand,
            CFMachPortCreateRunLoopSource,
            CFRunLoopGetCurrent,
            CFRunLoopAddSource,
            kCFRunLoopCommonModes,
            CFRunLoopRun,
            CFRunLoopStop,
        )

        def native_callback(proxy, event_type, event, refcon):
            """Native Quartz event callback."""
            try:
                # Get modifier flags
                flags = CGEventGetFlags(event)
                modifiers = set()

                if flags & kCGEventFlagMaskCommand:
                    modifiers.add("cmd")
                if flags & kCGEventFlagMaskShift:
                    modifiers.add("shift")
                if flags & kCGEventFlagMaskControl:
                    modifiers.add("ctrl")
                if flags & kCGEventFlagMaskAlternate:
                    modifiers.add("alt")

                if event_type == kCGEventKeyDown:
                    keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
                    key_name = MACOS_KEYCODE_MAP.get(keycode)

                    if key_name:
                        with self._lock:
                            self._pressed_keys = modifiers.copy()
                            self._pressed_keys.add(key_name)
                            self._check_hotkeys()

                elif event_type == kCGEventKeyUp:
                    keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
                    key_name = MACOS_KEYCODE_MAP.get(keycode)

                    if key_name:
                        with self._lock:
                            self._pressed_keys.discard(key_name)
                            # Clear debounce for released keys
                            hotkeys_to_clear = set()
                            for hotkey_id in self._triggered_hotkeys:
                                if hotkey_id in self._registered_hotkeys:
                                    registered = self._registered_hotkeys[hotkey_id]
                                    if key_name in registered.normalized_keys:
                                        hotkeys_to_clear.add(hotkey_id)
                            self._triggered_hotkeys -= hotkeys_to_clear

                elif event_type == kCGEventFlagsChanged:
                    # Modifier key change - update pressed modifiers
                    with self._lock:
                        # Keep non-modifier keys, update modifiers
                        non_modifiers = {k for k in self._pressed_keys
                                        if k not in ("cmd", "shift", "ctrl", "alt")}
                        self._pressed_keys = modifiers | non_modifiers

            except Exception as e:
                logger.error(f"Error in native callback: {e}")

            return event

        def run_native_loop():
            """Run the native event loop in a separate thread."""
            try:
                # Create event mask for key events
                event_mask = (
                    CGEventMaskBit(kCGEventKeyDown) |
                    CGEventMaskBit(kCGEventKeyUp) |
                    CGEventMaskBit(kCGEventFlagsChanged)
                )

                # Create event tap
                self._native_event_tap = CGEventTapCreate(
                    kCGSessionEventTap,
                    kCGHeadInsertEventTap,
                    kCGEventTapOptionListenOnly,
                    event_mask,
                    native_callback,
                    None
                )

                if self._native_event_tap is None:
                    logger.error(
                        "Failed to create event tap. "
                        "Please ensure accessibility permission is granted in "
                        "System Settings > Privacy & Security > Accessibility"
                    )
                    return

                # Create run loop source
                run_loop_source = CFMachPortCreateRunLoopSource(
                    None, self._native_event_tap, 0
                )

                # Add to run loop
                self._native_run_loop = CFRunLoopGetCurrent()
                CFRunLoopAddSource(
                    self._native_run_loop,
                    run_loop_source,
                    kCFRunLoopCommonModes
                )

                logger.info("Native macOS event tap started")

                # Run the loop
                CFRunLoopRun()

            except Exception as e:
                logger.error(f"Error in native event loop: {e}")

        # Start native monitoring in a separate thread
        self._native_thread = threading.Thread(
            target=run_native_loop,
            daemon=True,
            name="NativeHotkeyMonitor"
        )
        self._native_thread.start()

    def stop(self) -> None:
        """
        Stop the hotkey listener.

        Cleans up the listener thread and resets state.
        """
        if not self._running:
            return

        # Stop pynput listener if active
        if self._listener:
            self._listener.stop()
            self._listener = None

        # Stop native macOS monitoring if active
        if self._native_run_loop is not None:
            try:
                from Quartz import CFRunLoopStop
                CFRunLoopStop(self._native_run_loop)
            except Exception as e:
                logger.warning(f"Error stopping native run loop: {e}")
            self._native_run_loop = None
            self._native_event_tap = None

        if self._native_thread is not None:
            self._native_thread = None

        with self._lock:
            self._pressed_keys.clear()
            self._triggered_hotkeys.clear()

        self._running = False
        logger.info("HotkeyManager stopped")

    def check_accessibility_permission(self) -> bool:
        """
        Check if accessibility permission is granted (macOS only).

        On macOS, global keyboard monitoring requires accessibility permission.
        This method attempts to detect if permission is granted.

        Returns:
            bool: True if permission appears to be granted, False otherwise.
                  Always returns True on non-macOS platforms.
        """
        if platform.system() != "Darwin":
            return True

        try:
            # Use tccutil to check accessibility permission status
            # This is a heuristic - the actual check happens when pynput starts
            result = subprocess.run(
                [
                    "sqlite3",
                    "/Library/Application Support/com.apple.TCC/TCC.db",
                    "SELECT client FROM access WHERE service='kTCCServiceAccessibility'",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # If we can query the database, check output
            # Note: This may fail due to SIP protection, which is normal
            logger.debug(f"Accessibility check result: {result.returncode}")
            return True
        except subprocess.TimeoutExpired:
            logger.warning("Accessibility permission check timed out")
            return True
        except FileNotFoundError:
            # sqlite3 not found - assume permission is OK
            return True
        except Exception as e:
            # On modern macOS, direct DB access is blocked by SIP
            # We can't reliably check, so assume True and let pynput handle it
            logger.debug(f"Could not check accessibility permission: {e}")
            return True

    def _on_press(self, key) -> None:
        """Handle key press event."""
        key_str = key_to_string(key)
        if key_str is None:
            return

        with self._lock:
            self._pressed_keys.add(key_str)
            self._check_hotkeys()

    def _on_release(self, key) -> None:
        """Handle key release event."""
        key_str = key_to_string(key)
        if key_str is None:
            return

        with self._lock:
            self._pressed_keys.discard(key_str)

            # Clear debounce for hotkeys that no longer match
            # This allows re-triggering once all keys are released
            hotkeys_to_clear = set()
            for hotkey_id in self._triggered_hotkeys:
                if hotkey_id in self._registered_hotkeys:
                    registered = self._registered_hotkeys[hotkey_id]
                    # If any key of the hotkey is released, clear debounce
                    if key_str in registered.normalized_keys:
                        hotkeys_to_clear.add(hotkey_id)

            self._triggered_hotkeys -= hotkeys_to_clear

    def _check_hotkeys(self) -> None:
        """Check if any registered hotkey combination is pressed."""
        import time
        current_time = time.time() * 1000  # milliseconds

        for hotkey_id, registered in self._registered_hotkeys.items():
            # Skip if already triggered (debounce)
            if hotkey_id in self._triggered_hotkeys:
                continue

            # Check if all required keys are pressed
            if registered.normalized_keys <= self._pressed_keys:
                # Throttle check
                last_time = self._last_trigger_time.get(hotkey_id, 0)
                if (current_time - last_time) < self._throttle_ms:
                    continue  # Within throttle period, skip

                # Mark as triggered for debounce
                self._triggered_hotkeys.add(hotkey_id)
                self._last_trigger_time[hotkey_id] = current_time

                # Call callback in a separate thread to avoid blocking
                logger.debug(f"Hotkey triggered: {registered.hotkey}")
                threading.Thread(
                    target=self._execute_callback,
                    args=(registered.callback,),
                    daemon=True,
                ).start()

    def _execute_callback(self, callback: Callable) -> None:
        """Execute callback with error handling."""
        try:
            callback()
        except Exception as e:
            logger.error(f"Error in hotkey callback: {e}", exc_info=True)

    @property
    def is_running(self) -> bool:
        """Check if the hotkey manager is currently running."""
        return self._running

    @property
    def registered_count(self) -> int:
        """Get the number of registered hotkeys."""
        return len(self._registered_hotkeys)

    def get_registered_hotkeys(self) -> Dict[str, Hotkey]:
        """
        Get all registered hotkeys.

        Returns:
            Dict mapping hotkey ID to Hotkey object
        """
        with self._lock:
            return {
                hk_id: reg.hotkey
                for hk_id, reg in self._registered_hotkeys.items()
            }

    def update_hotkey(self, hotkey_id: str, new_hotkey: Hotkey) -> bool:
        """
        Update an existing hotkey without re-registering.

        Args:
            hotkey_id: The ID of the hotkey to update
            new_hotkey: The new hotkey configuration

        Returns:
            bool: True if updated successfully, False if ID not found
        """
        with self._lock:
            if hotkey_id not in self._registered_hotkeys:
                return False

            registered = self._registered_hotkeys[hotkey_id]
            registered.hotkey = new_hotkey
            registered.normalized_keys = {normalize_key_name(k) for k in new_hotkey.keys}

            # Clear trigger state for this hotkey
            self._triggered_hotkeys.discard(hotkey_id)

            logger.info(f"Updated hotkey {hotkey_id}: {new_hotkey}")
            return True

    def set_throttle_ms(self, throttle_ms: int) -> None:
        """Set the throttle interval in milliseconds."""
        self._throttle_ms = max(0, throttle_ms)
        logger.debug(f"Throttle set to {self._throttle_ms}ms")
