#if WINDOWS
using System.Runtime.InteropServices;
using NoaLog.Core.Models;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;

namespace NoaLog.Core.Capture;

/// <summary>Win32 BitBlt を使用した Windows 向けスクリーンキャプチャ実装。</summary>
public class WindowsScreenCapture : IScreenCapture
{
    #region Win32 Constants

    private const int SRCCOPY = 0x00CC0020;
    private const int SM_CXSCREEN = 0;
    private const int SM_CYSCREEN = 1;
    private const int BI_RGB = 0;
    private const int DIB_RGB_COLORS = 0;

    #endregion

    #region Win32 Structs

    [StructLayout(LayoutKind.Sequential)]
    private struct BITMAPINFOHEADER
    {
        public int biSize;
        public int biWidth;
        public int biHeight;
        public short biPlanes;
        public short biBitCount;
        public int biCompression;
        public int biSizeImage;
        public int biXPelsPerMeter;
        public int biYPelsPerMeter;
        public int biClrUsed;
        public int biClrImportant;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct BITMAPINFO
    {
        public BITMAPINFOHEADER bmiHeader;
    }

    #endregion

    #region P/Invoke - user32.dll

    [DllImport("user32.dll")]
    private static extern IntPtr GetDesktopWindow();

    [DllImport("user32.dll")]
    private static extern IntPtr GetDC(IntPtr hWnd);

    [DllImport("user32.dll")]
    private static extern int ReleaseDC(IntPtr hWnd, IntPtr hDC);

    [DllImport("user32.dll")]
    private static extern int GetSystemMetrics(int nIndex);

    #endregion

    #region P/Invoke - gdi32.dll

    [DllImport("gdi32.dll")]
    private static extern IntPtr CreateCompatibleDC(IntPtr hdc);

    [DllImport("gdi32.dll")]
    private static extern IntPtr CreateCompatibleBitmap(IntPtr hdc, int nWidth, int nHeight);

    [DllImport("gdi32.dll")]
    private static extern IntPtr SelectObject(IntPtr hdc, IntPtr hgdiobj);

    [DllImport("gdi32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool BitBlt(
        IntPtr hdcDest, int xDest, int yDest, int wDest, int hDest,
        IntPtr hdcSrc, int xSrc, int ySrc, int rop);

    [DllImport("gdi32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool DeleteObject(IntPtr hObject);

    [DllImport("gdi32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool DeleteDC(IntPtr hdc);

    [DllImport("gdi32.dll")]
    private static extern int GetDIBits(
        IntPtr hdc, IntPtr hbmp, int uStartScan, int cScanLines,
        byte[] lpvBits, ref BITMAPINFO lpbi, int uUsage);

    #endregion

    public bool IsAvailable => RuntimeInformation.IsOSPlatform(OSPlatform.Windows);

    public Task<byte[]> CaptureRegionAsync(Rect rect, CancellationToken cancellationToken = default)
    {
        return Task.Run(() => CaptureRegion(rect), cancellationToken);
    }

    public Task<byte[]> CaptureFullScreenAsync(CancellationToken cancellationToken = default)
    {
        return Task.Run(() =>
        {
            int width = GetSystemMetrics(SM_CXSCREEN);
            int height = GetSystemMetrics(SM_CYSCREEN);
            return CaptureRegion(new Rect(0, 0, width, height));
        }, cancellationToken);
    }

    private static byte[] CaptureRegion(Rect rect)
    {
        IntPtr hDesktopWnd = GetDesktopWindow();
        IntPtr hDesktopDC = GetDC(hDesktopWnd);
        IntPtr hMemoryDC = CreateCompatibleDC(hDesktopDC);
        IntPtr hBitmap = CreateCompatibleBitmap(hDesktopDC, rect.Width, rect.Height);
        IntPtr hOldBitmap = SelectObject(hMemoryDC, hBitmap);

        try
        {
            bool success = BitBlt(
                hMemoryDC, 0, 0, rect.Width, rect.Height,
                hDesktopDC, rect.X, rect.Y, SRCCOPY);

            if (!success)
            {
                throw new InvalidOperationException("BitBlt failed to capture the screen region.");
            }

            byte[] pixelData = GetBitmapPixelData(hMemoryDC, hBitmap, rect.Width, rect.Height);
            return ConvertToPng(pixelData, rect.Width, rect.Height);
        }
        finally
        {
            SelectObject(hMemoryDC, hOldBitmap);
            DeleteObject(hBitmap);
            DeleteDC(hMemoryDC);
            ReleaseDC(hDesktopWnd, hDesktopDC);
        }
    }

    private static byte[] GetBitmapPixelData(IntPtr hdc, IntPtr hBitmap, int width, int height)
    {
        var bmi = new BITMAPINFO
        {
            bmiHeader = new BITMAPINFOHEADER
            {
                biSize = Marshal.SizeOf<BITMAPINFOHEADER>(),
                biWidth = width,
                biHeight = -height, // top-down DIB (negative = top-down)
                biPlanes = 1,
                biBitCount = 32,
                biCompression = BI_RGB,
                biSizeImage = 0,
                biXPelsPerMeter = 0,
                biYPelsPerMeter = 0,
                biClrUsed = 0,
                biClrImportant = 0,
            }
        };

        int stride = width * 4;
        byte[] pixelData = new byte[stride * height];

        int result = GetDIBits(hdc, hBitmap, 0, height, pixelData, ref bmi, DIB_RGB_COLORS);

        if (result == 0)
        {
            throw new InvalidOperationException("GetDIBits failed to retrieve pixel data.");
        }

        return pixelData;
    }

    private static byte[] ConvertToPng(byte[] pixelData, int width, int height)
    {
        // pixelData is BGRA32 from GetDIBits (32bpp with BI_RGB, top-down)
        using var image = Image.LoadPixelData<Bgra32>(pixelData, width, height);
        using var stream = new MemoryStream();
        image.SaveAsPng(stream);
        return stream.ToArray();
    }
}
#endif
