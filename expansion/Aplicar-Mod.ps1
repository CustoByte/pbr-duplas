# Windows PowerShell 5.1+. No Python, administrator rights or game downloads.
[CmdletBinding()]
param(
    [string]$ImagePath,
    [string]$ToolPath,
    [string]$OutputPath,
    [string]$DolphinPath,
    [string]$StatePath,
    [switch]$DoNotLaunch,
    [switch]$NoGui
)
$ErrorActionPreference = 'Stop'
$PackageRoot = $PSScriptRoot
if (Test-Path -LiteralPath (Join-Path $PackageRoot 'Aplicar-Delta.ps1')) { . (Join-Path $PackageRoot 'Aplicar-Delta.ps1') }
$JobRoot = $null
$FailureLog = $null
$Events = New-Object 'System.Collections.Generic.List[string]'

function Note([string]$Text) {
    $Events.Add((Get-Date -Format 's') + ' ' + $Text)
    Write-Host $Text
}
function Hash([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Choose-Open([string]$Title, [string]$Filter) {
    if ($NoGui) { throw "Caminho obrigatorio ausente: $Title" }
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    try {
        $dialog.Title = $Title
        $dialog.Filter = $Filter
        if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { throw 'Operacao cancelada.' }
        return $dialog.FileName
    } finally { $dialog.Dispose() }
}
function Choose-RomFolder {
    if ($NoGui) { throw 'Informe -ImagePath com a imagem ou sua pasta.' }
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    try {
        $dialog.Description = 'Escolha a pasta que contem a ISO ou RVZ original do Pokemon Battle Revolution'
        $dialog.ShowNewFolderButton = $false
        if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { throw 'Operacao cancelada.' }
        return $dialog.SelectedPath
    } finally { $dialog.Dispose() }
}
function Full-Existing([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Arquivo nao encontrado: $Path" }
    return (Get-Item -LiteralPath $Path).FullName
}
function Run-Tool([string[]]$Arguments) {
    # Windows paths cannot contain double quotes. Quote each argument, preserving
    # spaces and shell metacharacters without passing through cmd.exe.
    $quoted = @($Arguments | ForEach-Object {
        if ($_.Contains('"') -or $_.EndsWith('\')) { throw 'Argumento de caminho invalido.' }
        '"' + $_ + '"'
    })
    $process = Start-Process -FilePath $ToolPath -ArgumentList $quoted -NoNewWindow -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        throw "DolphinTool falhou (codigo $($process.ExitCode)). Use uma versao recente do Dolphin."
    }
}
function Find-Partition([string]$Root) {
    $dolCandidates = @(Get-ChildItem -LiteralPath $Root -Filter 'main.dol' -Recurse -File |
        Where-Object { $_.Directory.Name -eq 'sys' })
    if ($dolCandidates.Count -ne 1) { throw 'Extracao incompleta ou particao de dados ambigua.' }
    return $dolCandidates[0].Directory.Parent.FullName
}
function Inventory([string]$Root) {
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) { throw 'Pasta files ausente na extracao.' }
    $prefix = $Root.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    $result = @{}
    foreach ($file in Get-ChildItem -LiteralPath $Root -Recurse -File) {
        if (($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Link inesperado na extracao.' }
        $relative = $file.FullName.Substring($prefix.Length).Replace('\', '/')
        $result[$relative] = @{ size = $file.Length; sha256 = (Hash $file.FullName) }
    }
    return $result
}
function Check-Identity([string]$Root) {
    $boot = [IO.File]::ReadAllBytes((Join-Path $Root 'sys/boot.bin'))
    if ($boot.Length -ne 1088 -or [Text.Encoding]::ASCII.GetString($boot, 0, 6) -ne 'RPBE01' -or
        $boot[6] -ne 0 -or $boot[7] -ne 0 -or
        [BitConverter]::ToString($boot[24..27]) -ne '5D-1C-9E-A3') {
        throw 'Versao incompativel. Necessario USA RPBE01, revisao 0.'
    }
}
function Check-Original([string]$Root, $Manifest) {
    Check-Identity $Root
    foreach ($property in $Manifest.original_sha256.PSObject.Properties) {
        if ((Hash (Join-Path $Root $property.Name)) -ne $property.Value) {
            throw "Original diferente da versao suportada: $($property.Name). A imagem pode estar modificada."
        }
    }
    Note 'Conferindo todos os arquivos extraidos...'
    $actual = Inventory (Join-Path $Root 'files')
    if ($actual.Count -ne $Manifest.game_files.Count) { throw 'Quantidade de arquivos extraidos incorreta.' }
    foreach ($entry in $Manifest.game_files) {
        if (-not $actual.ContainsKey($entry.path) -or $actual[$entry.path].size -ne $entry.size) {
            throw "Extracao incompleta ou arquivo inesperado: $($entry.path)"
        }
    }
    return $actual
}

try {
    Note 'PBR DUPLAS - APLICADOR AUTOATUALIZAVEL EXPERIMENTAL'
    $savedState = $null
    if ($StatePath -and (Test-Path -LiteralPath $StatePath -PathType Leaf)) {
        $savedState = Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
        if (-not $ImagePath) { $ImagePath = $savedState.original_image }
        if (-not $ToolPath -and (Test-Path -LiteralPath $savedState.tool_path -PathType Leaf)) { $ToolPath = $savedState.tool_path }
        if ($savedState.dolphin_path -and -not $DolphinPath -and (Test-Path -LiteralPath $savedState.dolphin_path -PathType Leaf)) { $DolphinPath = $savedState.dolphin_path }
        if (-not $OutputPath) { $OutputPath = $savedState.modified_image }
    }
    Note 'A imagem original sera somente lida. Nenhum save sera modificado.'
    $manifest = Get-Content -LiteralPath (Join-Path $PackageRoot 'manifesto.json') -Raw | ConvertFrom-Json
    foreach ($entry in $manifest.replacements) {
        if ($entry.package_path -match '(^[\/]|(^|[\/])\.\.([\/]|$)|:)' -or
            $entry.installed_path -notmatch '^(sys/main\.dol|files/.+)$' -or
            $entry.installed_path -match '(^|[\/])\.\.([\/]|$)|:') {
            throw 'Caminho de modificacao fora das pastas permitidas.'
        }
        $packageHash = if ($entry.patch_sha256) { $entry.patch_sha256 } else { $entry.sha256 }
        if ((Hash (Join-Path $PackageRoot $entry.package_path)) -ne $packageHash) {
            throw "Pacote danificado: $($entry.package_path). Extraia o ZIP novamente."
        }
    }
    if (-not $ImagePath) {
        $ImagePath = Choose-RomFolder
    }
    if (Test-Path -LiteralPath $ImagePath -PathType Container) {
        $images = @(Get-ChildItem -LiteralPath $ImagePath -File | Where-Object {
            $_.Extension.ToLowerInvariant() -in @('.iso', '.rvz', '.wia', '.gcz') -and $_.BaseName -notmatch '-Duplas'
        })
        if ($images.Count -eq 0) { throw 'Nenhuma ISO/RVZ original encontrada nessa pasta.' }
        if ($images.Count -eq 1) { $ImagePath = $images[0].FullName }
        else { $ImagePath = Choose-Open 'Ha varias imagens nessa pasta. Escolha Pokemon Battle Revolution' 'Jogos Wii|*.iso;*.rvz;*.wia;*.gcz' }
    }
    $ImagePath = Full-Existing $ImagePath
    if (-not $ToolPath) {
        foreach ($candidate in @((Join-Path $PackageRoot 'DolphinTool.exe'), (Join-Path $PackageRoot 'Dolphin/DolphinTool.exe'), (Join-Path (Split-Path $PackageRoot -Parent) 'DolphinTool.exe'))) {
            if (Test-Path -LiteralPath $candidate -PathType Leaf) { $ToolPath = $candidate; break }
        }
    }
    if (-not $ToolPath) {
        $DolphinPath = Choose-Open 'Escolha Dolphin.exe na pasta do Dolphin recente' 'Dolphin|Dolphin.exe'
        $ToolPath = Join-Path ([IO.Path]::GetDirectoryName($DolphinPath)) 'DolphinTool.exe'
    }
    $ToolPath = Full-Existing $ToolPath
    if (-not $DoNotLaunch) {
        if (-not $DolphinPath) { $DolphinPath = Join-Path ([IO.Path]::GetDirectoryName($ToolPath)) 'Dolphin.exe' }
        $DolphinPath = Full-Existing $DolphinPath
    }
    if (-not $OutputPath) {
        $OutputPath = Join-Path ([IO.Path]::GetDirectoryName($ImagePath)) ([IO.Path]::GetFileNameWithoutExtension($ImagePath) + '-Duplas.rvz')
        if ((Test-Path -LiteralPath $OutputPath) -or (Test-Path -LiteralPath ($OutputPath + '.relatorio.json'))) {
            $suffix = '-' + [DateTime]::Now.ToString('yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,6)
            $OutputPath = Join-Path ([IO.Path]::GetDirectoryName($ImagePath)) ([IO.Path]::GetFileNameWithoutExtension($ImagePath) + '-Duplas' + $suffix + '.rvz')
        }
    }
    $OutputPath = [IO.Path]::GetFullPath($OutputPath)
    if ([IO.Path]::GetExtension($OutputPath) -ne '.rvz') { throw 'O destino precisa terminar em .rvz.' }
    if ($OutputPath -eq $ImagePath) { throw 'O destino precisa ser diferente da imagem original.' }
    $reportPath = $OutputPath + '.relatorio.json'
    $manifestHash = Hash (Join-Path $PackageRoot 'manifesto.json')
    $replaceManaged = $false
    if ((Test-Path -LiteralPath $OutputPath) -or (Test-Path -LiteralPath $reportPath)) {
        if ($savedState -and $savedState.modified_image -eq $OutputPath -and
            (Test-Path -LiteralPath $OutputPath -PathType Leaf) -and (Hash $OutputPath) -eq $savedState.image_sha256) {
            if ($savedState.manifest_sha256 -eq $manifestHash) {
                Note 'Esta copia ja esta atualizada. Nao e necessario extrair ou converter novamente.'
                if (-not $DoNotLaunch) {
                    Start-Process -FilePath $DolphinPath -ArgumentList @('-e', ('"' + $OutputPath + '"')) | Out-Null
                }
                exit 0
            }
            $replaceManaged = $true
        } else {
            throw 'O destino ja existe e nao corresponde a copia gerenciada. Nada foi sobrescrito.'
        }
    }
    $parent = [IO.Path]::GetDirectoryName($OutputPath)
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) { throw 'A pasta de destino nao existe.' }
    $drive = New-Object System.IO.DriveInfo([IO.Path]::GetPathRoot($parent))
    $required = [long](($manifest.game_files | Measure-Object -Property size -Sum).Sum * 4 + 536870912)
    if ($drive.IsReady -and $drive.AvailableFreeSpace -lt $required) {
        throw ('Espaco insuficiente. Reserve aproximadamente {0:N1} GB livres na unidade de destino.' -f ($required / 1GB))
    }
    $JobRoot = Join-Path $parent ('.pbr-duplas-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $JobRoot | Out-Null
    $FailureLog = Join-Path $JobRoot 'falha.txt'
    $extracted = Join-Path $JobRoot 'entrada'
    Note '[1/5] Extraindo a particao de dados com o DolphinTool...'
    Run-Tool -Arguments @('extract', '-i', $ImagePath, '-o', $extracted, '--gameonly')
    $partition = Find-Partition $extracted
    Note '[2/5] Conferindo a revisao e os hashes originais...'
    $expectedFiles = Check-Original $partition $manifest
    Note '[3/5] Aplicando as modificacoes na copia temporaria...'
    foreach ($entry in $manifest.replacements) {
        $destination = Join-Path $partition $entry.installed_path
        $destinationParent = Split-Path $destination -Parent
        if (-not (Test-Path -LiteralPath $destinationParent)) { New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null }
        if ($entry.format -eq 'pbr-delta-v1') {
            Apply-PbrDelta $destination (Join-Path $PackageRoot $entry.package_path) $entry.sha256
        } else { Copy-Item -LiteralPath (Join-Path $PackageRoot $entry.package_path) -Destination $destination }
        if ((Hash $destination) -ne $entry.sha256) { throw 'Erro ao copiar o mod.' }
        if ($entry.installed_path.StartsWith('files/')) {
            $relative = $entry.installed_path.Substring(6)
            $expectedFiles[$relative] = @{ size = (Get-Item -LiteralPath $destination).Length; sha256 = $entry.sha256 }
        }
    }
    $built = Join-Path $JobRoot 'resultado.rvz'
    Note '[4/5] Gerando uma nova RVZ com o mod instalado...'
    Run-Tool -Arguments @('convert', '-i', (Join-Path $partition 'sys/main.dol'), '-o', $built,
        '-f', 'rvz', '-b', '131072', '-c', 'zstd', '-l', '5')
    if (-not (Test-Path -LiteralPath $built -PathType Leaf) -or (Get-Item -LiteralPath $built).Length -eq 0) {
        throw 'O DolphinTool nao produziu uma imagem valida.'
    }
    Note '[5/5] Reabrindo a RVZ gerada e conferindo todos os arquivos...'
    $roundtrip = Join-Path $JobRoot 'conferencia'
    Run-Tool -Arguments @('extract', '-i', $built, '-o', $roundtrip, '--gameonly')
    $checked = Find-Partition $roundtrip
    Check-Identity $checked
    $actualFiles = Inventory (Join-Path $checked 'files')
    if ($actualFiles.Count -ne $expectedFiles.Count) { throw 'A imagem gerada perdeu arquivos.' }
    foreach ($name in $expectedFiles.Keys) {
        if (-not $actualFiles.ContainsKey($name) -or $actualFiles[$name].sha256 -ne $expectedFiles[$name].sha256 -or
            $actualFiles[$name].size -ne $expectedFiles[$name].size) { throw "Falha na conferencia da imagem: $name" }
    }
    foreach ($entry in $manifest.replacements) {
        if ($entry.package_path -match '(^[\/]|(^|[\/])\.\.([\/]|$)|:)' -or
            $entry.installed_path -notmatch '^(sys/main\.dol|files/.+)$' -or
            $entry.installed_path -match '(^|[\/])\.\.([\/]|$)|:') {
            throw 'Caminho de modificacao fora das pastas permitidas.'
        }
        if ((Hash (Join-Path $checked $entry.installed_path)) -ne $entry.sha256) {
            throw "Mod ausente ou danificado na imagem final: $($entry.installed_path)"
        }
    }
    $report = [ordered]@{
        status = 'image_built_and_content_verified'; mod_version = $manifest.mod_version
        original_image = $ImagePath; modified_image = $OutputPath; sha256 = (Hash $built)
        checked_game_files = $actualFiles.Count; format = 'rvz'; dolphin_gameplay_tested = $false
        save_tested = $false; coop_included = $false; created_utc = [DateTime]::UtcNow.ToString('o')
    }
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $JobRoot 'relatorio.json') -Encoding UTF8
    # Move-Item without -Force refuses an existing output file.
    if ($replaceManaged) {
        [IO.File]::Replace($built, $OutputPath, ($OutputPath + '.anterior.rvz'))
    } else {
        Move-Item -LiteralPath $built -Destination $OutputPath
    }
    Move-Item -LiteralPath (Join-Path $JobRoot 'relatorio.json') -Destination $reportPath -Force
    if ($StatePath) {
        $stateParent = [IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($StatePath))
        if (-not (Test-Path -LiteralPath $stateParent)) { New-Item -ItemType Directory -Path $stateParent | Out-Null }
        $state = [ordered]@{
            original_image = $ImagePath; modified_image = $OutputPath
            tool_path = $ToolPath; dolphin_path = $DolphinPath
            image_sha256 = $report.sha256; manifest_sha256 = $manifestHash
            mod_version = $manifest.mod_version
        }
        $state | ConvertTo-Json | Set-Content -LiteralPath ($StatePath + '.tmp') -Encoding UTF8
        Move-Item -LiteralPath ($StatePath + '.tmp') -Destination $StatePath -Force
    }
    Note "PRONTO: $OutputPath"
    Note 'Abra essa nova RVZ no Dolphin do Windows. A campanha ainda precisa ser testada em jogo.'
    Remove-Item -LiteralPath $JobRoot -Recurse -Force
    $JobRoot = $null
    if (-not $DoNotLaunch) {
        try {
            Note 'Iniciando o jogo modificado no Dolphin...'
            Start-Process -FilePath $DolphinPath -ArgumentList @('-e', ('"' + $OutputPath + '"')) | Out-Null
        } catch {
            Note "A RVZ foi criada, mas o Dolphin nao abriu: $($_.Exception.Message)"
            Note "Abra manualmente: $OutputPath"
        }
    }
    exit 0
} catch {
    $message = $_.Exception.Message
    Write-Host "ERRO: $message" -ForegroundColor Red
    if ($JobRoot -and (Test-Path -LiteralPath $JobRoot)) {
        $Events.Add('ERRO: ' + $message)
        $Events | Set-Content -LiteralPath $FailureLog -Encoding UTF8
        Write-Host "Diagnostico e arquivos temporarios preservados em: $JobRoot"
        Write-Host 'Apos verificar o erro, essa pasta temporaria pode ser apagada.'
    }
    if (-not $NoGui) {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show("Nao foi possivel concluir:`n$message`n`nSua imagem original nao foi modificada.", 'PBR Duplas - falha') | Out-Null
    }
    exit 1
}
