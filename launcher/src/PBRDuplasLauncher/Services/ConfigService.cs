using System.IO;
using System.Text.Json;
using PBRDuplasLauncher.Models;

namespace PBRDuplasLauncher.Services;

public static class ConfigService
{
    public static readonly string ConfigDir =
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "PBRDuplas");

    private static readonly string ConfigPath = Path.Combine(ConfigDir, "config.json");

    public static LauncherConfig Load()
    {
        try
        {
            if (File.Exists(ConfigPath))
            {
                var json = File.ReadAllText(ConfigPath);
                return JsonSerializer.Deserialize<LauncherConfig>(json) ?? new LauncherConfig();
            }
        }
        catch { }
        return new LauncherConfig();
    }

    public static void Save(LauncherConfig config)
    {
        Directory.CreateDirectory(ConfigDir);
        var json = JsonSerializer.Serialize(config, new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(ConfigPath, json);
    }
}