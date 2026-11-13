# Dot-sourced by the applicator only for a manifest requiring local Snivy assets.
function Prepare-Snivy([string]$Partition, [string]$Source, [string]$CacheRoot) {
    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) { throw 'Selecione seu arquivo Tsutarja.brres.' }
    if ((Hash $Source) -ne '42ee39d351dc05e4f509267a2ce540286b134f6e8d024b776175a4c75c5a9308') {
        throw 'O Tsutarja.brres selecionado difere da versao compativel.'
    }
    $sdk = Join-Path $CacheRoot 'sdk'
    New-Item -ItemType Directory -Path $sdk -Force | Out-Null
    $sdkManifest = Get-Content -LiteralPath (Join-Path $PackageRoot 'experiments/snivy/sdk-downloads.json') -Raw | ConvertFrom-Json
    $entry = $sdkManifest.blender.'blender-3.3.21-windows-x64.zip'
    $blenderRoot = Join-Path $sdk 'blender-3.3.21-windows-x64'
    $blender = Join-Path $blenderRoot 'blender.exe'
    if (-not (Test-Path -LiteralPath $blender -PathType Leaf)) {
        Note 'Preparando conversor local da Snivy (primeiro uso: download de aproximadamente 300 MB)...'
        $archive = Join-Path $sdk 'blender.zip'
        if (-not (Test-Path -LiteralPath $archive) -or (Hash $archive) -ne $entry.sha256) {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            Invoke-WebRequest -UseBasicParsing -Uri $entry.url -OutFile ($archive + '.tmp')
            if ((Hash ($archive + '.tmp')) -ne $entry.sha256) { throw 'Download do Blender invalido.' }
            Move-Item -LiteralPath ($archive + '.tmp') -Destination $archive -Force
        }
        Expand-Archive -LiteralPath $archive -DestinationPath $sdk -Force
    }
    $python = Join-Path $blenderRoot '3.3/python/bin/python.exe'
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'Python interno do Blender nao encontrado.' }
    $dependencyRoot = Join-Path $sdk 'dependencies'
    $prepare = Join-Path $PackageRoot 'experiments/snivy/prepare_local_sdk.py'
    & $python $prepare --root $dependencyRoot | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao preparar dependencias da Snivy.' }
    $previousPythonPath = $env:PYTHONPATH
    try {
        $env:PYTHONPATH = (Join-Path $dependencyRoot 'python-deps')
        $script = Join-Path $PackageRoot 'experiments/snivy/convert_local.py'
        $assetCache = Join-Path $CacheRoot 'assets'
        $resultFile = Join-Path $CacheRoot 'conversion-result.json'
        & $python $script --blender $blender --source $Source --originals (Join-Path $Partition 'files') `
            --berrybush (Join-Path $dependencyRoot 'berrybush') --pbr-addon (Join-Path $dependencyRoot 'pbr-addon') `
            --cache $assetCache --result $resultFile | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) { throw 'Falha na conversao local da Snivy. A imagem anterior foi preservada.' }
        $result = Get-Content -LiteralPath $resultFile -Raw | ConvertFrom-Json
        $output = [IO.Path]::GetFullPath($result.private_assets)
        $allowed = [IO.Path]::GetFullPath($assetCache) + [IO.Path]::DirectorySeparatorChar
        if (-not $output.StartsWith($allowed, [StringComparison]::OrdinalIgnoreCase)) { throw 'Cache fora do destino permitido.' }
        $verification = Get-Content -LiteralPath (Join-Path $output 'verified-cache.json') -Raw | ConvertFrom-Json
        foreach ($name in @('pkx_501.fsys', 'menu_face.fsys', 'menu_pokemon.fsys')) {
            $file = Join-Path $output $name
            if ((Hash $file) -ne $verification.outputs.$name) { throw "Cache invalido: $name" }
        }
        return $output
    } finally { $env:PYTHONPATH = $previousPythonPath }
}
