"""
NoaLog Configuration Management

This module handles application configuration, paths, and settings.
"""

from pathlib import Path
from typing import Optional
import json
import os


class Config:
    """Application configuration manager."""

    # Application info
    APP_NAME = "NoaLog"
    APP_VERSION = "0.1.0"

    # Default directories
    _base_dir: Optional[Path] = None

    @classmethod
    def get_base_dir(cls) -> Path:
        """Get the base directory for the application."""
        if cls._base_dir is None:
            # In development, use the project root
            # In production, use user's app data directory
            if os.environ.get("NOALOG_DEV"):
                cls._base_dir = Path(__file__).parent.parent
            else:
                # Use platform-appropriate app data directory
                import sys
                if sys.platform == "darwin":
                    cls._base_dir = Path.home() / "Library" / "Application Support" / cls.APP_NAME
                elif sys.platform == "win32":
                    cls._base_dir = Path(os.environ.get("APPDATA", Path.home())) / cls.APP_NAME
                else:
                    cls._base_dir = Path.home() / f".{cls.APP_NAME.lower()}"

            # Ensure directory exists
            cls._base_dir.mkdir(parents=True, exist_ok=True)

        return cls._base_dir

    @classmethod
    def get_profiles_dir(cls) -> Path:
        """Get the profiles directory."""
        path = cls.get_base_dir() / "profiles"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def get_logs_dir(cls) -> Path:
        """Get the logs directory."""
        path = cls.get_base_dir() / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def get_config_file(cls) -> Path:
        """Get the main config file path."""
        return cls.get_base_dir() / "config.json"

    @classmethod
    def load_config(cls) -> dict:
        """Load configuration from file."""
        config_file = cls.get_config_file()
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return cls.get_default_config()

    @classmethod
    def save_config(cls, config: dict) -> None:
        """Save configuration to file."""
        config_file = cls.get_config_file()
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    @classmethod
    def get_default_config(cls) -> dict:
        """Get default configuration."""
        return {
            "version": cls.APP_VERSION,
            "theme": "light",
            "language": "ja",
            "ocr": {
                "lang": "japan",
                "use_angle_cls": True,
                "use_gpu": False,
            },
            "hotkey": {
                "debounce_ms": 100,
                "throttle_ms": 500,
                # Changed from cmd+shift to cmd+option to avoid Chrome extension conflicts
                "capture": ["cmd", "option", "l"],
                "region_selection": ["cmd", "option", "r"],
            },
            "ui": {
                "font_size": 14,
                "window_width": 900,
                "window_height": 700,
            },
            "copy": {
                "default_format": "plain",
                "include_timestamp": False,
            },
        }


# OCR preprocessing settings
OCR_PREPROCESS = {
    "grayscale": True,
    "denoise": True,
    "contrast_enhance": 1.2,
    "threshold": None,  # Auto
}

# Text normalization settings
TEXT_NORMALIZE = {
    "fullwidth_to_halfwidth": True,
    "normalize_whitespace": True,
    "strip_lines": True,
}

# Header parsing settings
HEADER_PARSE = {
    "separators": ["/", "／"],
    "narrator_keywords": ["地の文", "ナレーション", "語り"],
}
