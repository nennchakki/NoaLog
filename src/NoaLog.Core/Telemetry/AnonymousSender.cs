using System.Net.Http;
using System.Text;

namespace NoaLog.Core.Telemetry;

/// <summary>
/// 匿名修正データをGoogle Formsに送信する。
/// telemetry.enabled設定がTrueの場合のみ動作。
/// </summary>
public class AnonymousSender
{
    private readonly Storage.SqliteStorage _storage;
    private readonly HttpClient _httpClient = new();

    // Placeholder — replace with actual obfuscated URL when Google Form is created
    private const string ObfuscatedFormUrl = "";

    // Placeholder Google Forms entry IDs — fill in when form is created
    private const string EntryOcrEngine = "entry.000000001";
    private const string EntryFieldName = "entry.000000002";
    private const string EntryOriginalValue = "entry.000000003";
    private const string EntryCorrectedValue = "entry.000000004";
    private const string EntryGameId = "entry.000000005";

    public AnonymousSender(Storage.SqliteStorage storage) => _storage = storage;

    public async Task SendPendingAsync(CancellationToken ct = default)
    {
        try
        {
            // Check if telemetry is enabled
            var enabled = _storage.GetSetting("telemetry.enabled");
            if (enabled != "True") return;

            // Get unsent records
            var records = _storage.GetUnsentCorrectionRecords();
            if (records.Count == 0) return;

            // Deobfuscate form URL
            if (string.IsNullOrEmpty(ObfuscatedFormUrl)) return; // Not configured yet
            var formUrl = UrlObfuscator.Deobfuscate(ObfuscatedFormUrl);

            var sentIds = new List<int>();

            foreach (var record in records)
            {
                ct.ThrowIfCancellationRequested();

                try
                {
                    var content = new FormUrlEncodedContent(new Dictionary<string, string>
                    {
                        [EntryOcrEngine] = record.OcrEngine,
                        [EntryFieldName] = record.FieldName,
                        [EntryOriginalValue] = record.OriginalValue,
                        [EntryCorrectedValue] = record.CorrectedValue,
                        [EntryGameId] = record.GameId ?? "unknown",
                    });

                    var response = await _httpClient.PostAsync(formUrl, content, ct);
                    if (response.IsSuccessStatusCode)
                    {
                        sentIds.Add(record.Id);
                    }
                }
                catch
                {
                    // Individual record failure — skip and continue
                }
            }

            if (sentIds.Count > 0)
            {
                _storage.MarkCorrectionRecordsSent(sentIds);
            }
        }
        catch
        {
            // Telemetry must never crash the app
        }
    }
}
