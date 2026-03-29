using System.Text;
using System.Text.RegularExpressions;

namespace NoaLog.Core.PostProcess;

/// <summary>
/// Normalizes OCR output by correcting common character-level misreads.
/// </summary>
public static partial class CharNormalizer
{
    /// <summary>
    /// Simplified Chinese characters commonly misread by OCR in Japanese text,
    /// mapped to their correct Japanese (traditional/standard) forms.
    /// </summary>
    private static readonly Dictionary<char, char> SimplifiedToJapaneseMap = new()
    {
        { '对', '対' },
        { '关', '関' },
        { '东', '東' },
        { '书', '書' },
        { '车', '車' },
        { '长', '長' },
        { '门', '門' },
        { '问', '問' },
        { '间', '間' },
        { '见', '見' },
        { '说', '説' },
        { '语', '語' },
        { '读', '読' },
        { '买', '買' },
        { '开', '開' },
        { '写', '写' }, // same in modern Japanese but keep for completeness
        { '马', '馬' },
        { '鱼', '魚' },
        { '鸟', '鳥' },
        { '黑', '黒' },
        { '点', '點' }, // rare, but OCR sometimes picks simplified
        { '广', '広' },
        { '产', '産' },
        { '实', '実' },
        { '现', '現' },
        { '发', '発' },
        { '岁', '歳' },
        { '与', '与' }, // same glyph, no-op but listed for mapping completeness
        { '国', '國' }, // Japanese uses 国, but OCR may pick simplified variant glyph
        { '乐', '楽' },
        { '风', '風' },
    };

    /// <summary>
    /// Fullwidth symbol to halfwidth equivalents.
    /// </summary>
    private static readonly Dictionary<char, char> FullwidthSymbolMap = new()
    {
        { '\uFF08', '(' },   // （
        { '\uFF09', ')' },   // ）
        { '\uFF01', '!' },   // ！
        { '\uFF1F', '?' },   // ？
        { '\uFF1A', ':' },   // ：
        { '\uFF1B', ';' },   // ；
        { '\uFF0C', ',' },   // ，
        { '\uFF0E', '.' },   // ．
        { '\uFF3B', '[' },   // ［
        { '\uFF3D', ']' },   // ］
        { '\uFF5B', '{' },   // ｛
        { '\uFF5D', '}' },   // ｝
        { '\uFF0F', '/' },   // ／
        { '\uFF3C', '\\' },  // ＼
        { '\uFF20', '@' },   // ＠
        { '\uFF03', '#' },   // ＃
        { '\uFF04', '$' },   // ＄
        { '\uFF05', '%' },   // ％
        { '\uFF06', '&' },   // ＆
        { '\uFF0A', '*' },   // ＊
        { '\uFF0B', '+' },   // ＋
        { '\uFF0D', '-' },   // －
        { '\uFF1C', '<' },   // ＜
        { '\uFF1D', '=' },   // ＝
        { '\uFF1E', '>' },   // ＞
    };

    [GeneratedRegex(@"[\s\t]+")]
    private static partial Regex WhitespaceRegex();

    /// <summary>
    /// Applies all normalizations in order:
    /// 1. Simplified Chinese to Japanese kanji
    /// 2. Fullwidth ASCII to halfwidth
    /// 3. Fullwidth symbols to halfwidth
    /// 4. Whitespace normalization
    /// </summary>
    public static string Normalize(string text)
    {
        if (string.IsNullOrEmpty(text))
            return text;

        var sb = new StringBuilder(text.Length);

        foreach (char c in text)
        {
            // 1. Simplified Chinese → Japanese kanji
            if (SimplifiedToJapaneseMap.TryGetValue(c, out char jpChar))
            {
                sb.Append(jpChar);
                continue;
            }

            // 2. Fullwidth ASCII letters → halfwidth
            if (c is >= '\uFF21' and <= '\uFF3A') // Ａ-Ｚ
            {
                sb.Append((char)(c - 0xFF21 + 'A'));
                continue;
            }
            if (c is >= '\uFF41' and <= '\uFF5A') // ａ-ｚ
            {
                sb.Append((char)(c - 0xFF41 + 'a'));
                continue;
            }

            // 3. Fullwidth digits → halfwidth
            if (c is >= '\uFF10' and <= '\uFF19') // ０-９
            {
                sb.Append((char)(c - 0xFF10 + '0'));
                continue;
            }

            // 4. Fullwidth symbols → halfwidth
            if (FullwidthSymbolMap.TryGetValue(c, out char hwSym))
            {
                sb.Append(hwSym);
                continue;
            }

            sb.Append(c);
        }

        // 5. Normalize whitespace: collapse runs of spaces/tabs to single space, trim
        string result = WhitespaceRegex().Replace(sb.ToString(), " ");
        return result.Trim();
    }

    /// <summary>
    /// Attempts to fix katakana ソ/ン confusion based on surrounding context.
    /// This is opt-in because it requires dictionary validation to be reliable.
    /// </summary>
    /// <param name="text">Input text with potential katakana misreads.</param>
    /// <param name="corrections">Known word patterns: key = wrong form, value = correct form.</param>
    /// <returns>Text with katakana corrections applied.</returns>
    public static string FixKatakanaSonConfusion(string text, IReadOnlyDictionary<string, string> corrections)
    {
        if (string.IsNullOrEmpty(text) || corrections.Count == 0)
            return text;

        string result = text;
        foreach (var (wrong, correct) in corrections)
        {
            result = result.Replace(wrong, correct);
        }
        return result;
    }

    /// <summary>
    /// Attempts to fix katakana シ/ツ confusion based on surrounding context.
    /// This is opt-in because it requires dictionary validation to be reliable.
    /// </summary>
    /// <param name="text">Input text with potential katakana misreads.</param>
    /// <param name="corrections">Known word patterns: key = wrong form, value = correct form.</param>
    /// <returns>Text with katakana corrections applied.</returns>
    public static string FixKatakanaShiTsuConfusion(string text, IReadOnlyDictionary<string, string> corrections)
    {
        if (string.IsNullOrEmpty(text) || corrections.Count == 0)
            return text;

        string result = text;
        foreach (var (wrong, correct) in corrections)
        {
            result = result.Replace(wrong, correct);
        }
        return result;
    }
}
