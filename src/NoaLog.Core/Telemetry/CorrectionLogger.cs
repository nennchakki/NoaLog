namespace NoaLog.Core.Telemetry;

/// <summary>
/// ユーザーがOCR結果を手動修正した際に差分をcorrection_logに記録する。
/// </summary>
public class CorrectionLogger
{
    private readonly Storage.SqliteStorage _storage;

    public CorrectionLogger(Storage.SqliteStorage storage) => _storage = storage;

    /// <summary>
    /// フィールドの修正を記録。original != corrected の場合のみINSERT。
    /// </summary>
    public void LogCorrection(Models.LogEntry entry, string fieldName, string originalValue, string correctedValue)
    {
        if (string.IsNullOrEmpty(originalValue) && string.IsNullOrEmpty(correctedValue)) return;
        if (originalValue == correctedValue) return;

        var record = new Models.CorrectionRecord
        {
            LogEntryId = entry.Id,
            FieldName = fieldName,
            OriginalValue = originalValue,
            CorrectedValue = correctedValue,
            OcrEngine = entry.OcrEngine,
            GameId = entry.ProfileId, // use profile as game context
        };
        _storage.InsertCorrectionRecord(record);
    }
}
