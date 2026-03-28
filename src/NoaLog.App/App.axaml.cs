using System;
using System.IO;
using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;
using NoaLog.App.Views;
using NoaLog.App.ViewModels;
using NoaLog.Core.Storage;

namespace NoaLog.App;

public partial class App : Application
{
    public static SqliteStorage? Storage { get; private set; }

    public override void Initialize()
    {
        AvaloniaXamlLoader.Load(this);
    }

    public override void OnFrameworkInitializationCompleted()
    {
        // SQLiteストレージ初期化
        var appDataDir = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
        var noalogDir = Path.Combine(appDataDir, "NoaLog");
        Directory.CreateDirectory(noalogDir);
        var dbPath = Path.Combine(noalogDir, "noalog.db");

        Storage = new SqliteStorage(dbPath);
        Storage.Initialize();

        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            desktop.MainWindow = new MainWindow(Storage)
            {
                DataContext = new MainViewModel()
            };
        }
        base.OnFrameworkInitializationCompleted();
    }
}
