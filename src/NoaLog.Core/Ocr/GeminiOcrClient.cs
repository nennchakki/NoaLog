using System.Text;
using System.Text.Json;
using NoaLog.Core.Models;

namespace NoaLog.Core.Ocr;

/// <summary>
/// Gemini API を使ったクラウドOCRエンジン。
/// APIキーは環境変数 GEMINI_API_KEY から取得する。
/// キーが未設定の場合は IsReady = false となり、呼び出し側でフォールバック可能。
/// </summary>
public class GeminiOcrClient : IOcrEngine, IDisposable
{
    private const string DefaultModelId = "gemini-3.1-flash-lite";
    private const string ApiBase = "https://generativelanguage.googleapis.com/v1beta/models";
    private const string EnvVarName = "GEMINI_API_KEY";

    private const string BasePrompt =
        "画像内のテキストをOCRしてください。\n" +
        "出力はテキストのみ。説明・補足・Markdown装飾は不要。\n" +
        "\n" +
        "【ルール】\n" +
        "1. キャラクター名が表示されていれば、セリフの前に1行で書け。\n" +
        "2. セリフごとに改行で区切れ。\n" +
        "3. 「…」だけのセリフや空に見える行も省略せずそのまま出力しろ。\n" +
        "4. 固有名詞（人名・組織名）は省略・短縮せず、見えたとおり正確に書き写せ。\n" +
        "5. 効果音・擬音が続く場合でも、延々と繰り返さず数回程度に留めろ。\n" +
        "6. 読めない箇所は [不明] と書け。推測で補完するな。";

    private const double FixedConfidence = 0.9;

    private readonly HttpClient _httpClient;
    private readonly string _modelId;
    private readonly string? _apiKey;
    private readonly string _prompt;
    private bool _isReady;
    private bool _disposed;

    public string EngineName => _modelId;
    public bool IsReady => _isReady;

    /// <param name="modelId">使用するGeminiモデルID。省略時は gemini-2.5-flash-lite。</param>
    /// <param name="characterNames">OCRプロンプトへ語彙ヒントとして渡す登場人物名。null/空なら付与しない。</param>
    /// <param name="additionalRules">ゲーム固有の追加ルール行。BasePromptの後に追記される。</param>
    public GeminiOcrClient(
        string? modelId = null,
        IReadOnlyList<string>? characterNames = null,
        IReadOnlyList<string>? additionalRules = null)
    {
        _modelId = modelId ?? DefaultModelId;
        _apiKey = Environment.GetEnvironmentVariable(EnvVarName);
        _prompt = BuildPrompt(characterNames, additionalRules);
        _httpClient = new HttpClient
        {
            Timeout = TimeSpan.FromSeconds(120),
        };
    }

    private static string BuildPrompt(
        IReadOnlyList<string>? names,
        IReadOnlyList<string>? additionalRules)
    {
        var sb = new StringBuilder(BasePrompt);

        if (additionalRules is { Count: > 0 })
        {
            sb.AppendLine();
            sb.AppendLine();
            sb.AppendLine("【追加ルール】");
            for (int i = 0; i < additionalRules.Count; i++)
                sb.AppendLine($"{i + 1}. {additionalRules[i]}");
        }

        if (names is { Count: > 0 })
        {
            sb.AppendLine();
            sb.Append("次は登場人物名の一覧です。人名はこの表記に正規化してください（一覧にない人名はそのまま）:\n");
            sb.Append(string.Join("、", names));
        }

        return sb.ToString();
    }

    public Task InitializeAsync(CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(_apiKey))
        {
            Console.Error.WriteLine($"[Gemini] {EnvVarName} not set. Engine disabled.");
            _isReady = false;
        }
        else
        {
            Console.Error.WriteLine($"[Gemini] API key found. Engine ready ({_modelId}).");
            _isReady = true;
        }
        return Task.CompletedTask;
    }

    public async Task<OcrResult> RecognizeAsync(byte[] imageData, CancellationToken cancellationToken = default)
    {
        if (!_isReady || string.IsNullOrEmpty(_apiKey))
        {
            Console.Error.WriteLine("[Gemini] Not ready (API key missing).");
            return new OcrResult("", 0.0);
        }

        try
        {
            var base64 = Convert.ToBase64String(imageData);

            var requestBody = JsonSerializer.Serialize(new
            {
                contents = new[]
                {
                    new
                    {
                        parts = new object[]
                        {
                            new { text = _prompt },
                            new
                            {
                                inline_data = new
                                {
                                    mime_type = "image/png",
                                    data = base64,
                                }
                            }
                        }
                    }
                },
                generationConfig = new
                {
                    temperature = 0.0,
                    maxOutputTokens = 2048,
                }
            });

            var url = $"{ApiBase}/{_modelId}:generateContent?key={_apiKey}";
            using var content = new StringContent(requestBody, Encoding.UTF8, "application/json");
            var response = await _httpClient.PostAsync(url, content, cancellationToken).ConfigureAwait(false);

            if (!response.IsSuccessStatusCode)
            {
                var body = await response.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false);
                Console.Error.WriteLine($"[Gemini] HTTP {(int)response.StatusCode}: {body}");
                return new OcrResult("", 0.0);
            }

            using var stream = await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false);
            using var doc = await JsonDocument.ParseAsync(stream, cancellationToken: cancellationToken).ConfigureAwait(false);

            var text = ExtractText(doc.RootElement);
            return new OcrResult(text, FixedConfidence);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"[Gemini] Error: {ex.Message}");
            return new OcrResult("", 0.0);
        }
    }

    private static string ExtractText(JsonElement root)
    {
        if (!root.TryGetProperty("candidates", out var candidates) ||
            candidates.ValueKind != JsonValueKind.Array ||
            candidates.GetArrayLength() == 0)
        {
            return "";
        }

        var candidate = candidates[0];
        if (!candidate.TryGetProperty("content", out var content) ||
            !content.TryGetProperty("parts", out var parts) ||
            parts.ValueKind != JsonValueKind.Array)
        {
            return "";
        }

        var sb = new StringBuilder();
        foreach (var part in parts.EnumerateArray())
        {
            if (part.TryGetProperty("text", out var textEl) &&
                textEl.ValueKind == JsonValueKind.String)
            {
                sb.Append(textEl.GetString());
            }
        }
        return sb.ToString().Trim();
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
