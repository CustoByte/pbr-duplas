using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using Microsoft.Win32;
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]

namespace PbrLauncher {
 internal static class Program {
  private static Mutex instance;
  internal static void ReleaseInstance() { if (instance != null) { instance.ReleaseMutex(); instance.Dispose(); instance = null; } }
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] private static extern IntPtr FindWindow(string cls,string title);
  [DllImport("user32.dll")] private static extern bool SetForegroundWindow(IntPtr window);
  [DllImport("user32.dll")] private static extern bool ShowWindow(IntPtr window,int command);
  [STAThread] private static int Main(string[] args) {
   try {
    if (args.Contains("--self-test")) return SelfTest.Run(args);
    string root = Value(args,"--data-root") ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"PBR-Duplas");
    root = Path.GetFullPath(root); bool preview = args.Contains("--preview");
    if (!preview) { bool created; string id = Convert.ToBase64String(Encoding.UTF8.GetBytes(root.ToUpperInvariant())).Replace('/','_').Replace('\\','_'); if (id.Length>180) id=id.Substring(0,180); instance = new Mutex(true,"Local\\PBR-Duplas-Launcher-"+id,out created); if (!created) { instance.Dispose(); instance=null; IntPtr window=FindWindow(null,"PBR Duplas");if(window!=IntPtr.Zero){ShowWindow(window,9);SetForegroundWindow(window);}return 0; } }
    var app = new Application(); var view = new View(new Backend(root),preview);
    if (preview) { view.Window.Show();view.Window.Dispatcher.Invoke(System.Windows.Threading.DispatcherPriority.Render,new Action(()=>{}));view.Window.UpdateLayout();var image=new RenderTargetBitmap((int)view.Window.ActualWidth,(int)view.Window.ActualHeight,96,96,PixelFormats.Pbgra32);image.Render(view.Window);var png=new PngBitmapEncoder();png.Frames.Add(BitmapFrame.Create(image));using(var output=File.Create(Value(args,"--preview") ?? "launcher-preview.png"))png.Save(output);view.Window.Close();return 0; }
    return app.Run(view.Window);
   } catch(Exception ex) { if(args.Contains("--preview")||args.Contains("--self-test"))File.WriteAllText("launcher-error.txt",ex.ToString());else MessageBox.Show(ex.Message,"PBR Duplas",MessageBoxButton.OK,MessageBoxImage.Error);return 1; }
   finally { ReleaseInstance(); }
  }
  internal static string Value(string[] args,string name) { int i=Array.IndexOf(args,name);return i>=0&&i+1<args.Length?args[i+1]:null; }
 }
 internal sealed class View {
  internal readonly Window Window;
  private readonly Backend backend;
  private Dictionary<string,object> state,feed;
  private readonly Dictionary<string,TextBox> fields = new Dictionary<string,TextBox>();
  private bool busy;
  private readonly string[,] paths = { {"original_image","Imagem original do Battle Revolution","Imagem Wii|*.rvz;*.iso;*.wia;*.gcz"},{"dolphin_path","Dolphin.exe","Dolphin|Dolphin.exe"},{"tool_path","DolphinTool.exe","DolphinTool|DolphinTool.exe"} };
  private T Find<T>(string name) where T:class { return Window.FindName(name) as T; }
  private void Text(string name,string value) { Find<TextBlock>(name).Text=value; }
  private void Status(string title,string detail) { Text("Status",title);Text("Detail",detail); }
  private void Log(string line) { Window.Dispatcher.BeginInvoke(new Action(()=>{var log=Find<TextBox>("LogText");log.AppendText(line+Environment.NewLine);if(log.Text.Length>20000)log.Text=log.Text.Substring(log.Text.Length-15000);log.ScrollToEnd(); if(line.StartsWith("[")){Text("Detail",line);}})); }
  private void Progress(string detail,double percent) { Window.Dispatcher.BeginInvoke(new Action(()=>{Text("Detail",detail);var p=Find<ProgressBar>("Progress");p.IsIndeterminate=percent<0;p.Value=Math.Max(0,percent);})); }
  internal View(Backend backend,bool preview) {
   this.backend=backend;
   using(var stream=Assembly.GetExecutingAssembly().GetManifestResourceStream("MainWindow.xaml"))Window=(Window)XamlReader.Load(stream);
   Text("LauncherVersion","Launcher "+Store.Version);
   state=Store.Read(backend.StatePath);BuildSettings();Refresh();
   Find<Button>("HomeNav").Click+=(s,e)=>Page(false);Find<Button>("SettingsNav").Click+=(s,e)=>Page(true);
   Find<Button>("NewsNav").Click+=(s,e)=>Process.Start(new ProcessStartInfo("https://github.com/CustoByte/pbr-duplas/releases") {UseShellExecute=true});
   Find<Button>("LogsNav").Click+=(s,e)=>{if(!File.Exists(backend.LogPath))backend.Log("Launcher iniciado.");Process.Start("notepad.exe",Store.Quote(backend.LogPath));};
   Find<Button>("SaveSettings").Click+=(s,e)=>{try{SaveSettings();Page(false);Status("Configurações salvas","Os caminhos serão usados na próxima atualização.");}catch(Exception ex){Error(ex);}};
   Find<Button>("Check").Click+=async(s,e)=>await Check();Find<Button>("Update").Click+=async(s,e)=>await Update();Find<Button>("Play").Click+=async(s,e)=>await Play();
   Window.Closing+=(s,e)=>{if(busy){e.Cancel=true;Status("Operação em andamento","Aguarde a conclusão para fechar o launcher com segurança.");}};
   if(preview){Text("InstalledVersion","v0.14.0 · Charizard Y");Text("AvailableVersion","v0.14.0 · Charizard Y");Text("Connection","Conectado ao GitHub");Text("InstallStatus","Pronto para jogar");Status("Sua próxima batalha está pronta","O jogo está atualizado. Escolha seu time e entre na arena.");Find<Button>("Play").IsEnabled=true;Find<Button>("Update").Content="Atualizado";}
   else Window.Loaded+=async(s,e)=>await Check();
  }
  private void Page(bool settings) { Find<FrameworkElement>("HomePage").Visibility=settings?Visibility.Collapsed:Visibility.Visible;Find<FrameworkElement>("SettingsPage").Visibility=settings?Visibility.Visible:Visibility.Collapsed;Text("PageTitle",settings?"Configurações":"Visão geral"); }
  private void BuildSettings() {
   for(int i=0;i<paths.GetLength(0);i++){
    string key=paths[i,0],label=paths[i,1],filter=paths[i,2];var container=new StackPanel{Margin=new Thickness(0,0,0,13)};container.Children.Add(new TextBlock{Text=label,Margin=new Thickness(0,0,0,7),Foreground=new SolidColorBrush(Color.FromRgb(166,185,207))});var row=new Grid();row.ColumnDefinitions.Add(new ColumnDefinition());row.ColumnDefinitions.Add(new ColumnDefinition{Width=GridLength.Auto});var box=new TextBox{Text=Store.Get(state,key),VerticalContentAlignment=VerticalAlignment.Center};fields[key]=box;row.Children.Add(box);var browse=new Button{Content="Selecionar",Margin=new Thickness(9,0,0,0)};Grid.SetColumn(browse,1);browse.Click+=(s,e)=>{if(busy)return;var dialog=new OpenFileDialog{Title=label,Filter=filter,CheckFileExists=true};if(dialog.ShowDialog(Window)==true){box.Text=dialog.FileName;if(key=="dolphin_path"){string tool=Path.Combine(Path.GetDirectoryName(dialog.FileName),"DolphinTool.exe");if(File.Exists(tool))fields["tool_path"].Text=tool;}}};row.Children.Add(browse);container.Children.Add(row);Find<StackPanel>("PathFields").Children.Add(container);
   }
  }
  private void SaveSettings() { state=Store.Read(backend.StatePath);foreach(var field in fields){string path=field.Value.Text.Trim();if(path!=""&&!File.Exists(path))throw new FileNotFoundException("Arquivo não encontrado: "+path);state[field.Key]=path;}Store.Write(backend.StatePath,state);Refresh(); }
  private bool Installed() {return File.Exists(Store.Get(state,"modified_image"))&&File.Exists(Store.Get(state,"dolphin_path"));}
  private void Refresh() {
   state=Store.Read(backend.StatePath);Text("InstalledVersion",Store.Get(state,"mod_version")==""?"Não preparado":Store.Get(state,"mod_version"));Text("InstallStatus",Installed()?"Pronto para jogar":"Preparação necessária");
   Find<Button>("Play").IsEnabled=!busy&&Installed();Find<Button>("Check").IsEnabled=!busy;Find<Button>("Update").IsEnabled=!busy&&feed!=null;Find<Button>("SaveSettings").IsEnabled=!busy;Find<Button>("Update").Content=Installed()?"Atualizar":"Preparar jogo";
  }
  private void Error(Exception ex) {backend.Log(ex.ToString());Status("Não foi possível concluir",ex.Message);Find<ProgressBar>("Progress").IsIndeterminate=false;}
  private async Task Check() {
   if(busy)return;busy=true;Refresh();Text("Connection","Verificando atualizações");Find<ProgressBar>("Progress").IsIndeterminate=true;
   try {feed=await backend.Check();Text("AvailableVersion",GameVersion());Text("Connection","Conectado ao GitHub");if(Installed()&&Store.Get(state,"mod_version")==GameVersion()&&!NewLauncher())Status("Tudo pronto para jogar","Sua instalação está na versão mais recente.");else Status(Installed()?"Nova atualização disponível":"Vamos preparar seu jogo",Installed()?"Clique em Atualizar para instalar as mudanças do GitHub.":"Abra Configurações para escolher o jogo original e o Dolphin.");}
   catch(Exception ex){backend.Log(ex.ToString());feed=backend.OfflineFeed();Text("Connection","Modo offline");Text("AvailableVersion",feed==null?"Indisponível":GameVersion());Status(Installed()?"Você pode jogar offline":"Não foi possível consultar o GitHub",Installed()?"Sua versão instalada continua disponível. Tente verificar novamente mais tarde.":ex.Message);}
   finally{busy=false;Find<ProgressBar>("Progress").IsIndeterminate=false;Refresh();}
  }
  private string GameVersion() {string game=Store.Get(feed,"game_version");return game==""?Store.Get(feed,"version"):game;}
  private bool NewLauncher() {Version target;return Version.TryParse(Store.Get(feed,"launcher_version"),out target)&&target.CompareTo(new Version(Store.Version))>0;}
  private async Task<bool> ImageValid() {string expected=Store.Get(state,"image_sha256");return Installed()&&expected.Length==64&&await Task.Run(()=>Store.Hash(Store.Get(state,"modified_image")))==expected;}
  private void Require(string key) {if(!File.Exists(Store.Get(state,key)))throw new FileNotFoundException("Um caminho salvo não está disponível. Confira Configurações: "+key);}
  private bool DolphinRunning() {return Process.GetProcessesByName("Dolphin").Length>0;}
  private async Task Update() {
   if(busy||feed==null)return;string core=null;FileStream applicationLock=null;bool handoff=false;
   try{
    if(DolphinRunning())throw new InvalidOperationException("Feche o Dolphin antes de atualizar o jogo.");
    state=Store.Read(backend.StatePath);
    if(Installed()&&Store.Get(state,"mod_version")==GameVersion()&&!NewLauncher()){
     busy=true;Refresh();Status("Conferindo sua instalação","Verificando os arquivos do jogo já instalado…");Find<ProgressBar>("Progress").IsIndeterminate=true;
     if(await ImageValid()){Status("Seu jogo já está atualizado","Arquivos conferidos. Nenhum modelo precisa ser selecionado ou convertido.");return;}busy=false;
    }
    foreach(string key in new[]{"original_image","dolphin_path"})Require(key);
    if(!File.Exists(Store.Get(state,"tool_path"))){string tool=Path.Combine(Path.GetDirectoryName(Store.Get(state,"dolphin_path")),"DolphinTool.exe");if(File.Exists(tool)){state["tool_path"]=tool;fields["tool_path"].Text=tool;Store.Write(backend.StatePath,state);}else Require("tool_path");}
    try{applicationLock=new FileStream(Path.Combine(backend.Root,"aplicador.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None);}catch(IOException){throw new InvalidOperationException("Outro atualizador está em execução. Aguarde a conclusão.");}
    busy=true;Page(false);Refresh();Status("Preparando atualização","Verificando o pacote publicado no GitHub…");Find<ProgressBar>("Progress").IsIndeterminate=true;
    core=await backend.Prepare(feed,Progress);var manifest=Store.Read(Path.Combine(core,"manifesto.json"));
    object launcherObject;if(manifest.TryGetValue("launcher",out launcherObject)){
     var launcher=launcherObject as Dictionary<string,object>;
     Version targetLauncher;if(launcher!=null&&Version.TryParse(Store.Get(launcher,"version"),out targetLauncher)&&targetLauncher.CompareTo(new Version(Store.Version))>0){int code=await backend.Run(Path.Combine(core,"Iniciar-Launcher.ps1"),new[]{"-StatePath",backend.StatePath,"-DoNotLaunch"},Log);if(code!=0)throw new InvalidOperationException("Não foi possível atualizar o launcher.");handoff=true;return;}
    }
    // The worker recovers verified installed graphics or managed sources; no file dialogs.
    Status("Atualizando seu jogo","Esta etapa pode levar alguns minutos. O progresso aparece abaixo.");Find<ProgressBar>("Progress").IsIndeterminate=true;
    int result=await backend.Run(Path.Combine(core,"Aplicar-Mod.ps1"),new[]{"-StatePath",backend.StatePath,"-NoGui","-DoNotLaunch"},Log);
    if(result!=0)throw new InvalidOperationException("A atualização não foi concluída. Consulte Diagnóstico para ver o detalhe; sua instalação anterior foi preservada.");
    state=Store.Read(backend.StatePath);if(!Installed()||Store.Get(state,"mod_version")!=Store.Get(manifest,"mod_version"))throw new InvalidDataException("Não foi possível confirmar a instalação atualizada.");
    Find<ProgressBar>("Progress").Value=100;Status("Atualização concluída","Tudo pronto. Clique em Iniciar jogo para entrar na arena.");
   }catch(Exception ex){Error(ex);}
   finally{if(applicationLock!=null)applicationLock.Dispose();if(core!=null&&Directory.Exists(core)){try{Directory.Delete(core,true);}catch(Exception ex){backend.Log(ex.Message);}}busy=false;Find<ProgressBar>("Progress").IsIndeterminate=false;Refresh();if(handoff){Program.ReleaseInstance();Process.Start(new ProcessStartInfo("wscript.exe",Store.Quote(Path.Combine(backend.Root,"Launcher","Abrir.vbs"))){UseShellExecute=false,CreateNoWindow=true});Window.Close();}}
  }
  private async Task Play() {
   if(busy)return;
   try{state=Store.Read(backend.StatePath);if(!Installed())throw new FileNotFoundException("Escolha o jogo e o Dolphin em Configurações.");busy=true;Refresh();Status("Conferindo seu jogo","Verificando a instalação antes de iniciar…");Find<ProgressBar>("Progress").IsIndeterminate=true;if(!await ImageValid())throw new InvalidDataException("A imagem instalada não corresponde à versão verificada. Clique em Atualizar para reparar.");if(DolphinRunning())throw new InvalidOperationException("O Dolphin já está aberto. Feche-o antes de iniciar outra partida pelo launcher.");Process.Start(new ProcessStartInfo(Store.Get(state,"dolphin_path"),"-e "+Store.Quote(Store.Get(state,"modified_image"))){UseShellExecute=false,CreateNoWindow=true,WorkingDirectory=Path.GetDirectoryName(Store.Get(state,"dolphin_path"))});Status("Jogo iniciado","Boa batalha! O launcher pode permanecer aberto.");}catch(Exception ex){Error(ex);}finally{busy=false;Find<ProgressBar>("Progress").IsIndeterminate=false;Refresh();}
  }
 }
}
