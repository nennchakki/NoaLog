using NoaLog.Core.Models;

namespace NoaLog.Core.Capture;

/// <summary>macOS開発用スタブ。1x1の透明PNG画像を返す。</summary>
public class StubScreenCapture : IScreenCapture
{
    public bool IsAvailable => false;

    public Task<byte[]> CaptureRegionAsync(Rect rect, CancellationToken cancellationToken = default)
    {
        // 最小のPNG画像（1x1 transparent）を返す
        byte[] minimalPng = Convert.FromBase64String(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==");
        return Task.FromResult(minimalPng);
    }

    public Task<byte[]> CaptureFullScreenAsync(CancellationToken cancellationToken = default)
        => CaptureRegionAsync(new Rect(0, 0, 1, 1), cancellationToken);
}
