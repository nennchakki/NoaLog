namespace NoaLog.Core.Models;

public record Rect(int X, int Y, int Width, int Height)
{
    public (int X, int Y, int Width, int Height) ToTuple() => (X, Y, Width, Height);
}
