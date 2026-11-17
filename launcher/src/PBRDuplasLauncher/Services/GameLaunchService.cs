using System.Diagnostics;
using System.IO;
using PBRDuplasLauncher.Models;

namespace PBRDuplasLauncher.Services;

public class GameLaunchService
{
    public bool TryLaunchGame(LauncherConfig config, out string error)
    {
        error = "";

        if (string.IsNullOrWhiteSpace(config.GamePath) || !File.Exists(config.GamePath))
        {
            error = "Caminho do jogo (RVZ) não configurado ou arquivo não encontrado.";
            return false;
        }

        if (string.IsNullOrWhiteSpace(config.DolphinPath) || !File.Exists(config.DolphinPath))
        {
            error = "Caminho do Dolphin não configurado ou executável não encontrado.";
            return false;
        }

        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = config.DolphinPath,
                Arguments = $"\"{config.GamePath}\"",
                UseShellExecute = true
            };
            Process.Start(psi);
            return true;
        }
        catch (Exception ex)
        {
            error = $"Falha ao iniciar: {ex.Message}";
            return false;
        }
    }

    public static List<string> FindDolphinPaths()
    {
        var paths = new List<string>();
        var programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
        var programFilesX86 = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86);

        var candidates = new[]
        {
            Path.Combine(programFiles, "Dolphin", "Dolphin.exe"),
            Path.Combine(programFilesX86, "Dolphin", "Dolphin.exe"),
            Path.Combine(programFiles, "Dolphin Emulator", "Dolphin.exe"),
            Path.Combine(programFilesX86, "Dolphin Emulator", "Dolphin.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Dolphin", "Dolphin.exe"),
        };

        foreach (var c in candidates)
            if (File.Exists(c)) paths.Add(c);

        return paths;
    }
}