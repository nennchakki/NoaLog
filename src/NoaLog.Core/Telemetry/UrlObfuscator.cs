using System.IO.Compression;
using System.Text;

namespace NoaLog.Core.Telemetry;

/// <summary>
/// Google FormsのURLをバイナリ内で難読化するためのユーティリティ。
/// Deflate圧縮 + Hex変換で可読性を下げる。
/// </summary>
public static class UrlObfuscator
{
    public static string Obfuscate(string url)
    {
        var bytes = Encoding.UTF8.GetBytes(url);
        using var ms = new MemoryStream();
        using (var deflate = new DeflateStream(ms, CompressionLevel.Optimal, leaveOpen: true))
        {
            deflate.Write(bytes, 0, bytes.Length);
        }
        return Convert.ToHexString(ms.ToArray());
    }

    public static string Deobfuscate(string hex)
    {
        var compressed = Convert.FromHexString(hex);
        using var ms = new MemoryStream(compressed);
        using var deflate = new DeflateStream(ms, CompressionMode.Decompress);
        using var result = new MemoryStream();
        deflate.CopyTo(result);
        return Encoding.UTF8.GetString(result.ToArray());
    }
}
