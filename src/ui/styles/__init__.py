# UI Styles and Themes
# Base colors: white, ivory, dark navy, black
# Accent: light blue

from pathlib import Path

THEME_PATH = Path(__file__).parent / "theme.qss"


def load_theme() -> str:
    """Load the theme stylesheet.

    Returns:
        str: The QSS stylesheet content
    """
    if THEME_PATH.exists():
        with open(THEME_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return ""


__all__ = ["THEME_PATH", "load_theme"]
