using System.Text;
using System.Text.Json;
using NoaLog.Core.Models;

namespace NoaLog.Core.Ocr;

/// <summary>
/// Ollama HTTP API経由でQwen3-VLモデルを使用するOCRエンジン。
/// </summary>
public class QwenVlClient : IOcrEngine, IDisposable
{
    private const string DefaultModelName = "glm-ocr:latest";
    private const string Prompt =
        "この画像の日本語テキストを正確に読み取ってください。\n" +
        "文の最後まで正確に読み取り、推測で補わないでください。\n" +
        "ルビ（フリガナ）がある場合は、青空文庫形式で出力してください。\n" +
        "例: 先生《せんせい》が教室《きょうしつ》に入《はい》った\n" +
        "ルビがない漢字はそのまま出力してください。\n" +
        "テキストのみ出力し、説明は不要です。";
    private const double FixedConfidence = 0.8;

    private readonly HttpClient _httpClient;
    private string _baseUrl;
    private string _modelName;
    private bool _isReady;
    private bool _disposed;

    public string EngineName => _modelName;
    public string ModelName => _modelName;
    public string BaseUrl => _baseUrl;
    public bool IsReady => _isReady;

    /// <summary>推論開始時に発火（ラベル: "#0" 等）</summary>
    public event Action<string>? InferenceStarted;

    /// <summary>推論中のトークンを1つ受信するたびに発火</summary>
    public event Action<string>? TokenReceived;

    /// <summary>推論完了時に発火（最終テキスト）</summary>
    public event Action<string>? InferenceCompleted;

    public QwenVlClient(string baseUrl = "http://localhost:11434", string modelName = DefaultModelName)
    {
        _baseUrl = baseUrl.TrimEnd('/');
        _modelName = modelName;
        _httpClient = new HttpClient
        {
            Timeout = System.Threading.Timeout.InfiniteTimeSpan,
        };
    }

    public void SetBaseUrl(string url) => _baseUrl = url.TrimEnd('/');

    public async Task SwitchModelAsync(string modelName, CancellationToken ct = default)
    {
        _isReady = false;
        _modelName = modelName;
        await InitializeAsync(ct);
    }

    public async Task InitializeAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            // 1. モデル存在確認
            var response = await _httpClient.GetAsync(
                $"{_baseUrl}/api/tags", cancellationToken).ConfigureAwait(false);
            response.EnsureSuccessStatusCode();

            bool modelFound = false;
            using (var stream = await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false))
            using (var doc = await JsonDocument.ParseAsync(stream, cancellationToken: cancellationToken).ConfigureAwait(false))
            {
                if (doc.RootElement.TryGetProperty("models", out var models))
                {
                    foreach (var model in models.EnumerateArray())
                    {
                        if (model.TryGetProperty("name", out var name) &&
                            (name.GetString()?.StartsWith(_modelName) ?? false))
                        {
                            modelFound = true;
                            break;
                        }
                    }
                }
            }

            if (!modelFound) return;

            // 2. ウォームアップ（GPU VRAMにモデルをロード）— /api/chat + think:false
            Console.Error.WriteLine("[QwenVL] Warmup: loading model into GPU...");
            var warmupBody = JsonSerializer.Serialize(new
            {
                model = _modelName,
                messages = new[]
                {
                    new { role = "user", content = "test", images = Array.Empty<string>() }
                },
                stream = false,
                think = false,
            });
            using var warmupContent = new StringContent(warmupBody, Encoding.UTF8, "application/json");
            await _httpClient.PostAsync($"{_baseUrl}/api/chat", warmupContent, cancellationToken).ConfigureAwait(false);
            Console.Error.WriteLine("[QwenVL] Warmup complete.");

            _isReady = true;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"[QwenVL] InitializeAsync failed: {ex.Message}");
        }
    }

    public async Task<OcrResult> RecognizeAsync(byte[] imageData, CancellationToken cancellationToken = default)
    {
        return await RecognizeAsync(imageData, null, cancellationToken);
    }

    public async Task<OcrResult> RecognizeAsync(byte[] imageData, string? label, CancellationToken cancellationToken = default)
    {
        if (!_isReady)
            throw new InvalidOperationException("Engine not initialized. Call InitializeAsync first.");

        try
        {
            var regionLabel = label ?? "OCR";
            InferenceStarted?.Invoke(regionLabel);
            Console.Error.WriteLine($"[QwenVL] RecognizeAsync [{regionLabel}]: imageData={imageData.Length} bytes");

            var base64Image = Convert.ToBase64String(imageData);

            // /api/chat を使用（think: false はトップレベルでのみ有効）
            var requestBody = JsonSerializer.Serialize(new
            {
                model = _modelName,
                messages = new[]
                {
                    new
                    {
                        role = "user",
                        content = Prompt,
                        images = new[] { base64Image },
                    }
                },
                stream = false,
                think = false,
                options = new { temperature = 0.0 },
            });

            using var content = new StringContent(requestBody, Encoding.UTF8, "application/json");
            var response = await _httpClient.PostAsync(
                $"{_baseUrl}/api/chat", content, cancellationToken).ConfigureAwait(false);
            response.EnsureSuccessStatusCode();

            using var stream = await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false);
            using var doc = await JsonDocument.ParseAsync(stream, cancellationToken: cancellationToken).ConfigureAwait(false);

            // /api/chat のレスポンス: { "message": { "content": "..." } }
            var text = "";
            if (doc.RootElement.TryGetProperty("message", out var message) &&
                message.TryGetProperty("content", out var contentProp))
            {
                text = contentProp.GetString()?.Trim() ?? "";
            }

            InferenceCompleted?.Invoke(text);
            Console.Error.WriteLine($"[QwenVL] Result [{regionLabel}]: '{text}'");

            return new OcrResult(text, FixedConfidence);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"[QwenVL] Error: {ex.Message}");
            InferenceCompleted?.Invoke("");
            return new OcrResult("", 0.0);
        }
    }

    public Task ShutdownAsync()
    {
        Dispose();
        return Task.CompletedTask;
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;

        _httpClient.Dispose();
        GC.SuppressFinalize(this);
    }
}
