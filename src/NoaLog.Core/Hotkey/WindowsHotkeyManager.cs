#if WINDOWS
using System.Collections.Concurrent;
using System.Runtime.InteropServices;
using NoaLog.Core.Models;

namespace NoaLog.Core.Hotkey;

/// <summary>
/// Win32 RegisterHotKey を使用したグローバルホットキー管理。
/// 専用スレッドでメッセージループを実行し、WM_HOTKEY を受信する。
/// </summary>
public sealed class WindowsHotkeyManager : IHotkeyManager
{
    #region Win32 Constants

    private const int WM_HOTKEY = 0x0312;
    private const int WM_QUIT = 0x0012;
    private const uint MOD_ALT = 0x0001;
    private const uint MOD_CONTROL = 0x0002;
    private const uint MOD_SHIFT = 0x0004;
    private const uint MOD_WIN = 0x0008;

    private const uint WS_EX_NOACTIVATE = 0x08000000;
    private const int HWND_MESSAGE = -3;

    #endregion

    #region P/Invoke

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool RegisterHotKey(IntPtr hWnd, int id, uint fsModifiers, uint vk);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool UnregisterHotKey(IntPtr hWnd, int id);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern IntPtr CreateWindowEx(
        uint dwExStyle, string lpClassName, string lpWindowName,
        uint dwStyle, int x, int y, int nWidth, int nHeight,
        IntPtr hWndParent, IntPtr hMenu, IntPtr hInstance, IntPtr lpParam);

    [DllImport("user32.dll")]
    private static extern IntPtr DefWindowProc(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam);

    [DllImport("user32.dll")]
    private static extern bool PeekMessage(out MSG lpMsg, IntPtr hWnd, uint wMsgFilterMin, uint wMsgFilterMax, uint wRemoveMsg);

    [DllImport("user32.dll")]
    private static extern bool TranslateMessage(ref MSG lpMsg);

    [DllImport("user32.dll")]
    private static extern IntPtr DispatchMessage(ref MSG lpMsg);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool DestroyWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    private static extern bool PostMessage(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam);

    [DllImport("kernel32.dll")]
    private static extern IntPtr GetModuleHandle(string? lpModuleName);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern ushort RegisterClass(ref WNDCLASS lpWndClass);

    private delegate IntPtr WndProcDelegate(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam);

    [StructLayout(LayoutKind.Sequential)]
    private struct MSG
    {
        public IntPtr hwnd;
        public uint message;
        public IntPtr wParam;
        public IntPtr lParam;
        public uint time;
        public POINT pt;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct POINT
    {
        public int x;
        public int y;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct WNDCLASS
    {
        public uint style;
        public WndProcDelegate lpfnWndProc;
        public int cbClsExtra;
        public int cbWndExtra;
        public IntPtr hInstance;
        public IntPtr hIcon;
        public IntPtr hCursor;
        public IntPtr hbrBackground;
        public string? lpszMenuName;
        public string lpszClassName;
    }

    #endregion

    #region Virtual Key Code Mapping

    private static readonly Dictionary<string, uint> VirtualKeyCodes = new(StringComparer.OrdinalIgnoreCase)
    {
        // Letters
        ["A"] = 0x41, ["B"] = 0x42, ["C"] = 0x43, ["D"] = 0x44,
        ["E"] = 0x45, ["F"] = 0x46, ["G"] = 0x47, ["H"] = 0x48,
        ["I"] = 0x49, ["J"] = 0x4A, ["K"] = 0x4B, ["L"] = 0x4C,
        ["M"] = 0x4D, ["N"] = 0x4E, ["O"] = 0x4F, ["P"] = 0x50,
        ["Q"] = 0x51, ["R"] = 0x52, ["S"] = 0x53, ["T"] = 0x54,
        ["U"] = 0x55, ["V"] = 0x56, ["W"] = 0x57, ["X"] = 0x58,
        ["Y"] = 0x59, ["Z"] = 0x5A,

        // Numbers
        ["0"] = 0x30, ["1"] = 0x31, ["2"] = 0x32, ["3"] = 0x33,
        ["4"] = 0x34, ["5"] = 0x35, ["6"] = 0x36, ["7"] = 0x37,
        ["8"] = 0x38, ["9"] = 0x39,

        // Function keys
        ["F1"] = 0x70, ["F2"] = 0x71, ["F3"] = 0x72, ["F4"] = 0x73,
        ["F5"] = 0x74, ["F6"] = 0x75, ["F7"] = 0x76, ["F8"] = 0x77,
        ["F9"] = 0x78, ["F10"] = 0x79, ["F11"] = 0x7A, ["F12"] = 0x7B,

        // Special keys
        ["Space"] = 0x20, ["Enter"] = 0x0D, ["Tab"] = 0x09,
        ["Escape"] = 0x1B, ["Backspace"] = 0x08, ["Delete"] = 0x2E,
        ["Insert"] = 0x2D, ["Home"] = 0x24, ["End"] = 0x23,
        ["PageUp"] = 0x21, ["PageDown"] = 0x22,
        ["Up"] = 0x26, ["Down"] = 0x28, ["Left"] = 0x25, ["Right"] = 0x27,
        ["PrintScreen"] = 0x2C, ["Pause"] = 0x13, ["NumLock"] = 0x90,
        ["ScrollLock"] = 0x91, ["CapsLock"] = 0x14,
    };

    private static readonly Dictionary<string, uint> ModifierMap = new(StringComparer.OrdinalIgnoreCase)
    {
        ["Ctrl"] = MOD_CONTROL,
        ["Control"] = MOD_CONTROL,
        ["Alt"] = MOD_ALT,
        ["Shift"] = MOD_SHIFT,
        ["Meta"] = MOD_WIN,
        ["Win"] = MOD_WIN,
    };

    #endregion

    private readonly object _lock = new();
    private readonly Dictionary<int, string> _registeredHotkeys = new();
    private readonly Dictionary<string, int> _idToAtom = new();
    private int _nextAtomId = 1;

    private IntPtr _hwnd;
    private Thread? _messageLoopThread;
    private volatile bool _disposed;
    private readonly ManualResetEventSlim _windowCreated = new(false);

    // WndProc デリゲートを GC から保護するためフィールドに保持
    private WndProcDelegate? _wndProc;

    public event EventHandler<HotkeyEventArgs>? HotkeyPressed;

    public WindowsHotkeyManager()
    {
        _messageLoopThread = new Thread(MessageLoop)
        {
            Name = "HotkeyMessageLoop",
            IsBackground = true,
        };
        _messageLoopThread.Start();
        _windowCreated.Wait(TimeSpan.FromSeconds(5));
    }

    private void MessageLoop()
    {
        var hInstance = GetModuleHandle(null);
        _wndProc = WndProc;

        var className = $"NoaLogHotkey_{Guid.NewGuid():N}";
        var wc = new WNDCLASS
        {
            lpfnWndProc = _wndProc,
            hInstance = hInstance,
            lpszClassName = className,
        };

        RegisterClass(ref wc);

        _hwnd = CreateWindowEx(
            WS_EX_NOACTIVATE,
            className,
            "NoaLog Hotkey Window",
            0, 0, 0, 0, 0,
            (IntPtr)HWND_MESSAGE,
            IntPtr.Zero,
            hInstance,
            IntPtr.Zero);

        _windowCreated.Set();

        const uint PM_REMOVE = 0x0001;
        while (!_disposed)
        {
            if (PeekMessage(out var msg, IntPtr.Zero, 0, 0, PM_REMOVE))
            {
                if (msg.message == WM_QUIT)
                    break;

                TranslateMessage(ref msg);
                DispatchMessage(ref msg);
            }
            else
            {
                Thread.Sleep(10);
            }
        }

        // クリーンアップ
        if (_hwnd != IntPtr.Zero)
        {
            DestroyWindow(_hwnd);
            _hwnd = IntPtr.Zero;
        }
    }

    private IntPtr WndProc(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam)
    {
        if (msg == WM_HOTKEY)
        {
            var atomId = (int)wParam;
            string? id = null;

            lock (_lock)
            {
                _registeredHotkeys.TryGetValue(atomId, out id);
            }

            if (id is not null)
            {
                HotkeyPressed?.Invoke(this, new HotkeyEventArgs(id));
            }

            return IntPtr.Zero;
        }

        return DefWindowProc(hWnd, msg, wParam, lParam);
    }

    public bool Register(string id, Models.Hotkey hotkey)
    {
        if (_disposed || _hwnd == IntPtr.Zero)
            return false;

        if (!TryParseHotkey(hotkey, out var modifiers, out var vk))
            return false;

        lock (_lock)
        {
            // 既に同じ id で登録済みなら先に解除
            if (_idToAtom.ContainsKey(id))
                UnregisterCore(id);

            var atomId = _nextAtomId++;

            if (!RegisterHotKey(_hwnd, atomId, modifiers, vk))
                return false;

            _registeredHotkeys[atomId] = id;
            _idToAtom[id] = atomId;
            return true;
        }
    }

    public bool Unregister(string id)
    {
        if (_disposed)
            return false;

        lock (_lock)
        {
            return UnregisterCore(id);
        }
    }

    public void UnregisterAll()
    {
        if (_disposed)
            return;

        lock (_lock)
        {
            foreach (var atomId in _registeredHotkeys.Keys.ToList())
            {
                UnregisterHotKey(_hwnd, atomId);
            }

            _registeredHotkeys.Clear();
            _idToAtom.Clear();
        }
    }

    /// <summary>ロック取得済みの状態で呼び出すこと。</summary>
    private bool UnregisterCore(string id)
    {
        if (!_idToAtom.TryGetValue(id, out var atomId))
            return false;

        var result = UnregisterHotKey(_hwnd, atomId);
        _registeredHotkeys.Remove(atomId);
        _idToAtom.Remove(id);
        return result;
    }

    private static bool TryParseHotkey(Models.Hotkey hotkey, out uint modifiers, out uint vk)
    {
        modifiers = 0;
        vk = 0;

        foreach (var key in hotkey.Keys)
        {
            if (ModifierMap.TryGetValue(key, out var mod))
            {
                modifiers |= mod;
            }
            else if (VirtualKeyCodes.TryGetValue(key, out var keyCode))
            {
                vk = keyCode;
            }
            else
            {
                // 不明なキー名
                return false;
            }
        }

        // 仮想キーコードが見つからなかった場合は無効
        return vk != 0;
    }

    public void Dispose()
    {
        if (_disposed)
            return;

        _disposed = true;

        UnregisterAll();

        if (_hwnd != IntPtr.Zero)
        {
            PostMessage(_hwnd, WM_QUIT, IntPtr.Zero, IntPtr.Zero);
        }

        _messageLoopThread?.Join(TimeSpan.FromSeconds(3));
        _messageLoopThread = null;

        _windowCreated.Dispose();
    }
}
#endif
