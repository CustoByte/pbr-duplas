using System.Diagnostics;
using System.IO;
using System.IO.Compression;

namespace PBRDuplasLauncher.Services;

/// <summary>
/// Substitui os arquivos do launcher em execução sem exigir reinstalação:
/// extrai a nova versão em uma pasta temporária, grava um script que troca os
/// arquivos após o processo atual encerrar e reinicia o launcher.
/// </summary>
public static class SelfUpdater
{
    private static readonly string GuardPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "PBRDuplas", "updating.flag");

    /// <summary>Indica que uma atualização foi aplicada após a última inicialização.</summary>
    public static bool IsLoopGuardActive() => File.Exists(GuardPath);

    public static void ClearLoopGuard()
    {
        try { if (File.Exists(GuardPath)) File.Delete(GuardPath); } catch { }
    }

    public static void ScheduleUpdate(string zipPath, string installDir, string exeName)
    {
        var staging = Path.Combine(Path.GetTempPath(), "PBRDuplasUpdate", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(staging);
        ZipFile.ExtractToDirectory(zipPath, staging, overwriteFiles: true);

        Directory.CreateDirectory(Path.GetDirectoryName(GuardPath)!);
        File.WriteAllText(GuardPath, DateTime.Now.ToString("o"));

        var script = Path.Combine(Path.GetTempPath(), $"pbr-update-{Guid.NewGuid():N}.cmd");
        var exePath = Path.Combine(installDir, exeName);

        // Aspas duplicadas escapam aspas dentro do .cmd
        File.WriteAllText(script, $@"@echo off
setlocal
:wait
tasklist /fi ""IMAGENAME eq {exeName}"" 2>nul | find /i ""{exeName}"" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait
)
robocopy ""{staging}"" ""{installDir}"" /E /IS /IT /NFL /NDL /NJH /NJS /NP >nul
start """" ""{exePath}""
rmdir /s /q ""{staging}""
(goto) 2>nul & del ""%~f0""
");

        Process.Start(new ProcessStartInfo
        {
            FileName = "cmd.exe",
            Arguments = $"/c \"\"{script}\"\"",
            UseShellExecute = false,
            CreateNoWindow = true
        });

        System.Windows.Application.Current.Shutdown();
    }
}