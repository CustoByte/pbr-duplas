using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;
using PBRDuplasLauncher.Models;

namespace PBRDuplasLauncher.Services;

public class ApplyProgress
{
    public int Step { get; set; }
    public int TotalSteps { get; set; } = 6;
    public string Message { get; set; } = "";
    public double Percent { get; set; }
}

/// <summary>
/// Aplica o pacote de mods (aplicador-core.zip do release) sobre a ISO original,
/// produzindo uma ISO modificada que o Dolphin executa. Espelha expansion/Aplicar-Mod.ps1.
/// </summary>
public class ModApplyService
{
    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        PropertyNameCaseInsensitive = true
    };

    private readonly string _workRoot;
    private readonly string _toolPath;

    public ModApplyService(string? dolphinPath = null)
    {
        _workRoot = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "PBRDuplas", "work");
        _toolPath = ResolveDolphinTool(dolphinPath);
    }

    public string? DolphinToolPath => _toolPath;

    private static string ResolveDolphinTool(string? dolphinPath)
    {
        // 1. Ao lado do Dolphin informado
        if (!string.IsNullOrWhiteSpace(dolphinPath) && File.Exists(dolphinPath))
        {
            var dir = Path.GetDirectoryName(dolphinPath)!;
            var candidate = Path.Combine(dir, "DolphinTool.exe");
            if (File.Exists(candidate)) return candidate;
            var sub = Path.Combine(dir, "Tools", "DolphinTool.exe");
            if (File.Exists(sub)) return sub;
        }

        // 2. Pastas padrão do Dolphin
        var roots = new[]
        {
            Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
            Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Dolphin"),
        };
        foreach (var root in roots)
        {
            if (string.IsNullOrEmpty(root)) continue;
            foreach (var name in new[] { "Dolphin", "Dolphin Emulator" })
            {
                var dir = Path.Combine(root, name);
                if (!Directory.Exists(dir)) continue;
                foreach (var f in Directory.EnumerateFiles(dir, "DolphinTool.exe", SearchOption.AllDirectories))
                    return f;
            }
        }
        return "";
    }

    public static bool HasDolphinTool(string? dolphinPath) => new ModApplyService(dolphinPath).DolphinToolPath != "";

    public async Task ApplyModAsync(string originalImage, string packageZip, string outputImage,
        IProgress<ApplyProgress> progress, CancellationToken ct = default)
    {
        if (string.IsNullOrEmpty(_toolPath))
            throw new InvalidOperationException(
                "DolphinTool.exe não encontrado. Ele acompanha o Dolphin (pasta Tools).");

        Directory.CreateDirectory(_workRoot);
        var jobDir = Path.Combine(_workRoot, DateTime.Now.ToString("yyyyMMdd-HHmmss"));
        Directory.CreateDirectory(jobDir);

        try
        {
            // [1/6] Extrair pacote de mods
            progress.Report(new ApplyProgress { Step = 1, Message = "Extraindo pacote de mods...", Percent = 5 });
            var pkgDir = Path.Combine(jobDir, "pacote");
            ZipFile.ExtractToDirectory(packageZip, pkgDir, overwriteFiles: true);

            // Localizar manifesto e scripts (zip pode ter subpasta)
            var core = FindCore(pkgDir);
            var manifest = JsonSerializer.Deserialize<ModManifest>(
                await File.ReadAllTextAsync(core.ManifestPath, ct), JsonOpts)
                ?? throw new InvalidDataException("Manifesto do pacote inválido.");

            // [2/6] Extrair partição do jogo com DolphinTool
            progress.Report(new ApplyProgress { Step = 2, Message = "Extraindo dados do jogo (pode demorar)...", Percent = 15 });
            var extracted = Path.Combine(jobDir, "entrada");
            await RunToolAsync($"extract -i \"{originalImage}\" -o \"{extracted}\" --gameonly", ct);
            var partition = FindPartition(extracted)
                ?? throw new DirectoryNotFoundException("Partição de dados não encontrada na imagem.");

            // [3/6] Conferir hashes originais
            progress.Report(new ApplyProgress { Step = 3, Message = "Conferindo arquivos originais...", Percent = 35 });
            await VerifyOriginalAsync(partition, manifest, ct);

            // [4/6] Aplicar substituições (deltas binários ou arquivos completos)
            var total = manifest.Replacements.Count;
            for (int i = 0; i < total; i++)
            {
                ct.ThrowIfCancellationRequested();
                var entry = manifest.Replacements[i];
                progress.Report(new ApplyProgress
                {
                    Step = 4,
                    Message = $"Aplicando modificações ({i + 1}/{total})...",
                    Percent = 40 + 40.0 * i / total
                });
                var destination = Path.Combine(partition, entry.InstalledPath.Replace('/', Path.DirectorySeparatorChar));
                Directory.CreateDirectory(Path.GetDirectoryName(destination)!);
                var patchPath = Path.Combine(Path.GetDirectoryName(core.ManifestPath)!, entry.PackagePath);

                if (string.Equals(entry.Format, "pbr-delta-v1", StringComparison.OrdinalIgnoreCase))
                    ApplyPbrDelta(destination, patchPath, entry.Sha256);
                else
                    File.Copy(patchPath, destination, overwrite: true);

                if (await ComputeSha256Async(destination, ct) != entry.Sha256)
                    throw new InvalidDataException($"Checksum incorreto após aplicar: {entry.InstalledPath}");
            }

            // [5/6] Reconstruir imagem
            progress.Report(new ApplyProgress { Step = 5, Message = "Gerando nova imagem RVZ...", Percent = 85 });
            var outputDir = Path.GetDirectoryName(Path.GetFullPath(outputImage))!;
            Directory.CreateDirectory(outputDir);
            var built = Path.Combine(jobDir, "resultado.rvz");
            var mainDol = Path.Combine(partition, "sys", "main.dol");
            await RunToolAsync(
                $"convert -i \"{mainDol}\" -o \"{built}\" -f rvz -b 131072 -c zstd -l 5", ct);

            if (!File.Exists(built) || new FileInfo(built).Length == 0)
                throw new InvalidOperationException("O DolphinTool não produziu uma imagem válida.");

            // [6/6] Conferir o resultado e publicar
            progress.Report(new ApplyProgress { Step = 6, Message = "Conferindo a imagem gerada...", Percent = 95 });
            var roundtrip = Path.Combine(jobDir, "conferencia");
            await RunToolAsync($"extract -i \"{built}\" -o \"{roundtrip}\" --gameonly", ct);
            await VerifyRoundtripAsync(roundtrip, manifest, ct);

            if (File.Exists(outputImage)) File.Delete(outputImage);
            File.Move(built, outputImage);
            progress.Report(new ApplyProgress { Step = 6, Message = "Concluído.", Percent = 100 });
        }
        finally
        {
            TryDelete(jobDir);
        }
    }

    private (string ManifestPath, string ManifestName) FindCore(string pkgDir)
    {
        // procurar manifesto.json dentro do pacote
        var manifest = Directory.EnumerateFiles(pkgDir, "manifesto.json", SearchOption.AllDirectories).FirstOrDefault()
            ?? throw new FileNotFoundException("manifesto.json não encontrado no pacote de mods.");
        return (manifest, Path.GetFileName(manifest));
    }

    private async Task RunToolAsync(string arguments, CancellationToken ct)
    {
        var psi = new ProcessStartInfo
        {
            FileName = _toolPath,
            Arguments = arguments,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardError = true,
            RedirectStandardOutput = true,
        };
        using var process = Process.Start(psi)
            ?? throw new InvalidOperationException("Não foi possível iniciar o DolphinTool.");
        var errTask = process.StandardError.ReadToEndAsync(ct);
        var outTask = process.StandardOutput.ReadToEndAsync(ct);
        await process.WaitForExitAsync(ct);
        if (process.ExitCode != 0)
        {
            var err = (await errTask + " " + await outTask).Trim();
            throw new InvalidOperationException($"DolphinTool falhou (código {process.ExitCode}). {Truncate(err, 300)}");
        }
    }

    private static string? FindPartition(string extractedRoot)
    {
        var sys = Path.Combine(extractedRoot, "sys");
        var files = Path.Combine(extractedRoot, "files");
        if (Directory.Exists(sys) && Directory.Exists(files)) return extractedRoot;
        foreach (var dir in Directory.EnumerateDirectories(extractedRoot))
        {
            if (Directory.Exists(Path.Combine(dir, "sys")) && Directory.Exists(Path.Combine(dir, "files")))
                return dir;
        }
        return null;
    }

    private static async Task VerifyRoundtripAsync(string roundtripRoot, ModManifest manifest,
        CancellationToken ct)
    {
        var partition = FindPartition(roundtripRoot)
            ?? throw new DirectoryNotFoundException("A imagem gerada não contém partição válida.");

        foreach (var entry in manifest.Replacements)
        {
            if (!entry.InstalledPath.StartsWith("sys/") && !entry.InstalledPath.StartsWith("files/"))
                throw new InvalidDataException($"Caminho de modificação inválido: {entry.InstalledPath}");

            var full = Path.Combine(partition, entry.InstalledPath.Replace('/', Path.DirectorySeparatorChar));
            if (!File.Exists(full))
                throw new InvalidDataException($"Mod ausente na imagem final: {entry.InstalledPath}");

            var actual = await ComputeSha256Async(full, ct);
            if (!string.Equals(actual, entry.Sha256, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException($"Mod danificado na imagem final: {entry.InstalledPath}");
        }
    }

    private static async Task VerifyOriginalAsync(string partition, ModManifest manifest, CancellationToken ct)
    {
        foreach (var (path, expected) in manifest.OriginalSha256)
        {
            var full = Path.Combine(partition, path.Replace('/', Path.DirectorySeparatorChar));
            if (!File.Exists(full))
                throw new FileNotFoundException($"Arquivo esperado ausente: {path}");
            var actual = await ComputeSha256Async(full, ct);
            if (!string.Equals(actual, expected, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException(
                    $"Arquivo original diferente do suportado: {path}. A imagem pode estar modificada ou é outra revisão.");
        }
    }

    /// <summary>Aplica patch binário pbr-delta-v1 (gzip + JSON com ops copy/add).</summary>
    public static void ApplyPbrDelta(string originalPath, string patchPath, string expectedSha)
    {
        using var fileStream = File.OpenRead(patchPath);
        using var gzip = new GZipStream(fileStream, CompressionMode.Decompress);
        var doc = JsonSerializer.Deserialize<DeltaDoc>(gzip, JsonOpts)
            ?? throw new InvalidDataException("Patch inválido.");

        if (doc.Schema != 1 || doc.TargetSize < 0 || doc.TargetSize > 33554432)
            throw new InvalidDataException("Patch ou original incompatível.");

        var source = File.ReadAllBytes(originalPath);
        if (ComputeSha256(source) != doc.SourceSha256)
            throw new InvalidDataException("Arquivo original não corresponde ao esperado pelo patch.");

        using var output = new MemoryStream();
        foreach (var op in doc.Ops)
        {
            if (op.Kind == "copy")
            {
                if (op.Offset < 0 || op.Length < 0 || op.Offset + op.Length > source.Length)
                    throw new InvalidDataException("Bloco de patch inválido.");
                output.Write(source, (int)op.Offset, (int)op.Length);
            }
            else if (op.Kind == "add")
            {
                var added = Convert.FromBase64String(op.Data ?? "");
                output.Write(added, 0, added.Length);
            }
            else throw new InvalidDataException("Operação de patch desconhecida.");

            if (output.Length > doc.TargetSize)
                throw new InvalidDataException("Tamanho de patch inválido.");
        }

        if (output.Length != doc.TargetSize)
            throw new InvalidDataException("Patch incompleto.");

        var bytes = output.ToArray();
        if (ComputeSha256(bytes) != expectedSha)
            throw new InvalidDataException("Resultado do patch corrompido.");

        File.WriteAllBytes(originalPath, bytes);
    }

    private static string ComputeSha256(byte[] data)
        => Convert.ToHexString(SHA256.HashData(data)).ToLowerInvariant();

    private static async Task<string> ComputeSha256Async(string path, CancellationToken ct)
    {
        await using var stream = File.OpenRead(path);
        return Convert.ToHexString(await SHA256.HashDataAsync(stream, ct)).ToLowerInvariant();
    }

    private static void TryDelete(string path)
    {
        try { if (Directory.Exists(path)) Directory.Delete(path, recursive: true); } catch { }
    }

    private static string Truncate(string s, int max) => s.Length <= max ? s : s[..max] + "...";
}

public class ModManifest
{
    [JsonPropertyName("mod_version")]
    public string ModVersion { get; set; } = "";

    [JsonPropertyName("original_sha256")]
    public Dictionary<string, string> OriginalSha256 { get; set; } = new();

    [JsonPropertyName("replacements")]
    public List<ModReplacement> Replacements { get; set; } = new();
}

public class ModReplacement
{
    [JsonPropertyName("installed_path")]
    public string InstalledPath { get; set; } = "";

    [JsonPropertyName("package_path")]
    public string PackagePath { get; set; } = "";

    [JsonPropertyName("format")]
    public string Format { get; set; } = "";

    [JsonPropertyName("sha256")]
    public string Sha256 { get; set; } = "";
}

public class DeltaDoc
{
    [JsonPropertyName("schema")]
    public int Schema { get; set; }

    [JsonPropertyName("source_sha256")]
    public string SourceSha256 { get; set; } = "";

    [JsonPropertyName("target_sha256")]
    public string TargetSha256 { get; set; } = "";

    [JsonPropertyName("target_size")]
    public long TargetSize { get; set; }

    [JsonPropertyName("ops")]
    public List<DeltaOp> Ops { get; set; } = new();
}

public class DeltaOp
{
    [JsonPropertyName("kind")]
    public string Kind { get; set; } = "";

    [JsonPropertyName("offset")]
    public long Offset { get; set; }

    [JsonPropertyName("length")]
    public long Length { get; set; }

    [JsonPropertyName("data")]
    public string? Data { get; set; }
}
