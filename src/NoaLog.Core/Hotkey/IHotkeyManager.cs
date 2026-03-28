using NoaLog.Core.Models;

namespace NoaLog.Core.Hotkey;

/// <summary>
/// グローバルホットキーのプラットフォーム抽象化。
/// Windows: Win32 RegisterHotKey
/// macOS: 開発時はスタブ実装
/// </summary>
public interface IHotkeyManager : IDisposable
{
    /// <summary>ホットキーが押された時に発火するイベント</summary>
    event EventHandler<HotkeyEventArgs>? HotkeyPressed;

    /// <summary>ホットキーを登録する</summary>
    /// <param name="id">ホットキーの識別名</param>
    /// <param name="hotkey">キーの組み合わせ</param>
    bool Register(string id, Models.Hotkey hotkey);

    /// <summary>ホットキーの登録を解除する</summary>
    bool Unregister(string id);

    /// <summary>全ホットキーの登録を解除する</summary>
    void UnregisterAll();
}

/// <summary>ホットキーイベント引数</summary>
public class HotkeyEventArgs : EventArgs
{
    public string Id { get; }
    public HotkeyEventArgs(string id) => Id = id;
}
