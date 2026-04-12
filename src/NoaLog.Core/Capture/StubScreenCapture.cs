using NoaLog.Core.Models;

namespace NoaLog.Core.Capture;

public class StubScreenCapture : IScreenCapture
{
    public bool IsAvailable => false;

    public Task<byte[]> CaptureRegionAsync(Rect region, CancellationToken ct = default)
    {
        return Task.FromResult(Array.Empty<byte>());
    }

    public Task<byte[]> CaptureFullScreenAsync(CancellationToken ct = default)
    {
        return Task.FromResult(Array.Empty<byte>());
    }
}
