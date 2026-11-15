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

& (Join-Path $framework 'csc.exe') /nologo /codepage:65001 /target:winexe /platform:anycpu /optimize+ /warnaserror+ `
    ('/out:' + (Join-Path $Output 'PBR Duplas.exe')) ('/win32manifest:' + (Join-Path $PSScriptRoot 'app.manifest')) `
    ('/win32icon:' + (Join-Path $PSScriptRoot 'app.ico')) @references (Join-Path $PSScriptRoot 'Services.cs') (Join-Path $PSScriptRoot 'Bootstrap.cs')
if ($LASTEXITCODE -ne 0) { throw 'Falha ao compilar a entrada do launcher.' }
$sources = [ordered]@{}
Get-ChildItem -LiteralPath $PSScriptRoot -File | Where-Object { $_.Extension -in @('.cs','.xaml','.manifest','.ico','.ps1') } | ForEach-Object { $sources[$_.Name] = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
$installerSources = [ordered]@{}
foreach ($name in @('Aplicar-Mod.ps1','Iniciar-Launcher.ps1','Recuperar-Graficos.ps1')) { $installerSources[$name] = (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot ('../../expansion/' + $name)) -Algorithm SHA256).Hash.ToLowerInvariant() }
[ordered]@{ bootstrap_sha256=(Get-FileHash -LiteralPath (Join-Path $Output 'PBR Duplas.exe') -Algorithm SHA256).Hash.ToLowerInvariant(); installer_sources=$installerSources; launcher_version='1.0.0'; executable_sha256=(Get-FileHash -LiteralPath (Join-Path $Output 'PBR Launcher.exe') -Algorithm SHA256).Hash.ToLowerInvariant(); sources=$sources } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $Output 'build.json') -Encoding UTF8
