using NoaLog.Core.Models;

namespace NoaLog.Core.Capture;

/// <summary>
/// スクリーンキャプチャのプラットフォーム抽象化。
/// Windows: Win32 BitBlt / DXGI
/// macOS: 開発時はスタブ実装
/// </summary>
public interface IScreenCapture
{
    /// <summary>指定領域のスクリーンショットを取得する</summary>
    /// <param name="rect">キャプチャ領域</param>
    /// <returns>PNG形式の画像バイト配列</returns>
    Task<byte[]> CaptureRegionAsync(Rect rect, CancellationToken cancellationToken = default);

    /// <summary>全画面のスクリーンショットを取得する</summary>
    Task<byte[]> CaptureFullScreenAsync(CancellationToken cancellationToken = default);

    /// <summary>利用可能かどうか</summary>
    bool IsAvailable { get; }
}
