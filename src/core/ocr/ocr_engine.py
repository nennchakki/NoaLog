"""
NoaLog OCR Engine Module

manga-ocrを優先使用した日本語テキスト認識エンジン。
PaddleOCR、EasyOCRへのフォールバック機能付き。
"""

from dataclasses import dataclass, field
from typing import List, Any, Optional
import logging
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """OCR認識結果を格納するデータクラス。

    Attributes:
        text: 認識されたテキスト
        confidence: 信頼度スコア (0.0 - 1.0)
        raw_results: OCRエンジンの生出力
    """
    text: str
    confidence: float
    raw_results: List[Any] = field(default_factory=list)

    def is_valid(self, min_confidence: float = 0.5) -> bool:
        """信頼度が閾値以上かチェック。

        Args:
            min_confidence: 最小信頼度 (デフォルト: 0.5)

        Returns:
            信頼度が閾値以上ならTrue
        """
        return self.confidence >= min_confidence and len(self.text.strip()) > 0


# 前処理プリセット定義
PREPROCESS_PRESETS = {
    "default": {
        "grayscale": True,
        "denoise": True,
        "contrast": 1.2,
        "brightness": 0,
        "threshold": None,
        "blur_kernel": 3,
        "sharpen": False,
        "upscale": 1.0,
    },
    "header": {
        "grayscale": True,
        "denoise": True,
        "contrast": 1.4,  # ヘッダーはコントラスト高め
        "brightness": 10,
        "threshold": None,
        "blur_kernel": 3,
        "sharpen": True,  # シャープニングで文字輪郭を強調
        "upscale": 2.0,   # 解像度2倍でOCR精度向上
    },
    "body": {
        "grayscale": True,
        "denoise": True,
        "contrast": 1.1,  # 本文は控えめ
        "brightness": 0,
        "threshold": None,
        "blur_kernel": 5,  # ノイズ除去強め
        "sharpen": False,
        "upscale": 1.5,   # 解像度1.5倍
    },
    "high_contrast": {
        "grayscale": True,
        "denoise": True,
        "contrast": 1.8,
        "brightness": 20,
        "threshold": 128,
        "blur_kernel": 3,
        "sharpen": True,
        "upscale": 2.0,
    },
    "small_text": {
        # 小文字・小さい文字用の最適化プリセット
        "grayscale": True,
        "denoise": False,  # ノイズ除去は細部を失う可能性あり
        "contrast": 1.6,
        "brightness": 15,
        "threshold": None,
        "blur_kernel": 0,  # ブラーなし
        "sharpen": True,   # シャープニング必須
        "upscale": 3.0,    # 3倍にアップスケール
    },
    "none": {
        "grayscale": False,
        "denoise": False,
        "contrast": 1.0,
        "brightness": 0,
        "threshold": None,
        "blur_kernel": 0,
        "sharpen": False,
        "upscale": 1.0,
    },
}

# 日本語カタカナの類似文字マッピング（OCR後の修正用）
JAPANESE_SIMILAR_CHARS = {
    # ソとン、シとツなどの類似文字は文脈で判断が必要
    # ここでは単独では修正せず、パターンベースで修正
}

# 日本語→簡体字の誤認識パターン（OCR後の修正用）
SIMPLIFIED_TO_JAPANESE = {
    # 簡体字 → 日本語
    "东": "東",
    "车": "車",
    "马": "馬",
    "鱼": "魚",
    "鸟": "鳥",
    "龙": "龍",
    "门": "門",
    "风": "風",
    "书": "書",
    "长": "長",
    "时": "時",
    "见": "見",
    "贝": "貝",
    "页": "頁",
    "会": "會",
    "发": "發",
    "电": "電",
    "图": "圖",
    "乐": "樂",
    "华": "華",
    "语": "語",
    "说": "說",
    "请": "請",
    "让": "讓",
    "这": "這",
    "还": "還",
    "进": "進",
    "过": "過",
    "对": "對",
    "关": "關",
    "没": "沒",
    "学": "學",
    "国": "國",
    "来": "來",
    "为": "為",
    "与": "與",
    "体": "體",
    "从": "從",
    "个": "個",
    "业": "業",
    "义": "義",
    "产": "產",
    "亲": "親",
    "办": "辦",
    "动": "動",
    "务": "務",
    "区": "區",
    "医": "醫",
    "却": "卻",
    "历": "歷",
    "县": "縣",
    "参": "參",
    "变": "變",
    "号": "號",
    "听": "聽",
    "问": "問",
    "园": "園",
    "场": "場",
    "处": "處",
    "备": "備",
    "复": "復",
    "头": "頭",
    "学": "學",
    "实": "實",
    "宝": "寶",
    "对": "對",
    "导": "導",
    "岁": "歲",
    "币": "幣",
    "师": "師",
    "广": "廣",
    "应": "應",
    "张": "張",
    "录": "錄",
    "总": "總",
    "战": "戰",
    "术": "術",
    "机": "機",
    "杂": "雜",
    "条": "條",
    "构": "構",
    "标": "標",
    "欢": "歡",
    "气": "氣",
    "汉": "漢",
    "济": "濟",
    "浅": "淺",
    "点": "點",
    "爱": "愛",
    "现": "現",
    "环": "環",
    "码": "碼",
    "确": "確",
    "种": "種",
    "离": "離",
    "称": "稱",
    "级": "級",
    "线": "線",
    "经": "經",
    "给": "給",
    "统": "統",
    "继": "繼",
    "维": "維",
    "网": "網",
    "罗": "羅",
    "虑": "慮",
    "观": "觀",
    "规": "規",
    "认": "認",
    "议": "議",
    "设": "設",
    "证": "證",
    "评": "評",
    "词": "詞",
    "谢": "謝",
    "资": "資",
    "质": "質",
    "购": "購",
    "转": "轉",
    "软": "軟",
    "达": "達",
    "运": "運",
    "边": "邊",
    "选": "選",
    "钱": "錢",
    "银": "銀",
    "错": "錯",
    "镇": "鎮",
    "阅": "閱",
    "难": "難",
    "韩": "韓",
    "预": "預",
    "验": "驗",
    "黄": "黃",
}


class OCREngineError(Exception):
    """OCRエンジン関連のエラー。"""
    pass


class OCREngine:
    """OCRエンジン。

    manga-ocr（日本語特化）を優先使用し、PaddleOCR、EasyOCRにフォールバック。

    Attributes:
        lang: 認識言語 (デフォルト: "japan")
        use_gpu: GPU使用フラグ
        engine_type: 使用中のエンジン種別 ("manga_ocr", "paddleocr", "easyocr")
    """

    def __init__(
        self,
        lang: str = "japan",
        use_gpu: bool = False,
        use_angle_cls: bool = True,
        fallback_to_easyocr: bool = True,
    ):
        """OCRエンジンを初期化。

        Args:
            lang: 認識言語。PaddleOCR形式 ("japan", "en" など)
            use_gpu: GPU使用フラグ
            use_angle_cls: テキスト角度分類使用フラグ
            fallback_to_easyocr: PaddleOCR失敗時にEasyOCRへフォールバック
        """
        self.lang = lang
        self.use_gpu = use_gpu
        self.use_angle_cls = use_angle_cls
        self.fallback_to_easyocr = fallback_to_easyocr
        self.engine_type: Optional[str] = None
        self._ocr = None

        if cv2 is None:
            raise OCREngineError("OpenCV (cv2) is required but not installed")

        self._initialize_engine()

    def _initialize_engine(self) -> None:
        """OCRエンジンを初期化。manga-ocr優先、PaddleOCR、EasyOCRにフォールバック。"""
        # manga-ocrを試行（日本語漫画/ゲームテキスト特化、濁点・白抜き文字に強い）
        if self._try_init_manga_ocr():
            return

        # フォールバック: PaddleOCR
        if self._try_init_paddleocr():
            return

        # フォールバック: EasyOCR
        if self.fallback_to_easyocr and self._try_init_easyocr():
            return

        raise OCREngineError(
            "No OCR engine available. "
            "Please install manga-ocr (pip install manga-ocr), "
            "PaddleOCR (pip install paddleocr paddlepaddle), "
            "or EasyOCR (pip install easyocr)"
        )

    def _try_init_manga_ocr(self) -> bool:
        """manga-ocrの初期化を試行。

        Returns:
            初期化成功時True
        """
        try:
            from manga_ocr import MangaOcr

            self._ocr = MangaOcr()
            self.engine_type = "manga_ocr"
            logger.info("manga-ocr initialized successfully")
            return True

        except ImportError:
            logger.warning("manga-ocr not available")
            return False
        except Exception as e:
            logger.warning(f"manga-ocr initialization failed: {e}")
            return False

    def _try_init_paddleocr(self) -> bool:
        """PaddleOCRの初期化を試行。

        Returns:
            初期化成功時True
        """
        try:
            from paddleocr import PaddleOCR
            import logging as std_logging
            import os

            # Suppress PaddleOCR logs and connectivity check
            std_logging.getLogger("ppocr").setLevel(std_logging.WARNING)
            os.environ.setdefault("DISABLE_MODEL_SOURCE_CHECK", "True")

            # PaddleOCR v3+ only accepts 'lang' parameter
            self._ocr = PaddleOCR(lang=self.lang)
            self.engine_type = "paddleocr"
            logger.info("PaddleOCR initialized successfully")
            return True

        except ImportError:
            logger.warning("PaddleOCR not available")
            return False
        except Exception as e:
            logger.warning(f"PaddleOCR initialization failed: {e}")
            return False

    def _try_init_easyocr(self) -> bool:
        """EasyOCRの初期化を試行。

        Returns:
            初期化成功時True
        """
        try:
            import easyocr

            # EasyOCRの言語コードに変換
            lang_map = {
                "japan": ["ja", "en"],
                "en": ["en"],
                "ch": ["ch_sim", "en"],
                "korean": ["ko", "en"],
            }
            langs = lang_map.get(self.lang, ["ja", "en"])

            self._ocr = easyocr.Reader(
                langs,
                gpu=self.use_gpu,
                verbose=False,
            )
            self.engine_type = "easyocr"
            logger.info("EasyOCR initialized successfully")
            return True

        except ImportError:
            logger.warning("EasyOCR not available")
            return False
        except Exception as e:
            logger.warning(f"EasyOCR initialization failed: {e}")
            return False

    def preprocess_image(
        self,
        image: np.ndarray,
        preset: str = "default",
        **custom_options,
    ) -> np.ndarray:
        """画像を前処理。

        Args:
            image: 入力画像 (BGR形式のnumpy配列)
            preset: プリセット名 ("default", "header", "body", "high_contrast", "small_text", "none")
            **custom_options: カスタム前処理オプション (プリセットを上書き)

        Returns:
            前処理済み画像

        Raises:
            OCREngineError: 前処理失敗時
        """
        if image is None or image.size == 0:
            raise OCREngineError("Invalid image: empty or None")

        # プリセット取得
        if preset not in PREPROCESS_PRESETS:
            logger.warning(f"Unknown preset '{preset}', using 'default'")
            preset = "default"

        options = PREPROCESS_PRESETS[preset].copy()
        options.update(custom_options)

        processed = image.copy()

        try:
            # 1. アップスケーリング（最初に実行して解像度を上げる）
            upscale = options.get("upscale", 1.0)
            if upscale > 1.0:
                new_width = int(processed.shape[1] * upscale)
                new_height = int(processed.shape[0] * upscale)
                # INTER_CUBIC は高品質なアップスケーリング
                processed = cv2.resize(
                    processed, (new_width, new_height),
                    interpolation=cv2.INTER_CUBIC
                )
                logger.debug(f"Upscaled image by {upscale}x to {new_width}x{new_height}")

            # 2. グレースケール変換
            if options.get("grayscale", True):
                if len(processed.shape) == 3:
                    processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)

            # 3. ノイズ除去 (ガウシアンブラー)
            blur_kernel = options.get("blur_kernel", 3)
            if options.get("denoise", True) and blur_kernel > 0:
                if blur_kernel % 2 == 0:
                    blur_kernel += 1  # 奇数にする
                processed = cv2.GaussianBlur(processed, (blur_kernel, blur_kernel), 0)

            # 4. コントラスト・明度調整
            contrast = options.get("contrast", 1.0)
            brightness = options.get("brightness", 0)
            if contrast != 1.0 or brightness != 0:
                processed = cv2.convertScaleAbs(processed, alpha=contrast, beta=brightness)

            # 5. シャープニング（文字輪郭を強調）
            if options.get("sharpen", False):
                # アンシャープマスクによるシャープニング
                gaussian = cv2.GaussianBlur(processed, (0, 0), 2.0)
                processed = cv2.addWeighted(processed, 1.5, gaussian, -0.5, 0)
                logger.debug("Applied sharpening filter")

            # 6. 二値化 (閾値指定時)
            threshold = options.get("threshold")
            if threshold is not None:
                if len(processed.shape) == 3:
                    processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
                _, processed = cv2.threshold(
                    processed, threshold, 255, cv2.THRESH_BINARY
                )

            return processed

        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            raise OCREngineError(f"Preprocessing failed: {e}") from e

    def postprocess_text(self, text: str) -> str:
        """OCR結果の後処理。

        簡体字を日本語に変換し、一般的な誤認識を修正。

        Args:
            text: OCR認識結果のテキスト

        Returns:
            後処理済みテキスト
        """
        if not text:
            return text

        result = text

        # 簡体字を日本語（繁体字/新字体）に変換
        for simplified, japanese in SIMPLIFIED_TO_JAPANESE.items():
            result = result.replace(simplified, japanese)

        return result

    def recognize(
        self,
        image: np.ndarray,
        preprocess: bool = True,
        preset: str = "default",
        postprocess: bool = True,
    ) -> OCRResult:
        """画像からテキストを認識。

        Args:
            image: 入力画像 (BGR形式のnumpy配列)
            preprocess: 前処理を行うか
            preset: 前処理プリセット名
            postprocess: 後処理（簡体字変換など）を行うか

        Returns:
            OCRResult: 認識結果
        """
        if image is None or image.size == 0:
            return OCRResult(text="", confidence=0.0, raw_results=[])

        # 前処理
        if preprocess:
            try:
                processed = self.preprocess_image(image, preset=preset)
            except OCREngineError:
                processed = image
        else:
            processed = image

        # エンジン別のOCR実行
        if self.engine_type == "manga_ocr":
            result = self._recognize_manga_ocr(processed)
        elif self.engine_type == "paddleocr":
            result = self._recognize_paddleocr(processed)
        elif self.engine_type == "easyocr":
            result = self._recognize_easyocr(processed)
        else:
            return OCRResult(text="", confidence=0.0, raw_results=[])

        # 後処理（簡体字変換など）
        if postprocess and result.text:
            result.text = self.postprocess_text(result.text)

        return result

    def _recognize_manga_ocr(self, image: np.ndarray) -> OCRResult:
        """manga-ocrで認識。

        manga-ocrはPIL Imageを受け取るため変換が必要。
        信頼度スコアは提供されないため1.0固定。

        Args:
            image: 前処理済み画像

        Returns:
            OCRResult: 認識結果
        """
        try:
            from PIL import Image

            # numpy配列 → PIL Image に変換
            if len(image.shape) == 2:
                # グレースケール
                pil_image = Image.fromarray(image)
            else:
                # BGR → RGB
                pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

            text = self._ocr(pil_image)

            if not text or not text.strip():
                return OCRResult(text="", confidence=0.0, raw_results=[])

            return OCRResult(
                text=text.strip(),
                confidence=1.0,  # manga-ocrは信頼度スコアを返さない
                raw_results=[text],
            )

        except Exception as e:
            logger.error(f"manga-ocr recognition failed: {e}")
            return OCRResult(text="", confidence=0.0, raw_results=[])

    def _recognize_paddleocr(self, image: np.ndarray) -> OCRResult:
        """PaddleOCRで認識。

        Args:
            image: 前処理済み画像

        Returns:
            OCRResult: 認識結果
        """
        try:
            # PaddleOCR v3+ requires 3-channel (BGR) images
            # Convert grayscale to BGR if necessary
            if len(image.shape) == 2:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            elif len(image.shape) == 3 and image.shape[2] == 1:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

            # PaddleOCR v3+ uses predict() method
            result = self._ocr.predict(image)

            if not result:
                return OCRResult(text="", confidence=0.0, raw_results=[])

            # PaddleOCR v3+ returns OCRResult (dict-like) with rec_texts and rec_scores
            ocr_result = result[0] if isinstance(result, list) else result

            # Extract texts and scores - OCRResult supports dict-style access
            texts = []
            confidences = []

            try:
                # OCRResult is dict-like, use [] or get() access
                rec_texts = ocr_result.get('rec_texts') if hasattr(ocr_result, 'get') else ocr_result['rec_texts']
                rec_scores = ocr_result.get('rec_scores') if hasattr(ocr_result, 'get') else ocr_result['rec_scores']
                texts = list(rec_texts) if rec_texts else []
                confidences = list(rec_scores) if rec_scores else []
            except (KeyError, TypeError):
                logger.warning("Could not extract rec_texts/rec_scores from OCR result")

            if not texts:
                return OCRResult(text="", confidence=0.0, raw_results=result)

            combined_text = "\n".join(str(t) for t in texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return OCRResult(
                text=combined_text,
                confidence=avg_confidence,
                raw_results=result,
            )

        except Exception as e:
            logger.error(f"PaddleOCR recognition failed: {e}")
            return OCRResult(text="", confidence=0.0, raw_results=[])

    def _recognize_easyocr(self, image: np.ndarray) -> OCRResult:
        """EasyOCRで認識。

        Args:
            image: 前処理済み画像

        Returns:
            OCRResult: 認識結果
        """
        try:
            result = self._ocr.readtext(image)

            if not result:
                return OCRResult(text="", confidence=0.0, raw_results=[])

            # 結果を解析
            texts = []
            confidences = []

            for detection in result:
                # detection: (bbox, text, confidence)
                if len(detection) >= 3:
                    texts.append(detection[1])
                    confidences.append(detection[2])

            if not texts:
                return OCRResult(text="", confidence=0.0, raw_results=result)

            combined_text = "\n".join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return OCRResult(
                text=combined_text,
                confidence=avg_confidence,
                raw_results=result,
            )

        except Exception as e:
            logger.error(f"EasyOCR recognition failed: {e}")
            return OCRResult(text="", confidence=0.0, raw_results=[])

    def recognize_header(self, image: np.ndarray) -> OCRResult:
        """ヘッダー領域向けに最適化された認識。

        ヘッダーは話者名・所属など短いテキストが多いため、
        高コントラスト設定で認識精度を向上。

        Args:
            image: ヘッダー領域の画像

        Returns:
            OCRResult: 認識結果
        """
        return self.recognize(image, preprocess=True, preset="header")

    def recognize_body(self, image: np.ndarray) -> OCRResult:
        """本文領域向けに最適化された認識。

        本文は長文テキストが多いため、
        ノイズ除去を強化しつつ自然なコントラストで認識。

        Args:
            image: 本文領域の画像

        Returns:
            OCRResult: 認識結果
        """
        return self.recognize(image, preprocess=True, preset="body")

    def get_engine_info(self) -> dict:
        """現在のエンジン情報を取得。

        Returns:
            エンジン情報の辞書
        """
        return {
            "engine_type": self.engine_type,
            "lang": self.lang,
            "use_gpu": self.use_gpu,
            "use_angle_cls": self.use_angle_cls,
        }
