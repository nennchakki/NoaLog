"""
Screen Capture Module

This module provides screen capture functionality using the mss library.
Supports full screen capture and region-based capture with cross-platform
compatibility (macOS/Windows).
"""

import logging
from typing import Optional

import mss
import mss.tools
import numpy as np

from models import Rect


logger = logging.getLogger(__name__)


class ScreenCaptureError(Exception):
    """Exception raised for screen capture errors."""
    pass


class ScreenCapture:
    """
    Screen capture handler using mss library.

    Provides methods for capturing the full screen or specific regions,
    returning images as OpenCV-compatible numpy arrays (BGR format).

    Example:
        >>> capture = ScreenCapture()
        >>> # Full screen capture
        >>> image = capture.capture_full_screen()
        >>> # Region capture
        >>> rect = Rect(x=100, y=100, width=800, height=600)
        >>> region_image = capture.capture_region(rect)
    """

    def __init__(self) -> None:
        """Initialize ScreenCapture instance."""
        self._sct: Optional[mss.mss] = None

    def _get_sct(self) -> mss.mss:
        """
        Get or create mss instance.

        Returns:
            mss.mss: The mss screen capture instance.
        """
        if self._sct is None:
            self._sct = mss.mss()
        return self._sct

    def _screenshot_to_numpy(self, screenshot: mss.screenshot.ScreenShot) -> np.ndarray:
        """
        Convert mss screenshot to numpy array in BGR format.

        The mss library captures in BGRA format. This method converts
        to BGR format which is the standard for OpenCV.

        Args:
            screenshot: The mss screenshot object.

        Returns:
            np.ndarray: Image in BGR format (height, width, 3).
        """
        # mss returns BGRA format
        img = np.array(screenshot, dtype=np.uint8)

        # Convert BGRA to BGR (drop alpha channel)
        if img.shape[2] == 4:
            img = img[:, :, :3]

        return img

    def get_monitors(self) -> list[dict]:
        """
        Get list of available monitors.

        Returns:
            list[dict]: List of monitor dictionaries with keys:
                - left: X coordinate of top-left corner
                - top: Y coordinate of top-left corner
                - width: Monitor width in pixels
                - height: Monitor height in pixels

        Note:
            Index 0 is a virtual monitor representing all screens combined.
            Physical monitors start from index 1.
        """
        sct = self._get_sct()
        monitors = []

        for i, monitor in enumerate(sct.monitors):
            monitors.append({
                "index": i,
                "left": monitor["left"],
                "top": monitor["top"],
                "width": monitor["width"],
                "height": monitor["height"],
                "is_primary": i == 1,  # First physical monitor is typically primary
                "is_virtual": i == 0,  # Index 0 is virtual (all screens)
            })

        logger.debug(f"Found {len(monitors)} monitors (including virtual)")
        return monitors

    def capture_full_screen(self, monitor_index: int = 0) -> np.ndarray:
        """
        Capture the full screen of specified monitor.

        Args:
            monitor_index: Index of monitor to capture.
                - 0: Virtual monitor (all screens combined)
                - 1: Primary monitor
                - 2+: Additional monitors
                Defaults to 0 (all screens).

        Returns:
            np.ndarray: Captured image in BGR format (OpenCV compatible).

        Raises:
            ScreenCaptureError: If capture fails or invalid monitor index.

        Example:
            >>> capture = ScreenCapture()
            >>> img = capture.capture_full_screen(monitor_index=1)
            >>> print(img.shape)  # (height, width, 3)
        """
        sct = self._get_sct()

        # Validate monitor index
        if monitor_index < 0 or monitor_index >= len(sct.monitors):
            available = len(sct.monitors) - 1
            raise ScreenCaptureError(
                f"Invalid monitor index: {monitor_index}. "
                f"Available monitors: 0-{available}"
            )

        try:
            monitor = sct.monitors[monitor_index]
            logger.debug(
                f"Capturing monitor {monitor_index}: "
                f"{monitor['width']}x{monitor['height']} "
                f"at ({monitor['left']}, {monitor['top']})"
            )

            screenshot = sct.grab(monitor)
            img = self._screenshot_to_numpy(screenshot)

            logger.debug(f"Captured image shape: {img.shape}")
            return img

        except Exception as e:
            logger.error(f"Failed to capture screen: {e}")
            raise ScreenCaptureError(f"Failed to capture screen: {e}") from e

    def capture_region(self, rect: Rect, monitor_index: int = 0) -> np.ndarray:
        """
        Capture a specific region of the screen.

        The region coordinates are relative to the specified monitor.
        For monitor_index=0 (virtual), coordinates are in global screen space.

        Args:
            rect: Rectangle defining the capture region.
                Contains x, y (top-left corner), width, and height.
            monitor_index: Index of monitor for coordinate reference.
                Defaults to 0 (global coordinates).

        Returns:
            np.ndarray: Captured image in BGR format (OpenCV compatible).

        Raises:
            ScreenCaptureError: If capture fails or region is invalid.
            ValueError: If rect has invalid dimensions.

        Example:
            >>> capture = ScreenCapture()
            >>> rect = Rect(x=100, y=100, width=800, height=600)
            >>> img = capture.capture_region(rect, monitor_index=1)
        """
        # Validate rect dimensions
        if rect.width <= 0 or rect.height <= 0:
            raise ValueError(
                f"Invalid rect dimensions: width={rect.width}, height={rect.height}. "
                "Both must be positive."
            )

        sct = self._get_sct()

        # Validate monitor index
        if monitor_index < 0 or monitor_index >= len(sct.monitors):
            available = len(sct.monitors) - 1
            raise ScreenCaptureError(
                f"Invalid monitor index: {monitor_index}. "
                f"Available monitors: 0-{available}"
            )

        try:
            # Get monitor offset for coordinate calculation
            monitor = sct.monitors[monitor_index]

            # Calculate absolute coordinates
            # If monitor_index is 0 (virtual), rect coordinates are already global
            # Otherwise, add monitor offset to get global coordinates
            if monitor_index == 0:
                # Global coordinates - use rect as-is
                capture_region = rect.to_mss_monitor()
            else:
                # Monitor-relative coordinates - add monitor offset
                capture_region = {
                    "left": monitor["left"] + rect.x,
                    "top": monitor["top"] + rect.y,
                    "width": rect.width,
                    "height": rect.height,
                }

            logger.debug(
                f"Capturing region: {capture_region['width']}x{capture_region['height']} "
                f"at ({capture_region['left']}, {capture_region['top']})"
            )

            screenshot = sct.grab(capture_region)
            img = self._screenshot_to_numpy(screenshot)

            logger.debug(f"Captured region shape: {img.shape}")
            return img

        except Exception as e:
            logger.error(f"Failed to capture region: {e}")
            raise ScreenCaptureError(f"Failed to capture region: {e}") from e

    def close(self) -> None:
        """
        Close the mss instance and release resources.

        Call this method when done with screen capture to free resources.
        The instance can be reused after close() - a new mss instance
        will be created on the next capture call.
        """
        if self._sct is not None:
            self._sct.close()
            self._sct = None
            logger.debug("ScreenCapture resources released")

    def __enter__(self) -> "ScreenCapture":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - ensures resources are released."""
        self.close()

    def __del__(self) -> None:
        """Destructor - ensures resources are released."""
        self.close()
