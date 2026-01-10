"""
NoaLog Log Exporter Module

This module handles exporting log entries to various formats:
- Text (.txt) - Plain text format
- CSV (.csv) - Timestamp, speaker, organization, body
- JSON (.json) - Structured data
- Markdown (.md) - Human-readable format
"""

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from io import StringIO
from pathlib import Path
from typing import List, Optional, Callable

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.models import LogEntry, CopyFormat, LogType


class ExportFormat(Enum):
    """Supported export formats."""
    TEXT = "txt"
    CSV = "csv"
    JSON = "json"
    MARKDOWN = "md"


class TimestampFormat(Enum):
    """Timestamp format options."""
    ISO = "iso"              # 2026-01-04T12:30:45
    DATETIME = "datetime"    # 2026-01-04 12:30:45
    DATE_ONLY = "date"       # 2026-01-04
    TIME_ONLY = "time"       # 12:30:45
    COMPACT = "compact"      # 20260104_123045


@dataclass
class ExportOptions:
    """Options for controlling export behavior."""
    # Date range filter (inclusive)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # Speaker filter (list of speaker names to include)
    speaker_filter: Optional[List[str]] = None

    # Exclude deleted entries (default: True)
    exclude_deleted: bool = True

    # Exclude duplicate entries (default: False)
    exclude_duplicates: bool = False

    # Timestamp format
    timestamp_format: TimestampFormat = TimestampFormat.DATETIME

    # Include timestamp in output
    include_timestamp: bool = True

    # Entry separator for text-based formats
    entry_separator: str = "\n---\n"

    # Use display values (edited if available) vs raw values
    use_display_values: bool = True

    # Include narration entries
    include_narration: bool = True


@dataclass
class ExportResult:
    """Result of an export operation."""
    success: bool
    content: str = ""
    file_path: Optional[Path] = None
    entry_count: int = 0
    filtered_count: int = 0  # Number of entries excluded by filters
    error_message: str = ""


class LogExporter:
    """
    Handles exporting log entries to various formats.

    Supports:
    - Multiple output formats (TXT, CSV, JSON, Markdown)
    - Date range filtering
    - Speaker filtering
    - Deleted/duplicate exclusion
    - Customizable timestamp formats
    - CopyFormat preset integration
    """

    def __init__(self, entries: Optional[List[LogEntry]] = None):
        """
        Initialize the exporter.

        Args:
            entries: List of LogEntry objects to export
        """
        self.entries = entries or []
        self._copy_format_presets = CopyFormat.get_presets()

    def set_entries(self, entries: List[LogEntry]) -> None:
        """Set the entries to export."""
        self.entries = entries

    def add_entry(self, entry: LogEntry) -> None:
        """Add a single entry to the export list."""
        self.entries.append(entry)

    def clear_entries(self) -> None:
        """Clear all entries."""
        self.entries.clear()

    # =========================================================================
    # Filtering
    # =========================================================================

    def _filter_entries(self, options: ExportOptions) -> List[LogEntry]:
        """
        Apply filters to entries based on export options.

        Args:
            options: Export options containing filter criteria

        Returns:
            Filtered list of LogEntry objects
        """
        filtered = self.entries.copy()

        # Exclude deleted entries
        if options.exclude_deleted:
            filtered = [e for e in filtered if not e.is_deleted]

        # Exclude duplicate entries
        if options.exclude_duplicates:
            filtered = [e for e in filtered if not e.is_duplicate]

        # Exclude narration if not included
        if not options.include_narration:
            filtered = [e for e in filtered if e.log_type != LogType.NARRATION]

        # Date range filter
        if options.start_date or options.end_date:
            filtered = self._filter_by_date(filtered, options.start_date, options.end_date)

        # Speaker filter
        if options.speaker_filter:
            filtered = self._filter_by_speaker(filtered, options.speaker_filter, options.use_display_values)

        return filtered

    def _filter_by_date(
        self,
        entries: List[LogEntry],
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> List[LogEntry]:
        """Filter entries by date range."""
        result = []
        for entry in entries:
            try:
                # Parse ISO timestamp
                entry_dt = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00'))
                # Remove timezone info for comparison if naive datetime is provided
                if start_date and start_date.tzinfo is None:
                    entry_dt = entry_dt.replace(tzinfo=None)
                if end_date and end_date.tzinfo is None:
                    entry_dt = entry_dt.replace(tzinfo=None)

                if start_date and entry_dt < start_date:
                    continue
                if end_date and entry_dt > end_date:
                    continue
                result.append(entry)
            except (ValueError, AttributeError):
                # Skip entries with invalid timestamps
                continue
        return result

    def _filter_by_speaker(
        self,
        entries: List[LogEntry],
        speakers: List[str],
        use_display_values: bool
    ) -> List[LogEntry]:
        """Filter entries by speaker names."""
        # Normalize speaker names for comparison
        speakers_lower = [s.lower().strip() for s in speakers]

        result = []
        for entry in entries:
            if use_display_values:
                name = entry.display_name.lower().strip()
            else:
                name = entry.speaker_name.lower().strip()

            if name in speakers_lower:
                result.append(entry)
        return result

    # =========================================================================
    # Timestamp Formatting
    # =========================================================================

    def _format_timestamp(self, timestamp: str, format_type: TimestampFormat) -> str:
        """
        Format a timestamp string according to the specified format.

        Args:
            timestamp: ISO format timestamp string
            format_type: Desired output format

        Returns:
            Formatted timestamp string
        """
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            # Remove timezone for consistent formatting
            dt = dt.replace(tzinfo=None)

            if format_type == TimestampFormat.ISO:
                return dt.isoformat()
            elif format_type == TimestampFormat.DATETIME:
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            elif format_type == TimestampFormat.DATE_ONLY:
                return dt.strftime("%Y-%m-%d")
            elif format_type == TimestampFormat.TIME_ONLY:
                return dt.strftime("%H:%M:%S")
            elif format_type == TimestampFormat.COMPACT:
                return dt.strftime("%Y%m%d_%H%M%S")
            else:
                return timestamp
        except (ValueError, AttributeError):
            return timestamp

    # =========================================================================
    # Export Methods
    # =========================================================================

    def export(
        self,
        format_type: ExportFormat,
        options: Optional[ExportOptions] = None,
        output_path: Optional[Path] = None
    ) -> ExportResult:
        """
        Export entries to the specified format.

        Args:
            format_type: The output format (TEXT, CSV, JSON, MARKDOWN)
            options: Export options for filtering and formatting
            output_path: Optional file path to save the output

        Returns:
            ExportResult containing the exported content and metadata
        """
        options = options or ExportOptions()

        # Apply filters
        filtered_entries = self._filter_entries(options)
        filtered_count = len(self.entries) - len(filtered_entries)

        # Export based on format
        try:
            if format_type == ExportFormat.TEXT:
                content = self._export_text(filtered_entries, options)
            elif format_type == ExportFormat.CSV:
                content = self._export_csv(filtered_entries, options)
            elif format_type == ExportFormat.JSON:
                content = self._export_json(filtered_entries, options)
            elif format_type == ExportFormat.MARKDOWN:
                content = self._export_markdown(filtered_entries, options)
            else:
                return ExportResult(
                    success=False,
                    error_message=f"Unsupported format: {format_type}"
                )

            # Save to file if path provided
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)

            return ExportResult(
                success=True,
                content=content,
                file_path=output_path,
                entry_count=len(filtered_entries),
                filtered_count=filtered_count
            )

        except Exception as e:
            return ExportResult(
                success=False,
                error_message=str(e)
            )

    def _export_text(self, entries: List[LogEntry], options: ExportOptions) -> str:
        """
        Export entries to plain text format.

        Uses CopyFormat 'plain' preset as base template.
        """
        lines = []
        copy_format = self._copy_format_presets.get("plain")

        for entry in entries:
            parts = []

            # Add timestamp if requested
            if options.include_timestamp:
                ts = self._format_timestamp(entry.timestamp, options.timestamp_format)
                parts.append(f"[{ts}]")

            # Format entry using CopyFormat template
            if options.use_display_values:
                name = entry.display_name
                org = entry.display_org
                body = entry.display_body
            else:
                name = entry.speaker_name
                org = entry.speaker_org
                body = entry.body_text

            header = f"{name} / {org}" if org else name

            # Handle narration entries differently
            if entry.log_type == LogType.NARRATION:
                parts.append(f"[Narration]")
                parts.append(body)
            else:
                parts.append(header)
                parts.append(body)

            lines.append("\n".join(parts))

        return options.entry_separator.join(lines)

    def _export_csv(self, entries: List[LogEntry], options: ExportOptions) -> str:
        """
        Export entries to CSV format.

        Columns: timestamp, speaker_name, speaker_org, body_text, log_type
        """
        output = StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)

        # Write header
        writer.writerow(["timestamp", "speaker_name", "speaker_org", "body_text", "log_type"])

        # Write entries
        for entry in entries:
            if options.use_display_values:
                name = entry.display_name
                org = entry.display_org
                body = entry.display_body
            else:
                name = entry.speaker_name
                org = entry.speaker_org
                body = entry.body_text

            ts = self._format_timestamp(entry.timestamp, options.timestamp_format)

            writer.writerow([ts, name, org, body, entry.log_type.value])

        return output.getvalue()

    def _export_json(self, entries: List[LogEntry], options: ExportOptions) -> str:
        """
        Export entries to JSON format.

        Returns a JSON object with metadata and entries array.
        """
        data = {
            "export_info": {
                "exported_at": datetime.now().isoformat(),
                "entry_count": len(entries),
                "format_version": "1.0"
            },
            "entries": []
        }

        for entry in entries:
            if options.use_display_values:
                name = entry.display_name
                org = entry.display_org
                body = entry.display_body
            else:
                name = entry.speaker_name
                org = entry.speaker_org
                body = entry.body_text

            ts = self._format_timestamp(entry.timestamp, options.timestamp_format)

            entry_data = {
                "id": entry.id,
                "timestamp": ts,
                "log_type": entry.log_type.value,
                "speaker": {
                    "name": name,
                    "organization": org
                },
                "body": body,
                "profile_id": entry.profile_id
            }

            # Include raw values if not using display values
            if not options.use_display_values:
                entry_data["raw"] = {
                    "header": entry.raw_header,
                    "body": entry.raw_body
                }

            data["entries"].append(entry_data)

        return json.dumps(data, ensure_ascii=False, indent=2)

    def _export_markdown(self, entries: List[LogEntry], options: ExportOptions) -> str:
        """
        Export entries to Markdown format.

        Uses a readable format with headers and blockquotes.
        """
        lines = []

        # Add title
        lines.append("# NoaLog Export")
        lines.append("")
        lines.append(f"Exported at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Entry count: {len(entries)}")
        lines.append("")
        lines.append("---")
        lines.append("")

        for entry in entries:
            if options.use_display_values:
                name = entry.display_name
                org = entry.display_org
                body = entry.display_body
            else:
                name = entry.speaker_name
                org = entry.speaker_org
                body = entry.body_text

            header = f"{name} / {org}" if org else name

            # Timestamp
            if options.include_timestamp:
                ts = self._format_timestamp(entry.timestamp, options.timestamp_format)
                lines.append(f"#### {ts}")
                lines.append("")

            # Handle narration differently
            if entry.log_type == LogType.NARRATION:
                lines.append(f"*{body}*")
            else:
                lines.append(f"**{header}**")
                lines.append("")
                # Use blockquote for dialogue body
                body_lines = body.split('\n')
                for line in body_lines:
                    lines.append(f"> {line}")

            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def export_to_text(
        self,
        output_path: Optional[Path] = None,
        options: Optional[ExportOptions] = None
    ) -> ExportResult:
        """Convenience method for text export."""
        return self.export(ExportFormat.TEXT, options, output_path)

    def export_to_csv(
        self,
        output_path: Optional[Path] = None,
        options: Optional[ExportOptions] = None
    ) -> ExportResult:
        """Convenience method for CSV export."""
        return self.export(ExportFormat.CSV, options, output_path)

    def export_to_json(
        self,
        output_path: Optional[Path] = None,
        options: Optional[ExportOptions] = None
    ) -> ExportResult:
        """Convenience method for JSON export."""
        return self.export(ExportFormat.JSON, options, output_path)

    def export_to_markdown(
        self,
        output_path: Optional[Path] = None,
        options: Optional[ExportOptions] = None
    ) -> ExportResult:
        """Convenience method for Markdown export."""
        return self.export(ExportFormat.MARKDOWN, options, output_path)

    # =========================================================================
    # CopyFormat Integration
    # =========================================================================

    def format_entry_with_preset(
        self,
        entry: LogEntry,
        preset_name: str = "plain",
        use_display_values: bool = True
    ) -> str:
        """
        Format a single entry using a CopyFormat preset.

        Args:
            entry: The LogEntry to format
            preset_name: Name of the preset (plain, markdown, quote, script)
            use_display_values: Use display (edited) values if available

        Returns:
            Formatted string
        """
        preset = self._copy_format_presets.get(preset_name)
        if not preset:
            preset = self._copy_format_presets["plain"]

        if use_display_values:
            name = entry.display_name
            org = entry.display_org
            body = entry.display_body
        else:
            name = entry.speaker_name
            org = entry.speaker_org
            body = entry.body_text

        header = f"{name} / {org}" if org else name

        return preset.template.format(
            name=name,
            org=org,
            header=header,
            body=body,
            timestamp=entry.timestamp
        )

    def format_entries_with_preset(
        self,
        entries: Optional[List[LogEntry]] = None,
        preset_name: str = "plain",
        use_display_values: bool = True,
        separator: str = "\n\n"
    ) -> str:
        """
        Format multiple entries using a CopyFormat preset.

        Args:
            entries: List of entries (uses self.entries if None)
            preset_name: Name of the preset
            use_display_values: Use display values
            separator: String to use between entries

        Returns:
            Formatted string of all entries
        """
        entries = entries or self.entries
        formatted = [
            self.format_entry_with_preset(entry, preset_name, use_display_values)
            for entry in entries
        ]
        return separator.join(formatted)

    # =========================================================================
    # Export Statistics
    # =========================================================================

    def get_export_statistics(self, options: Optional[ExportOptions] = None) -> dict:
        """
        Get statistics about the entries to be exported.

        Args:
            options: Export options for filtering

        Returns:
            Dictionary with statistics
        """
        options = options or ExportOptions()
        filtered = self._filter_entries(options)

        # Count by speaker
        speaker_counts = {}
        for entry in filtered:
            name = entry.display_name if options.use_display_values else entry.speaker_name
            speaker_counts[name] = speaker_counts.get(name, 0) + 1

        # Count by log type
        type_counts = {
            "dialogue": sum(1 for e in filtered if e.log_type == LogType.DIALOGUE),
            "narration": sum(1 for e in filtered if e.log_type == LogType.NARRATION)
        }

        # Date range
        timestamps = []
        for entry in filtered:
            try:
                dt = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00'))
                timestamps.append(dt)
            except:
                pass

        date_range = {}
        if timestamps:
            date_range = {
                "earliest": min(timestamps).isoformat(),
                "latest": max(timestamps).isoformat()
            }

        return {
            "total_entries": len(self.entries),
            "filtered_entries": len(filtered),
            "excluded_count": len(self.entries) - len(filtered),
            "speaker_counts": speaker_counts,
            "type_counts": type_counts,
            "date_range": date_range
        }
