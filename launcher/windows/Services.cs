using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Web.Script.Serialization;

namespace PbrLauncher {
 internal static class Store {
  internal const string Version = "1.0.0";
  internal const string Feed = "https://raw.githubusercontent.com/CustoByte/pbr-duplas/feat/full493-waterfall/expansion/update-test.json";
  internal static JavaScriptSerializer Json() { return new JavaScriptSerializer { MaxJsonLength = 8 * 1024 * 1024 }; }
  internal static Dictionary<string, object> Read(string path) { return File.Exists(path) ? Json().Deserialize<Dictionary<string, object>>(File.ReadAllText(path, Encoding.UTF8)) : new Dictionary<string, object>(); }
  internal static string Get(IDictionary<string, object> data, string key) { object value; return data.TryGetValue(key, out value) && value != null ? Convert.ToString(value) : ""; }
  internal static void Write(string path, object value) {
   Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path)));
   string temp = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
   try { File.WriteAllText(temp, Json().Serialize(value), new UTF8Encoding(false)); if (File.Exists(path)) File.Replace(temp, path, path + ".backup"); else File.Move(temp, path); }
   finally { if (File.Exists(temp)) File.Delete(temp); }
  }
  internal static string Hash(string path) { using (var file = File.OpenRead(path)) using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(file)).Replace("-", "").ToLowerInvariant(); }
  internal static void ValidateFeed(Dictionary<string, object> feed) {
   if (Get(feed,"schema") != "1" || !Regex.IsMatch(Get(feed,"version"), @"^v[A-Za-z0-9._-]{1,95}$") || !Regex.IsMatch(Get(feed,"package_sha256"), @"^[a-f0-9]{64}$")) throw new InvalidDataException("Resposta de atualização incompatível.");
   ValidateUrl(Get(feed,"package_url"));
  }
  internal static void ValidateUrl(string source) {
   Uri uri; if (!Uri.TryCreate(source, UriKind.Absolute, out uri) || uri.Scheme != "https" || uri.Port != 443 || uri.UserInfo != "" || uri.Query != "" || uri.Fragment != "") throw new InvalidDataException("Endereço de atualização inválido.");
   bool raw = uri.Host == "raw.githubusercontent.com" && Regex.IsMatch(uri.AbsolutePath,@"^/CustoByte/pbr-duplas/(v[A-Za-z0-9._-]+|[a-f0-9]{40})/expansion/packages/[A-Za-z0-9._-]+/aplicador-core\.zip$");
   bool release = uri.Host == "github.com" && Regex.IsMatch(uri.AbsolutePath,@"^/CustoByte/pbr-duplas/releases/download/v[A-Za-z0-9._-]+/aplicador-core\.zip$");
   if (!raw && !release) throw new InvalidDataException("Pacote fora do repositório autorizado.");
  }
  internal static string Quote(string value) {
   var output = new StringBuilder("\""); int slashes = 0;
   foreach (char c in value) { if (c == '\\') { slashes++; continue; } if (c == '"') { output.Append('\\', slashes * 2 + 1); output.Append('"'); } else { output.Append('\\', slashes); output.Append(c); } slashes = 0; }
   output.Append('\\', slashes * 2); output.Append('"'); return output.ToString();
  }
  internal static void Extract(string zip, string destination) {
   string prefix = Path.GetFullPath(destination).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
   var names = new HashSet<string>(StringComparer.OrdinalIgnoreCase); long total = 0;
   using (var archive = ZipFile.OpenRead(zip)) {
    if (archive.Entries.Count > 2000) throw new InvalidDataException("Pacote com entradas demais.");
    foreach (var entry in archive.Entries) {
     string name = entry.FullName.Replace('\\','/'); total += entry.Length;
     if (name == "" || name.StartsWith("/") || name.Contains(":") || name.Split('/').Contains("..") || entry.Length > 100 * 1024 * 1024 || total > 250L * 1024 * 1024 || ((entry.ExternalAttributes >> 16) & 0xF000) == 0xA000) throw new InvalidDataException("Caminho ou tamanho inválido no pacote.");
     string target = Path.GetFullPath(Path.Combine(destination, name));
     if (!target.StartsWith(prefix, StringComparison.OrdinalIgnoreCase) || !names.Add(target)) throw new InvalidDataException("Caminho repetido ou fora do pacote.");
    }
    Directory.CreateDirectory(destination);
    foreach (var entry in archive.Entries) { string target = Path.Combine(destination, entry.FullName.Replace('/',Path.DirectorySeparatorChar)); if (entry.FullName.EndsWith("/")) Directory.CreateDirectory(target); else { Directory.CreateDirectory(Path.GetDirectoryName(target)); entry.ExtractToFile(target); } }
   }
  }
 }
 internal sealed class Backend {
  internal readonly string Root;
  internal string StatePath { get { return Path.Combine(Root,"estado.json"); } }
  internal string LogPath { get { return Path.Combine(Root,"Launcher","launcher.log"); } }
  internal Backend(string root) { Root = Path.GetFullPath(root); Directory.CreateDirectory(Path.Combine(Root,"Launcher")); }
  internal void Log(string text) { lock(this) File.AppendAllText(LogPath, DateTime.Now.ToString("s") + " " + text + Environment.NewLine, Encoding.UTF8); }
  private static async Task<T> Deadline<T>(WebClient client, Task<T> task, int milliseconds) {
   if (await Task.WhenAny(task, Task.Delay(milliseconds)) != task) { client.CancelAsync(); throw new TimeoutException("O GitHub demorou a responder. Sua instalação continua disponível."); } return await task;
  }
  internal async Task<Dictionary<string,object>> Check() {
   ServicePointManager.SecurityProtocol |= SecurityProtocolType.Tls12;
   using (var client = new TimedClient()) { var text = await Deadline(client, client.DownloadStringTaskAsync(Store.Feed), 25000); var feed = Store.Json().Deserialize<Dictionary<string,object>>(text); Store.ValidateFeed(feed); Store.Write(Path.Combine(Root,"Launcher","last-feed.json"),feed); return feed; }
  }
  internal Dictionary<string,object> OfflineFeed() {
   foreach (string path in new [] { Path.Combine(Root,"Launcher","last-feed.json"),Path.Combine(Root,"ultima-versao.json") }) { try { var value = Store.Read(path); Store.ValidateFeed(value); return value; } catch {} }
   return null;
  }
  internal async Task<string> Prepare(Dictionary<string,object> feed, Action<string,double> progress) {
   Store.ValidateFeed(feed); string hash = Store.Get(feed,"package_sha256"), cache = Path.Combine(Root,"cache"); Directory.CreateDirectory(cache);
   string package = Path.Combine(cache, hash + ".zip");
   if (!File.Exists(package) || await Task.Run(() => Store.Hash(package)) != hash) {
    string partial = package + "." + Guid.NewGuid().ToString("N") + ".tmp";
    try {
     using (var client = new TimedClient()) { client.DownloadProgressChanged += (s,e) => progress("Baixando atualização…", e.ProgressPercentage); var download=client.DownloadFileTaskAsync(new Uri(Store.Get(feed,"package_url")),partial);if(await Task.WhenAny(download,Task.Delay(240000))!=download){client.CancelAsync();throw new TimeoutException("O download demorou demais. Tente atualizar novamente.");}await download; }
     if (await Task.Run(() => Store.Hash(partial)) != hash) throw new InvalidDataException("O download não passou na verificação de integridade.");
     if (File.Exists(package)) File.Delete(package); File.Move(partial,package);
    } finally { if (File.Exists(partial)) File.Delete(partial); }
   }
   // Every run extracts the hash-checked ZIP into a fresh folder, never executes
   // scripts from an unverified leftover directory. Files stay owned by this user.
   string core = Path.Combine(cache,"launcher-run-" + Guid.NewGuid().ToString("N"));
   try { await Task.Run(() => Store.Extract(package,core)); if (!File.Exists(Path.Combine(core,"Aplicar-Mod.ps1")) || !File.Exists(Path.Combine(core,"manifesto.json"))) throw new InvalidDataException("Atualização incompleta."); return core; }
   catch { if (Directory.Exists(core)) Directory.Delete(core,true); throw; }
  }
  internal async Task<int> Run(string script, string[] arguments, Action<string> output) {
   var info = new ProcessStartInfo { FileName = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System),@"WindowsPowerShell\v1.0\powershell.exe"), Arguments = "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File " + Store.Quote(script) + " " + String.Join(" ", arguments.Select(Store.Quote)), UseShellExecute = false, CreateNoWindow = true, WindowStyle = ProcessWindowStyle.Hidden, RedirectStandardOutput = true, RedirectStandardError = true, StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8 };
   info.EnvironmentVariables["PBR_LAUNCHER_WORKER"] = "1";
   using (var process = new Process { StartInfo = info }) {
    process.OutputDataReceived += (s,e) => { if (e.Data != null) { Log(e.Data); output(e.Data); } };
    process.ErrorDataReceived += (s,e) => { if (e.Data != null) { Log(e.Data); output(e.Data); } };
    process.Start(); process.BeginOutputReadLine(); process.BeginErrorReadLine(); await Task.Run(() => process.WaitForExit()); return process.ExitCode;
   }
  }
  private sealed class TimedClient : WebClient {
   protected override WebRequest GetWebRequest(Uri address) { var request = base.GetWebRequest(address); request.Timeout = 45000; var http = request as HttpWebRequest; if (http != null) http.ReadWriteTimeout = 45000; return request; }
  }
 }
}
