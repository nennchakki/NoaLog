using NoaLog.Core.Ocr;
using Xunit;
using Xunit.Abstractions;

namespace NoaLog.Tests;

/// <summary>
/// manga-ocr ONNX 推論の統合テスト。
/// data/models/ にモデルファイルが存在する場合のみ実行。
/// </summary>
public class OcrIntegrationTests
{
    private readonly ITestOutputHelper _output;

    private static string ModelsDir => Path.GetFullPath(
        Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "data", "models"));

    private static string EncoderPath => Path.Combine(ModelsDir, "manga_ocr_encoder.onnx");
    private static string DecoderPath => Path.Combine(ModelsDir, "manga_ocr_decoder.onnx");
    private static string VocabPath => Path.Combine(ModelsDir, "tokenizer", "vocab.txt");

    private static bool ModelsExist =>
        File.Exists(EncoderPath) && File.Exists(DecoderPath) && File.Exists(VocabPath);

    public OcrIntegrationTests(ITestOutputHelper output)
    {
        _output = output;
    }

    [Fact]
    public async Task Initialize_LoadsModelsSuccessfully()
    {
        if (!ModelsExist)
        {
            _output.WriteLine($"Skipped: ONNX models not found in {ModelsDir}");
            return;
        }

        using var ocr = new MangaOcrOnnx(EncoderPath, DecoderPath, VocabPath);
        Assert.False(ocr.IsReady);

        await ocr.InitializeAsync();
        Assert.True(ocr.IsReady);
        _output.WriteLine("Model loaded successfully");
    }

    [Fact]
    public async Task Recognize_JapaneseText_ReturnsNonEmpty()
    {
        if (!ModelsExist)
        {
            _output.WriteLine($"Skipped: ONNX models not found in {ModelsDir}");
            return;
        }

        var testImagePath = "/tmp/test_ocr.png";
        if (!File.Exists(testImagePath))
        {
            _output.WriteLine("Skipped: Test image not found at /tmp/test_ocr.png");
            return;
        }

        using var ocr = new MangaOcrOnnx(EncoderPath, DecoderPath, VocabPath);
        await ocr.InitializeAsync();

        var imageData = await File.ReadAllBytesAsync(testImagePath);
        var result = await ocr.RecognizeAsync(imageData);

        _output.WriteLine($"OCR Result: '{result.Text}' (confidence: {result.Confidence})");

        Assert.NotNull(result);
        Assert.False(string.IsNullOrEmpty(result.Text), "OCR result text should not be empty");
        Assert.True(result.Confidence > 0, "Confidence should be positive");
    }
}
