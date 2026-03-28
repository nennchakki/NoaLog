using System.Text;

namespace NoaLog.Core.Ocr;

/// <summary>
/// Lightweight BERT tokenizer for decoding manga-ocr output tokens back to text.
/// Decode only — no encoding logic needed.
/// </summary>
public class BertTokenizer
{
    public const int PadTokenId = 0;
    public const int UnkTokenId = 1;
    public const int ClsTokenId = 2;
    public const int SepTokenId = 3;
    public const int MaskTokenId = 4;
    public const int DecoderStartTokenId = 2; // Same as [CLS]

    private readonly Dictionary<int, string> _idToToken;
    private readonly int _vocabSize;

    /// <summary>
    /// Special token IDs to skip during decoding.
    /// </summary>
    private static readonly HashSet<int> SpecialTokenIds = new() { PadTokenId, UnkTokenId, ClsTokenId, SepTokenId, MaskTokenId };

    public int VocabSize => _vocabSize;

    /// <summary>
    /// Load a vocab.txt file where each line is a token and the line number (0-indexed) is the token ID.
    /// </summary>
    /// <param name="vocabPath">Path to vocab.txt.</param>
    public BertTokenizer(string vocabPath)
    {
        var lines = File.ReadAllLines(vocabPath);
        _vocabSize = lines.Length;
        _idToToken = new Dictionary<int, string>(lines.Length);
        for (var i = 0; i < lines.Length; i++)
        {
            _idToToken[i] = lines[i];
        }
    }

    /// <summary>
    /// Decode a sequence of token IDs to text.
    /// Handles subword merging (## prefix) and skips special tokens.
    /// For Japanese text, tokens are concatenated directly without spaces.
    /// </summary>
    /// <param name="tokenIds">Token IDs produced by the model.</param>
    /// <returns>Decoded text string.</returns>
    public string Decode(IReadOnlyList<int> tokenIds)
    {
        var sb = new StringBuilder();

        foreach (var id in tokenIds)
        {
            if (SpecialTokenIds.Contains(id))
                continue;

            if (!_idToToken.TryGetValue(id, out var token))
                continue;

            // Strip ## prefix for subword tokens
            if (token.StartsWith("##"))
            {
                sb.Append(token.AsSpan(2));
            }
            else
            {
                sb.Append(token);
            }
        }

        return sb.ToString();
    }
}
