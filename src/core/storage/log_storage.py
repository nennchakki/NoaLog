"""
NoaLog Log Storage Module

This module provides persistent storage for log entries using JSONL format.
Each profile has its own log file, with support for concurrent access via file locking.
"""

from pathlib import Path
from typing import List, Optional, Callable
from datetime import datetime
from contextlib import contextmanager
import fcntl
import os

from ...config import Config
from ...models import LogEntry


class LogStorageError(Exception):
    """Base exception for log storage errors."""
    pass


class FileAccessError(LogStorageError):
    """Raised when file operations fail."""
    pass


class LogNotFoundError(LogStorageError):
    """Raised when a log entry is not found."""
    pass


class LogStorage:
    """
    Persistent storage for log entries using JSONL format.

    Features:
    - JSONL format for efficient append-only writes
    - Per-profile log files
    - File locking for concurrent access safety
    - Support for logical deletion (soft delete)
    - Date range filtering
    - Log entry updates with edit tracking

    File location: ~/.noalog/logs/{profile_id}.jsonl
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize LogStorage.

        Args:
            base_dir: Base directory for log files. If None, uses Config.get_logs_dir()
        """
        self._base_dir = base_dir or Config.get_logs_dir()
        self._ensure_dir_exists()

    def _ensure_dir_exists(self) -> None:
        """Ensure the logs directory exists."""
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_file_path(self, profile_id: str) -> Path:
        """
        Get the log file path for a profile.

        Args:
            profile_id: Profile identifier

        Returns:
            Path to the JSONL log file
        """
        return self._base_dir / f"{profile_id}.jsonl"

    @contextmanager
    def _file_lock(self, file_path: Path, mode: str = "r+"):
        """
        Context manager for file locking.

        Uses fcntl for POSIX-compatible file locking.
        Exclusive lock for writes, shared lock for reads.

        Args:
            file_path: Path to the file
            mode: File open mode

        Yields:
            File handle with lock acquired
        """
        # Create file if it doesn't exist for write modes
        if "w" in mode or "a" in mode or "+" in mode:
            file_path.touch(exist_ok=True)

        if not file_path.exists():
            raise FileAccessError(f"Log file not found: {file_path}")

        f = None
        try:
            f = open(file_path, mode, encoding="utf-8")

            # Determine lock type based on mode
            if "r" in mode and "+" not in mode and "w" not in mode and "a" not in mode:
                # Read-only: shared lock
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            else:
                # Write mode: exclusive lock
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)

            yield f

        except IOError as e:
            raise FileAccessError(f"Failed to access log file: {e}")
        finally:
            if f:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                except:
                    pass
                f.close()

    def append(self, entry: LogEntry) -> LogEntry:
        """
        Append a log entry to the profile's log file.

        Args:
            entry: LogEntry to persist

        Returns:
            The persisted LogEntry

        Raises:
            FileAccessError: If file operations fail
        """
        if not entry.profile_id:
            raise LogStorageError("LogEntry must have a profile_id")

        file_path = self._get_log_file_path(entry.profile_id)

        with self._file_lock(file_path, "a") as f:
            f.write(entry.to_jsonl() + "\n")

        return entry

    def append_many(self, entries: List[LogEntry]) -> List[LogEntry]:
        """
        Append multiple log entries efficiently.

        All entries must belong to the same profile.

        Args:
            entries: List of LogEntry objects to persist

        Returns:
            List of persisted LogEntry objects

        Raises:
            LogStorageError: If entries belong to different profiles
            FileAccessError: If file operations fail
        """
        if not entries:
            return []

        # Validate all entries have same profile_id
        profile_ids = set(e.profile_id for e in entries)
        if len(profile_ids) > 1:
            raise LogStorageError("All entries must belong to the same profile")

        profile_id = entries[0].profile_id
        if not profile_id:
            raise LogStorageError("LogEntry must have a profile_id")

        file_path = self._get_log_file_path(profile_id)

        with self._file_lock(file_path, "a") as f:
            for entry in entries:
                f.write(entry.to_jsonl() + "\n")

        return entries

    def get_all(
        self,
        profile_id: str,
        include_deleted: bool = False
    ) -> List[LogEntry]:
        """
        Get all log entries for a profile.

        Args:
            profile_id: Profile identifier
            include_deleted: If True, include logically deleted entries

        Returns:
            List of LogEntry objects

        Raises:
            FileAccessError: If file operations fail
        """
        file_path = self._get_log_file_path(profile_id)

        if not file_path.exists():
            return []

        entries = []
        with self._file_lock(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = LogEntry.from_jsonl(line)
                    if include_deleted or not entry.is_deleted:
                        entries.append(entry)
                except Exception as e:
                    # Log parsing error but continue
                    # In production, this should be logged properly
                    continue

        return entries

    def get_by_id(self, profile_id: str, entry_id: str) -> Optional[LogEntry]:
        """
        Get a specific log entry by ID.

        Args:
            profile_id: Profile identifier
            entry_id: LogEntry ID

        Returns:
            LogEntry if found, None otherwise
        """
        entries = self.get_all(profile_id, include_deleted=True)
        for entry in entries:
            if entry.id == entry_id:
                return entry
        return None

    def get_by_date_range(
        self,
        profile_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_deleted: bool = False
    ) -> List[LogEntry]:
        """
        Get log entries within a date range.

        Args:
            profile_id: Profile identifier
            start_date: Start of date range (inclusive). If None, no lower bound.
            end_date: End of date range (inclusive). If None, no upper bound.
            include_deleted: If True, include logically deleted entries

        Returns:
            List of LogEntry objects within the date range
        """
        entries = self.get_all(profile_id, include_deleted=include_deleted)

        filtered = []
        for entry in entries:
            try:
                entry_date = datetime.fromisoformat(entry.timestamp)

                if start_date and entry_date < start_date:
                    continue
                if end_date and entry_date > end_date:
                    continue

                filtered.append(entry)
            except ValueError:
                # Skip entries with invalid timestamps
                continue

        return filtered

    def update(self, entry: LogEntry) -> LogEntry:
        """
        Update an existing log entry.

        This rewrites the entire file with the updated entry.
        For frequent updates, consider using a different storage strategy.

        Args:
            entry: LogEntry with updated data

        Returns:
            The updated LogEntry

        Raises:
            LogNotFoundError: If the entry doesn't exist
            FileAccessError: If file operations fail
        """
        if not entry.profile_id:
            raise LogStorageError("LogEntry must have a profile_id")

        file_path = self._get_log_file_path(entry.profile_id)

        if not file_path.exists():
            raise LogNotFoundError(f"Log entry not found: {entry.id}")

        # Read all entries, update the matching one, and rewrite
        entries = []
        found = False

        with self._file_lock(file_path, "r+") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    existing = LogEntry.from_jsonl(line)
                    if existing.id == entry.id:
                        entries.append(entry)
                        found = True
                    else:
                        entries.append(existing)
                except Exception:
                    continue

            if not found:
                raise LogNotFoundError(f"Log entry not found: {entry.id}")

            # Rewrite the file
            f.seek(0)
            f.truncate()
            for e in entries:
                f.write(e.to_jsonl() + "\n")

        return entry

    def soft_delete(self, profile_id: str, entry_id: str) -> LogEntry:
        """
        Mark a log entry as deleted (logical deletion).

        Args:
            profile_id: Profile identifier
            entry_id: LogEntry ID to delete

        Returns:
            The deleted LogEntry

        Raises:
            LogNotFoundError: If the entry doesn't exist
        """
        entry = self.get_by_id(profile_id, entry_id)
        if not entry:
            raise LogNotFoundError(f"Log entry not found: {entry_id}")

        entry.is_deleted = True
        return self.update(entry)

    def restore(self, profile_id: str, entry_id: str) -> LogEntry:
        """
        Restore a logically deleted entry.

        Args:
            profile_id: Profile identifier
            entry_id: LogEntry ID to restore

        Returns:
            The restored LogEntry

        Raises:
            LogNotFoundError: If the entry doesn't exist
        """
        entry = self.get_by_id(profile_id, entry_id)
        if not entry:
            raise LogNotFoundError(f"Log entry not found: {entry_id}")

        entry.is_deleted = False
        return self.update(entry)

    def hard_delete(self, profile_id: str, entry_id: str) -> bool:
        """
        Permanently delete a log entry from storage.

        WARNING: This operation cannot be undone.

        Args:
            profile_id: Profile identifier
            entry_id: LogEntry ID to delete permanently

        Returns:
            True if entry was deleted, False if not found
        """
        file_path = self._get_log_file_path(profile_id)

        if not file_path.exists():
            return False

        entries = []
        found = False

        with self._file_lock(file_path, "r+") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    existing = LogEntry.from_jsonl(line)
                    if existing.id == entry_id:
                        found = True
                    else:
                        entries.append(existing)
                except Exception:
                    continue

            if not found:
                return False

            # Rewrite the file without the deleted entry
            f.seek(0)
            f.truncate()
            for e in entries:
                f.write(e.to_jsonl() + "\n")

        return True

    def count(self, profile_id: str, include_deleted: bool = False) -> int:
        """
        Count log entries for a profile.

        Args:
            profile_id: Profile identifier
            include_deleted: If True, include logically deleted entries

        Returns:
            Number of entries
        """
        return len(self.get_all(profile_id, include_deleted=include_deleted))

    def exists(self, profile_id: str) -> bool:
        """
        Check if a log file exists for a profile.

        Args:
            profile_id: Profile identifier

        Returns:
            True if log file exists
        """
        return self._get_log_file_path(profile_id).exists()

    def delete_log_file(self, profile_id: str) -> bool:
        """
        Delete the entire log file for a profile.

        WARNING: This operation cannot be undone.

        Args:
            profile_id: Profile identifier

        Returns:
            True if file was deleted, False if it didn't exist
        """
        file_path = self._get_log_file_path(profile_id)

        if not file_path.exists():
            return False

        try:
            os.remove(file_path)
            return True
        except OSError as e:
            raise FileAccessError(f"Failed to delete log file: {e}")

    def compact(self, profile_id: str) -> int:
        """
        Compact the log file by removing logically deleted entries.

        This is a maintenance operation that permanently removes soft-deleted
        entries to reclaim disk space.

        Args:
            profile_id: Profile identifier

        Returns:
            Number of entries removed
        """
        file_path = self._get_log_file_path(profile_id)

        if not file_path.exists():
            return 0

        entries = []
        deleted_count = 0

        with self._file_lock(file_path, "r+") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = LogEntry.from_jsonl(line)
                    if entry.is_deleted:
                        deleted_count += 1
                    else:
                        entries.append(entry)
                except Exception:
                    continue

            # Rewrite the file without deleted entries
            f.seek(0)
            f.truncate()
            for e in entries:
                f.write(e.to_jsonl() + "\n")

        return deleted_count

    def search(
        self,
        profile_id: str,
        predicate: Callable[[LogEntry], bool],
        include_deleted: bool = False
    ) -> List[LogEntry]:
        """
        Search log entries using a custom predicate function.

        Args:
            profile_id: Profile identifier
            predicate: Function that returns True for matching entries
            include_deleted: If True, include logically deleted entries

        Returns:
            List of matching LogEntry objects
        """
        entries = self.get_all(profile_id, include_deleted=include_deleted)
        return [e for e in entries if predicate(e)]

    def get_log_file_size(self, profile_id: str) -> int:
        """
        Get the size of the log file in bytes.

        Args:
            profile_id: Profile identifier

        Returns:
            File size in bytes, 0 if file doesn't exist
        """
        file_path = self._get_log_file_path(profile_id)
        if file_path.exists():
            return file_path.stat().st_size
        return 0
