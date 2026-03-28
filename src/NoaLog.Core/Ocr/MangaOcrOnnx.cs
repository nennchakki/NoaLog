using Microsoft.ML.OnnxRuntime;
using Microsoft.ML.OnnxRuntime.Tensors;
using NoaLog.Core.Models;

namespace NoaLog.Core.Ocr;

/// <summary>
/// manga-ocr ONNX implementation.
/// Uses DeiT-Tiny encoder + BERT-base-japanese decoder for Japanese OCR.
/// </summary>
public class MangaOcrOnnx : IOcrEngine, IDisposable
{
    // Model architecture constants
    private const int ImageSize = 224;
    private const int EncoderHiddenSize = 192;
    private const int EncoderNumPatches = 197; // (224/16)^2 + 1
    private const int DecoderMaxLength = 300;

    // ONNX I/O names
    private const string EncoderInputName = "pixel_values";
    private const string EncoderOutputName = "last_hidden_state";
    private const string DecoderInputIdsName = "input_ids";
    private const string DecoderEncoderHiddenStatesName = "encoder_hidden_states";
    private const string DecoderOutputName = "logits";

    private readonly string _encoderModelPath;
    private readonly string _decoderModelPath;
    private readonly string _vocabPath;

    private InferenceSession? _encoderSession;
    private InferenceSession? _decoderSession;
    private BertTokenizer? _tokenizer;
    private bool _disposed;

    public string EngineName => "manga_ocr_onnx";
    public bool IsReady => _encoderSession != null && _decoderSession != null && _tokenizer != null;

    public MangaOcrOnnx(string encoderModelPath, string decoderModelPath, string vocabPath)
    {
        _encoderModelPath = encoderModelPath;
        _decoderModelPath = decoderModelPath;
        _vocabPath = vocabPath;
    }

    public Task InitializeAsync(CancellationToken cancellationToken = default)
    {
        return Task.Run(() =>
        {
            var sessionOptions = new SessionOptions
            {
                GraphOptimizationLevel = GraphOptimizationLevel.ORT_ENABLE_ALL,
                IntraOpNumThreads = 2, // Conserve CPU for game co-execution
            };

            _encoderSession = new InferenceSession(_encoderModelPath, sessionOptions);
            _decoderSession = new InferenceSession(_decoderModelPath, sessionOptions);
            _tokenizer = new BertTokenizer(_vocabPath);
        }, cancellationToken);
    }

    public Task<OcrResult> RecognizeAsync(byte[] imageData, CancellationToken cancellationToken = default)
    {
        if (!IsReady)
            throw new InvalidOperationException("Engine not initialized. Call InitializeAsync first.");

        return Task.Run(() => Recognize(imageData), cancellationToken);
    }

    private OcrResult Recognize(byte[] imageData)
    {
        // 1. Preprocess image → float tensor
        var pixelValues = OcrPreprocessor.Process(imageData);

        // 2. Run encoder
        var encoderHiddenStates = RunEncoder(pixelValues);

        // 3. Run decoder (autoregressive greedy decoding)
        var tokenIds = RunDecoder(encoderHiddenStates);

        // 4. Decode tokens to text
        var text = _tokenizer!.Decode(tokenIds);

        // manga-ocr doesn't provide confidence scores; use 1.0 for successful recognition
        var confidence = text.Length > 0 ? 1.0 : 0.0;

        return new OcrResult(text, confidence);
    }

    private float[] RunEncoder(float[] pixelValues)
    {
        var inputTensor = new DenseTensor<float>(
            pixelValues, new[] { 1, 3, ImageSize, ImageSize });

        var inputs = new[]
        {
            NamedOnnxValue.CreateFromTensor(EncoderInputName, inputTensor),
        };

        using var results = _encoderSession!.Run(inputs);

        var outputTensor = results[0].AsTensor<float>();
        var output = new float[EncoderNumPatches * EncoderHiddenSize];
        for (int i = 0; i < output.Length; i++)
            output[i] = outputTensor.GetValue(i);
        return output;
    }

    private List<int> RunDecoder(float[] encoderHiddenStates)
    {
        var vocabSize = _tokenizer!.VocabSize;
        var generatedTokens = new List<int> { BertTokenizer.DecoderStartTokenId };

        var encoderTensor = new DenseTensor<float>(
            encoderHiddenStates, new[] { 1, EncoderNumPatches, EncoderHiddenSize });

        for (int step = 0; step < DecoderMaxLength - 1; step++)
        {
            var seqLen = generatedTokens.Count;

            // Build input_ids tensor (int64)
            var inputIds = new long[seqLen];
            for (int i = 0; i < seqLen; i++)
                inputIds[i] = generatedTokens[i];

            var inputIdsTensor = new DenseTensor<long>(inputIds, new[] { 1, seqLen });

            var inputs = new[]
            {
                NamedOnnxValue.CreateFromTensor(DecoderInputIdsName, inputIdsTensor),
                NamedOnnxValue.CreateFromTensor(DecoderEncoderHiddenStatesName, encoderTensor),
            };

            using var results = _decoderSession!.Run(inputs);

            var logits = results[0].AsTensor<float>();

            // Extract logits for the last token position: [0, seqLen-1, :]
            int nextTokenId = Argmax(logits, seqLen - 1, vocabSize);
            generatedTokens.Add(nextTokenId);

            // Stop at [SEP] token
            if (nextTokenId == BertTokenizer.SepTokenId)
                break;
        }

        return generatedTokens;
    }

    /// <summary>
    /// Find the token with the highest logit at the given sequence position.
    /// logits shape: (1, seq_len, vocab_size)
    /// </summary>
    private static int Argmax(Tensor<float> logits, int seqPosition, int vocabSize)
    {
        int bestId = 0;
        float bestVal = float.NegativeInfinity;

        for (int i = 0; i < vocabSize; i++)
        {
            float val = logits[0, seqPosition, i];
            if (val > bestVal)
            {
                bestVal = val;
                bestId = i;
            }
        }

        return bestId;
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

        _encoderSession?.Dispose();
        _decoderSession?.Dispose();
        _encoderSession = null;
        _decoderSession = null;
        GC.SuppressFinalize(this);
    }
}
