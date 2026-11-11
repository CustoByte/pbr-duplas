# Stable bootstrap. All game-changing/application logic comes from versioned core.
[CmdletBinding()]
param(
    [string]$ImagePath, [string]$ToolPath, [string]$DolphinPath, [string]$OutputPath,
    [string]$DataRoot, [string]$FeedUrl = 'https://github.com/CustoByte/pbr-duplas/releases/latest/download/update.json',
    [switch]$NoGui, [switch]$DoNotLaunch
)
$ErrorActionPreference = 'Stop'
$runtime = (Get-Process -Id $PID).Path
$runDirectory = $null
$lock = $null

function Download([string]$Source, [string]$Target, [int]$Timeout) {
    if ($Source.StartsWith('https://')) {
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $Source -OutFile $Target -UseBasicParsing -TimeoutSec $Timeout
    } elseif ($NoGui -and (Test-Path -LiteralPath $Source -PathType Leaf)) {
        # Explicit local feed path is available for offline workflow verification.
        Copy-Item -LiteralPath $Source -Destination $Target
    } else { throw 'Endereco de atualizacao invalido; HTTPS obrigatorio.' }
}
function FileHash([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Validate-Zip([string]$Path, [string]$Destination) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead($Path)
    try {
        $prefix = [IO.Path]::GetFullPath($Destination).TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
        foreach ($entry in $zip.Entries) {
            $name = $entry.FullName.Replace('\','/')
            if ($name -match '(^/|(^|/)\.\.(/|$)|:)' -or $entry.Length -gt 104857600) { throw 'Caminho/tamanho inesperado no pacote.' }
            $candidate = [IO.Path]::GetFullPath((Join-Path $Destination $name))
            if (-not $candidate.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Pacote tenta sair da pasta temporaria.' }
        }
    } finally { $zip.Dispose() }
}
try {
    if (-not $DataRoot) { $DataRoot = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'PBR-Duplas' }
    $DataRoot = [IO.Path]::GetFullPath($DataRoot)
    New-Item -ItemType Directory -Path $DataRoot -Force | Out-Null
    try {
        $lock = [IO.File]::Open((Join-Path $DataRoot 'aplicador.lock'), [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    } catch { throw 'Outra instancia do aplicador ja esta em execucao.' }
    $cache = Join-Path $DataRoot 'cache'
    New-Item -ItemType Directory -Path $cache -Force | Out-Null
    $lastPath = Join-Path $DataRoot 'ultima-versao.json'
    $feedTemporary = Join-Path $cache ('feed-' + [Guid]::NewGuid().ToString('N') + '.json')
    $package = $null
    try {
        Write-Host 'Consultando atualizacoes no GitHub...'
        Download $FeedUrl $feedTemporary 25
        $feed = Get-Content -LiteralPath $feedTemporary -Raw | ConvertFrom-Json
        if ($feed.schema -ne 1 -or $feed.package_sha256 -notmatch '^[a-f0-9]{64}$') { throw 'Manifesto de atualizacao incompativel.' }
        $url = [string]$feed.package_url
        if ($url.StartsWith('https://')) {
            $uri = [Uri]$url
            if ($uri.Host -ne 'github.com' -or -not $uri.AbsolutePath.StartsWith('/CustoByte/pbr-duplas/releases/download/')) {
                throw 'Pacote fora do repositorio autorizado.'
            }
        } elseif (-not $NoGui) { throw 'Endereco de pacote invalido.' }
        $package = Join-Path $cache ($feed.package_sha256 + '.zip')
        if (-not (Test-Path -LiteralPath $package) -or (FileHash $package) -ne $feed.package_sha256) {
            Write-Host "Baixando pacote $($feed.version)..."
            $partial = $package + '.' + [Guid]::NewGuid().ToString('N') + '.tmp'
            try {
                Download $url $partial 240
                if ((FileHash $partial) -ne $feed.package_sha256) { throw 'Download corrompido: hash diferente do publicado.' }
                Move-Item -LiteralPath $partial -Destination $package -Force
            } finally { if (Test-Path -LiteralPath $partial) { Remove-Item -LiteralPath $partial -Force } }
        } else { Write-Host "Pacote $($feed.version) ja esta no cache." }
        $feed | ConvertTo-Json | Set-Content -LiteralPath $lastPath -Encoding UTF8
    } catch {
        Write-Host "Nao foi possivel consultar/baixar a versao nova: $($_.Exception.Message)"
        $package = $null
        if (Test-Path -LiteralPath $lastPath) {
            $old = Get-Content -LiteralPath $lastPath -Raw | ConvertFrom-Json
            if ($old.package_sha256 -match '^[a-f0-9]{64}$') {
                $candidate = Join-Path $cache ($old.package_sha256 + '.zip')
                if ((Test-Path -LiteralPath $candidate) -and (FileHash $candidate) -eq $old.package_sha256) {
                    $package = $candidate
                }
            }
        }
        if (-not $package) {
            $base = Join-Path $PSScriptRoot 'base.zip'
            $baseHash = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'base.sha256') -Raw).Trim()
            if ((FileHash $base) -ne $baseHash) { throw 'Pacote inicial danificado.' }
            $package = $base
        }
        Write-Host 'Usando a ultima versao disponivel localmente.'
    } finally {
        if (Test-Path -LiteralPath $feedTemporary) { Remove-Item -LiteralPath $feedTemporary -Force }
    }
    $runDirectory = Join-Path $cache ('execucao-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $runDirectory | Out-Null
    Validate-Zip $package $runDirectory
    [IO.Compression.ZipFile]::ExtractToDirectory($package, $runDirectory)
    $core = Join-Path $runDirectory 'Aplicar-Mod.ps1'
    if (-not (Test-Path -LiteralPath $core -PathType Leaf)) { throw 'Pacote sem aplicador.' }
    if (-not $ToolPath) {
        foreach ($candidate in @((Join-Path $PSScriptRoot 'DolphinTool.exe'), (Join-Path $PSScriptRoot 'Dolphin/DolphinTool.exe'), (Join-Path (Split-Path $PSScriptRoot -Parent) 'DolphinTool.exe'))) {
            if (Test-Path -LiteralPath $candidate -PathType Leaf) { $ToolPath = $candidate; break }
        }
    }
    $parameters = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $core, '-StatePath', (Join-Path $DataRoot 'estado.json'))
    foreach ($item in @(@('-ImagePath',$ImagePath), @('-ToolPath',$ToolPath), @('-DolphinPath',$DolphinPath), @('-OutputPath',$OutputPath))) {
        if ($item[1]) { $parameters += $item }
    }
    if ($NoGui) { $parameters += '-NoGui' }
    if ($DoNotLaunch) { $parameters += '-DoNotLaunch' }
    & $runtime @parameters
    $resultCode = $LASTEXITCODE
    exit $resultCode
} catch {
    Write-Host "ERRO DO ATUALIZADOR: $($_.Exception.Message)" -ForegroundColor Red
    if (-not $NoGui) {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show($_.Exception.Message, 'PBR Duplas') | Out-Null
    }
    exit 1
} finally {
    if ($runDirectory -and (Test-Path -LiteralPath $runDirectory)) { Remove-Item -LiteralPath $runDirectory -Recurse -Force }
    if ($lock) { $lock.Dispose() }
}
