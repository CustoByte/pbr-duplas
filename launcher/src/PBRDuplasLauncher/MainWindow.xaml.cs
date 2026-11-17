using System.IO;
using System.Windows;
using System.Windows.Controls;
using Microsoft.Win32;
using PBRDuplasLauncher.Models;
using PBRDuplasLauncher.Services;

namespace PBRDuplasLauncher;

public partial class MainWindow : Window
{
    private const string LauncherVersion = "1.0.0";
    private readonly LauncherConfig _config;
    private readonly GameLaunchService _launchService = new();
    private readonly UpdateService _updateService = new();
    private UpdateManifest? _pendingManifest;

    public MainWindow()
    {
        InitializeComponent();
        _config = ConfigService.Load();
        LoadConfigIntoUi();

        VersionText.Text = $"Launcher v{LauncherVersion}";
        GameVersionText.Text = string.IsNullOrWhiteSpace(_config.InstalledVersion)
            ? "Jogo — não instalado"
            : $"Jogo {_config.InstalledVersion}";

        Log("PBR Duplas iniciado.");
        ValidateLaunchReady();

        if (_config.AutoCheckUpdates)
            Loaded += async (_, _) => await CheckForUpdatesAsync(silent: true);
    }

    private void LoadConfigIntoUi()
    {
        GamePathBox.Text = _config.GamePath;
        DolphinPathBox.Text = _config.DolphinPath;
        AutoUpdateCheck.IsChecked = _config.AutoCheckUpdates;
        RepoBox.Text = $"{_config.GitHubOwner}/{_config.GitHubRepo}";
    }

    private void Log(string message)
    {
        var line = $"[{DateTime.Now:HH:mm:ss}] {message}";
        LogText.Text = string.IsNullOrEmpty(LogText.Text) ? line : $"{LogText.Text}\n{line}";
        LogScroll.ScrollToEnd();
    }

    private void ValidateLaunchReady()
    {
        var hasGame = !string.IsNullOrWhiteSpace(_config.GamePath) && File.Exists(_config.GamePath);
        var hasDolphin = !string.IsNullOrWhiteSpace(_config.DolphinPath) && File.Exists(_config.DolphinPath);
        LaunchHintText.Text = hasGame && hasDolphin
            ? $"Pronto. {Path.GetFileName(_config.GamePath)}"
            : "Configure o jogo e o Dolphin em CONFIGURAÇÕES.";
    }

    private void ShowPage(FrameworkElement page)
    {
        PageHome.Visibility = Visibility.Collapsed;
        PageUpdates.Visibility = Visibility.Collapsed;
        PageNotes.Visibility = Visibility.Collapsed;
        PageSettings.Visibility = Visibility.Collapsed;
        page.Visibility = Visibility.Visible;
    }

    private void NavNotes_Click(object sender, RoutedEventArgs e)
    {
        ShowPage(PageNotes);
        _ = LoadNotesAsync();
    }

    private async Task LoadNotesAsync()
    {
        NotesList.ItemsSource = null;
        var releases = await _updateService.GetReleasesAsync(_config.GitHubOwner, _config.GitHubRepo);

        if (releases.Count == 0)
        {
            Log("Não foi possível carregar as notas de versão.");
            return;
        }

        var current = UpdateService.NormalizeTag(_config.InstalledVersion);

        NotesList.ItemsSource = releases.Select(r => new
        {
            Tag = r.TagName,
            Title = string.IsNullOrWhiteSpace(r.Name) ? r.TagName : r.Name,
            Notes = string.IsNullOrWhiteSpace(r.Body) ? "Sem notas publicadas." : r.Body,
            Date = FormatDate(r.PublishedAt),
            BadgeVisibility = r.Prerelease ? Visibility.Visible : Visibility.Collapsed,
            IsCurrent = string.Equals(UpdateService.NormalizeTag(r.TagName), current,
                StringComparison.OrdinalIgnoreCase)
        }).ToList();

        Log($"{releases.Count} versões carregadas.");
    }

    private static string FormatDate(string iso)
    {
        return DateTime.TryParse(iso, out var dt) ? dt.ToLocalTime().ToString("dd/MM/yyyy") : "";
    }

    private void NavHome_Click(object sender, RoutedEventArgs e) => ShowPage(PageHome);

    private void NavUpdates_Click(object sender, RoutedEventArgs e)
    {
        ShowPage(PageUpdates);
        _ = CheckForUpdatesAsync(silent: false);
    }

    private void NavSettings_Click(object sender, RoutedEventArgs e) => ShowPage(PageSettings);

    private void LaunchButton_Click(object sender, RoutedEventArgs e)
    {
        if (_launchService.TryLaunchGame(_config, out var error))
        {
            Log("Dolphin iniciado com o jogo.");
            Application.Current.Shutdown();
        }
        else
        {
            Log($"Erro: {error}");
            MessageBox.Show(error, "PBR Duplas", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    private void BrowseGame_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog
        {
            Title = "Selecione o arquivo do jogo",
            Filter = "Imagens de jogo|*.rvz;*.iso;*.wbfs;*.gcm|Todos os arquivos|*.*"
        };
        if (dialog.ShowDialog() == true)
        {
            GamePathBox.Text = dialog.FileName;
            _config.GamePath = dialog.FileName;
            ConfigService.Save(_config);
            ValidateLaunchReady();
        }
    }

    private void BrowseDolphin_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog
        {
            Title = "Selecione o executável do Dolphin",
            Filter = "Executável|*.exe|Todos os arquivos|*.*"
        };
        if (dialog.ShowDialog() == true)
            DolphinPathBox.Text = dialog.FileName;
    }

    private void AutoDetectDolphin_Click(object sender, RoutedEventArgs e)
    {
        var found = GameLaunchService.FindDolphinPaths();
        if (found.Count > 0)
        {
            DolphinPathBox.Text = found[0];
            Log($"Dolphin localizado: {found[0]}");
        }
        else
        {
            Log("Dolphin não encontrado nas pastas padrão.");
            MessageBox.Show("Dolphin não encontrado automaticamente. Use PROCURAR.",
                "PBR Duplas", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }

    private void SaveSettings_Click(object sender, RoutedEventArgs e)
    {
        _config.GamePath = GamePathBox.Text.Trim();
        _config.DolphinPath = DolphinPathBox.Text.Trim();
        _config.AutoCheckUpdates = AutoUpdateCheck.IsChecked == true;

        var repo = RepoBox.Text.Trim();
        var parts = repo.Split('/', StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length == 2)
        {
            _config.GitHubOwner = parts[0];
            _config.GitHubRepo = parts[1];
        }

        ConfigService.Save(_config);
        ValidateLaunchReady();
        Log("Configurações salvas.");
    }

    private async Task CheckForUpdatesAsync(bool silent)
    {
        UpdateStatusText.Text = "Consultando atualizações...";
        UpdateDetailsText.Text = "";
        DownloadUpdateButton.Visibility = Visibility.Collapsed;

        var manifest = await _updateService.GetManifestAsync(_config.GitHubOwner, _config.GitHubRepo);

        if (manifest is null)
        {
            UpdateStatusText.Text = "Não foi possível consultar as atualizações.";
            if (!silent) Log("Falha ao consultar o manifesto de atualização.");
            return;
        }

        _pendingManifest = manifest;
        _config.LastUpdateCheck = DateTime.Now.ToString("o");
        ConfigService.Save(_config);

        var launcherOutdated = UpdateService.IsUpdateAvailable(LauncherVersion, manifest.Version);
        var gameOutdated = !string.IsNullOrWhiteSpace(manifest.GameVersion)
                           && UpdateService.IsUpdateAvailable(_config.InstalledVersion, manifest.GameVersion);

        var lines = new List<string>();
        if (!string.IsNullOrWhiteSpace(manifest.Notes)) lines.Add(manifest.Notes);
        if (gameOutdated) lines.Add($"Jogo: {_config.InstalledVersion} → {manifest.GameVersion}");
        UpdateDetailsText.Text = string.Join("\n\n", lines);

        if (launcherOutdated)
        {
            UpdateStatusText.Text = $"Nova versão do launcher: {manifest.Version}";
            DownloadUpdateButton.Content = "ATUALIZAR LAUNCHER";
            DownloadUpdateButton.Visibility = Visibility.Visible;
            Log($"Atualização do launcher disponível: {manifest.Version}");
        }
        else if (gameOutdated)
        {
            UpdateStatusText.Text = $"Nova versão do jogo: {manifest.GameVersion}";
            DownloadUpdateButton.Content = "BAIXAR JOGO";
            DownloadUpdateButton.Visibility = Visibility.Visible;
            Log($"Atualização do jogo disponível: {manifest.GameVersion}");
        }
        else
        {
            UpdateStatusText.Text = $"Tudo atualizado ({manifest.Version}).";
        }
    }

    private void CheckUpdatesButton_Click(object sender, RoutedEventArgs e) =>
        _ = CheckForUpdatesAsync(silent: false);

    private async void DownloadUpdateButton_Click(object sender, RoutedEventArgs e)
    {
        if (_pendingManifest is null) return;

        var manifest = _pendingManifest;
        var launcherOutdated = UpdateService.IsUpdateAvailable(LauncherVersion, manifest.Version);

        DownloadUpdateButton.IsEnabled = false;
        UpdateProgress.Visibility = Visibility.Visible;

        try
        {
            var progress = new Progress<double>(p => UpdateProgress.Value = p);

            if (launcherOutdated && !string.IsNullOrWhiteSpace(manifest.LauncherUrl))
            {
                var dir = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "PBRDuplas", "updates", manifest.Version);

                UpdateStatusText.Text = "Baixando launcher...";
                var (zipPath, sha) = await _updateService.DownloadAsync(
                    manifest.LauncherUrl, dir, "launcher.zip", progress);

                if (!string.IsNullOrWhiteSpace(manifest.LauncherSha256)
                    && !string.Equals(sha, manifest.LauncherSha256, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidDataException("O arquivo baixado não confere com o checksum publicado.");

                UpdateStatusText.Text = "Aplicando atualização...";
                var installDir = AppContext.BaseDirectory;
                UpdateService.ExtractLauncher(zipPath, installDir);
                Log($"Launcher atualizado para {manifest.Version}.");

                MessageBox.Show(
                    "Launcher atualizado. Feche e abra novamente para usar a nova versão.",
                    "PBR Duplas", MessageBoxButton.OK, MessageBoxImage.Information);
                UpdateStatusText.Text = $"Launcher atualizado para {manifest.Version}.";
            }
            else if (!string.IsNullOrWhiteSpace(manifest.GameUrl))
            {
                var dir = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "PBRDuplas", "game", manifest.GameVersion);

                UpdateStatusText.Text = "Baixando jogo...";
                var (zipPath, sha) = await _updateService.DownloadAsync(
                    manifest.GameUrl, dir, "jogo.zip", progress);

                if (!string.IsNullOrWhiteSpace(manifest.GameSha256)
                    && !string.Equals(sha, manifest.GameSha256, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidDataException("O arquivo baixado não confere com o checksum publicado.");

                _config.InstalledVersion = manifest.GameVersion;
                ConfigService.Save(_config);
                GameVersionText.Text = $"Jogo {manifest.GameVersion}";

                Log($"Jogo baixado em {zipPath}.");
                UpdateStatusText.Text = $"Jogo {manifest.GameVersion} baixado.";

                var open = MessageBox.Show(
                    $"Pacote do jogo baixado em:\n{zipPath}\n\nAbrir a pasta?",
                    "PBR Duplas", MessageBoxButton.YesNo, MessageBoxImage.Question);
                if (open == MessageBoxResult.Yes)
                    System.Diagnostics.Process.Start("explorer.exe", $"\"{Path.GetDirectoryName(zipPath)}\"");
            }
        }
        catch (Exception ex)
        {
            UpdateStatusText.Text = "Falha na atualização.";
            Log($"Erro: {ex.Message}");
            MessageBox.Show($"Falha ao atualizar: {ex.Message}", "PBR Duplas",
                MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            DownloadUpdateButton.IsEnabled = true;
            UpdateProgress.Visibility = Visibility.Collapsed;
        }
    }
}