using FuzzySharp;
using NoaLog.Core.Dict;
using NoaLog.Core.Models;

namespace NoaLog.Core.PostProcess;

/// <summary>
/// Main post-processing pipeline that orchestrates character normalization,
/// dictionary lookup, and fuzzy matching for OCR output correction.
/// </summary>
public class DictProcessor
{
    private readonly DictManager _dictManager;

    /// <summary>
    /// Confidence threshold at or above which fuzzy matches are auto-applied.
    /// </summary>
    private const int AutoReplaceThreshold = 95;

    /// <summary>
    /// Minimum confidence for a fuzzy match to be logged as a candidate.
    /// </summary>
    private const int CandidateThreshold = 80;

    public DictProcessor(DictManager dictManager)
    {
        _dictManager = dictManager;
    }

    /// <summary>
    /// Processes raw OCR text through the post-processing pipeline:
    /// 1. Character normalization
    /// 2. Exact dictionary match
    /// 3. Fuzzy matching (auto-replace at 95+, log candidate at 80-94)
    /// </summary>
    /// <param name="rawText">Raw OCR output text.</param>
    /// <param name="gameId">Optional game identifier for game-specific dictionaries.</param>
    /// <returns>Processed text after all pipeline stages.</returns>
    public string Process(string rawText, string? gameId = null)
    {
        if (string.IsNullOrWhiteSpace(rawText))
            return rawText;

        // Step 1: Character normalization
        string normalized = CharNormalizer.Normalize(rawText);

        // Step 2: Exact dictionary match
        string? exactMatch = _dictManager.FindExactMatch(normalized, gameId);
        if (exactMatch is not null)
            return exactMatch;

        // Step 3: Fuzzy matching against dictionary entries
        var entries = _dictManager.GetEntries(gameId);
        if (entries.Count == 0)
            return normalized;

        int bestScore = 0;
        string? bestReplacement = null;

        foreach (var entry in entries)
        {
            int score = Fuzz.Ratio(normalized, entry.Wrong);
            if (score > bestScore)
            {
                bestScore = score;
                bestReplacement = entry.Correct;
            }
        }

        if (bestReplacement is not null)
        {
            if (bestScore >= AutoReplaceThreshold)
            {
                return bestReplacement;
            }

            if (bestScore >= CandidateThreshold)
            {
                System.Diagnostics.Debug.WriteLine(
                    $"[DictProcessor] Fuzzy candidate (score={bestScore}): " +
                    $"'{normalized}' -> '{bestReplacement}'");
            }
        }

        return normalized;
    }

    /// <summary>
    /// Processes a full LogEntry by applying the pipeline to header and body.
    /// Sets SpeakerName, SpeakerOrg, and BodyText from processed results.
    /// </summary>
    /// <param name="entry">The log entry to process in place.</param>
    public void ProcessEntry(LogEntry entry)
    {
        string processedHeader = Process(entry.RawHeader);
        string processedBody = Process(entry.RawBody);

        // Parse header: "Name / Org" or just "Name"
        ParseHeader(processedHeader, out string speakerName, out string speakerOrg);

        entry.SpeakerName = speakerName;
        entry.SpeakerOrg = speakerOrg;
        entry.BodyText = processedBody;
    }

    private static void ParseHeader(string header, out string speakerName, out string speakerOrg)
    {
        if (string.IsNullOrWhiteSpace(header))
        {
            speakerName = "";
            speakerOrg = "";
            return;
        }

        int separatorIndex = header.IndexOf(" / ", StringComparison.Ordinal);
        if (separatorIndex >= 0)
        {
            speakerName = header[..separatorIndex].Trim();
            speakerOrg = header[(separatorIndex + 3)..].Trim();
        }
        else
        {
            speakerName = header.Trim();
            speakerOrg = "";
        }
    }
}
