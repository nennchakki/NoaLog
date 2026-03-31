using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;
using SixLabors.ImageSharp.Processing;

namespace NoaLog.Core.Ocr;

public static class OcrPreprocessor
{
    private const int ImageSize = 224;
    private const int ChannelCount = 3;
    private const int PixelsPerChannel = ImageSize * ImageSize;
    private const int TensorLength = ChannelCount * PixelsPerChannel;

    private static readonly float[] MeanRgb = { 0.485f, 0.456f, 0.406f };
    private static readonly float[] StdRgb = { 0.229f, 0.224f, 0.225f };

    /// <summary>
    /// Preprocess image bytes into a float tensor for the DeiT encoder.
    /// Returns float[1 * 3 * 224 * 224] in NCHW format.
    /// </summary>
    public static float[] Process(byte[] imageData)
    {
        using var image = Image.Load<Rgb24>(imageData);

        // 暗い背景（ゲームUI等）を検出して反転 → 白背景黒文字にする
        if (IsDarkBackground(image))
        {
            image.Mutate(ctx => ctx.Invert());
        }

        // Calculate scale to fit within 224x224 while maintaining aspect ratio
        float scale = Math.Min(
            (float)ImageSize / image.Width,
            (float)ImageSize / image.Height);

        int resizedWidth = (int)(image.Width * scale);
        int resizedHeight = (int)(image.Height * scale);

        // Resize with Lanczos3 resampler
        image.Mutate(ctx => ctx.Resize(new ResizeOptions
        {
            Size = new Size(resizedWidth, resizedHeight),
            Sampler = KnownResamplers.Lanczos3,
            Mode = ResizeMode.Max,
        }));

        // Create 224x224 white canvas and center the resized image on it
        using var canvas = new Image<Rgb24>(ImageSize, ImageSize, new Rgb24(255, 255, 255));

        int offsetX = (ImageSize - image.Width) / 2;
        int offsetY = (ImageSize - image.Height) / 2;

        canvas.Mutate(ctx => ctx.DrawImage(image, new Point(offsetX, offsetY), 1f));

        // Normalize and output in NCHW format: [batch][channel][height][width]
        var tensor = new float[TensorLength];

        canvas.ProcessPixelRows(accessor =>
        {
            for (int y = 0; y < ImageSize; y++)
            {
                Span<Rgb24> row = accessor.GetRowSpan(y);

                for (int x = 0; x < ImageSize; x++)
                {
                    Rgb24 pixel = row[x];

                    // channel 0 = R, channel 1 = G, channel 2 = B
                    tensor[0 * PixelsPerChannel + y * ImageSize + x] =
                        (pixel.R / 255f - MeanRgb[0]) / StdRgb[0];
                    tensor[1 * PixelsPerChannel + y * ImageSize + x] =
                        (pixel.G / 255f - MeanRgb[1]) / StdRgb[1];
                    tensor[2 * PixelsPerChannel + y * ImageSize + x] =
                        (pixel.B / 255f - MeanRgb[2]) / StdRgb[2];
                }
            }
        });

        return tensor;
    }

    /// <summary>
    /// 画像の平均輝度を計算し、暗い背景かどうかを判定する。
    /// 平均輝度が128未満なら暗い背景と判定。
    /// </summary>
    private static bool IsDarkBackground(Image<Rgb24> image)
    {
        long totalBrightness = 0;
        int pixelCount = 0;

        // サンプリング: 全ピクセルは重いので、4ピクセルおきにチェック
        image.ProcessPixelRows(accessor =>
        {
            for (int y = 0; y < accessor.Height; y += 4)
            {
                var row = accessor.GetRowSpan(y);
                for (int x = 0; x < accessor.Width; x += 4)
                {
                    var p = row[x];
                    totalBrightness += (p.R + p.G + p.B) / 3;
                    pixelCount++;
                }
            }
        });

        if (pixelCount == 0) return false;
        return totalBrightness / pixelCount < 128;
    }
}
