# LogExporter モジュール実装レポート

## 概要

`LogExporter` は NoaLog のログエントリを様々なフォーマットでエクスポートするためのモジュールです。複数の出力形式、柔軟なフィルタリング、カスタマイズ可能なタイムスタンプ形式をサポートしています。

**実装ファイル**: `/Users/dansetsu/NoaLog/src/core/storage/exporter.py`

---

## 対応フォーマット

| フォーマット | 拡張子 | 説明 |
|-------------|--------|------|
| TEXT | .txt | プレーンテキスト形式 |
| CSV | .csv | タイムスタンプ、話者、所属、本文のカラム構成 |
| JSON | .json | メタデータ付き構造化データ |
| MARKDOWN | .md | 見出し・引用を使った読みやすい形式 |

---

## 各フォーマットの出力例

### TEXT形式 (.txt)

```text
[2026-01-04 10:30:00]
Alice / Marketing
This is a test message from Alice.
---
[2026-01-04 10:31:00]
Bob / Engineering
Hello Alice! Nice to meet you.
---
[2026-01-04 10:32:00]
[Narration]
The two colleagues shook hands.
```

### CSV形式 (.csv)

```csv
"timestamp","speaker_name","speaker_org","body_text","log_type"
"2026-01-04 10:30:00","Alice","Marketing","This is a test message from Alice.","dialogue"
"2026-01-04 10:31:00","Bob","Engineering","Hello Alice! Nice to meet you.","dialogue"
"2026-01-04 10:32:00","","","The two colleagues shook hands.","narration"
```

### JSON形式 (.json)

```json
{
  "export_info": {
    "exported_at": "2026-01-04T15:30:00",
    "entry_count": 3,
    "format_version": "1.0"
  },
  "entries": [
    {
      "id": "1",
      "timestamp": "2026-01-04 10:30:00",
      "log_type": "dialogue",
      "speaker": {
        "name": "Alice",
        "organization": "Marketing"
      },
      "body": "This is a test message from Alice.",
      "profile_id": "test-profile"
    }
  ]
}
```

### Markdown形式 (.md)

```markdown
# NoaLog Export

Exported at: 2026-01-04 15:30:00
Entry count: 3

---

#### 2026-01-04 10:30:00

**Alice / Marketing**

> This is a test message from Alice.

---

#### 2026-01-04 10:31:00

**Bob / Engineering**

> Hello Alice! Nice to meet you.

---

#### 2026-01-04 10:32:00

*The two colleagues shook hands.*

---
```

---

## クラス・メソッド説明

### ExportFormat (Enum)

サポートする出力フォーマットを定義:
- `TEXT` - テキスト形式
- `CSV` - CSV形式
- `JSON` - JSON形式
- `MARKDOWN` - Markdown形式

### TimestampFormat (Enum)

タイムスタンプの出力形式:
- `ISO` - `2026-01-04T12:30:45`
- `DATETIME` - `2026-01-04 12:30:45` (デフォルト)
- `DATE_ONLY` - `2026-01-04`
- `TIME_ONLY` - `12:30:45`
- `COMPACT` - `20260104_123045`

### ExportOptions (dataclass)

エクスポートの動作を制御するオプション:

| オプション | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `start_date` | datetime | None | 開始日時フィルタ |
| `end_date` | datetime | None | 終了日時フィルタ |
| `speaker_filter` | List[str] | None | 話者名フィルタ |
| `exclude_deleted` | bool | True | 削除済みを除外 |
| `exclude_duplicates` | bool | False | 重複を除外 |
| `timestamp_format` | TimestampFormat | DATETIME | タイムスタンプ形式 |
| `include_timestamp` | bool | True | タイムスタンプを含める |
| `entry_separator` | str | "\n---\n" | エントリ間の区切り |
| `use_display_values` | bool | True | 編集済み値を優先 |
| `include_narration` | bool | True | ナレーションを含める |

### ExportResult (dataclass)

エクスポート結果:

| 属性 | 型 | 説明 |
|------|-----|------|
| `success` | bool | 成功/失敗 |
| `content` | str | エクスポートされた内容 |
| `file_path` | Path | 保存先パス（指定時） |
| `entry_count` | int | 出力されたエントリ数 |
| `filtered_count` | int | フィルタで除外された数 |
| `error_message` | str | エラーメッセージ |

### LogExporter クラス

主要メソッド:

#### コンストラクタ・基本操作

```python
# 初期化
exporter = LogExporter(entries: List[LogEntry])

# エントリ操作
exporter.set_entries(entries)
exporter.add_entry(entry)
exporter.clear_entries()
```

#### エクスポートメソッド

```python
# 汎用エクスポート
result = exporter.export(
    format_type: ExportFormat,
    options: ExportOptions = None,
    output_path: Path = None
) -> ExportResult

# 便利メソッド
result = exporter.export_to_text(output_path, options)
result = exporter.export_to_csv(output_path, options)
result = exporter.export_to_json(output_path, options)
result = exporter.export_to_markdown(output_path, options)
```

#### CopyFormat プリセット活用

```python
# 単一エントリのフォーマット
formatted = exporter.format_entry_with_preset(
    entry: LogEntry,
    preset_name: str = "plain",  # plain, markdown, quote, script
    use_display_values: bool = True
)

# 複数エントリのフォーマット
formatted = exporter.format_entries_with_preset(
    entries: List[LogEntry] = None,
    preset_name: str = "plain",
    use_display_values: bool = True,
    separator: str = "\n\n"
)
```

#### 統計情報

```python
stats = exporter.get_export_statistics(options: ExportOptions = None)
# 返値:
# {
#   "total_entries": 10,
#   "filtered_entries": 8,
#   "excluded_count": 2,
#   "speaker_counts": {"Alice": 5, "Bob": 3},
#   "type_counts": {"dialogue": 7, "narration": 1},
#   "date_range": {"earliest": "...", "latest": "..."}
# }
```

---

## 使用例

### 基本的な使用

```python
from src.core.storage.exporter import LogExporter, ExportFormat, ExportOptions
from src.models import LogEntry

# ログエントリを取得（例: LogStorageから）
entries = log_storage.get_all_logs()

# エクスポーター初期化
exporter = LogExporter(entries)

# Markdown形式でエクスポート
result = exporter.export_to_markdown(
    output_path=Path("~/Documents/log_export.md")
)

if result.success:
    print(f"Exported {result.entry_count} entries to {result.file_path}")
```

### フィルタリング付きエクスポート

```python
from datetime import datetime

# オプション設定
options = ExportOptions(
    # 日付範囲フィルタ
    start_date=datetime(2026, 1, 1),
    end_date=datetime(2026, 1, 31),

    # 特定の話者のみ
    speaker_filter=["Alice", "Bob"],

    # 削除済みと重複を除外
    exclude_deleted=True,
    exclude_duplicates=True,

    # タイムスタンプ形式
    timestamp_format=TimestampFormat.DATE_ONLY,

    # ナレーションを除外
    include_narration=False
)

# CSV形式でエクスポート
result = exporter.export_to_csv(options=options)
print(result.content)
```

### コピー用フォーマット

```python
# CopyFormatプリセットを使用
exporter = LogExporter(entries)

# Script形式（名前: セリフ）
formatted = exporter.format_entries_with_preset(
    preset_name="script",
    separator="\n"
)
# 出力例:
# Alice: Hello, how are you?
# Bob: I'm fine, thank you!

# Quote形式（引用スタイル）
formatted = exporter.format_entries_with_preset(
    preset_name="quote",
    separator="\n\n"
)
# 出力例:
# > Hello, how are you?
# > -- Alice / Marketing
```

### 統計情報の取得

```python
exporter = LogExporter(entries)
stats = exporter.get_export_statistics()

print(f"総エントリ数: {stats['total_entries']}")
print(f"話者別: {stats['speaker_counts']}")
print(f"種別: {stats['type_counts']}")
print(f"期間: {stats['date_range']['earliest']} ~ {stats['date_range']['latest']}")
```

---

## アーキテクチャ

```
LogExporter
    |
    +-- ExportFormat (Enum)
    |       TEXT, CSV, JSON, MARKDOWN
    |
    +-- TimestampFormat (Enum)
    |       ISO, DATETIME, DATE_ONLY, TIME_ONLY, COMPACT
    |
    +-- ExportOptions (dataclass)
    |       フィルタリングとフォーマットオプション
    |
    +-- ExportResult (dataclass)
    |       エクスポート結果
    |
    +-- CopyFormat (models.py)
            プリセットテンプレート連携
```

---

## 拡張性

### 新しいフォーマットの追加

1. `ExportFormat` Enumに新しい値を追加
2. `_export_xxx()` メソッドを実装
3. `export()` メソッドの分岐に追加

```python
class ExportFormat(Enum):
    # 既存
    TEXT = "txt"
    CSV = "csv"
    JSON = "json"
    MARKDOWN = "md"
    # 新規追加
    HTML = "html"

# 実装例
def _export_html(self, entries: List[LogEntry], options: ExportOptions) -> str:
    lines = ["<!DOCTYPE html>", "<html>", "<body>"]
    for entry in entries:
        lines.append(f"<div class='entry'>")
        lines.append(f"  <strong>{entry.display_header}</strong>")
        lines.append(f"  <p>{entry.display_body}</p>")
        lines.append(f"</div>")
    lines.extend(["</body>", "</html>"])
    return "\n".join(lines)
```

### カスタムフィルタの追加

`ExportOptions` にフィールドを追加し、`_filter_entries()` でハンドリング:

```python
@dataclass
class ExportOptions:
    # 既存フィールド...

    # カスタムフィルタ追加
    min_body_length: int = 0
    profile_ids: Optional[List[str]] = None
```

### CopyFormat プリセットの拡張

`models.py` の `CopyFormat.get_presets()` に新しいプリセットを追加:

```python
@classmethod
def get_presets(cls) -> Dict[str, "CopyFormat"]:
    return {
        # 既存...
        "timestamped": cls(
            name="Timestamped",
            template="[{timestamp}] {name}: {body}",
            include_timestamp=True
        ),
    }
```

---

## 関連ファイル

| ファイル | 説明 |
|----------|------|
| `/src/core/storage/exporter.py` | LogExporter 本体 |
| `/src/core/storage/__init__.py` | モジュールエクスポート |
| `/src/models.py` | LogEntry, CopyFormat 定義 |
| `/src/config.py` | 設定管理 |

---

## 完了報告

### 実装ファイル
- [x] `/src/core/storage/exporter.py` - LogExporter モジュール
- [x] `/src/core/storage/__init__.py` - エクスポート追加

### 実装機能
| 機能 | ステータス |
|------|-----------|
| TEXT エクスポート | 完了 |
| CSV エクスポート | 完了 |
| JSON エクスポート | 完了 |
| Markdown エクスポート | 完了 |
| 日付範囲フィルタ | 完了 |
| 話者フィルタ | 完了 |
| 削除済み除外 | 完了 |
| タイムスタンプ形式選択 | 完了 |
| CopyFormat 連携 | 完了 |
| 統計情報取得 | 完了 |

### test-engineer への引き継ぎ
- テスト対象: `LogExporter` クラス
- 重点テスト箇所:
  - 各フォーマット出力の正確性
  - フィルタリングロジック
  - 日付パース・フォーマット
  - エッジケース（空エントリ、不正な日付など）

### frontend-dev への連携
- 利用可能なクラス: `LogExporter`, `ExportFormat`, `ExportOptions`
- 使用例: 上記「使用例」セクション参照
