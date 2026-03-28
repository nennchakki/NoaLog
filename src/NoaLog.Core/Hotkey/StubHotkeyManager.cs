namespace NoaLog.Core.Hotkey;

/// <summary>macOS開発用スタブ。ホットキーは動作しない。</summary>
public class StubHotkeyManager : IHotkeyManager
{
    public event EventHandler<HotkeyEventArgs>? HotkeyPressed;

    public bool Register(string id, Models.Hotkey hotkey) => false;
    public bool Unregister(string id) => false;
    public void UnregisterAll() { }
    public void Dispose() { }
}
