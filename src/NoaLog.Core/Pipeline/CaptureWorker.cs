using NoaLog.Core.Capture;
using NoaLog.Core.Models;
using NoaLog.Core.Ocr;
using NoaLog.Core.PostProcess;
using NoaLog.Core.Storage;

namespace NoaLog.Core.Pipeline;

public class CaptureWorker
{
    private readonly CaptureQueue _queue;
    private readonly IScreenCapture _capture;
    private readonly IOcrEngine _ocr;
    private readonly SqliteStorage _storage;
    private readonly DictProcessor? _dictProcessor;
    private CancellationTokenSource? _cts;
    private Task? _workerTask;

    // Event for UI notification when a new log entry is created
    public event EventHandler<LogEntry>? EntryCreated;

    // Event for UI notification when processing fails
    public event EventHandler<Exception>? ProcessingFailed;

    public CaptureWorker(CaptureQueue queue, IScreenCapture capture, IOcrEngine ocr, SqliteStorage storage, DictProcessor? dictProcessor = null)
    {
        _queue = queue;
        _capture = capture;
        _ocr = ocr;
        _storage = storage;
        _dictProcessor = dictProcessor;
    }

    public void Start()
    {
        _cts = new CancellationTokenSource();
        _workerTask = Task.Run(() => ProcessLoopAsync(_cts.Token));
    }

    public async Task StopAsync()
    {
        _queue.Complete();
        _cts?.Cancel();
        if (_workerTask != null)
            await _workerTask;
        _cts?.Dispose();
    }

    private async Task ProcessLoopAsync(CancellationToken ct)
    {
        await foreach (var request in _queue.ReadAllAsync(ct))
        {
            try
            {
                await ProcessRequestAsync(request, ct);
            }
            catch (OperationCanceledException) when (ct.IsCancellationRequested)
            {
                break;
            }
            catch (Exception ex)
            {
                // Log error but continue processing
                Console.Error.WriteLine($"CaptureWorker error: {ex.Message}");
                ProcessingFailed?.Invoke(this, ex);
            }
        }
    }

    private async Task ProcessRequestAsync(CaptureRequest request, CancellationToken ct)
    {
        Console.Error.WriteLine($"[CaptureWorker] Processing request: Header={request.HeaderRect}, Body={request.BodyRect}, Engine={_ocr.EngineName}, IsReady={_ocr.IsReady}");

        // 1. Capture header region
        var headerImage = await _capture.CaptureRegionAsync(request.HeaderRect, ct);
        Console.Error.WriteLine($"[CaptureWorker] Header captured: {headerImage.Length} bytes");
        // デバッグ: キャプチャ画像をファイルに保存
        try { await File.WriteAllBytesAsync("/tmp/noalog_header.png", headerImage, ct); } catch { }
        var headerResult = await _ocr.RecognizeAsync(headerImage, ct);
        Console.Error.WriteLine($"[CaptureWorker] Header OCR: '{headerResult.Text}'");

        // 2. Capture body region
        var bodyImage = await _capture.CaptureRegionAsync(request.BodyRect, ct);
        Console.Error.WriteLine($"[CaptureWorker] Body captured: {bodyImage.Length} bytes");
        try { await File.WriteAllBytesAsync("/tmp/noalog_body.png", bodyImage, ct); } catch { }
        var bodyResult = await _ocr.RecognizeAsync(bodyImage, ct);
        Console.Error.WriteLine($"[CaptureWorker] Body OCR: '{bodyResult.Text}'");

        // 3. Capture narrator region (optional)
        string narratorText = "";
        if (request.NarratorRect is { } narratorRect)
        {
            var narratorImage = await _capture.CaptureRegionAsync(narratorRect, ct);
            var narratorResult = await _ocr.RecognizeAsync(narratorImage, ct);
            narratorText = narratorResult.Text;
        }

        // 4. Build log entry
        var entry = new LogEntry
        {
            Id = Guid.NewGuid().ToString(),
            ProfileId = request.ProfileId,
            Timestamp = DateTime.UtcNow,
            LogType = request.LogType == "narration" ? LogType.Narration : LogType.Dialogue,
            RawHeader = headerResult.Text,
            RawBody = bodyResult.Text,
            SpeakerName = headerResult.Text,
            BodyText = bodyResult.Text,
            OcrEngine = _ocr.EngineName,
        };

        // 5. Post-process OCR results via dictionary
        _dictProcessor?.ProcessEntry(entry);

        // 6. Save to storage
        _storage.InsertLogEntry(entry);

        // 7. Notify UI
        EntryCreated?.Invoke(this, entry);
    }
}
