# Reuse the verified private Blender SDK already prepared for Snivy.
function Prepare-MegaLucario([string]$Partition, [string]$Source, [string]$CacheRoot, [string]$SnivyCacheRoot) {
    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) { throw 'Selecione o mega-lucario.zip aprovado.' }
    $scripts = Join-Path $PackageRoot 'experiments/mega_lucario'
    $reader = Join-Path $scripts 'tools/read_source_windows.exe'
    $readerProof = Get-Content -LiteralPath (Join-Path $scripts 'tools/reader-build.json') -Raw | ConvertFrom-Json
    if ((Hash $reader) -ne $readerProof.exe_sha256) { throw 'Leitor FBX do Mega Lucario danificado.' }
    $blenderRoot = Join-Path $SnivyCacheRoot 'sdk/blender-3.3.21-windows-x64'
    $blender = Join-Path $blenderRoot 'blender.exe'
    $python = Join-Path $blenderRoot '3.3/python/bin/python.exe'
    if (-not (Test-Path -LiteralPath $blender) -or -not (Test-Path -LiteralPath $python)) { throw 'O SDK da Snivy deve ser preparado antes do Mega Lucario.' }
    $dependencies = Join-Path $SnivyCacheRoot 'sdk/dependencies'
    New-Item -ItemType Directory -Path $CacheRoot -Force | Out-Null
    $assetCache = Join-Path $CacheRoot 'assets'
    $resultFile = Join-Path $CacheRoot 'conversion-result.json'
    $previousPythonPath = $env:PYTHONPATH
    try {
        $env:PYTHONPATH = Join-Path $dependencies 'python-deps'
        & $python (Join-Path $scripts 'convert_local.py') --blender $blender --source $Source `
            --originals (Join-Path $Partition 'files') --pbr-addon (Join-Path $dependencies 'pbr-addon') `
            --reader $reader --cache $assetCache --result $resultFile | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) { throw 'Falha na conversao do Mega Lucario. A imagem anterior foi preservada.' }
        $result = Get-Content -LiteralPath $resultFile -Raw | ConvertFrom-Json
        $output = [IO.Path]::GetFullPath($result.private_assets)
        $allowed = [IO.Path]::GetFullPath($assetCache) + [IO.Path]::DirectorySeparatorChar
        if (-not $output.StartsWith($allowed, [StringComparison]::OrdinalIgnoreCase)) { throw 'Cache Mega fora do destino permitido.' }
        $verification = Get-Content -LiteralPath (Join-Path $output 'verified-cache.json') -Raw | ConvertFrom-Json
        foreach ($name in @('pkx_502.fsys', 'menu_face.fsys', 'menu_pokemon.fsys')) {
            if ((Hash (Join-Path $output $name)) -ne $verification.outputs.$name) { throw "Cache Mega invalido: $name" }
        }
        return $output
    } finally { $env:PYTHONPATH = $previousPythonPath }
}
