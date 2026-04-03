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

    // 並列処理制御
    private readonly SemaphoreSlim _concurrency = new(3, 3);
    private readonly object _orderLock = new();
    private readonly SortedDictionary<int, LogEntry> _completedBuffer = new();
    private int _nextSequence;
    private int _nextEmitSequence;

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
        var tasks = new List<Task>();

        await foreach (var request in _queue.ReadAllAsync(ct))
        {
            var seq = _nextSequence++;
            await _concurrency.WaitAsync(ct);

            tasks.Add(Task.Run(async () =>
            {
                try
                {
                    var entry = await ProcessRequestAsync(request, seq, ct);
                    if (entry != null)
                        EmitInOrder(seq, entry);
                }
                catch (OperationCanceledException) when (ct.IsCancellationRequested)
                {
                    // shutdown
                }
                catch (Exception ex)
                {
                    Console.Error.WriteLine($"CaptureWorker error: {ex.Message}");
                    ProcessingFailed?.Invoke(this, ex);
                }
                finally
                {
                    _concurrency.Release();
                }
            }, ct));
        }

        try { await Task.WhenAll(tasks); } catch { }
    }

    private void EmitInOrder(int seq, LogEntry entry)
    {
        lock (_orderLock)
        {
            _completedBuffer[seq] = entry;

            while (_completedBuffer.TryGetValue(_nextEmitSequence, out var next))
            {
                _completedBuffer.Remove(_nextEmitSequence);
                _storage.InsertLogEntry(next);
                EntryCreated?.Invoke(this, next);
                _nextEmitSequence++;
            }
        }
    }

    private async Task<LogEntry?> ProcessRequestAsync(CaptureRequest request, int seq, CancellationToken ct)
    {
        Console.Error.WriteLine($"[CaptureWorker] #{seq} Processing: TextArea={request.TextAreaRect}, Engine={_ocr.EngineName}");

        var qwen = _ocr as QwenVlClient;

        // 1. テキスト領域（名前+本文）をキャプチャ → OCR1回
        var textImage = await _capture.CaptureRegionAsync(request.TextAreaRect, ct);
        Console.Error.WriteLine($"[CaptureWorker] #{seq} TextArea capture: {textImage.Length} bytes");

        var result = qwen != null
            ? await qwen.RecognizeAsync(textImage, $"#{seq}", ct)
            : await _ocr.RecognizeAsync(textImage, ct);

        // 2. テキストを話者名と本文に分離（最初の行がSpeaker、残りがBody）
        var (speaker, body) = SplitSpeakerAndBody(result.Text);

        // 3. Build log entry
        var entry = new LogEntry
        {
            Id = Guid.NewGuid().ToString(),
            ProfileId = request.ProfileId,
            Timestamp = DateTime.UtcNow,
            LogType = request.LogType == "narration" ? LogType.Narration : LogType.Dialogue,
            RawHeader = speaker,
            RawBody = body,
            SpeakerName = speaker,
            BodyText = body,
            OcrEngine = _ocr.EngineName,
        };

        // 4. Post-process OCR results via dictionary
        _dictProcessor?.ProcessEntry(entry);

        return entry;
    }

private static (string Speaker, string Body) SplitSpeakerAndBody(string text)
    {
        if (string.IsNullOrWhiteSpace(text))
            return ("", "");

        var lines = text.Split('\n', StringSplitOptions.RemoveEmptyEntries);
        if (lines.Length == 0)
            return ("", "");
        if (lines.Length == 1)
            return ("", lines[0].Trim());

        // 最初の行がSpeaker、残りがBody
        return (lines[0].Trim(), string.Join("\n", lines[1..]).Trim());
    }
}
