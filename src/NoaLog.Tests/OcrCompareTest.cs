using NoaLog.Core.Ocr;
using Xunit;
using Xunit.Abstractions;

namespace NoaLog.Tests;

public class OcrCompareTest
{
    private readonly ITestOutputHelper _output;
    public OcrCompareTest(ITestOutputHelper output) => _output = output;

    private static string ModelsDir => Path.GetFullPath(
        Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "data", "models"));

    [Fact]
    public async Task Compare_MangaOcr_vs_Qwen_OnYuukaImage()
    {
        var imagePath = "/Users/dansetsu/Downloads/image44.jpg";
        if (!File.Exists(imagePath)) { _output.WriteLine("Skipped: image not found"); return; }
        var imageData = await File.ReadAllBytesAsync(imagePath);

        // manga-ocr
        var encoder = Path.Combine(ModelsDir, "manga_ocr_encoder.onnx");
        var decoder = Path.Combine(ModelsDir, "manga_ocr_decoder.onnx");
        var vocab = Path.Combine(ModelsDir, "tokenizer", "vocab.txt");
        if (File.Exists(encoder))
        {
            using var mangaOcr = new MangaOcrOnnx(encoder, decoder, vocab);
            await mangaOcr.InitializeAsync();
            var sw = System.Diagnostics.Stopwatch.StartNew();
            var result = await mangaOcr.RecognizeAsync(imageData);
            sw.Stop();
            _output.WriteLine($"[manga-ocr] {sw.ElapsedMilliseconds}ms");
            _output.WriteLine($"[manga-ocr] '{result.Text}'");
        }

        // Qwen VL
        try
        {
            using var qwen = new QwenVlClient();
            await qwen.InitializeAsync();
            if (qwen.IsReady)
            {
                var sw = System.Diagnostics.Stopwatch.StartNew();
                var result = await qwen.RecognizeAsync(imageData);
                sw.Stop();
                _output.WriteLine($"[qwen-vl]   {sw.ElapsedMilliseconds}ms");
                _output.WriteLine($"[qwen-vl]   '{result.Text}'");
            }
            else { _output.WriteLine("[qwen-vl] Not ready"); }
        }
        catch { _output.WriteLine("[qwen-vl] Ollama not available"); }
    }
}
