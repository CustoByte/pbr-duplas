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

    /// <summary>Lê o manifesto de atualização publicado no repositório.</summary>
    public async Task<UpdateManifest?> GetManifestAsync(string owner, string repo,
        CancellationToken ct = default)
    {
        var url = $"https://raw.githubusercontent.com/{owner}/{repo}/main/launcher/update.json";
        try
        {
            var json = await Http.GetStringAsync(url, ct);
            return JsonSerializer.Deserialize<UpdateManifest>(json,
                new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
        }
        catch
        {
            return null;
        }
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

    private static Version Normalize(string v)
    {
        if (string.IsNullOrWhiteSpace(v)) return new Version(0, 0, 0);
        var core = v.TrimStart('v', 'V').Split('-')[0];
        var nums = core.Split('.').Select(p => int.TryParse(p, out var n) ? n : 0).ToList();
        while (nums.Count < 3) nums.Add(0);
        return new Version(nums[0], nums[1], nums[2]);
    }
}