using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;
using System.Threading.Tasks;
using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;
using NoaLog.App.Views;
using NoaLog.App.ViewModels;
using NoaLog.Core.Capture;
using NoaLog.Core.Dict;
using NoaLog.Core.Hotkey;
using NoaLog.Core.Ocr;
using NoaLog.Core.Pipeline;
using NoaLog.Core.PostProcess;
using NoaLog.Core.Storage;

namespace NoaLog.App;

public partial class App : Application
{
    // --- 共通サービス ---
    public static SqliteStorage? Storage { get; private set; }
    public static DictManager? DictManager { get; private set; }
    public static DictProcessor? DictProcessor { get; private set; }
    public static IOcrEngine? OcrEngine { get; set; }
    public static CaptureQueue? CaptureQueue { get; private set; }
    public static CaptureWorker? CaptureWorker { get; private set; }
    public static IScreenCapture? ScreenCapture { get; private set; }
    public static IHotkeyManager? HotkeyManager { get; private set; }

    /// <summary>OCRエンジンが切り替わった時に発火するイベント</summary>
    public static event EventHandler? OcrEngineChanged;

    public static void NotifyOcrEngineChanged() => OcrEngineChanged?.Invoke(null, EventArgs.Empty);

    public override void Initialize()
    {
        AvaloniaXamlLoader.Load(this);
    }

    public override void OnFrameworkInitializationCompleted()
    {
        // 1. アプリデータディレクトリ
        var appDataDir = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
        var noalogDir = Path.Combine(appDataDir, "NoaLog");
        Directory.CreateDirectory(noalogDir);

        // 2. SQLiteストレージ
        var dbPath = Path.Combine(noalogDir, "noalog.db");
        Storage = new SqliteStorage(dbPath);
        Storage.Initialize();

        // 3. 辞書管理 + 後処理パイプライン
        var builtinDictDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "data", "dictionaries", "_builtin");
        DictManager = new DictManager(builtinDictDir, Storage);
        DictManager.LoadAll();
        DictProcessor = new DictProcessor(DictManager);

        // 4. プラットフォーム依存サービス
        if (OperatingSystem.IsWindows())
        {
#if WINDOWS
            ScreenCapture = new WindowsScreenCapture();
            HotkeyManager = new WindowsHotkeyManager();
#endif
        }
        else if (OperatingSystem.IsMacOS())
        {
#if !WINDOWS
            RequestAccessibilityPermission();
            ScreenCapture = new MacScreenCapture();
            HotkeyManager = new MacHotkeyManager();
#endif
        }

        // フォールバック
        ScreenCapture ??= new StubScreenCapture();
        HotkeyManager ??= new StubHotkeyManager();

        // 5. OCRエンジン（Gemini API）
        var savedGeminiModel = Storage.GetSetting("gemini.model") ?? "gemini-3.1-flash-lite";
        OcrEngine = new GeminiOcrClient(modelId: savedGeminiModel);
        _ = InitializeOcrAsync();

        // 6. キャプチャパイプライン
        CaptureQueue = new CaptureQueue();
        CaptureWorker = new CaptureWorker(CaptureQueue, ScreenCapture, OcrEngine, Storage, DictProcessor);
        CaptureWorker.Start();

        // 7. メインウィンドウ
        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            desktop.MainWindow = new MainWindow(Storage)
            {
                DataContext = new MainViewModel()
            };

            desktop.ShutdownRequested += OnShutdownRequested;
        }

        base.OnFrameworkInitializationCompleted();
    }

    private static async Task InitializeOcrAsync()
    {
        try
        {
            await OcrEngine!.InitializeAsync(CancellationToken.None);
            OcrEngineChanged?.Invoke(null, EventArgs.Empty);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"OCR init failed: {ex.Message}");
        }
    }

#if !WINDOWS
    [System.Runtime.InteropServices.DllImport("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")]
    private static extern bool AXIsProcessTrustedWithOptions(IntPtr options);

    [System.Runtime.InteropServices.DllImport("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")]
    private static extern IntPtr CFDictionaryCreate(IntPtr allocator, IntPtr[] keys, IntPtr[] values, long numValues, IntPtr keyCallBacks, IntPtr valueCallBacks);

    [System.Runtime.InteropServices.DllImport("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")]
    private static extern IntPtr CFStringCreateWithCString(IntPtr allocator, string str, int encoding);

    [System.Runtime.InteropServices.DllImport("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")]
    private static extern void CFRelease(IntPtr obj);

    private static readonly IntPtr kCFBooleanTrue = new(0x01);

    private static void RequestAccessibilityPermission()
    {
        if (!OperatingSystem.IsMacOS()) return;

        try
        {
            var key = CFStringCreateWithCString(IntPtr.Zero, "AXTrustedCheckOptionPrompt", 0x08000100);
            var keys = new[] { key };
            var values = new[] { kCFBooleanTrue };
            var options = CFDictionaryCreate(IntPtr.Zero, keys, values, 1, IntPtr.Zero, IntPtr.Zero);

            bool trusted = AXIsProcessTrustedWithOptions(options);
            Console.Error.WriteLine($"[macOS] Accessibility permission: {(trusted ? "granted" : "not granted — dialog shown")}");

            CFRelease(options);
            CFRelease(key);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"[macOS] Accessibility check failed: {ex.Message}");
        }
    }
#endif

    private void OnShutdownRequested(object? sender, ShutdownRequestedEventArgs e)
    {
        // 即座に強制終了 — バックグラウンドタスクの完了を待たない
        // Wait/awaitするとデッドロックの原因になる
        Environment.Exit(0);
    }
}
