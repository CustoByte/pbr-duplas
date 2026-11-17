using System.IO;
using System.Windows;

namespace PBRDuplasLauncher;

public partial class App : Application
{
    private static readonly string LogPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "PBRDuplas", "launcher-error.log");

    protected override void OnStartup(StartupEventArgs e)
    {
        AppDomain.CurrentDomain.UnhandledException += (s, args) => Log(args.ExceptionObject as Exception);
        DispatcherUnhandledException += (s, args) => { Log(args.Exception); args.Handled = true; };

        try
        {
            base.OnStartup(e);
        }
        catch (Exception ex)
        {
            Log(ex);
            throw;
        }
    }

    private static void Log(Exception? ex)
    {
        if (ex is null) return;
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(LogPath)!);
            File.AppendAllText(LogPath, $"[{DateTime.Now:O}]\n{ex}\n\n");
        }
        catch { }

        MessageBox.Show(ex.Message, "PBR Duplas — erro", MessageBoxButton.OK, MessageBoxImage.Error);
    }
}