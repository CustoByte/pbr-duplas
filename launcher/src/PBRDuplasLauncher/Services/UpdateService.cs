using System.IO;
using System.IO.Compression;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text.Json;
using PBRDuplasLauncher.Models;

namespace PBRDuplasLauncher.Services;

public class UpdateService
{
    private static readonly HttpClient Http = new() { Timeout = TimeSpan.FromMinutes(10) };

    static UpdateService()
    {
        Http.DefaultRequestHeaders.UserAgent.ParseAdd("PBR-Duplas-Launcher/1.0");
    }

    /// <summary>
    /// Lê o manifesto de atualização publicado no repositório.
    /// Usa a API do GitHub (sem cache) e recorre ao raw.githubusercontent como reserva.
    /// </summary>
    public async Task<UpdateManifest?> GetManifestAsync(string owner, string repo,
        CancellationToken ct = default)
    {
        var manifest = await TryGetManifestFromApiAsync(owner, repo, ct);
        if (manifest is not null) return manifest;

        try
        {
            var url = $"https://raw.githubusercontent.com/{owner}/{repo}/main/launcher/update.json"
                      + $"?t={DateTime.UtcNow.Ticks}";
            var json = await Http.GetStringAsync(url, ct);
            return JsonSerializer.Deserialize<UpdateManifest>(json,
                new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
        }
        catch
        {
            return null;
        }
    }

    private async Task<UpdateManifest?> TryGetManifestFromApiAsync(string owner, string repo,
        CancellationToken ct)
    {
        var url = $"https://api.github.com/repos/{owner}/{repo}/contents/launcher/update.json?ref=main";
        try
        {
            using var request = new HttpRequestMessage(HttpMethod.Get, url);
            request.Headers.Accept.ParseAdd("application/vnd.github.raw");
            request.Headers.TryAddWithoutValidation("Cache-Control", "no-cache");
            using var response = await Http.SendAsync(request, ct);
            if (!response.IsSuccessStatusCode) return null;

            var json = await response.Content.ReadAsStringAsync(ct);
            return JsonSerializer.Deserialize<UpdateManifest>(json,
                new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
        }
        catch
        {
            return null;
        }
    }

    /// <summary>Lista todas as releases publicadas, da mais recente para a mais antiga.</summary>
    public async Task<List<ReleaseInfo>> GetReleasesAsync(string owner, string repo,
        CancellationToken ct = default)
    {
        var url = $"https://api.github.com/repos/{owner}/{repo}/releases?per_page=100";
        var result = new List<ReleaseInfo>();
        try
        {
            using var request = new HttpRequestMessage(HttpMethod.Get, url);
            request.Headers.Accept.ParseAdd("application/vnd.github+json");
            using var response = await Http.SendAsync(request, ct);
            if (!response.IsSuccessStatusCode) return result;

            using var doc = JsonDocument.Parse(await response.Content.ReadAsStringAsync(ct));
            foreach (var r in doc.RootElement.EnumerateArray())
            {
                var release = new ReleaseInfo
                {
                    TagName = r.TryGetProperty("tag_name", out var t) ? t.GetString() ?? "" : "",
                    Name = r.TryGetProperty("name", out var n) ? n.GetString() ?? "" : "",
                    Body = r.TryGetProperty("body", out var b) ? b.GetString() ?? "" : "",
                    PublishedAt = r.TryGetProperty("published_at", out var p) ? p.GetString() ?? "" : "",
                    Prerelease = r.TryGetProperty("prerelease", out var pre) && pre.GetBoolean()
                };
                if (r.TryGetProperty("assets", out var assets))
                {
                    foreach (var a in assets.EnumerateArray())
                    {
                        release.Assets.Add(new ReleaseAsset
                        {
                            Name = a.GetProperty("name").GetString() ?? "",
                            BrowserDownloadUrl = a.GetProperty("browser_download_url").GetString() ?? "",
                            Size = a.TryGetProperty("size", out var sz) ? sz.GetInt64() : 0
                        });
                    }
                }
                result.Add(release);
            }
        }
        catch { }
        return result;
    }

    public async Task<(string Path, string Sha256)> DownloadAsync(string url, string targetDir,
        string fileName, IProgress<double>? progress = null, CancellationToken ct = default)
    {
        Directory.CreateDirectory(targetDir);
        var targetPath = Path.Combine(targetDir, fileName);

        using var response = await Http.GetAsync(url, HttpCompletionOption.ResponseHeadersRead, ct);
        response.EnsureSuccessStatusCode();

        var total = response.Content.Headers.ContentLength ?? -1;
        await using var source = await response.Content.ReadAsStreamAsync(ct);
        await using var target = File.Create(targetPath);

        var buffer = new byte[81920];
        long downloaded = 0;
        int read;
        while ((read = await source.ReadAsync(buffer, ct)) > 0)
        {
            await target.WriteAsync(buffer.AsMemory(0, read), ct);
            downloaded += read;
            if (total > 0) progress?.Report((double)downloaded / total * 100);
        }

        return (targetPath, await ComputeSha256Async(targetPath, ct));
    }

    private static async Task<string> ComputeSha256Async(string path, CancellationToken ct)
    {
        await using var stream = File.OpenRead(path);
        var hash = await SHA256.HashDataAsync(stream, ct);
        return Convert.ToHexString(hash).ToLowerInvariant();
    }

    /// <summary>Extrai um zip de launcher para a pasta de instalação.</summary>
    public static void ExtractLauncher(string zipPath, string installDir)
    {
        Directory.CreateDirectory(installDir);
        using var archive = ZipFile.OpenRead(zipPath);
        foreach (var entry in archive.Entries)
        {
            if (string.IsNullOrEmpty(entry.Name)) continue;

            var destination = Path.GetFullPath(Path.Combine(installDir, entry.FullName));
            if (!destination.StartsWith(Path.GetFullPath(installDir), StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException($"Caminho inválido no pacote: {entry.FullName}");

            Directory.CreateDirectory(Path.GetDirectoryName(destination)!);
            entry.ExtractToFile(destination, overwrite: true);
        }
    }

    /// <summary>Compara versões no formato v1.2.3[-sufixo].</summary>
    public static bool IsUpdateAvailable(string currentVersion, string latestTag)
    {
        if (string.IsNullOrWhiteSpace(latestTag)) return false;
        return Normalize(latestTag) > Normalize(currentVersion);
    }

    public static string NormalizeTag(string v) => string.IsNullOrWhiteSpace(v) ? "" : v.Trim();

    private static Version Normalize(string v)
    {
        if (string.IsNullOrWhiteSpace(v)) return new Version(0, 0, 0);
        var core = v.TrimStart('v', 'V').Split('-')[0];
        var nums = core.Split('.').Select(p => int.TryParse(p, out var n) ? n : 0).ToList();
        while (nums.Count < 3) nums.Add(0);
        return new Version(nums[0], nums[1], nums[2]);
    }
}