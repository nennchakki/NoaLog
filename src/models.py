"""
NoaLog Data Models

This module defines the data structures used throughout the application.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import uuid


class LogType(Enum):
    """Type of log entry."""
    DIALOGUE = "dialogue"  # Normal dialogue with speaker
    NARRATION = "narration"  # Narration/description text


@dataclass
class Rect:
    """Rectangle definition for capture regions."""
    x: int
    y: int
    width: int
    height: int

    def to_tuple(self) -> tuple:
        """Convert to (x, y, width, height) tuple."""
        return (self.x, self.y, self.width, self.height)

    def to_mss_monitor(self) -> dict:
        """Convert to mss monitor format."""
        return {
            "left": self.x,
            "top": self.y,
            "width": self.width,
            "height": self.height,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Rect":
        """Create from dictionary."""
        return cls(
            x=data["x"],
            y=data["y"],
            width=data["width"],
            height=data["height"],
        )


@dataclass
class Hotkey:
    """Hotkey combination definition."""
    keys: List[str]  # List of key names (e.g., ["cmd", "shift", "l"])

    def __str__(self) -> str:
        """Human-readable representation."""
        return " + ".join(self.keys)

    @classmethod
    def from_list(cls, keys: List[str]) -> "Hotkey":
        """Create from list of key names."""
        return cls(keys=keys)


@dataclass
class Profile:
    """Capture profile for a specific application."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Capture regions
    header_rect: Optional[Rect] = None
    body_rect: Optional[Rect] = None
    narrator_rect: Optional[Rect] = None  # 語り部/第三者用のキャプチャ領域

    # Narrator settings
    narrator_label: str = "語り部"  # narrator_rectキャプチャ時に使用するラベル

    # Hotkey
    hotkey: Optional[Hotkey] = None
    narrator_hotkey: Optional[Hotkey] = None  # narrator用の別キー

    # OCR settings (profile-specific overrides)
    ocr_settings: Dict[str, Any] = field(default_factory=dict)

    # Active flag
    is_active: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        """Create from dictionary."""
        profile = cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            is_active=data.get("is_active", True),
            ocr_settings=data.get("ocr_settings", {}),
            narrator_label=data.get("narrator_label", "語り部"),
        )

        if data.get("header_rect"):
            profile.header_rect = Rect.from_dict(data["header_rect"])
        if data.get("body_rect"):
            profile.body_rect = Rect.from_dict(data["body_rect"])
        if data.get("narrator_rect"):
            profile.narrator_rect = Rect.from_dict(data["narrator_rect"])
        if data.get("hotkey"):
            profile.hotkey = Hotkey.from_list(data["hotkey"]["keys"])
        if data.get("narrator_hotkey"):
            profile.narrator_hotkey = Hotkey.from_list(data["narrator_hotkey"]["keys"])

        return profile

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "Profile":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class LogEntry:
    """Single conversation log entry."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    profile_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # Log type
    log_type: LogType = LogType.DIALOGUE

    # Raw OCR results (never modified)
    raw_header: str = ""
    raw_body: str = ""

    # Parsed/normalized results
    speaker_name: str = ""
    speaker_org: str = ""
    body_text: str = ""

    # Edited values (user modifications)
    edited_speaker_name: Optional[str] = None
    edited_speaker_org: Optional[str] = None
    edited_body_text: Optional[str] = None

    # Metadata
    is_deleted: bool = False  # Soft delete flag
    is_duplicate: bool = False  # Duplicate flag

    @property
    def display_name(self) -> str:
        """Get the display name (edited if available, else parsed)."""
        return self.edited_speaker_name if self.edited_speaker_name else self.speaker_name

    @property
    def display_org(self) -> str:
        """Get the display organization (edited if available, else parsed)."""
        return self.edited_speaker_org if self.edited_speaker_org else self.speaker_org

    @property
    def display_body(self) -> str:
        """Get the display body text (edited if available, else parsed)."""
        return self.edited_body_text if self.edited_body_text else self.body_text

    @property
    def display_header(self) -> str:
        """Get formatted header for display."""
        name = self.display_name
        org = self.display_org
        if org:
            return f"{name} / {org}"
        return name

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["log_type"] = self.log_type.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "LogEntry":
        """Create from dictionary."""
        entry = cls(
            id=data.get("id", str(uuid.uuid4())),
            profile_id=data.get("profile_id", ""),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            log_type=LogType(data.get("log_type", "dialogue")),
            raw_header=data.get("raw_header", ""),
            raw_body=data.get("raw_body", ""),
            speaker_name=data.get("speaker_name", ""),
            speaker_org=data.get("speaker_org", ""),
            body_text=data.get("body_text", ""),
            edited_speaker_name=data.get("edited_speaker_name"),
            edited_speaker_org=data.get("edited_speaker_org"),
            edited_body_text=data.get("edited_body_text"),
            is_deleted=data.get("is_deleted", False),
            is_duplicate=data.get("is_duplicate", False),
        )
        return entry

    def to_jsonl(self) -> str:
        """Serialize to JSONL format (single line)."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_jsonl(cls, line: str) -> "LogEntry":
        """Deserialize from JSONL line."""
        data = json.loads(line.strip())
        return cls.from_dict(data)


@dataclass
class CopyFormat:
    """Copy format template."""
    name: str
    template: str  # Template string with placeholders
    include_timestamp: bool = False
    separator: str = "\n"

    # Available placeholders:
    # {name} - speaker name
    # {org} - speaker organization
    # {header} - formatted header (name / org)
    # {body} - body text
    # {timestamp} - timestamp

    @classmethod
    def get_presets(cls) -> Dict[str, "CopyFormat"]:
        """Get preset copy formats."""
        return {
            "plain": cls(
                name="Plain",
                template="{header}\n{body}",
            ),
            "markdown": cls(
                name="Markdown",
                template="**{header}**\n{body}",
            ),
            "quote": cls(
                name="Quote",
                template="> {body}\n> -- {header}",
            ),
            "script": cls(
                name="Script",
                template="{name}: {body}",
            ),
        }
