namespace NoaLog.Core.Models;

public class Profile
{
    public string Id { get; set; }
    public string Name { get; set; } = "";
    public string Description { get; set; } = "";
    public Rect? TextAreaRect { get; set; }
    public Rect? NarratorRect { get; set; }
    public Hotkey? Hotkey { get; set; }
    public Hotkey? NarratorHotkey { get; set; }
    public string NarratorLabel { get; set; } = "語り部";
    public Dictionary<string, object>? OcrSettings { get; set; }
    public bool IsActive { get; set; } = true;
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }

    public Profile()
    {
        Id = Guid.NewGuid().ToString();
        CreatedAt = DateTime.UtcNow;
        UpdatedAt = DateTime.UtcNow;
    }
}
