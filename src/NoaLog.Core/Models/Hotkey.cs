namespace NoaLog.Core.Models;

public record Hotkey(List<string> Keys)
{
    public override string ToString() => string.Join("+", Keys);
}
