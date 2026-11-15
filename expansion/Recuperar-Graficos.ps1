# Reuse verified, locally installed graphics. Never opens a file-selection dialog.
$PbrGraphicsFiles = @('pkx_501.fsys','pkx_502.fsys','pkx_503.fsys','menu_face.fsys','menu_pokemon.fsys')
function Test-PbrGraphicsCache([string]$Folder, [string]$Revision) {
    try {
        $receipt = Get-Content -LiteralPath (Join-Path $Folder 'graphics.json') -Raw | ConvertFrom-Json
        if ($receipt.schema -ne 1 -or $receipt.revision -ne $Revision) { return $false }
        foreach ($name in $PbrGraphicsFiles) {
            $path = Join-Path $Folder $name
            if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or
                ((Get-Item -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or
                $receipt.outputs.$name -notmatch '^[a-f0-9]{64}$' -or (Hash $path) -ne $receipt.outputs.$name) { return $false }
        }
        return $true
    } catch { return $false }
}
function Save-PbrGraphics([string]$Files, [string]$DataRoot, [string]$Revision) {
    if ($Revision -notmatch '^[a-z0-9-]{1,80}$') { throw 'Revisao de graficos invalida.' }
    $root = Join-Path $DataRoot 'Graphics'
    New-Item -ItemType Directory -Path $root -Force | Out-Null
    $destination = Join-Path $root $Revision
    if (Test-PbrGraphicsCache $destination $Revision) { return $destination }
    $stage = Join-Path $root ('preparando-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $stage | Out-Null
    try {
        $outputs = [ordered]@{}
        foreach ($name in $PbrGraphicsFiles) {
            $source = Join-Path $Files $name
            if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Grafico instalado ausente: $name" }
            Copy-Item -LiteralPath $source -Destination (Join-Path $stage $name)
            $outputs[$name] = Hash (Join-Path $stage $name)
        }
        [ordered]@{ schema=1; revision=$Revision; outputs=$outputs } | ConvertTo-Json -Depth 5 |
            Set-Content -LiteralPath (Join-Path $stage 'graphics.json') -Encoding UTF8
        if (-not (Test-PbrGraphicsCache $stage $Revision)) { throw 'Falha ao conferir o cache de graficos.' }
        if (Test-Path -LiteralPath $destination) { Move-Item -LiteralPath $destination -Destination ($destination + '.anterior-' + [Guid]::NewGuid().ToString('N')) }
        Move-Item -LiteralPath $stage -Destination $destination
        return $destination
    } finally { if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force } }
}
function Restore-PbrGraphics($Manifest, $SavedState, [string]$DataRoot, [string]$Work) {
    if (-not $Manifest.local_graphics) { return $null }
    $revision = [string]$Manifest.local_graphics.revision
    if ($revision -notmatch '^[a-z0-9-]{1,80}$') { throw 'Revisao de graficos invalida.' }
    $cached = Join-Path $DataRoot ('Graphics/' + $revision)
    if (Test-PbrGraphicsCache $cached $revision) { Note 'Reutilizando os modelos e retratos ja verificados no cache local.'; return $cached }
    if (-not $SavedState) { return $null }
    $compatible = $SavedState.graphics_revision -eq $revision -or $Manifest.local_graphics.import_versions -contains $SavedState.mod_version
    if (-not $compatible -or -not $SavedState.modified_image -or
        $SavedState.image_sha256 -notmatch '^[a-f0-9]{64}$' -or
        -not (Test-Path -LiteralPath $SavedState.modified_image -PathType Leaf)) { return $null }
    if ((Hash $SavedState.modified_image) -ne $SavedState.image_sha256) { Note 'A imagem anterior nao corresponde ao comprovante; ela nao sera usada como fonte de graficos.'; return $null }
    Note 'Recuperando automaticamente os modelos do jogo ja instalado. Nenhum ZIP sera solicitado.'
    $recovery = Join-Path $Work 'graficos-instalados'
    try {
        Run-Tool -Arguments @('extract','-i',$SavedState.modified_image,'-o',$recovery,'--gameonly')
        $partition = Find-Partition $recovery
        Check-Identity $partition
        return Save-PbrGraphics (Join-Path $partition 'files') $DataRoot $revision
    } finally { if (Test-Path -LiteralPath $recovery) { Remove-Item -LiteralPath $recovery -Recurse -Force } }
}
function Keep-PbrSource([string]$Source, [string]$DataRoot, [string]$Name) {
    if (-not $Source -or -not (Test-Path -LiteralPath $Source -PathType Leaf)) { return $Source }
    $root = Join-Path $DataRoot 'Sources'
    New-Item -ItemType Directory -Path $root -Force | Out-Null
    $target = Join-Path $root $Name
    if ([IO.Path]::GetFullPath($Source) -eq [IO.Path]::GetFullPath($target)) { return $target }
    if (-not (Test-Path -LiteralPath $target) -or (Hash $Source) -ne (Hash $target)) {
        Copy-Item -LiteralPath $Source -Destination ($target + '.tmp') -Force
        if ((Hash $Source) -ne (Hash ($target + '.tmp'))) { throw 'Falha ao guardar o modelo na biblioteca local.' }
        Move-Item -LiteralPath ($target + '.tmp') -Destination $target -Force
    }
    return $target
}
