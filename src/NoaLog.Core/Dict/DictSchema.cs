using System.Text.Json.Serialization;

namespace NoaLog.Core.Dict;

/// <summary>辞書ファイルのJSONスキーマ定義</summary>
public class DictFile
{
    [JsonPropertyName("meta")]
    public DictMeta Meta { get; set; } = new();

    [JsonPropertyName("entries")]
    public List<DictFileEntry> Entries { get; set; } = new();
}

public class DictMeta
{
    [JsonPropertyName("game_id")]
    public string GameId { get; set; } = "";

    [JsonPropertyName("version")]
    public string Version { get; set; } = "1.0.0";

    [JsonPropertyName("description")]
    public string? Description { get; set; }
}

public class DictFileEntry
{
    [JsonPropertyName("wrong")]
    public string Wrong { get; set; } = "";

    [JsonPropertyName("correct")]
    public string Correct { get; set; } = "";

    [JsonPropertyName("category")]
    public string Category { get; set; } = "proper_noun";

    [JsonPropertyName("match_type")]
    public string MatchType { get; set; } = "exact";
}
