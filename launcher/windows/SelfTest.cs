using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text;

namespace PbrLauncher {
 internal static class SelfTest {
  private static void Assert(bool value,string label){if(!value)throw new InvalidOperationException(label);}
  private static void Reject(Action action,string label){bool rejected=false;try{action();}catch(InvalidDataException){rejected=true;}Assert(rejected,label);}
  internal static int Run(string[] args){
   string report=Program.Value(args,"--self-test")??"launcher-tests.json";string root=Path.Combine(Path.GetTempPath(),"pbr-launcher-test-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(root);var checks=new List<string>();
   try{
    var state=new Dictionary<string,object>{{"original_image",@"D:\Jogos\Original.rvz"},{"modified_image",@"D:\Jogos\Meu jogo.rvz"},{"image_sha256",new string('a',64)},{"mod_version","v0.14.0-charizard-y-test.2"},{"snivy_source",@"D:\Modelos\Tsutarja.brres"},{"custom_user_field","preserved"}};
    string path=Path.Combine(root,"estado.json");Store.Write(path,state);var read=Store.Read(path);read["dolphin_path"]=@"D:\Dolphin\Dolphin.exe";Store.Write(path,read);Assert(Store.Get(Store.Read(path),"image_sha256")==new string('a',64)&&Store.Get(Store.Read(path),"custom_user_field")=="preserved","Legacy state merge");checks.Add("legacy state preserved with atomic writes and backup");
    var feed=new Dictionary<string,object>{{"schema",1},{"version","v0.15.0-launcher-test.1"},{"package_sha256",new string('a',64)},{"package_url","https://raw.githubusercontent.com/CustoByte/pbr-duplas/v0.15.0-launcher-test.1/expansion/packages/launcher-test1/aplicador-core.zip"}};Store.ValidateFeed(feed);
    foreach(string url in new[]{"https://example.com/aplicador-core.zip","http://github.com/CustoByte/pbr-duplas/releases/download/v1/aplicador-core.zip","https://github.com/other/repo/releases/download/v1/aplicador-core.zip","https://raw.githubusercontent.com/CustoByte/pbr-duplas/main/expansion/packages/x/aplicador-core.zip","https://github.com/CustoByte/pbr-duplas/releases/download/v1/aplicador-core.zip?x=1"})Reject(()=>Store.ValidateUrl(url),"URL rejected: "+url);checks.Add("trusted immutable repository URLs only");
    foreach(string name in new[]{"../escape.txt","/absolute.txt","C:/escape.txt"}){string zip=Path.Combine(root,Guid.NewGuid()+".zip");using(var z=ZipFile.Open(zip,ZipArchiveMode.Create)){using(var w=new StreamWriter(z.CreateEntry(name).Open()))w.Write("owned fixture");}Reject(()=>Store.Extract(zip,Path.Combine(root,"invalid")),"Zip traversal rejected");}
    Assert(!File.Exists(Path.Combine(root,"escape.txt")),"No escaped file");checks.Add("ZIP traversal rejected before extraction");
    string good=Path.Combine(root,"good.zip");using(var z=ZipFile.Open(good,ZipArchiveMode.Create)){foreach(string name in new[]{"Aplicar-Mod.ps1","manifesto.json"})using(var w=new StreamWriter(z.CreateEntry(name).Open()))w.Write(name.EndsWith("json")?"{}":"exit 0");}
    string hash=Store.Hash(good);feed["package_sha256"]=hash;var backend=new Backend(root);Directory.CreateDirectory(Path.Combine(root,"cache"));File.Copy(good,Path.Combine(root,"cache",hash+".zip"));string first=backend.Prepare(feed,(a,b)=>{}).GetAwaiter().GetResult();string second=backend.Prepare(feed,(a,b)=>{}).GetAwaiter().GetResult();Assert(first!=second&&File.Exists(Path.Combine(first,"Aplicar-Mod.ps1")),"Fresh extraction from verified cached ZIP");checks.Add("hash-verified offline package reuse with fresh extraction");
    Store.Write(Path.Combine(root,"Launcher","last-feed.json"),feed);Assert(Store.Get(backend.OfflineFeed(),"package_sha256")==hash,"Offline cached feed");checks.Add("offline feed fallback");
    string fixture=Path.Combine(root,"worker com espaço.ps1");File.WriteAllText(fixture,"param([string]$Message)\n[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)\nAdd-Type 'using System;using System.Runtime.InteropServices;public static class Visibility { [DllImport(\"kernel32.dll\")] public static extern IntPtr GetConsoleWindow(); [DllImport(\"user32.dll\")] public static extern bool IsWindowVisible(IntPtr h); }'\nif ([Visibility]::IsWindowVisible([Visibility]::GetConsoleWindow())) { exit 99 }\nWrite-Output $Message\nexit 23\n",new UTF8Encoding(true));
    string message="ação d'água e $() com espaços e fim\\";var lines=new List<string>();int code=backend.Run(fixture,new[]{"-Message",message},line=>{lock(lines)lines.Add(line);}).GetAwaiter().GetResult();Assert(code==23&&lines.Contains(message),"Hidden worker, Unicode quoting, literal dollar/apostrophe, exit code");checks.Add("PowerShell worker hidden; Unicode paths/literal arguments; exit/error propagation");
    Store.Write(Path.GetFullPath(report),new{passed=true,checks=checks,gameplay_tested=false});return 0;
   }catch(Exception ex){Store.Write(Path.GetFullPath(report),new{passed=false,checks=checks,error=ex.ToString()});return 1;}
   finally{try{Directory.Delete(root,true);}catch{}}
  }
 }
}
