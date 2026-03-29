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
using NoaLog.Core.Telemetry;
#if PRO
using NoaLog.Core.Ollama;
#endif

namespace NoaLog.App;

public partial class App : Application
{
    // --- 共通サービス ---
    public static SqliteStorage? Storage { get; private set; }
    public static DictManager? DictManager { get; private set; }
    public static DictProcessor? DictProcessor { get; private set; }
    public static IOcrEngine? OcrEngine { get; private set; }
    public static CaptureQueue? CaptureQueue { get; private set; }
    public static CaptureWorker? CaptureWorker { get; private set; }
    public static IScreenCapture? ScreenCapture { get; private set; }
    public static IHotkeyManager? HotkeyManager { get; private set; }
    public static CorrectionLogger? CorrectionLogger { get; private set; }
    public static AnonymousSender? AnonymousSender { get; private set; }

#if PRO
    public static OllamaManager? OllamaManager { get; private set; }
#endif

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

        // 4. テレメトリ
        CorrectionLogger = new CorrectionLogger(Storage);
        AnonymousSender = new AnonymousSender(Storage);

        // 5. プラットフォーム依存サービス
#if WINDOWS
        ScreenCapture = new WindowsScreenCapture();
        HotkeyManager = new WindowsHotkeyManager();
#else
        ScreenCapture = new StubScreenCapture();
        HotkeyManager = new StubHotkeyManager();
#endif

        // 6. OCRエンジン
        OcrEngine = CreateOcrEngine(noalogDir);

        // 7. キャプチャパイプライン
        CaptureQueue = new CaptureQueue();
        CaptureWorker = new CaptureWorker(CaptureQueue, ScreenCapture, OcrEngine, Storage, DictProcessor);
        CaptureWorker.Start();

        // 8. メインウィンドウ
        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            desktop.MainWindow = new MainWindow(Storage, CorrectionLogger)
            {
                DataContext = new MainViewModel()
            };

            desktop.ShutdownRequested += OnShutdownRequested;
        }

        base.OnFrameworkInitializationCompleted();
    }

    private static IOcrEngine CreateOcrEngine(string noalogDir)
    {
        var modelsDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "data", "models");

#if PRO
        var engineSetting = Storage?.GetSetting("ocr.engine") ?? "manga-ocr";
        if (engineSetting == "Qwen3-VL")
        {
            OllamaManager = new OllamaManager();
            _ = InitializeProOcrAsync();
            return new QwenVlClient();
        }
#endif

        var encoder = Path.Combine(modelsDir, "manga_ocr_encoder.onnx");
        var decoder = Path.Combine(modelsDir, "manga_ocr_decoder.onnx");
        var vocab = Path.Combine(modelsDir, "tokenizer", "vocab.txt");
        return new MangaOcrOnnx(encoder, decoder, vocab);
    }

#if PRO
    private static async Task InitializeProOcrAsync()
    {
        try
        {
            await OllamaManager!.StartServerAsync(CancellationToken.None);
            if (!await OllamaManager.IsModelAvailableAsync("qwen3-vl:2b", CancellationToken.None))
            {
                await OllamaManager.PullModelAsync("qwen3-vl:2b", null, CancellationToken.None);
            }
            await OcrEngine!.InitializeAsync(CancellationToken.None);
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Pro OCR init failed: {ex.Message}");
        }
    }

    /// <summary>
    /// ランタイムでOCRエンジンを切り替える（設定画面から呼ばれる）。
    /// </summary>
    public static async Task SwitchOcrEngineAsync(string engineName)
    {
        if (CaptureWorker == null || Storage == null) return;

        // 現在のワーカーを停止
        CaptureQueue?.Complete();

        // 旧エンジンをシャットダウン
        if (OcrEngine != null)
            await OcrEngine.ShutdownAsync();

        // 新エンジン作成
        var appDataDir = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
        var noalogDir = Path.Combine(appDataDir, "NoaLog");
        OcrEngine = CreateOcrEngine(noalogDir);

        // 新パイプライン再構築
        CaptureQueue = new CaptureQueue();
        CaptureWorker = new CaptureWorker(CaptureQueue, ScreenCapture!, OcrEngine, Storage, DictProcessor);
        CaptureWorker.Start();
    }
#endif

    private void OnShutdownRequested(object? sender, ShutdownRequestedEventArgs e)
    {
        CaptureQueue?.Complete();

        if (OcrEngine is IDisposable disposableEngine)
            disposableEngine.Dispose();

        if (HotkeyManager is IDisposable disposableHotkey)
            disposableHotkey.Dispose();

#if PRO
        OllamaManager?.Dispose();
#endif
    }
}
