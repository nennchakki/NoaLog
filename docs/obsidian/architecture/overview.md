# NoaLog アーキテクチャ概要

## システム構成図

```mermaid
graph TB
    subgraph UI["UI Layer (PySide6)"]
        MW[MainWindow]
        PE[ProfileEditor]
        CO[CaptureOverlay]
    end

    subgraph Controller["Application Controller"]
        AC[AppController]
    end

    subgraph Core["Core Modules"]
        SC[ScreenCapture<br/>mss]
        HK[HotkeyManager<br/>pynput]
        OCR[OCREngine<br/>PaddleOCR/EasyOCR]
    end

    subgraph Storage["Storage Layer"]
        LS[LogStorage<br/>JSONL]
        EX[Exporter<br/>txt/csv/json/md]
    end

    subgraph Data["Data Models"]
        P[Profile]
        LE[LogEntry]
        R[Rect]
        HKM[Hotkey]
    end

    MW --> AC
    PE --> AC
    CO --> AC

    AC --> SC
    AC --> HK
    AC --> OCR
    AC --> LS
    AC --> EX

    SC --> R
    HK --> HKM
    LS --> LE
    EX --> LE

    AC --> P
    AC --> LE
```

## モジュール一覧

| モジュール | パス | 責務 |
|-----------|------|------|
| ScreenCapture | `core/capture/screen_capture.py` | mssライブラリによる画面キャプチャ |
| HotkeyManager | `core/hotkey/hotkey_manager.py` | グローバルホットキー監視 |
| OCREngine | `core/ocr/ocr_engine.py` | テキスト認識（PaddleOCR/EasyOCR） |
| LogStorage | `core/storage/log_storage.py` | JSONL形式での永続化 |
| Exporter | `core/storage/exporter.py` | 各種フォーマットへのエクスポート |
| MainWindow | `ui/views/main_window.py` | メインUI |
| ProfileEditor | `ui/views/profile_editor.py` | プロファイル編集ダイアログ |
| CaptureOverlay | `ui/widgets/capture_overlay.py` | 領域選択オーバーレイ |
| AppController | `app_controller.py` | アプリケーション統合 |

## キャプチャフロー

```mermaid
sequenceDiagram
    participant U as User
    participant HK as HotkeyManager
    participant AC as AppController
    participant SC as ScreenCapture
    participant OCR as OCREngine
    participant LS as LogStorage
    participant UI as MainWindow

    U->>HK: Cmd+Shift+L
    HK->>AC: hotkey_triggered()
    AC->>AC: get_current_profile()
    AC->>SC: capture_region(header_rect)
    SC-->>AC: header_image
    AC->>SC: capture_region(body_rect)
    SC-->>AC: body_image
    AC->>OCR: recognize_header(header_image)
    OCR-->>AC: header_text
    AC->>OCR: recognize_body(body_image)
    OCR-->>AC: body_text
    AC->>AC: create_log_entry()
    AC->>LS: save(log_entry)
    AC->>UI: add_log_entry(log_entry)
    UI-->>U: 表示更新
```

## データフロー

```
[画面] → [キャプチャ] → [前処理] → [OCR] → [パース] → [LogEntry] → [Storage/UI]
```

## 設計原則

1. **関心の分離**: Core/UI/Storageの明確な分離
2. **シグナル駆動**: Qt Signalによる疎結合な通信
3. **プロファイル駆動**: 設定はすべてProfileに集約
4. **非破壊編集**: raw_*とedited_*の分離
5. **クロスプラットフォーム**: macOS/Windows両対応
