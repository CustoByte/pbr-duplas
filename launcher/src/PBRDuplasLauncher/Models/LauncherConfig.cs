namespace PBRDuplasLauncher.Models;

public class LauncherConfig
{
    public string GamePath { get; set; } = "";
    public string DolphinPath { get; set; } = "";
    public string InstalledVersion { get; set; } = "";
    public string LastUpdateCheck { get; set; } = "";
    public bool AutoCheckUpdates { get; set; } = true;
    public string GitHubOwner { get; set; } = "CustoByte";
    public string GitHubRepo { get; set; } = "pbr-duplas";
}