namespace NoaLog.Core.Ollama;

public record PullProgress(string Status, long CompletedBytes, long TotalBytes);
