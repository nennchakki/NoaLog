# OCR processing module
# Handles text recognition using PaddleOCR

from .ocr_engine import OCREngine, OCRResult, OCREngineError, PREPROCESS_PRESETS

__all__ = ["OCREngine", "OCRResult", "OCREngineError", "PREPROCESS_PRESETS"]
