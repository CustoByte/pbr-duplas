using System.IO;
using System.Windows;
using System.Windows.Controls;
using Microsoft.Win32;
using PBRDuplasLauncher.Models;
using PBRDuplasLauncher.Services;

namespace PBRDuplasLauncher;

public partial class MainWindow : Window
{
    private static readonly string LauncherVersion = ReadLauncherVersion();
    private readonly LauncherConfig _config;
    private readonly GameLaunchService _launchService = new();
    private readonly UpdateService _updateService = new();
    private UpdateManifest? _pendingManifest;

    private static string ReadLauncherVersion()
    {
        var info = System.Reflection.Assembly.GetExecutingAssembly()
            .GetCustomAttributes(typeof(System.Reflection.AssemblyInformationalVersionAttribute), false)
            .OfType<System.Reflection.AssemblyInformationalVersionAttribute>()
            .FirstOrDefault()?.InformationalVersion;

        if (!string.IsNullOrWhiteSpace(info))
            return info.Split('+')[0];

        var v = System.Reflection.Assembly.GetExecutingAssembly().GetName().Version;
        return v is null ? "0.0.0" : $"{v.Major}.{v.Minor}.{v.Build}";
    }

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
            Loaded += async (_, _) => await AutoUpdateOnStartupAsync();
    }

    /// <summary>
    /// Ao abrir, aplica silenciosamente uma versão nova do launcher e só então segue.
    /// Sem diálogo: baixa, verifica, substitui os arquivos e reinicia.
    /// </summary>
    private async Task AutoUpdateOnStartupAsync()
    {
        try
        {
            if (SelfUpdater.IsLoopGuardActive())
            {
                // Já tentamos atualizar nesta execução; evita reiniciar em ciclo.
                SelfUpdater.ClearLoopGuard();
                Log("Atualização já aplicada nesta execução.");
            }
            else
            {
                Log($"Verificando atualização (versão atual {LauncherVersion})...");
                var manifest = await _updateService.GetManifestAsync(_config.GitHubOwner, _config.GitHubRepo);
                if (manifest is null)
                {
                    Log("Manifesto de atualização indisponível.");
                    return;
                }

                _config.LastUpdateCheck = DateTime.Now.ToString("o");
                ConfigService.Save(_config);
                Log($"Manifesto: {manifest.Version}");

                if (!UpdateService.IsUpdateAvailable(LauncherVersion, manifest.Version)
                    || string.IsNullOrWhiteSpace(manifest.LauncherUrl))
                {
                    Log($"Launcher já está atualizado ({LauncherVersion}).");
                    return;
                }

                UpdateStatusText.Text = $"Atualizando para {manifest.Version}...";
                Log($"Atualizando launcher {LauncherVersion} → {manifest.Version}...");

                var dir = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "PBRDuplas", "updates", manifest.Version);

                var (zipPath, sha) = await _updateService.DownloadAsync(
                    manifest.LauncherUrl, dir, "launcher.zip");

                if (!string.IsNullOrWhiteSpace(manifest.LauncherSha256)
                    && !string.Equals(sha, manifest.LauncherSha256, StringComparison.OrdinalIgnoreCase))
                {
                    Log("Pacote de atualização inválido (checksum). Seguindo com a versão atual.");
                    return;
                }

                Log("Aplicando atualização e reiniciando...");
                SelfUpdater.ScheduleUpdate(zipPath, AppContext.BaseDirectory, "PBR Duplas.exe");
            }
        }
        catch (Exception ex)
        {
            Log($"Não foi possível atualizar automaticamente: {ex.Message}");
        }
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
        try
        {
            Directory.CreateDirectory(ConfigService.ConfigDir);
            File.AppendAllText(Path.Combine(ConfigService.ConfigDir, "launcher.log"),
                $"[{DateTime.Now:O}] {message}\n");
        }
        catch { }
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
        PageInstall.Visibility = Visibility.Collapsed;
        PageUpdates.Visibility = Visibility.Collapsed;
        PageNotes.Visibility = Visibility.Collapsed;
        PageSettings.Visibility = Visibility.Collapsed;
        page.Visibility = Visibility.Visible;
    }

    private void NavInstall_Click(object sender, RoutedEventArgs e)
    {
        ShowPage(PageInstall);

        // Reaproveita a ISO já configurada: o campo "Arquivo do jogo" em
        // CONFIGURAÇÕES é a fonte da verdade; OriginalImagePath só é salvo
        // depois de uma instalação bem-sucedida.
        var candidates = new[] { _config.OriginalImagePath, _config.GamePath }
            .Where(p => !string.IsNullOrWhiteSpace(p) && File.Exists(p))
            .Where(p => !p.EndsWith("- PBR Duplas.rvz", StringComparison.OrdinalIgnoreCase));

        var existing = candidates.FirstOrDefault();
        if (existing is not null && string.IsNullOrWhiteSpace(InstallImagePathBox.Text))
            InstallImagePathBox.Text = existing;
    }

    private void BrowseInstallImage_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog
        {
            Title = "Selecione a ISO original do Pokémon Battle Revolution",
            Filter = "Imagens de jogo|*.iso;*.rvz;*.wbfs;*.gcm|Todos os arquivos|*.*"
        };
        if (dialog.ShowDialog() == true)
        {
            InstallImagePathBox.Text = dialog.FileName;
            // Salva imediatamente para não precisar escolher de novo depois.
            _config.OriginalImagePath = dialog.FileName;
            ConfigService.Save(_config);
        }
    }

    private void InstallLog(string message)
    {
        var line = $"[{DateTime.Now:HH:mm:ss}] {message}";
        InstallLogText.Text = string.IsNullOrEmpty(InstallLogText.Text) ? line : $"{InstallLogText.Text}\n{line}";
        InstallLogScroll.ScrollToEnd();
    }

    private async void InstallButton_Click(object sender, RoutedEventArgs e)
    {
        var imagePath = InstallImagePathBox.Text.Trim();
        if (string.IsNullOrWhiteSpace(imagePath) || !File.Exists(imagePath))
        {
            MessageBox.Show("Selecione a ISO do jogo primeiro.", "PBR Duplas",
                MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        var applier = new ModApplyService(_config.DolphinPath);
        if (string.IsNullOrEmpty(applier.DolphinToolPath))
        {
            MessageBox.Show(
                "DolphinTool.exe não encontrado.\n\nEle vem junto com o Dolphin, na pasta Tools.\n" +
                "Configure o caminho do Dolphin em CONFIGURAÇÕES para o launcher localizá-lo.",
                "PBR Duplas", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        InstallButton.IsEnabled = false;
        InstallProgress.Value = 0;
        InstallLogText.Text = "";
        InstallStatusText.Text = "Iniciando...";

        try
        {
            // baixar pacote de mods mais recente
            InstallStatusText.Text = "Baixando pacote de modificações...";
            InstallLog("Consultando a versão mais recente do mod...");

            var manifest = await _updateService.GetManifestAsync(_config.GitHubOwner, _config.GitHubRepo);
            if (manifest is null || string.IsNullOrWhiteSpace(manifest.ModPackageUrl))
                throw new InvalidOperationException("Nenhum pacote de modificações publicado no repositório.");

            InstallLog($"Versão do mod: {manifest.Version}");

            var pkgDir = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "PBRDuplas", "packages");
            var pkgProgress = new Progress<double>(p => InstallProgress.Value = p * 0.15);
            var (zipPath, sha) = await _updateService.DownloadAsync(
                manifest.ModPackageUrl, pkgDir, "aplicador-core.zip", pkgProgress);

            if (!string.IsNullOrWhiteSpace(manifest.ModPackageSha256)
                && !string.Equals(sha, manifest.ModPackageSha256, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("O pacote baixado não confere com o checksum publicado.");

            InstallLog("Pacote baixado e verificado.");
            InstallProgress.Value = 15;

            // saída: cópia modificada ao lado da original
            var outputPath = Path.Combine(
                Path.GetDirectoryName(imagePath)!,
                Path.GetFileNameWithoutExtension(imagePath) + " - PBR Duplas.rvz");

            var progress = new Progress<ApplyProgress>(p =>
            {
                InstallProgress.Value = 15 + p.Percent * 0.85;
                InstallStatusText.Text = p.Message;
            });

            InstallLog("Aplicando modificações (isso pode levar vários minutos)...");
            await applier.ApplyModAsync(imagePath, zipPath, outputPath, progress);

            _config.OriginalImagePath = imagePath;
            _config.ModdedImagePath = outputPath;
            _config.GamePath = outputPath;
            _config.InstalledVersion = manifest.Version;
            ConfigService.Save(_config);

            GameVersionText.Text = $"Jogo {manifest.Version}";
            GamePathBox.Text = outputPath;
            ValidateLaunchReady();

            InstallStatusText.Text = "Instalação concluída.";
            InstallLog($"Jogo modificado criado: {outputPath}");
            Log($"Mods aplicados: {manifest.Version}");

            MessageBox.Show($"Instalação concluída.\n\nJogo modificado:\n{outputPath}",
                "PBR Duplas", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            InstallStatusText.Text = "Falha na instalação.";
            InstallLog($"Erro: {ex.Message}");
            Log($"Erro na instalação: {ex.Message}");
            MessageBox.Show($"Não foi possível aplicar as modificações:\n\n{ex.Message}",
                "PBR Duplas", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            InstallButton.IsEnabled = true;
        }
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
                Log($"Launcher atualizado para {manifest.Version}. Reiniciando...");

                SelfUpdater.ScheduleUpdate(zipPath, AppContext.BaseDirectory, "PBR Duplas.exe");
                return;
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