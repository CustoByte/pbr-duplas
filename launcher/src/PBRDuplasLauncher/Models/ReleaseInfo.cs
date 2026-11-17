namespace PBRDuplasLauncher.Models;

public class ReleaseInfo
{
    public string TagName { get; set; } = "";
    public string Name { get; set; } = "";
    public string Body { get; set; } = "";
    public string PublishedAt { get; set; } = "";
    public bool Prerelease { get; set; }
    public List<ReleaseAsset> Assets { get; set; } = new();
}

public class ReleaseAsset
{
    public string Name { get; set; } = "";
    public string BrowserDownloadUrl { get; set; } = "";
    public long Size { get; set; }
}

// Manifest publicado no repo (launcher/update.json)
public class UpdateManifest
{
    public int Schema { get; set; }
    public string Version { get; set; } = "";
    public string Notes { get; set; } = "";
    public string LauncherUrl { get; set; } = "";
    public string LauncherSha256 { get; set; } = "";
    public string GameVersion { get; set; } = "";
    public string GameUrl { get; set; } = "";
    public string GameSha256 { get; set; } = "";
}