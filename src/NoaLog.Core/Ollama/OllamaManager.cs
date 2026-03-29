using System.Diagnostics;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;

namespace NoaLog.Core.Ollama;

/// <summary>
/// Ollamaサーバーのプロセス管理。
/// サーバー起動、モデルpull、シャットダウンを提供。
/// </summary>
public class OllamaManager : IDisposable
{
    private readonly string _ollamaPath;
    private readonly HttpClient _httpClient;
    private Process? _serverProcess;
    private bool _weStartedServer;

    public OllamaState State { get; private set; } = OllamaState.NotStarted;

    public string BaseUrl => "http://localhost:11434";

    public OllamaManager(string ollamaPath = "ollama")
    {
        _ollamaPath = ollamaPath;
        _httpClient = new HttpClient { BaseAddress = new Uri("http://localhost:11434") };
    }

    public async Task StartServerAsync(CancellationToken cancellationToken = default)
    {
        State = OllamaState.Starting;

        // Check if server is already running
        try
        {
            using var response = await _httpClient.GetAsync("/", cancellationToken);
            if (response.IsSuccessStatusCode)
            {
                State = OllamaState.Running;
                _weStartedServer = false;
                return;
            }
        }
        catch (HttpRequestException)
        {
            // Server not running, we need to start it
        }

        // Start the server process
        var psi = new ProcessStartInfo
        {
            FileName = _ollamaPath,
            Arguments = "serve",
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };

        try
        {
            _serverProcess = Process.Start(psi);
            if (_serverProcess is null)
            {
                State = OllamaState.Error;
                throw new InvalidOperationException("Failed to start Ollama process.");
            }

            // Wait up to 10 seconds for the server to respond
            var timeout = TimeSpan.FromSeconds(10);
            var stopwatch = Stopwatch.StartNew();

            while (stopwatch.Elapsed < timeout)
            {
                cancellationToken.ThrowIfCancellationRequested();

                try
                {
                    using var response = await _httpClient.GetAsync("/", cancellationToken);
                    if (response.IsSuccessStatusCode)
                    {
                        State = OllamaState.Running;
                        _weStartedServer = true;
                        return;
                    }
                }
                catch (HttpRequestException)
                {
                    // Not ready yet
                }

                await Task.Delay(500, cancellationToken);
            }

            State = OllamaState.Error;
            throw new TimeoutException("Ollama server did not start within 10 seconds.");
        }
        catch (Exception) when (State != OllamaState.Error)
        {
            State = OllamaState.Error;
            throw;
        }
    }

    public async Task<bool> IsModelAvailableAsync(string model, CancellationToken cancellationToken = default)
    {
        using var response = await _httpClient.GetAsync("/api/tags", cancellationToken);
        response.EnsureSuccessStatusCode();

        using var doc = await JsonDocument.ParseAsync(
            await response.Content.ReadAsStreamAsync(cancellationToken), cancellationToken: cancellationToken);

        if (doc.RootElement.TryGetProperty("models", out var models))
        {
            foreach (var entry in models.EnumerateArray())
            {
                if (entry.TryGetProperty("name", out var name)
                    && name.GetString() is { } n
                    && n.StartsWith(model, StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }
        }

        return false;
    }

    public async Task PullModelAsync(
        string model,
        IProgress<PullProgress>? progress = null,
        CancellationToken cancellationToken = default)
    {
        State = OllamaState.Pulling;

        try
        {
            var requestBody = new { name = model, stream = true };
            using var request = new HttpRequestMessage(HttpMethod.Post, "/api/pull")
            {
                Content = new StringContent(
                    JsonSerializer.Serialize(requestBody), Encoding.UTF8, "application/json"),
            };

            using var response = await _httpClient.SendAsync(
                request, HttpCompletionOption.ResponseHeadersRead, cancellationToken);
            response.EnsureSuccessStatusCode();

            using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
            using var reader = new StreamReader(stream);

            while (await reader.ReadLineAsync(cancellationToken) is { } line)
            {
                cancellationToken.ThrowIfCancellationRequested();

                if (string.IsNullOrWhiteSpace(line))
                    continue;

                using var doc = JsonDocument.Parse(line);
                var root = doc.RootElement;

                var status = root.TryGetProperty("status", out var s) ? s.GetString() ?? "" : "";
                long completed = root.TryGetProperty("completed", out var c) ? c.GetInt64() : 0;
                long total = root.TryGetProperty("total", out var t) ? t.GetInt64() : 0;

                progress?.Report(new PullProgress(status, completed, total));
            }

            State = OllamaState.Running;
        }
        catch
        {
            State = OllamaState.Error;
            throw;
        }
    }

    public async Task ShutdownAsync()
    {
        if (_weStartedServer && _serverProcess is not null && !_serverProcess.HasExited)
        {
            try
            {
                _serverProcess.Kill(entireProcessTree: true);
                await _serverProcess.WaitForExitAsync(
                    new CancellationTokenSource(TimeSpan.FromSeconds(3)).Token);
            }
            catch (OperationCanceledException)
            {
                // Graceful wait timed out — process should already be killed
            }
            catch
            {
                // Best effort
            }
        }

        _serverProcess?.Dispose();
        _serverProcess = null;
        _weStartedServer = false;
        State = OllamaState.NotStarted;
    }

    public void Dispose()
    {
        ShutdownAsync().GetAwaiter().GetResult();
        _httpClient.Dispose();
        GC.SuppressFinalize(this);
    }
}
