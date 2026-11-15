[CmdletBinding()]
param([string]$StatePath, [switch]$DoNotLaunch)
$ErrorActionPreference = 'Stop'
if (-not $StatePath) { $StatePath = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'PBR-Duplas/estado.json' }
$dataRoot = Split-Path ([IO.Path]::GetFullPath($StatePath)) -Parent
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'manifesto.json') -Raw | ConvertFrom-Json
$version = [string]$manifest.launcher.version
$expected = [string]$manifest.launcher.sha256
if ($version -notmatch '^\d+\.\d+\.\d+$' -or $expected -notmatch '^[a-f0-9]{64}$') { throw 'Identidade do launcher invalida.' }
$source = Join-Path $PSScriptRoot 'launcher/PBR Launcher.exe'
if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw 'O launcher nao passou na verificacao de integridade.' }
$launcherRoot = Join-Path $dataRoot 'Launcher'
$versionRoot = Join-Path $launcherRoot ('versions/' + $version + '-' + $expected.Substring(0,12))
New-Item -ItemType Directory -Path $versionRoot -Force | Out-Null
$target = Join-Path $versionRoot 'PBR Launcher.exe'
if (-not (Test-Path -LiteralPath $target) -or (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { Copy-Item -LiteralPath $source -Destination $target -Force }
# Keep the entry point stable while executable versions remain side by side.
$command = '"' + $target + '" --data-root "' + $dataRoot + '"'
$vbs = 'CreateObject("WScript.Shell").Run "' + $command.Replace('"','""') + '", 1, False'
$entry = Join-Path $launcherRoot 'Abrir.vbs'
[IO.File]::WriteAllText($entry + '.tmp', $vbs, [Text.Encoding]::Unicode)
Move-Item -LiteralPath ($entry + '.tmp') -Destination $entry -Force
$shell = New-Object -ComObject WScript.Shell
foreach ($folder in @([Environment]::GetFolderPath('DesktopDirectory'), (Join-Path ([Environment]::GetFolderPath('Programs')) 'PBR Duplas'))) {
    if (-not $folder) { continue }
    New-Item -ItemType Directory -Path $folder -Force | Out-Null
    $shortcut = $shell.CreateShortcut((Join-Path $folder 'PBR Duplas.lnk'))
    $shortcut.TargetPath = Join-Path ([Environment]::GetFolderPath('System')) 'wscript.exe'
    $shortcut.Arguments = '"' + $entry + '"'
    $shortcut.IconLocation = $target + ',0'
    $shortcut.WorkingDirectory = $launcherRoot
    $shortcut.Description = 'Atualizar e jogar PBR Duplas'
    $shortcut.Save()
}
[ordered]@{ version=$version; executable=$target; sha256=$expected } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $launcherRoot 'installed.json') -Encoding UTF8
if (-not $DoNotLaunch) {
    # The first migration starts inside the legacy CMD. Hide its shared console
    # after the GUI is installed; future starts use the shortcut and WinExe.
    try {
        Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class PbrConsole { [DllImport("kernel32.dll")] public static extern IntPtr GetConsoleWindow(); [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n); }'
        $console = [PbrConsole]::GetConsoleWindow()
        if ($console -ne [IntPtr]::Zero) { [void][PbrConsole]::ShowWindow($console,0) }
    } catch { }
    Start-Process -FilePath $target -WorkingDirectory $versionRoot -ArgumentList @('--data-root', ('"' + $dataRoot + '"')) | Out-Null
}
