using System.Text.Json;
using NoaLog.Core.Models;

namespace NoaLog.Core.Ocr;

/// <summary>
/// Ollama HTTP API経由でQwen3-VLモデルを使用するOCRエンジン。
/// Pro版でのみインスタンス化される。
/// </summary>
public class QwenVlClient : IOcrEngine, IDisposable
{
    private const string ModelName = "qwen3-vl:2b";
    private const string Prompt = "Read all Japanese text in this image exactly as written. Output only the text, nothing else.";
    private const double FixedConfidence = 0.8;

    private readonly HttpClient _httpClient;
    private readonly string _baseUrl;
    private bool _isReady;
    private bool _disposed;

    public string EngineName => "qwen_vl";
    public bool IsReady => _isReady;

    public QwenVlClient(string baseUrl = "http://localhost:11434")
    {
        _baseUrl = baseUrl.TrimEnd('/');
        _httpClient = new HttpClient
        {
            Timeout = TimeSpan.FromSeconds(30),
        };
    }

    public async Task InitializeAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            var response = await _httpClient.GetAsync(
                $"{_baseUrl}/api/tags", cancellationToken).ConfigureAwait(false);
            response.EnsureSuccessStatusCode();

            using var stream = await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false);
            using var doc = await JsonDocument.ParseAsync(stream, cancellationToken: cancellationToken).ConfigureAwait(false);

            if (doc.RootElement.TryGetProperty("models", out var models))
            {
                foreach (var model in models.EnumerateArray())
                {
                    if (model.TryGetProperty("name", out var name) &&
                        name.GetString() == ModelName)
                    {
                        _isReady = true;
                        return;
                    }
                }
            }
        }
        catch
        {
            // Ollama not reachable or response parse error — leave IsReady false
        }
    }

    public async Task<OcrResult> RecognizeAsync(byte[] imageData, CancellationToken cancellationToken = default)
    {
        if (!_isReady)
            throw new InvalidOperationException("Engine not initialized. Call InitializeAsync first.");

        try
        {
            var base64Image = Convert.ToBase64String(imageData);

            var requestBody = JsonSerializer.Serialize(new
            {
                model = ModelName,
                prompt = Prompt,
                images = new[] { base64Image },
                stream = false,
                options = new { temperature = 0.0 },
            });

            using var content = new StringContent(requestBody, System.Text.Encoding.UTF8, "application/json");
            var response = await _httpClient.PostAsync(
                $"{_baseUrl}/api/generate", content, cancellationToken).ConfigureAwait(false);
            response.EnsureSuccessStatusCode();

            using var stream = await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false);
            using var doc = await JsonDocument.ParseAsync(stream, cancellationToken: cancellationToken).ConfigureAwait(false);

            var text = doc.RootElement.TryGetProperty("response", out var responseProp)
                ? responseProp.GetString()?.Trim() ?? ""
                : "";

            return new OcrResult(text, FixedConfidence);
        }
        catch
        {
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
