using System.Text;
using System.Text.Json;
using NoaLog.Core.Models;

namespace NoaLog.Core.Export;

/// <summary>
/// ログエントリのエクスポートロジック（UIに依存しない）
/// </summary>
public static class LogExporter
{
    /// <summary>
    /// 複数エントリをプレーンテキスト形式に変換する
    /// </summary>
    public static string ToPlainText(IReadOnlyList<LogEntry> entries)
    {
        var sb = new StringBuilder();
        for (var i = 0; i < entries.Count; i++)
        {
            var entry = entries[i];
            var header = string.IsNullOrEmpty(entry.DisplayOrg)
                ? entry.DisplayName
                : $"{entry.DisplayName} {entry.DisplayOrg}";

            sb.AppendLine(header);
            sb.AppendLine(entry.DisplayBody);

            if (i < entries.Count - 1)
                sb.AppendLine();
        }

        return sb.ToString().TrimEnd();
    }

    /// <summary>
    /// 複数エントリをMarkdown形式に変換する
    /// </summary>
    public static string ToMarkdown(IReadOnlyList<LogEntry> entries)
    {
        var sb = new StringBuilder();
        for (var i = 0; i < entries.Count; i++)
        {
            var entry = entries[i];
            var header = string.IsNullOrEmpty(entry.DisplayOrg)
                ? entry.DisplayName
                : $"{entry.DisplayName} / {entry.DisplayOrg}";

            sb.AppendLine($"## {header}");
            sb.AppendLine($"*{entry.Timestamp:yyyy-MM-dd HH:mm:ss}*");
            sb.AppendLine();
            sb.AppendLine(entry.DisplayBody);

            // 最後のエントリ以外はセパレータを挟む
            if (i < entries.Count - 1)
            {
                sb.AppendLine();
                sb.AppendLine("---");
                sb.AppendLine();
            }
        }

        return sb.ToString().TrimEnd();
    }

    /// <summary>
    /// 複数エントリをJSON形式に変換する
    /// </summary>
    public static string ToJson(IReadOnlyList<LogEntry> entries)
    {
        var items = new List<object>(entries.Count);
        foreach (var entry in entries)
        {
            items.Add(new
            {
                timestamp = entry.Timestamp.ToString("yyyy-MM-ddTHH:mm:ss"),
                speaker = entry.DisplayName,
                organization = entry.DisplayOrg,
                body = entry.DisplayBody,
            });
        }

        var options = new JsonSerializerOptions
        {
            WriteIndented = true,
            Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
        };
        return JsonSerializer.Serialize(items, options);
    }

    /// <summary>
    /// 単一エントリを指定フォーマットで変換する（CopyPanel用）
    /// </summary>
    /// <param name="entry">対象のログエントリ</param>
    /// <param name="format">フォーマット名: "plain", "markdown", "json"</param>
    public static string FormatEntry(LogEntry entry, string format)
    {
        var list = new List<LogEntry> { entry };
        return format switch
        {
            "markdown" => ToMarkdown(list),
            "json" => ToJson(list),
            _ => ToPlainText(list),
        };
    }
}
