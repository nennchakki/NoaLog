using FuzzySharp;

namespace NoaLog.Core.PostProcess;

/// <summary>
/// FuzzySharp を使用したファジーマッチング。
/// OCR誤読の候補を辞書エントリとマッチングする。
/// </summary>
public class FuzzyMatcher
{
    // Score thresholds
    public const int AutoReplaceThreshold = 95;  // 95+ → auto-replace
    public const int CandidateThreshold = 80;    // 80-94 → log as candidate

    /// <summary>
    /// Find the best match for the given text from a list of dictionary entries.
    /// Returns (matchedCorrectText, score) or null if no match above CandidateThreshold.
    /// </summary>
    public static FuzzyMatchResult? FindBestMatch(string input, IReadOnlyList<DictEntry> entries)
    {
        if (string.IsNullOrEmpty(input) || entries.Count == 0)
            return null;

        FuzzyMatchResult? best = null;

        foreach (var entry in entries)
        {
            int score = Fuzz.Ratio(input, entry.WrongText);
            if (score >= CandidateThreshold && (best is null || score > best.Score))
            {
                best = new FuzzyMatchResult(entry.CorrectText, score, entry.WrongText);
            }
        }

        return best;
    }

    /// <summary>
    /// Try to find and replace substrings within text using fuzzy matching.
    /// Only replaces if score >= AutoReplaceThreshold.
    /// </summary>
    public static FuzzyProcessResult ProcessText(string text, IReadOnlyList<DictEntry> entries)
    {
        var replacements = new List<FuzzyReplacement>();
        var candidates = new List<FuzzyMatchResult>();
        var processedText = text;

        if (string.IsNullOrEmpty(text) || entries.Count == 0)
            return new FuzzyProcessResult(processedText, replacements, candidates);

        foreach (var entry in entries)
        {
            if (string.IsNullOrEmpty(entry.WrongText))
                continue;

            // Sliding window: check substrings of the same length as WrongText
            int windowLen = entry.WrongText.Length;
            if (windowLen > processedText.Length)
                continue;

            // Scan from end to start so replacements don't shift indices
            for (int i = processedText.Length - windowLen; i >= 0; i--)
            {
                string substring = processedText.Substring(i, windowLen);
                int score = Fuzz.Ratio(substring, entry.WrongText);

                if (score >= AutoReplaceThreshold)
                {
                    replacements.Add(new FuzzyReplacement(substring, entry.CorrectText, score));
                    processedText = string.Concat(
                        processedText.AsSpan(0, i),
                        entry.CorrectText,
                        processedText.AsSpan(i + windowLen));
                    // After replacement, adjust loop position
                    i = Math.Min(i, processedText.Length - windowLen);
                }
                else if (score >= CandidateThreshold)
                {
                    candidates.Add(new FuzzyMatchResult(entry.CorrectText, score, substring));
                }
            }
        }

        return new FuzzyProcessResult(processedText, replacements, candidates);
    }
}

/// <summary>
/// Dictionary entry mapping a wrong (OCR-misread) text to its correct form.
/// </summary>
public record DictEntry(string WrongText, string CorrectText, string Category = "proper_noun");

/// <summary>
/// Result of a single fuzzy match lookup.
/// </summary>
public record FuzzyMatchResult(string CorrectText, int Score, string MatchedWrongText);

/// <summary>
/// Result of processing a full text string with fuzzy matching.
/// </summary>
public record FuzzyProcessResult(
    string ProcessedText,
    List<FuzzyReplacement> Replacements,
    List<FuzzyMatchResult> Candidates);

/// <summary>
/// A single replacement that was applied during text processing.
/// </summary>
public record FuzzyReplacement(string Original, string Replacement, int Score);
