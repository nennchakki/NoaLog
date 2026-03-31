using System.Collections.Concurrent;
using System.Diagnostics;
using System.Runtime.InteropServices;
using NoaLog.Core.Models;

namespace NoaLog.Core.Hotkey;

/// <summary>
/// macOS用グローバルホットキーマネージャー。
/// CGEventTapを使用してシステムワイドのキーボードイベントを監視。
/// Note: macOSのアクセシビリティ権限が必要（システム設定 > プライバシーとセキュリティ > アクセシビリティ）。
/// </summary>
public sealed class MacHotkeyManager : IHotkeyManager, IDisposable
{
    #region Native Constants

    private const int kCGSessionEventTap = 1;
    private const int kCGHeadInsertEventTap = 0;
    private const int kCGEventTapOptionListenOnly = 1;
    private const int kCGEventKeyDown = 10;
    private const int kCGKeyboardEventKeycode = 9;

    // CGEventFlags
    private const ulong kCGEventFlagMaskShift = 0x00020000;
    private const ulong kCGEventFlagMaskControl = 0x00040000;
    private const ulong kCGEventFlagMaskAlternate = 0x00080000;
    private const ulong kCGEventFlagMaskCommand = 0x00100000;

    // Modifier mask to ignore non-modifier bits (device-dependent flags, etc.)
    private const ulong ModifierMask =
        kCGEventFlagMaskShift | kCGEventFlagMaskControl |
        kCGEventFlagMaskAlternate | kCGEventFlagMaskCommand;

    private static readonly IntPtr kCFRunLoopCommonModes = CFStringCreateWithCString(IntPtr.Zero, "kCFRunLoopCommonModes", 0);

    #endregion

    #region P/Invoke — Core Graphics (ApplicationServices)

    private const string AppServices = "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices";
    private const string CoreFoundationLib = "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation";

    // CGEventTapCallback: IntPtr proxy, int type, IntPtr event, IntPtr userInfo -> IntPtr
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate IntPtr CGEventTapCallBack(IntPtr proxy, int type, IntPtr @event, IntPtr userInfo);

    [DllImport(AppServices)]
    private static extern IntPtr CGEventTapCreate(
        int tap,
        int place,
        int options,
        ulong eventsOfInterest,
        CGEventTapCallBack callback,
        IntPtr userInfo);

    [DllImport(AppServices)]
    private static extern void CGEventTapEnable(IntPtr tap, bool enable);

    [DllImport(AppServices)]
    private static extern ulong CGEventGetFlags(IntPtr @event);

    [DllImport(AppServices)]
    private static extern long CGEventGetIntegerValueField(IntPtr @event, int field);

    #endregion

    #region P/Invoke — Core Foundation

    [DllImport(CoreFoundationLib)]
    private static extern IntPtr CFMachPortCreateRunLoopSource(IntPtr allocator, IntPtr port, int order);

    [DllImport(CoreFoundationLib)]
    private static extern void CFRunLoopAddSource(IntPtr rl, IntPtr source, IntPtr mode);

    [DllImport(CoreFoundationLib)]
    private static extern IntPtr CFRunLoopGetCurrent();

    [DllImport(CoreFoundationLib)]
    private static extern void CFRunLoopRun();

    [DllImport(CoreFoundationLib)]
    private static extern void CFRunLoopStop(IntPtr rl);

    [DllImport(CoreFoundationLib)]
    private static extern void CFRelease(IntPtr cf);

    [DllImport(CoreFoundationLib)]
    private static extern IntPtr CFStringCreateWithCString(IntPtr allocator, string cStr, int encoding);

    #endregion

    #region macOS Virtual Key Code Mapping

    private static readonly Dictionary<string, ushort> VirtualKeyCodes = new(StringComparer.OrdinalIgnoreCase)
    {
        // Letters
        ["A"] = 0, ["B"] = 11, ["C"] = 8, ["D"] = 2,
        ["E"] = 14, ["F"] = 3, ["G"] = 5, ["H"] = 4,
        ["I"] = 34, ["J"] = 38, ["K"] = 40, ["L"] = 37,
        ["M"] = 46, ["N"] = 45, ["O"] = 31, ["P"] = 35,
        ["Q"] = 12, ["R"] = 15, ["S"] = 1, ["T"] = 17,
        ["U"] = 32, ["V"] = 9, ["W"] = 13, ["X"] = 7,
        ["Y"] = 16, ["Z"] = 6,

        // Numbers
        ["0"] = 29, ["1"] = 18, ["2"] = 19, ["3"] = 20,
        ["4"] = 21, ["5"] = 23, ["6"] = 22, ["7"] = 26,
        ["8"] = 28, ["9"] = 25,

        // Function keys
        ["F1"] = 122, ["F2"] = 120, ["F3"] = 99, ["F4"] = 118,
        ["F5"] = 96, ["F6"] = 97, ["F7"] = 98, ["F8"] = 100,
        ["F9"] = 101, ["F10"] = 109, ["F11"] = 103, ["F12"] = 111,

        // Special keys
        ["Space"] = 49, ["Enter"] = 36, ["Return"] = 36,
        ["Tab"] = 48, ["Escape"] = 53, ["Delete"] = 51,
        ["Backspace"] = 51,
    };

    private static readonly Dictionary<string, ulong> ModifierMap = new(StringComparer.OrdinalIgnoreCase)
    {
        ["Ctrl"] = kCGEventFlagMaskControl,
        ["Control"] = kCGEventFlagMaskControl,
        ["Alt"] = kCGEventFlagMaskAlternate,
        ["Option"] = kCGEventFlagMaskAlternate,
        ["Shift"] = kCGEventFlagMaskShift,
        ["Meta"] = kCGEventFlagMaskCommand,
        ["Cmd"] = kCGEventFlagMaskCommand,
        ["Command"] = kCGEventFlagMaskCommand,
    };

    #endregion

    private readonly ConcurrentDictionary<string, (ushort keyCode, ulong modifiers)> _registeredHotkeys = new();

    private Thread? _tapThread;
    private IntPtr _runLoop;
    private IntPtr _eventTap;
    private IntPtr _runLoopSource;
    private volatile bool _disposed;
    private readonly ManualResetEventSlim _tapReady = new(false);

    // コールバックデリゲートをGCから保護するためフィールドに保持
    private CGEventTapCallBack? _callback;

    public event EventHandler<HotkeyEventArgs>? HotkeyPressed;

    public MacHotkeyManager()
    {
        StartEventTap();
    }

    private void StartEventTap()
    {
        _tapThread = new Thread(RunEventTap)
        {
            IsBackground = true,
            Name = "MacHotkeyTap",
        };
        _tapThread.Start();

        // イベントタップの準備完了を最大5秒待機
        if (!_tapReady.Wait(TimeSpan.FromSeconds(5)))
        {
            Debug.WriteLine("MacHotkeyManager: Event tap creation timed out. Accessibility permission may be missing.");
        }
    }

    private void RunEventTap()
    {
        // キーダウンイベントのみ監視
        ulong eventMask = 1UL << kCGEventKeyDown;

        _callback = OnEventTapCallback;

        _eventTap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly,
            eventMask,
            _callback,
            IntPtr.Zero);

        if (_eventTap == IntPtr.Zero)
        {
            Debug.WriteLine("MacHotkeyManager: CGEventTapCreate failed. Grant Accessibility permission to this app.");
            _tapReady.Set();
            return;
        }

        _runLoopSource = CFMachPortCreateRunLoopSource(IntPtr.Zero, _eventTap, 0);
        if (_runLoopSource == IntPtr.Zero)
        {
            Debug.WriteLine("MacHotkeyManager: CFMachPortCreateRunLoopSource failed.");
            CFRelease(_eventTap);
            _eventTap = IntPtr.Zero;
            _tapReady.Set();
            return;
        }

        _runLoop = CFRunLoopGetCurrent();
        CFRunLoopAddSource(_runLoop, _runLoopSource, kCFRunLoopCommonModes);
        CGEventTapEnable(_eventTap, true);

        _tapReady.Set();

        // このスレッドをブロックしてイベントループを実行
        CFRunLoopRun();
    }

    private IntPtr OnEventTapCallback(IntPtr proxy, int type, IntPtr @event, IntPtr userInfo)
    {
        // タップが無効化された場合（システムタイムアウト）、再有効化
        if (type == 0 && _eventTap != IntPtr.Zero) // kCGEventTapDisabledByTimeout = 0xFFFFFFFE but arrives as negative
        {
            // イベントタイプが想定外の場合は再有効化を試みる
        }

        // kCGEventTapDisabledByTimeout / kCGEventTapDisabledByUserInput の処理
        const int kCGEventTapDisabledByTimeout = unchecked((int)0xFFFFFFFE);
        if (type == kCGEventTapDisabledByTimeout)
        {
            CGEventTapEnable(_eventTap, true);
            return @event;
        }

        if (type != kCGEventKeyDown)
            return @event;

        var keyCode = (ushort)CGEventGetIntegerValueField(@event, kCGKeyboardEventKeycode);
        var flags = CGEventGetFlags(@event) & ModifierMask;

        foreach (var kvp in _registeredHotkeys)
        {
            if (kvp.Value.keyCode == keyCode && kvp.Value.modifiers == flags)
            {
                // UIスレッドをブロックしないよう、ThreadPoolで発火
                var id = kvp.Key;
                ThreadPool.QueueUserWorkItem(_ =>
                {
                    HotkeyPressed?.Invoke(this, new HotkeyEventArgs(id));
                });
                break;
            }
        }

        return @event;
    }

    public bool Register(string id, Models.Hotkey hotkey)
    {
        if (_disposed)
            return false;

        if (!TryParseHotkey(hotkey, out var keyCode, out var modifiers))
            return false;

        _registeredHotkeys[id] = (keyCode, modifiers);
        return true;
    }

    public bool Unregister(string id)
    {
        if (_disposed)
            return false;

        return _registeredHotkeys.TryRemove(id, out _);
    }

    public void UnregisterAll()
    {
        _registeredHotkeys.Clear();
    }

    private static bool TryParseHotkey(Models.Hotkey hotkey, out ushort keyCode, out ulong modifiers)
    {
        keyCode = 0;
        modifiers = 0;
        var keyFound = false;

        foreach (var key in hotkey.Keys)
        {
            if (ModifierMap.TryGetValue(key, out var mod))
            {
                modifiers |= mod;
            }
            else if (VirtualKeyCodes.TryGetValue(key, out var vk))
            {
                keyCode = vk;
                keyFound = true;
            }
            else
            {
                // 不明なキー名
                Debug.WriteLine($"MacHotkeyManager: Unknown key name '{key}'");
                return false;
            }
        }

        return keyFound;
    }

    public void Dispose()
    {
        if (_disposed)
            return;

        _disposed = true;
        UnregisterAll();

        // CFRunLoopを停止
        if (_runLoop != IntPtr.Zero)
        {
            CFRunLoopStop(_runLoop);
        }

        // イベントタップを無効化・解放
        if (_eventTap != IntPtr.Zero)
        {
            CGEventTapEnable(_eventTap, false);
            CFRelease(_eventTap);
            _eventTap = IntPtr.Zero;
        }

        if (_runLoopSource != IntPtr.Zero)
        {
            CFRelease(_runLoopSource);
            _runLoopSource = IntPtr.Zero;
        }

        _tapThread?.Join(TimeSpan.FromSeconds(3));
        _tapThread = null;

        _tapReady.Dispose();
    }
}
