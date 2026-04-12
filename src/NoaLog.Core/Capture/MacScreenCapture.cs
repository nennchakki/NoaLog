#if !WINDOWS
using System.Diagnostics;
using NoaLog.Core.Models;

namespace NoaLog.Core.Capture;

/// <summary>
/// macOS用スクリーンキャプチャ。screencaptureコマンドを使用。
/// </summary>
public class MacScreenCapture : IScreenCapture
{
    public bool IsAvailable => OperatingSystem.IsMacOS();

    public async Task<byte[]> CaptureRegionAsync(Rect rect, CancellationToken cancellationToken = default)
    {
        var tempPath = Path.Combine(Path.GetTempPath(), $"noalog_capture_{Guid.NewGuid():N}.png");
        try
        {
            // screencapture -R x,y,w,h -x (no sound) output.png
            var process = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = "screencapture",
                    Arguments = $"-R{rect.X},{rect.Y},{rect.Width},{rect.Height} -x \"{tempPath}\"",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true,
                }
            };

            process.Start();
            await process.WaitForExitAsync(cancellationToken);

            if (process.ExitCode != 0 || !File.Exists(tempPath))
                return Array.Empty<byte>();

            return await File.ReadAllBytesAsync(tempPath, cancellationToken);
        }
        finally
        {
            try { File.Delete(tempPath); } catch { }
        }
    }

    public async Task<byte[]> CaptureFullScreenAsync(CancellationToken cancellationToken = default)
    {
        var tempPath = Path.Combine(Path.GetTempPath(), $"noalog_capture_{Guid.NewGuid():N}.png");
        try
        {
            var process = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = "screencapture",
                    Arguments = $"-x \"{tempPath}\"",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true,
                }
            };

            process.Start();
            await process.WaitForExitAsync(cancellationToken);

            if (process.ExitCode != 0 || !File.Exists(tempPath))
                return Array.Empty<byte>();

            return await File.ReadAllBytesAsync(tempPath, cancellationToken);
        }
        finally
        {
            try { File.Delete(tempPath); } catch { }
        }
    }
}

#endif
