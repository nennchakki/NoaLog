using System.Diagnostics;
using System.Text;
using System.Text.Json;
using NoaLog.Core.Models;

namespace NoaLog.Core.Ocr;

/// <summary>
/// Ollama /api/chat 経由でVLMモデルを使用するOCRエンジン。
/// </summary>
public class OllamaOcrClient : IOcrEngine, IDisposable
{
    private const string DefaultModelName = "glm-ocr:latest";

    // 高速OCR用の短いPrompt（速度優先）。
    // 旧Prompt（ルビ対応・将来戻す可能性あり）の意図:
    //   この画像の日本語テキストを正確に読み取ってください。
    //   文の最後まで正確に読み取り、推測で補わないでください。
    //   ルビ（フリガナ）がある場合は、青空文庫形式で出力してください。
    //   例: 先生《せんせい》が教室《きょうしつ》に入《はい》った
    //   ルビがない漢字はそのまま出力してください。
    //   テキストのみ出力し、説明は不要です。
    // ルビ対応が必要になったら上記の和文Promptに差し替える。
    private const string Prompt =
        "Text Recognition. Return only the Japanese text. Do not explain.";

    // モデルをVRAMに常駐させる時間（毎リクエストで延長される）
    private const string KeepAlive = "30m";

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

    /// <summary>推論完了時に発火（最終テキスト）</summary>
    public event Action<string>? InferenceCompleted;

    public OllamaOcrClient(string baseUrl = "http://localhost:11434", string modelName = DefaultModelName)
    {
        _baseUrl = baseUrl.TrimEnd('/');
        _modelName = modelName;
        _httpClient = new HttpClient
        {
            Timeout = TimeSpan.FromSeconds(300),
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

            // 2. ウォームアップ（GPU VRAMにモデルをロードのみ）
            // messages空配列 + keep_alive により、推論せずモデルロードだけ走らせる。
            Console.Error.WriteLine($"[OCR] Warmup: loading {_modelName} into GPU...");
            var warmupBody = JsonSerializer.Serialize(new
            {
                model = _modelName,
                messages = Array.Empty<object>(),
                stream = false,
                keep_alive = KeepAlive,
            });
            using var warmupContent = new StringContent(warmupBody, Encoding.UTF8, "application/json");
            await _httpClient.PostAsync($"{_baseUrl}/api/chat", warmupContent, cancellationToken).ConfigureAwait(false);
            Console.Error.WriteLine("[OCR] Warmup complete.");

            _isReady = true;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"[OCR] InitializeAsync failed: {ex.Message}");
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

        var regionLabel = label ?? "OCR";
        var totalSw = Stopwatch.StartNew();

        try
        {
            InferenceStarted?.Invoke(regionLabel);

            // 将来的なリサイズ・グレースケール・余白削除のための前処理フック
            var prepared = PrepareImageForOcr(imageData);

            Console.Error.WriteLine($"[OCR] RecognizeAsync [{regionLabel}]: {prepared.Length} bytes, model={_modelName}");

            var b64Sw = Stopwatch.StartNew();
            var base64Image = Convert.ToBase64String(prepared);
            b64Sw.Stop();

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
                keep_alive = KeepAlive,
                options = new
                {
                    temperature = 0.0,
                    num_predict = 128,
                    num_ctx = 1024,
                },
            });

            using var content = new StringContent(requestBody, Encoding.UTF8, "application/json");

            var httpSw = Stopwatch.StartNew();
            var response = await _httpClient.PostAsync(
                $"{_baseUrl}/api/chat", content, cancellationToken).ConfigureAwait(false);
            response.EnsureSuccessStatusCode();
            using var stream = await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false);
            httpSw.Stop();

            var parseSw = Stopwatch.StartNew();
            using var doc = await JsonDocument.ParseAsync(stream, cancellationToken: cancellationToken).ConfigureAwait(false);

            var text = "";
            if (doc.RootElement.TryGetProperty("message", out var message) &&
                message.TryGetProperty("content", out var contentProp))
            {
                text = contentProp.GetString()?.Trim() ?? "";
            }

            // Ollamaが返すサーバー側メトリクス（ナノ秒）
            long? totalDur = TryGetLong(doc.RootElement, "total_duration");
            long? loadDur = TryGetLong(doc.RootElement, "load_duration");
            long? promptEvalDur = TryGetLong(doc.RootElement, "prompt_eval_duration");
            long? evalDur = TryGetLong(doc.RootElement, "eval_duration");
            long? promptTokens = TryGetLong(doc.RootElement, "prompt_eval_count");
            long? evalTokens = TryGetLong(doc.RootElement, "eval_count");
            parseSw.Stop();

            totalSw.Stop();

            Console.Error.WriteLine(
                $"[OCR] Timing {regionLabel}: total={totalSw.ElapsedMilliseconds}ms, " +
                $"b64={b64Sw.ElapsedMilliseconds}ms, http={httpSw.ElapsedMilliseconds}ms, " +
                $"parse={parseSw.ElapsedMilliseconds}ms");

            Console.Error.WriteLine(
                $"[OCR] Ollama {regionLabel}: " +
                $"total={NsToMs(totalDur)}ms, load={NsToMs(loadDur)}ms, " +
                $"prompt_eval={NsToMs(promptEvalDur)}ms, eval={NsToMs(evalDur)}ms, " +
                $"prompt_tokens={promptTokens?.ToString() ?? "?"}, " +
                $"eval_tokens={evalTokens?.ToString() ?? "?"}");

            InferenceCompleted?.Invoke(text);
            Console.Error.WriteLine($"[OCR] Result [{regionLabel}]: '{text}'");

            return new OcrResult(text, FixedConfidence);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"[OCR] Error: {ex.Message}");
            InferenceCompleted?.Invoke("");
            return new OcrResult("", 0.0);
        }
    }

    /// <summary>
    /// OCR投入前の画像前処理フック。現状はno-op。
    /// 将来的に ImageSharp によるリサイズ・グレースケール・余白削除を追加する想定。
    /// </summary>
    private static byte[] PrepareImageForOcr(byte[] imageData)
    {
        return imageData;
    }

    private static long? TryGetLong(JsonElement root, string propertyName)
    {
        if (root.TryGetProperty(propertyName, out var prop) &&
            prop.ValueKind == JsonValueKind.Number &&
            prop.TryGetInt64(out var value))
        {
            return value;
        }
        return null;
    }

    private static string NsToMs(long? ns)
    {
        if (ns is null) return "?";
        return (ns.Value / 1_000_000).ToString();
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
