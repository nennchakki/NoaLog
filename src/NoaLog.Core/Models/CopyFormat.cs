namespace NoaLog.Core.Models;

public record CopyFormat(string Name, string Template, bool IncludeTimestamp, string Separator = "\n")
{
    public static class Presets
    {
        public static CopyFormat Plain { get; } = new("Plain", "{header}\n{body}", false);
        public static CopyFormat Markdown { get; } = new("Markdown", "**{header}**\n{body}", false);
        public static CopyFormat Quote { get; } = new("Quote", "> {body}\n> -- {header}", false);
        public static CopyFormat Script { get; } = new("Script", "{name}: {body}", false);
    }
}
