using System.Threading.Channels;
using NoaLog.Core.Models;

namespace NoaLog.Core.Pipeline;

public record CaptureRequest(
    string ProfileId,
    Rect TextAreaRect,
    Rect? NarratorRect,
    string LogType = "dialogue",
    string? NarratorLabel = null
);

public class CaptureQueue
{
    private readonly Channel<CaptureRequest> _channel;

    public CaptureQueue(int capacity = 10)
    {
        _channel = Channel.CreateBounded<CaptureRequest>(new BoundedChannelOptions(capacity)
        {
            FullMode = BoundedChannelFullMode.DropOldest,
            SingleReader = true,
            SingleWriter = false,
        });
    }

    public ValueTask EnqueueAsync(CaptureRequest request, CancellationToken ct = default)
        => _channel.Writer.WriteAsync(request, ct);

    public IAsyncEnumerable<CaptureRequest> ReadAllAsync(CancellationToken ct = default)
        => _channel.Reader.ReadAllAsync(ct);

    public void Complete() => _channel.Writer.Complete();
}
