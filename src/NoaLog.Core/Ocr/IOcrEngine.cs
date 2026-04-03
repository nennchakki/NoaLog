using NoaLog.Core.Models;

namespace NoaLog.Core.Ocr;

/// <summary>
/// OCRエンジンの共通インターフェース。
/// 現在はQwenVlClientのみ使用。
/// </summary>
public interface IOcrEngine
{
    /// <summary>エンジン名 (例: "manga_ocr_onnx", "qwen_vl")</summary>
    string EngineName { get; }

    /// <summary>エンジンが使用可能かどうか</summary>
    bool IsReady { get; }

    /// <summary>エンジンを初期化する</summary>
    Task InitializeAsync(CancellationToken cancellationToken = default);

    /// <summary>画像からテキストを認識する</summary>
    /// <param name="imageData">PNG/JPEG画像のバイト配列</param>
    Task<OcrResult> RecognizeAsync(byte[] imageData, CancellationToken cancellationToken = default);

    /// <summary>リソースを解放する</summary>
    Task ShutdownAsync();
}
