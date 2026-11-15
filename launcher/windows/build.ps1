param([string]$Output = "$PSScriptRoot/out")
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Path $Output -Force | Out-Null
$framework = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319'
$wpf = Join-Path $framework 'WPF'
$references = @('System.dll','System.Core.dll','System.Web.Extensions.dll','System.IO.Compression.dll','System.IO.Compression.FileSystem.dll','System.Xaml.dll') | ForEach-Object { '/reference:' + (Join-Path $framework $_) }
$references += @('PresentationCore.dll','PresentationFramework.dll','WindowsBase.dll') | ForEach-Object { '/reference:' + (Join-Path $wpf $_) }
& (Join-Path $framework 'csc.exe') /nologo /codepage:65001 /target:winexe /platform:anycpu /optimize+ /warnaserror+ `
    ('/out:' + (Join-Path $Output 'PBR Launcher.exe')) ('/win32manifest:' + (Join-Path $PSScriptRoot 'app.manifest')) `
    ('/win32icon:' + (Join-Path $PSScriptRoot 'app.ico')) ('/resource:' + (Join-Path $PSScriptRoot 'MainWindow.xaml') + ',MainWindow.xaml') `
    @references (Join-Path $PSScriptRoot 'Services.cs') (Join-Path $PSScriptRoot 'App.cs') (Join-Path $PSScriptRoot 'SelfTest.cs')
if ($LASTEXITCODE -ne 0) { throw 'Falha ao compilar o launcher.' }
