using NoaLog.Core.Ocr;
using Xunit;
using Xunit.Abstractions;

namespace NoaLog.Tests;

/// <summary>
/// Qwen3-VL ONNX推論の統合テスト。
/// Ollamaが起動しqwen3-vl:4bが利用可能な場合のみ実行。
/// </summary>
public class QwenVlIntegrationTests
{
    private readonly ITestOutputHelper _output;

    public QwenVlIntegrationTests(ITestOutputHelper output)
    {
        _output = output;
    }

    private static async Task<bool> IsOllamaAvailable()
    {
        try
        {
            using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(3) };
            var response = await http.GetAsync("http://localhost:11434/api/tags");
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    [Fact]
    public async Task Initialize_ConnectsToOllama()
    {
        if (!await IsOllamaAvailable())
        {
            _output.WriteLine("Skipped: Ollama not running");
            return;
        }

        using var client = new QwenVlClient();
        await client.InitializeAsync();

        _output.WriteLine($"IsReady: {client.IsReady}");
        Assert.True(client.IsReady, "qwen3-vl:4b model should be available");
    }

    [Fact]
    public async Task Recognize_JapaneseText_ReturnsResult()
    {
        if (!await IsOllamaAvailable())
        {
            _output.WriteLine("Skipped: Ollama not running");
            return;
        }

        // テスト画像を確認
        var testImagePath = "/tmp/test_ocr.png";
        if (!File.Exists(testImagePath))
        {
            _output.WriteLine("Skipped: Test image not found at /tmp/test_ocr.png");
            return;
        }

        using var client = new QwenVlClient();
        await client.InitializeAsync();

        if (!client.IsReady)
        {
            _output.WriteLine("Skipped: qwen3-vl:4b not available");
            return;
        }

        var imageData = await File.ReadAllBytesAsync(testImagePath);
        var result = await client.RecognizeAsync(imageData);

        _output.WriteLine($"Qwen VL Result: '{result.Text}' (confidence: {result.Confidence})");

        Assert.NotNull(result);
        Assert.False(string.IsNullOrEmpty(result.Text), "Qwen VL should return text");
    }
}
