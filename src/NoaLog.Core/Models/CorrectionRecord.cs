namespace NoaLog.Core.Models;

public class CorrectionRecord
{
    public int Id { get; set; }
    public string LogEntryId { get; set; } = "";
    public string FieldName { get; set; } = "";
    public string OriginalValue { get; set; } = "";
    public string CorrectedValue { get; set; } = "";
    public string OcrEngine { get; set; } = "";
    public string? GameId { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public bool IsSent { get; set; }
}
