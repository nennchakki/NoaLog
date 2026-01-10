# LogStorage Module Implementation Report

**Date:** 2026-01-04
**Author:** backend-dev
**Window:** 3
**Status:** Completed

---

## Overview

LogStorageモジュールは、NoaLogアプリケーションのログエントリを永続化するためのストレージレイヤーを提供します。JSONL（JSON Lines）形式を採用し、プロファイルごとに独立したログファイルを管理します。

### Implemented Files

| File | Description |
|------|-------------|
| `/src/core/storage/log_storage.py` | LogStorageクラス本体 |
| `/src/core/storage/__init__.py` | モジュールエクスポート |

---

## File Format Specification

### JSONL Format

各ログエントリは1行のJSONとして保存されます。

```
{"id": "uuid", "profile_id": "...", "timestamp": "...", ...}\n
{"id": "uuid", "profile_id": "...", "timestamp": "...", ...}\n
```

### File Location

```
~/.noalog/logs/{profile_id}.jsonl
```

### Entry Schema

```json
{
  "id": "string (UUID)",
  "profile_id": "string",
  "timestamp": "string (ISO 8601)",
  "log_type": "dialogue | narration",
  "raw_header": "string",
  "raw_body": "string",
  "speaker_name": "string",
  "speaker_org": "string",
  "body_text": "string",
  "edited_speaker_name": "string | null",
  "edited_speaker_org": "string | null",
  "edited_body_text": "string | null",
  "is_deleted": "boolean",
  "is_duplicate": "boolean"
}
```

---

## Class/Method Reference

### LogStorage Class

メインのストレージクラス。

#### Constructor

```python
LogStorage(base_dir: Optional[Path] = None)
```

- `base_dir`: ログファイルの保存先ディレクトリ（デフォルト: `Config.get_logs_dir()`）

#### Core Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `append(entry)` | ログエントリを追記 | `LogEntry` |
| `append_many(entries)` | 複数エントリを一括追記 | `List[LogEntry]` |
| `get_all(profile_id, include_deleted)` | 全ログ取得 | `List[LogEntry]` |
| `get_by_id(profile_id, entry_id)` | ID指定で取得 | `Optional[LogEntry]` |
| `get_by_date_range(profile_id, start_date, end_date, include_deleted)` | 日付範囲でフィルタ | `List[LogEntry]` |
| `update(entry)` | ログエントリを更新 | `LogEntry` |
| `soft_delete(profile_id, entry_id)` | 論理削除 | `LogEntry` |
| `restore(profile_id, entry_id)` | 論理削除から復元 | `LogEntry` |
| `hard_delete(profile_id, entry_id)` | 物理削除 | `bool` |
| `compact(profile_id)` | 論理削除エントリを完全削除 | `int` |
| `search(profile_id, predicate, include_deleted)` | カスタム検索 | `List[LogEntry]` |

#### Utility Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `count(profile_id, include_deleted)` | エントリ数をカウント | `int` |
| `exists(profile_id)` | ログファイル存在確認 | `bool` |
| `delete_log_file(profile_id)` | ログファイル全体を削除 | `bool` |
| `get_log_file_size(profile_id)` | ファイルサイズ取得 | `int` |

### Exception Classes

| Exception | Description |
|-----------|-------------|
| `LogStorageError` | ベース例外クラス |
| `FileAccessError` | ファイル操作失敗 |
| `LogNotFoundError` | ログエントリが見つからない |

---

## Error Handling

### File Operations

```python
try:
    storage.append(entry)
except FileAccessError as e:
    # ファイルアクセスエラー（権限、ディスク容量など）
    logger.error(f"Failed to write log: {e}")
```

### Entry Not Found

```python
try:
    storage.update(entry)
except LogNotFoundError as e:
    # エントリが存在しない
    logger.warning(f"Entry not found: {e}")
```

### Validation Errors

```python
try:
    storage.append(entry_without_profile_id)
except LogStorageError as e:
    # profile_idが未設定
    logger.error(f"Invalid entry: {e}")
```

### JSONL Parse Errors

パース不能な行はスキップされ、処理を継続します。本番環境では適切なログ記録が推奨されます。

---

## Concurrency & File Locking

### Lock Mechanism

`fcntl`モジュールを使用したPOSIX互換のファイルロックを実装。

```python
@contextmanager
def _file_lock(self, file_path: Path, mode: str = "r+"):
    """
    - Read-only mode: Shared lock (LOCK_SH)
    - Write modes: Exclusive lock (LOCK_EX)
    """
```

### Lock Types

| Operation | Lock Type | Description |
|-----------|-----------|-------------|
| `get_all()` | Shared (LOCK_SH) | 複数の読み取りを許可 |
| `append()` | Exclusive (LOCK_EX) | 排他的書き込み |
| `update()` | Exclusive (LOCK_EX) | 排他的読み書き |

### Thread Safety

- 同一プロセス内の複数スレッドからのアクセスは、ファイルロックにより安全
- 複数プロセスからの同時アクセスも対応

---

## Performance Considerations

### Append-Only Write

追記モードにより、書き込みはO(1)の時間複雑度。

```python
# Efficient: Single append
storage.append(entry)

# More efficient for bulk: Batch append
storage.append_many([entry1, entry2, entry3])
```

### Update/Delete Operations

更新・削除操作はファイル全体の再書き込みが必要（O(n)）。

```python
# Warning: Full file rewrite
storage.update(entry)  # O(n)
storage.soft_delete(profile_id, entry_id)  # O(n)
```

### Recommended Practices

1. **大量更新の回避**: 頻繁な更新が必要な場合はインメモリキャッシュを検討
2. **バッチ処理**: 複数エントリの追加は`append_many()`を使用
3. **定期的なcompact**: 論理削除が蓄積したら`compact()`でファイルサイズを最適化

### Memory Usage

`get_all()`は全エントリをメモリにロードするため、大量のログがある場合は注意が必要。将来的にはページネーション対応を検討。

---

## Usage Examples

### Basic CRUD

```python
from src.core.storage import LogStorage
from src.models import LogEntry

storage = LogStorage()

# Create
entry = LogEntry(profile_id="profile-123", speaker_name="Alice", body_text="Hello")
storage.append(entry)

# Read
all_entries = storage.get_all("profile-123")
single_entry = storage.get_by_id("profile-123", entry.id)

# Update (with edit tracking)
entry.edited_body_text = "Hello, World!"
storage.update(entry)

# Delete (soft)
storage.soft_delete("profile-123", entry.id)

# Restore
storage.restore("profile-123", entry.id)
```

### Date Range Filtering

```python
from datetime import datetime

start = datetime(2026, 1, 1)
end = datetime(2026, 1, 31)

january_logs = storage.get_by_date_range(
    "profile-123",
    start_date=start,
    end_date=end
)
```

### Custom Search

```python
# Search by speaker name
alice_logs = storage.search(
    "profile-123",
    predicate=lambda e: e.speaker_name == "Alice"
)

# Search edited entries
edited_logs = storage.search(
    "profile-123",
    predicate=lambda e: e.edited_body_text is not None
)
```

---

## Integration Points

### For frontend-dev

```python
# API endpoint implementation example
@app.route("/api/profiles/<profile_id>/logs")
def get_logs(profile_id):
    storage = LogStorage()
    entries = storage.get_all(profile_id)
    return jsonify([e.to_dict() for e in entries])
```

### For test-engineer

**Test Targets:**
- `append()` / `append_many()` - 正常系・異常系
- `get_all()` - 空ファイル、大量データ
- `update()` - 存在しないエントリ
- `soft_delete()` / `restore()` - 論理削除フロー
- `_file_lock()` - 並行アクセス

**Test Data Requirements:**
- 様々な`LogType`を持つエントリ
- 編集済みフィールドを持つエントリ
- 論理削除されたエントリ

---

## Dependencies

- Python 3.9+
- Standard library only (`pathlib`, `fcntl`, `json`, `datetime`, `contextlib`)
- Internal: `src.config.Config`, `src.models.LogEntry`

---

## Future Enhancements

1. **Pagination**: `get_all()`にオフセット/リミットサポート
2. **Index**: 高速検索のためのインデックスファイル
3. **Compression**: 古いログの自動圧縮
4. **Backup**: 自動バックアップ機能
5. **Windows Support**: `fcntl`の代わりに`msvcrt`を使用したWindows対応
