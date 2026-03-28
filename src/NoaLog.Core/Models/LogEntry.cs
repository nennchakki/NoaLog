namespace NoaLog.Core.Models;

public class LogEntry
{
    public string Id { get; set; }
    public string ProfileId { get; set; } = "";
    public DateTime Timestamp { get; set; }
    public LogType LogType { get; set; } = LogType.Dialogue;
    public string RawHeader { get; set; } = "";
    public string RawBody { get; set; } = "";
    public string SpeakerName { get; set; } = "";
    public string SpeakerOrg { get; set; } = "";
    public string BodyText { get; set; } = "";
    public string? EditedSpeakerName { get; set; }
    public string? EditedSpeakerOrg { get; set; }
    public string? EditedBodyText { get; set; }
    public string? CapturePath { get; set; }
    public string OcrEngine { get; set; } = "manga_ocr_onnx";
    public double OcrConfidence { get; set; }
    public bool IsDeleted { get; set; }
    public bool IsDuplicate { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }

    public string DisplayName => EditedSpeakerName ?? SpeakerName;
    public string DisplayOrg => EditedSpeakerOrg ?? SpeakerOrg;
    public string DisplayBody => EditedBodyText ?? BodyText;

    public string DisplayHeader =>
        string.IsNullOrEmpty(DisplayOrg)
            ? DisplayName
            : $"{DisplayName} / {DisplayOrg}";

    public LogEntry()
    {
        Id = Guid.NewGuid().ToString();
        Timestamp = DateTime.UtcNow;
        CreatedAt = DateTime.UtcNow;
        UpdatedAt = DateTime.UtcNow;
    }
}
