"""
NoaLog Application Controller

各モジュールを統合し、キャプチャフローを制御するメインコントローラー。
ファサードパターンにより、ScreenCapture、HotkeyManager、OCREngine、MainWindowを統合。
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Callable

from PySide6.QtCore import QObject, Signal, Slot, QTimer

from models import Profile, LogEntry, Rect, Hotkey, LogType
from config import Config, HEADER_PARSE
from core.capture.screen_capture import ScreenCapture, ScreenCaptureError
from core.hotkey.hotkey_manager import HotkeyManager
from core.ocr.ocr_engine import OCREngine, OCREngineError, OCRResult

logger = logging.getLogger(__name__)


class AppControllerError(Exception):
    """AppController関連のエラー。"""
    pass


class AppController(QObject):
    """
    アプリケーション統合コントローラー。

    各モジュール（ScreenCapture、HotkeyManager、OCREngine、MainWindow）を統合し、
    キャプチャフロー全体を制御する。

    キャプチャフロー:
        1. ホットキー検出またはUIボタン押下
        2. 現在のプロファイルからヘッダー/ボディ領域を取得
        3. 画面キャプチャ実行
        4. OCR実行（ヘッダー→話者名抽出、ボディ→本文抽出）
        5. LogEntry作成
        6. UIに通知
        7. ストレージに保存

    Attributes:
        config: アプリケーション設定
        current_profile: 現在選択中のプロファイル
    """

    # シグナル
    capture_started = Signal()
    capture_completed = Signal(LogEntry)  # 作成されたLogEntry
    capture_failed = Signal(str)  # エラーメッセージ
    ocr_engine_ready = Signal(str)  # エンジン種別
    profile_changed = Signal(Profile)
    region_selection_started = Signal()
    region_selection_completed = Signal(object, object)  # header_rect, body_rect

    def __init__(self, config: Config, parent: Optional[QObject] = None):
        """
        AppControllerを初期化。

        Args:
            config: アプリケーション設定
            parent: 親QObject
        """
        super().__init__(parent)

        self.config = config
        self._current_profile: Optional[Profile] = None
        self._profiles: List[Profile] = []
        self._log_entries: List[LogEntry] = []
        self._hotkey_id: Optional[str] = None
        self._is_capturing = False

        # モジュール初期化
        self._screen_capture: Optional[ScreenCapture] = None
        self._hotkey_manager: Optional[HotkeyManager] = None
        self._ocr_engine: Optional[OCREngine] = None
        self._main_window = None  # 循環インポート回避のため後から設定

        # 範囲指定モード用
        self._capture_overlay = None
        self._region_selection_hotkey_id: Optional[str] = None
        self._capture_hotkey_id: Optional[str] = None

        # 初期化フラグ
        self._initialized = False

        logger.info("AppController created")

    def initialize(self) -> bool:
        """
        各モジュールを初期化。

        Returns:
            bool: 初期化成功時True

        Raises:
            AppControllerError: 初期化失敗時
        """
        if self._initialized:
            logger.warning("AppController already initialized")
            return True

        try:
            # ScreenCapture初期化
            self._init_screen_capture()

            # HotkeyManager初期化
            self._init_hotkey_manager()

            # OCREngine初期化（遅延初期化も可能）
            self._init_ocr_engine()

            self._initialized = True
            logger.info("AppController initialized successfully")
            return True

        except Exception as e:
            logger.error(f"AppController initialization failed: {e}")
            raise AppControllerError(f"Initialization failed: {e}") from e

    def _init_screen_capture(self) -> None:
        """ScreenCaptureを初期化。"""
        try:
            self._screen_capture = ScreenCapture()
            monitors = self._screen_capture.get_monitors()
            logger.info(f"ScreenCapture initialized: {len(monitors)} monitors detected")
        except Exception as e:
            logger.error(f"Failed to initialize ScreenCapture: {e}")
            raise

    def _init_hotkey_manager(self) -> None:
        """HotkeyManagerを初期化。"""
        try:
            hotkey_config = self.config.load_config().get("hotkey", {})
            throttle_ms = hotkey_config.get("throttle_ms", 500)
            self._hotkey_manager = HotkeyManager(throttle_ms=throttle_ms)
            logger.info(f"HotkeyManager initialized (throttle: {throttle_ms}ms)")
        except Exception as e:
            logger.error(f"Failed to initialize HotkeyManager: {e}")
            raise

    def _init_ocr_engine(self) -> None:
        """OCREngineを初期化。"""
        try:
            ocr_config = self.config.load_config().get("ocr", {})
            self._ocr_engine = OCREngine(
                lang=ocr_config.get("lang", "japan"),
                use_gpu=ocr_config.get("use_gpu", False),
                use_angle_cls=ocr_config.get("use_angle_cls", True),
            )
            engine_info = self._ocr_engine.get_engine_info()
            logger.info(f"OCREngine initialized: {engine_info['engine_type']}")
            self.ocr_engine_ready.emit(engine_info["engine_type"])
        except OCREngineError as e:
            logger.error(f"Failed to initialize OCREngine: {e}")
            # OCRエンジンなしでも動作可能とするが、警告を出す
            self._ocr_engine = None
            logger.warning("Running without OCR engine - capture will fail")

    def set_main_window(self, window) -> None:
        """
        MainWindowを設定し、シグナルを接続。

        Args:
            window: MainWindowインスタンス
        """
        from ui.views.main_window import MainWindow

        self._main_window = window

        # MainWindowのシグナルを接続
        window.capture_requested.connect(self.on_capture_requested)
        window.profile_changed.connect(self._on_ui_profile_changed)
        window.hotkey_settings_changed.connect(self._on_hotkey_settings_changed)

        # AppControllerのシグナルをMainWindowに接続
        self.capture_completed.connect(window.add_log_entry)
        self.capture_started.connect(lambda: window.set_status("キャプチャ中..."))
        self.capture_failed.connect(lambda msg: window.set_status(f"エラー: {msg}"))
        self.ocr_engine_ready.connect(window.set_ocr_status)

        logger.info("MainWindow connected to AppController")

    def set_profiles(self, profiles: List[Profile]) -> None:
        """
        プロファイルリストを設定。

        Args:
            profiles: プロファイルのリスト
        """
        self._profiles = profiles

        # MainWindowに反映
        if self._main_window:
            self._main_window.set_profiles(profiles)

        # 最初のプロファイルを選択
        if profiles:
            self.set_current_profile(profiles[0])

        logger.info(f"Profiles set: {len(profiles)} profiles")

    def set_current_profile(self, profile: Profile) -> None:
        """
        現在のプロファイルを設定。

        Args:
            profile: 選択するプロファイル
        """
        # 既存のホットキーを解除
        self._unregister_hotkey()

        self._current_profile = profile

        # 新しいホットキーを登録
        if profile.hotkey and self._hotkey_manager:
            self._register_hotkey(profile.hotkey)

        self.profile_changed.emit(profile)
        logger.info(f"Current profile set: {profile.name}")

    def _register_hotkey(self, hotkey: Hotkey) -> None:
        """ホットキーを登録。"""
        if not self._hotkey_manager:
            return

        try:
            self._hotkey_id = self._hotkey_manager.register_hotkey(
                hotkey, self._on_hotkey_triggered
            )
            logger.info(f"Hotkey registered: {hotkey}")
        except Exception as e:
            logger.error(f"Failed to register hotkey: {e}")

    def _unregister_hotkey(self) -> None:
        """ホットキーを解除。"""
        if self._hotkey_manager and self._hotkey_id:
            self._hotkey_manager.unregister_hotkey(self._hotkey_id)
            self._hotkey_id = None
            logger.debug("Hotkey unregistered")

    def start_hotkey_listener(self) -> None:
        """ホットキーリスナーを開始。"""
        if self._hotkey_manager and not self._hotkey_manager.is_running:
            self._hotkey_manager.start()
            logger.info("Hotkey listener started")

    def stop_hotkey_listener(self) -> None:
        """ホットキーリスナーを停止。"""
        if self._hotkey_manager and self._hotkey_manager.is_running:
            self._hotkey_manager.stop()
            logger.info("Hotkey listener stopped")

    def _on_hotkey_triggered(self) -> None:
        """ホットキーがトリガーされた時の処理。"""
        logger.debug("Hotkey triggered")
        # Qt のメインスレッドでキャプチャを実行
        QTimer.singleShot(0, self.execute_capture)

    @Slot()
    def on_capture_requested(self) -> None:
        """UIからキャプチャ要求を受けた時の処理。"""
        logger.debug("Capture requested from UI")
        self.execute_capture()

    @Slot(str)
    def _on_ui_profile_changed(self, profile_id: str) -> None:
        """UIでプロファイルが変更された時の処理。"""
        for profile in self._profiles:
            if profile.id == profile_id:
                self.set_current_profile(profile)
                break

    def execute_capture(self) -> Optional[LogEntry]:
        """
        キャプチャフローを実行。

        フロー:
            1. プロファイル確認
            2. 領域情報取得
            3. 画面キャプチャ
            4. OCR実行（ヘッダー、ボディ）
            5. LogEntry作成
            6. 通知・保存

        Returns:
            Optional[LogEntry]: 作成されたLogEntry。失敗時はNone
        """
        # 二重実行防止
        if self._is_capturing:
            logger.warning("Capture already in progress")
            return None

        self._is_capturing = True
        self.capture_started.emit()

        try:
            # 1. プロファイル確認
            if not self._current_profile:
                raise AppControllerError("No profile selected")

            profile = self._current_profile
            logger.info(f"Starting capture with profile: {profile.name}")

            # 2. 領域情報取得
            header_rect = profile.header_rect
            body_rect = profile.body_rect

            if not header_rect and not body_rect:
                raise AppControllerError(
                    "No capture regions defined in profile. "
                    "Please configure header_rect or body_rect."
                )

            # 3. 画面キャプチャ
            header_image = None
            body_image = None

            if self._screen_capture:
                if header_rect:
                    header_image = self._capture_region(header_rect, "header")
                if body_rect:
                    body_image = self._capture_region(body_rect, "body")
            else:
                raise AppControllerError("ScreenCapture not initialized")

            # 4. OCR実行
            header_result = OCRResult(text="", confidence=0.0)
            body_result = OCRResult(text="", confidence=0.0)

            if self._ocr_engine:
                if header_image is not None:
                    header_result = self._ocr_engine.recognize_header(header_image)
                    logger.debug(f"Header OCR: {header_result.text[:50]}...")

                if body_image is not None:
                    body_result = self._ocr_engine.recognize_body(body_image)
                    logger.debug(f"Body OCR: {body_result.text[:50]}...")
            else:
                logger.warning("OCR engine not available, creating empty entry")

            # 5. LogEntry作成
            entry = self._create_log_entry(
                profile=profile,
                header_result=header_result,
                body_result=body_result,
            )

            # 6. ストレージに保存（将来実装）
            self._save_log_entry(entry)

            # 7. 通知
            self._log_entries.append(entry)
            self.capture_completed.emit(entry)

            if self._main_window:
                self._main_window.set_status("キャプチャ完了")

            logger.info(f"Capture completed: {entry.id}")
            return entry

        except ScreenCaptureError as e:
            error_msg = f"Screen capture failed: {e}"
            logger.error(error_msg)
            self.capture_failed.emit(error_msg)
            return None

        except OCREngineError as e:
            error_msg = f"OCR failed: {e}"
            logger.error(error_msg)
            self.capture_failed.emit(error_msg)
            return None

        except AppControllerError as e:
            error_msg = str(e)
            logger.error(error_msg)
            self.capture_failed.emit(error_msg)
            return None

        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(error_msg, exc_info=True)
            self.capture_failed.emit(error_msg)
            return None

        finally:
            self._is_capturing = False

    def _capture_region(self, rect: Rect, region_name: str):
        """
        指定領域をキャプチャ。

        Args:
            rect: キャプチャ領域
            region_name: 領域名（ログ用）

        Returns:
            np.ndarray: キャプチャ画像

        Raises:
            ScreenCaptureError: キャプチャ失敗時
        """
        logger.debug(f"Capturing {region_name} region: {rect}")
        return self._screen_capture.capture_region(rect)

    def _create_log_entry(
        self,
        profile: Profile,
        header_result: OCRResult,
        body_result: OCRResult,
    ) -> LogEntry:
        """
        LogEntryを作成。

        Args:
            profile: 使用したプロファイル
            header_result: ヘッダーOCR結果
            body_result: ボディOCR結果

        Returns:
            LogEntry: 作成されたLogEntry
        """
        # ヘッダーから話者名・所属を抽出
        speaker_name, speaker_org = self._parse_header(header_result.text)

        # ログタイプを判定
        log_type = self._determine_log_type(speaker_name)

        entry = LogEntry(
            profile_id=profile.id,
            log_type=log_type,
            raw_header=header_result.text,
            raw_body=body_result.text,
            speaker_name=speaker_name,
            speaker_org=speaker_org,
            body_text=body_result.text.strip(),
        )

        logger.debug(f"LogEntry created: speaker={speaker_name}, type={log_type}")
        return entry

    def _parse_header(self, header_text: str) -> tuple:
        """
        ヘッダーテキストから話者名と所属を抽出。

        Args:
            header_text: ヘッダーOCR結果

        Returns:
            tuple: (speaker_name, speaker_org)
        """
        if not header_text:
            return ("", "")

        text = header_text.strip()

        # セパレータで分割を試みる
        separators = HEADER_PARSE.get("separators", ["/", "/"])
        for sep in separators:
            if sep in text:
                parts = text.split(sep, 1)
                name = parts[0].strip()
                org = parts[1].strip() if len(parts) > 1 else ""
                return (name, org)

        # セパレータがない場合は全体を名前として扱う
        return (text, "")

    def _determine_log_type(self, speaker_name: str) -> LogType:
        """
        話者名からログタイプを判定。

        Args:
            speaker_name: 話者名

        Returns:
            LogType: ログタイプ
        """
        if not speaker_name:
            return LogType.NARRATION

        # ナレーションキーワードチェック
        narrator_keywords = HEADER_PARSE.get(
            "narrator_keywords", ["地の文", "ナレーション", "語り"]
        )
        for keyword in narrator_keywords:
            if keyword in speaker_name:
                return LogType.NARRATION

        return LogType.DIALOGUE

    def _save_log_entry(self, entry: LogEntry) -> None:
        """
        LogEntryをストレージに保存。

        Args:
            entry: 保存するLogEntry
        """
        # TODO: ストレージモジュール実装後に連携
        # 現在は将来の実装のためのプレースホルダー
        logs_dir = self.config.get_logs_dir()
        log_file = logs_dir / f"session_{datetime.now().strftime('%Y%m%d')}.jsonl"

        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(entry.to_jsonl() + "\n")
            logger.debug(f"LogEntry saved to {log_file}")
        except Exception as e:
            logger.error(f"Failed to save log entry: {e}")

    def get_log_entries(self) -> List[LogEntry]:
        """現在セッションのLogEntryリストを取得。"""
        return self._log_entries.copy()

    def clear_log_entries(self) -> None:
        """現在セッションのLogEntryをクリア。"""
        self._log_entries.clear()
        if self._main_window:
            self._main_window.clear_logs()
        logger.info("Log entries cleared")

    def get_ocr_engine_info(self) -> Optional[dict]:
        """OCRエンジン情報を取得。"""
        if self._ocr_engine:
            return self._ocr_engine.get_engine_info()
        return None

    def load_profiles(self) -> List[Profile]:
        """
        保存されたプロファイルを読み込む。

        Returns:
            List[Profile]: 保存されたプロファイルのリスト（なければ空リスト）
        """
        profiles_dir = self.config.get_profiles_dir()
        profiles = []

        if not profiles_dir.exists():
            logger.info(f"Profiles directory does not exist: {profiles_dir}")
            return profiles

        for profile_file in profiles_dir.glob("*.json"):
            try:
                with open(profile_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    profile = Profile.from_dict(data)
                    profiles.append(profile)
                    logger.debug(f"Loaded profile: {profile.name}")
            except Exception as e:
                logger.warning(f"Failed to load profile {profile_file}: {e}")

        logger.info(f"Loaded {len(profiles)} profiles from {profiles_dir}")
        return profiles

    def register_region_selection_hotkey(self, hotkey: Hotkey) -> None:
        """
        範囲指定モード用のホットキーを登録。

        Args:
            hotkey: ホットキー設定
        """
        if self._hotkey_manager:
            self._region_selection_hotkey_id = self._hotkey_manager.register_hotkey(
                hotkey, self._on_region_selection_hotkey
            )
            logger.info(f"Region selection hotkey registered: {hotkey}")

    def register_global_hotkeys(self) -> None:
        """設定ファイルからグローバルホットキーを登録。"""
        if not self._hotkey_manager:
            logger.error("HotkeyManager not initialized")
            return

        hotkey_config = self.config.load_config().get("hotkey", {})

        # 範囲指定ホットキー
        region_keys = hotkey_config.get("region_selection", ["cmd", "shift", "r"])
        region_hotkey = Hotkey(keys=region_keys)
        self._region_selection_hotkey_id = self._hotkey_manager.register_hotkey(
            region_hotkey, self._on_region_selection_hotkey
        )
        logger.info(f"Region selection hotkey registered: {region_hotkey}")

        # キャプチャホットキー
        capture_keys = hotkey_config.get("capture", ["cmd", "shift", "l"])
        capture_hotkey = Hotkey(keys=capture_keys)
        self._capture_hotkey_id = self._hotkey_manager.register_hotkey(
            capture_hotkey, self._on_capture_hotkey
        )
        logger.info(f"Capture hotkey registered: {capture_hotkey}")

    def _on_capture_hotkey(self) -> None:
        """キャプチャホットキーがトリガーされた時の処理。"""
        logger.debug("Capture hotkey triggered")
        try:
            from PySide6.QtCore import QMetaObject, Qt
            QMetaObject.invokeMethod(self, "trigger_capture", Qt.ConnectionType.QueuedConnection)
        except Exception as e:
            logger.error(f"Error invoking trigger_capture: {e}")

    @Slot()
    def trigger_capture(self) -> None:
        """ホットキーからキャプチャを実行（Qtメインスレッドで実行）。"""
        logger.info("trigger_capture called")
        self.execute_capture()

    def quick_capture(self) -> Optional[LogEntry]:
        """
        保存された範囲で即座にキャプチャを実行。
        フルスクリーンアプリからでも使用可能（オーバーレイ不要）。

        Returns:
            Optional[LogEntry]: 作成されたLogEntry。失敗時はNone
        """
        if not self._current_profile:
            logger.warning("Quick capture: No profile selected")
            if self._main_window:
                self._main_window.set_status("プロファイルが選択されていません")
            return None

        if not self._current_profile.header_rect and not self._current_profile.body_rect:
            logger.warning("Quick capture: No regions defined")
            if self._main_window:
                self._main_window.set_status("キャプチャ範囲が設定されていません。範囲指定を行ってください。")
            return None

        # execute_capture を直接呼び出し（プロファイルに保存された範囲を使用）
        logger.info("Quick capture: Using saved regions")
        return self.execute_capture()

    @Slot()
    def trigger_quick_capture(self) -> None:
        """ホットキーからクイックキャプチャを実行（Qtメインスレッドで実行）。"""
        logger.info("trigger_quick_capture called")
        self.quick_capture()

    def update_capture_hotkey(self, new_keys: List[str]) -> bool:
        """
        キャプチャホットキーを更新。

        Args:
            new_keys: 新しいキーの組み合わせ（例: ["cmd", "shift", "l"]）

        Returns:
            bool: 更新成功時True
        """
        if not self._hotkey_manager or not self._capture_hotkey_id:
            return False

        new_hotkey = Hotkey(keys=new_keys)
        success = self._hotkey_manager.update_hotkey(self._capture_hotkey_id, new_hotkey)

        if success:
            # 設定に保存
            config_data = self.config.load_config()
            config_data.setdefault("hotkey", {})["capture"] = new_keys
            self.config.save_config(config_data)
            logger.info(f"Capture hotkey updated: {new_hotkey}")

        return success

    def update_region_selection_hotkey(self, new_keys: List[str]) -> bool:
        """
        範囲指定ホットキーを更新。

        Args:
            new_keys: 新しいキーの組み合わせ（例: ["cmd", "shift", "r"]）

        Returns:
            bool: 更新成功時True
        """
        if not self._hotkey_manager or not self._region_selection_hotkey_id:
            return False

        new_hotkey = Hotkey(keys=new_keys)
        success = self._hotkey_manager.update_hotkey(self._region_selection_hotkey_id, new_hotkey)

        if success:
            # 設定に保存
            config_data = self.config.load_config()
            config_data.setdefault("hotkey", {})["region_selection"] = new_keys
            self.config.save_config(config_data)
            logger.info(f"Region selection hotkey updated: {new_hotkey}")

        return success

    @Slot(dict)
    def _on_hotkey_settings_changed(self, settings: dict) -> None:
        """ホットキー設定変更時の処理。"""
        logger.info(f"Hotkey settings changed: {settings}")

        # キャプチャホットキー更新
        if "capture" in settings:
            self.update_capture_hotkey(settings["capture"])

        # 範囲指定ホットキー更新
        if "region_selection" in settings:
            self.update_region_selection_hotkey(settings["region_selection"])

        if self._main_window:
            self._main_window.set_status("ホットキー設定を更新しました")

    def _on_region_selection_hotkey(self) -> None:
        """範囲指定ホットキーがトリガーされた時の処理。"""
        logger.debug("Region selection hotkey triggered")
        # Qt のメインスレッドで実行
        try:
            from PySide6.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(self, "start_region_selection", Qt.ConnectionType.QueuedConnection)
            logger.debug("QMetaObject.invokeMethod called")
        except Exception as e:
            logger.error(f"Error invoking start_region_selection: {e}")

    @Slot()
    def start_region_selection(self) -> None:
        """2段階範囲選択プロセスを開始。"""
        logger.info("start_region_selection called")

        try:
            from ui.widgets.capture_overlay import CaptureOverlay

            if self._capture_overlay and self._capture_overlay.isVisible():
                logger.warning("Region selection already in progress")
                return

            self.region_selection_started.emit()
            logger.debug("Creating CaptureOverlay...")

            # Create overlay
            self._capture_overlay = CaptureOverlay()
            self._capture_overlay.regions_selected.connect(self._on_regions_selected)
            self._capture_overlay.selection_cancelled.connect(self._on_region_selection_cancelled)

            logger.debug("Starting two-stage selection...")
            # Start two-stage selection
            self._capture_overlay.start_two_stage_selection()
            logger.info("CaptureOverlay should now be visible")

            if self._main_window:
                self._main_window.set_status("範囲指定モード: ヘッダー領域を選択してください")
        except Exception as e:
            logger.error(f"Error in start_region_selection: {e}", exc_info=True)

    @Slot(object, object)
    def _on_regions_selected(self, header_rect: Rect, body_rect: Rect) -> None:
        """範囲選択完了時の処理。"""
        logger.info(f"Regions selected - Header: {header_rect}, Body: {body_rect}")

        # Auto-create profile if none exists
        if not self._current_profile:
            logger.info("No profile exists - auto-creating default profile")
            self._current_profile = Profile(
                name="Default",
                description="Auto-created default profile"
            )
            self._profiles.append(self._current_profile)
            self.profile_changed.emit(self._current_profile)

        # Update current profile
        self._current_profile.header_rect = header_rect
        self._current_profile.body_rect = body_rect
        self._current_profile.updated_at = datetime.now().isoformat()

        # Save profile
        self._save_profile(self._current_profile)

        self.region_selection_completed.emit(header_rect, body_rect)

        if self._main_window:
            self._main_window.set_status(
                f"範囲指定完了 - Header: ({header_rect.x}, {header_rect.y}, {header_rect.width}x{header_rect.height}), "
                f"Body: ({body_rect.x}, {body_rect.y}, {body_rect.width}x{body_rect.height})"
            )

        self._cleanup_overlay()

    @Slot()
    def _on_region_selection_cancelled(self) -> None:
        """範囲選択キャンセル時の処理。"""
        logger.info("Region selection cancelled")
        if self._main_window:
            self._main_window.set_status("範囲指定がキャンセルされました")
        self._cleanup_overlay()

    def _cleanup_overlay(self) -> None:
        """キャプチャオーバーレイをクリーンアップ。"""
        if self._capture_overlay:
            self._capture_overlay.deleteLater()
            self._capture_overlay = None

    def _save_profile(self, profile: Profile) -> None:
        """
        プロファイルをディスクに保存。

        Args:
            profile: 保存するプロファイル
        """
        profiles_dir = self.config.get_profiles_dir()
        profiles_dir.mkdir(parents=True, exist_ok=True)
        profile_file = profiles_dir / f"{profile.id}.json"

        try:
            with open(profile_file, "w", encoding="utf-8") as f:
                f.write(profile.to_json())
            logger.info(f"Profile saved: {profile_file}")
        except Exception as e:
            logger.error(f"Failed to save profile: {e}")

    def shutdown(self) -> None:
        """
        AppControllerをシャットダウン。

        全てのリソースを解放し、リスナーを停止。
        """
        logger.info("Shutting down AppController...")

        # ホットキーリスナー停止
        self.stop_hotkey_listener()

        # ScreenCaptureリソース解放
        if self._screen_capture:
            self._screen_capture.close()
            self._screen_capture = None

        # 状態リセット
        self._initialized = False
        self._current_profile = None

        logger.info("AppController shutdown complete")

    def __del__(self):
        """デストラクタ。"""
        try:
            self.shutdown()
        except Exception:
            pass
