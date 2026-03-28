namespace NoaLog.Core.Models;

public record OcrResult(string Text, double Confidence, List<object>? RawResults = null)
{
    public bool IsValid(double minConfidence = 0.5) => Confidence >= minConfidence;
}
