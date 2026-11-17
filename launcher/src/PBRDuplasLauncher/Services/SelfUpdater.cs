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
    public static void ScheduleUpdate(string zipPath, string installDir, string exeName)
    {
        var staging = Path.Combine(Path.GetTempPath(), "PBRDuplasUpdate", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(staging);
        ZipFile.ExtractToDirectory(zipPath, staging, overwriteFiles: true);

        var script = Path.Combine(Path.GetTempPath(), $"pbr-update-{Guid.NewGuid():N}.cmd");
        var exePath = Path.Combine(installDir, exeName);

        File.WriteAllText(script, $@"@echo off
setlocal
timeout /t 2 /nobreak >nul
robocopy ""{staging}"" ""{installDir}"" /E /IS /IT /NFL /NDL /NJH /NJS /NP >nul
start """" ""{exePath}""
rmdir /s /q ""{staging}""
del ""%~f0""
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