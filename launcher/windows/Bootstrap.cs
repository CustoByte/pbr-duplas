using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Windows;
using System.Reflection;
[assembly: AssemblyTitle("PBR Duplas")]
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]

namespace PbrLauncher {
 internal static class Bootstrap {
  [STAThread] private static int Main(string[] args) {
   bool verify=args.Contains("--verify");
   try {
    string root=AppDomain.CurrentDomain.BaseDirectory;var state=Store.Read(Path.Combine(root,"installed.json"));
    string executable=Path.GetFullPath(Store.Get(state,"executable"));
    string versions=Path.GetFullPath(Path.Combine(root,"versions"))+Path.DirectorySeparatorChar;
    if(!executable.StartsWith(versions,StringComparison.OrdinalIgnoreCase)||!File.Exists(executable)||Store.Hash(executable)!=Store.Get(state,"sha256"))throw new InvalidDataException("O launcher instalado não passou na verificação. Execute o CMD de atualização para recuperá-lo.");
    if(!verify){string data=Directory.GetParent(root.TrimEnd(Path.DirectorySeparatorChar)).FullName;Process.Start(new ProcessStartInfo(executable,"--data-root "+Store.Quote(data)){UseShellExecute=false,CreateNoWindow=true,WorkingDirectory=Path.GetDirectoryName(executable)});}
    return 0;
   }catch(Exception ex){if(!verify)MessageBox.Show(ex.Message,"PBR Duplas",MessageBoxButton.OK,MessageBoxImage.Error);return 1;}
  }
 }
}
