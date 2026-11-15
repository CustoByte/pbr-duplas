param([string]$Output)
$ErrorActionPreference = 'Stop'
$root = Join-Path $env:RUNNER_TEMP ('pbr-integration-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $root | Out-Null
$checks = New-Object 'System.Collections.Generic.List[string]'
try {
    foreach ($file in @('expansion/Aplicar-Mod.ps1','expansion/Iniciar-Launcher.ps1','expansion/Recuperar-Graficos.ps1')) {
        $tokens=$null; $errors=$null
        [void][Management.Automation.Language.Parser]::ParseFile((Join-Path (Get-Location) $file),[ref]$tokens,[ref]$errors)
        if ($errors.Count) { throw ($errors | Out-String) }
    }
    $checks.Add('PowerShell 5.1 scripts parse')
    function Hash([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
    function Note([string]$Message) { Write-Host $Message }
    . ./expansion/Recuperar-Graficos.ps1
    $files = Join-Path $root 'files'; New-Item -ItemType Directory -Path $files | Out-Null
    foreach ($name in $PbrGraphicsFiles) { [IO.File]::WriteAllText((Join-Path $files $name), ('owned fixture ' + $name)) }
    $data = Join-Path $root 'data'; $revision='snivy4-mega3-charizard-y1'; $cache=Save-PbrGraphics $files $data $revision
    if (-not (Test-PbrGraphicsCache $cache $revision)) { throw 'New cache invalid' }
    $manifest = [pscustomobject]@{local_graphics=[pscustomobject]@{revision=$revision;import_versions=@('v0.14.0-charizard-y-test.1','v0.14.0-charizard-y-test.2')}}
    function Run-Tool { throw 'Unexpected extraction while valid cache exists' }
    $work=Join-Path $root 'work'; New-Item -ItemType Directory -Path $work | Out-Null
    if ((Restore-PbrGraphics $manifest $null $data $work) -ne $cache) { throw 'Cache not reused' }
    $checks.Add('verified graphics reused without source ZIPs, dialogs or extraction')
    [IO.File]::WriteAllText((Join-Path $cache 'pkx_503.fsys'),'corrupt')
    if (Test-PbrGraphicsCache $cache $revision) { throw 'Tampered cache accepted' }
    $image=Join-Path $root 'managed.rvz'; [IO.File]::WriteAllText($image,'owned image fixture')
    $state=[pscustomobject]@{modified_image=$image;image_sha256=(Hash $image);mod_version='v0.14.0-charizard-y-test.2'}
    $script:extractCalls=0
    function Run-Tool([string[]]$Arguments) { $script:extractCalls++; $at=[Array]::IndexOf($Arguments,'-o');$dest=$Arguments[$at+1];New-Item -ItemType Directory -Path (Join-Path $dest 'files') -Force | Out-Null;Copy-Item -Path (Join-Path $files '*') -Destination (Join-Path $dest 'files') }
    function Find-Partition([string]$Path) { return $Path }
    function Check-Identity([string]$Path) { if (-not (Test-Path (Join-Path $Path 'files/pkx_503.fsys'))) {throw 'Missing partition fixture'} }
    $recovered=Restore-PbrGraphics $manifest $state $data $work
    if ($script:extractCalls -ne 1 -or -not (Test-PbrGraphicsCache $recovered $revision)) { throw 'Installed image recovery failed' }
    if (Test-Path (Join-Path $work 'graficos-instalados')) { throw 'Recovery extraction left behind' }
    [void](Restore-PbrGraphics $manifest $state $data $work)
    if ($script:extractCalls -ne 1) { throw 'Repeated update re-extracted graphics' }
    $checks.Add('corrupted cache repaired from hash-verified managed image; next update uses cache')
    $wrong=[pscustomobject]@{local_graphics=[pscustomobject]@{revision='new-incompatible';import_versions=@('unknown')}}
    if ($null -ne (Restore-PbrGraphics $wrong $state $data $work)) { throw 'Incompatible revision reused' }
    $state.image_sha256='0'*64
    if ($null -ne (Restore-PbrGraphics $manifest $state (Join-Path $root 'other') $work)) { throw 'Unverified image imported' }
    $checks.Add('incompatible graphics and unverified images rejected')
    $statePath=Join-Path $data 'estado.json';[IO.File]::WriteAllText($statePath,'{"mod_version":"v0.14.0-charizard-y-test.2","custom":"untouched"}')
    $originalState=[IO.File]::ReadAllBytes($statePath)
    $package=Join-Path $root 'package';New-Item -ItemType Directory -Path (Join-Path $package 'launcher') -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $Output 'PBR Launcher.exe') -Destination (Join-Path $package 'launcher/PBR Launcher.exe')
    Copy-Item -LiteralPath (Join-Path $Output 'PBR Duplas.exe') -Destination (Join-Path $package 'launcher/PBR Duplas.exe')
    Copy-Item ./expansion/Iniciar-Launcher.ps1 $package
    @{launcher=@{version='1.0.0';sha256=(Hash (Join-Path $Output 'PBR Launcher.exe'));bootstrap_sha256=(Hash (Join-Path $Output 'PBR Duplas.exe'))}} | ConvertTo-Json | Set-Content (Join-Path $package 'manifesto.json') -Encoding UTF8
    & (Join-Path $package 'Iniciar-Launcher.ps1') -StatePath $statePath -DoNotLaunch
    if (-not (Test-Path (Join-Path $data 'Launcher/PBR Duplas.exe'))) { throw 'Stable GUI entry missing' }
    if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($statePath)) -ne [Convert]::ToBase64String($originalState)) { throw 'Migration modified game state' }
    $installed=Get-Content (Join-Path $data 'Launcher/installed.json') -Raw | ConvertFrom-Json
    if ((Hash $installed.executable) -ne $installed.sha256) {throw 'Installed executable hash mismatch'}
    $checks.Add('legacy migration creates versioned WinExe and stable shortcuts, preserving estado.json')
    $binary=[IO.File]::ReadAllBytes($installed.executable);$pe=[BitConverter]::ToInt32($binary,60)
    if ([BitConverter]::ToUInt16($binary,$pe+92) -ne 2) {throw 'Executable requires console subsystem'}
    $entry=Join-Path $data 'Launcher/PBR Duplas.exe'
    $verified=Start-Process -FilePath $entry -ArgumentList '--verify' -Wait -PassThru
    if ($verified.ExitCode -ne 0) { throw 'Stable executable cannot verify installed GUI' }
    $checks.Add('Windows GUI subsystem: no CMD required')
    @{passed=$true;checks=$checks;gameplay_tested=$false} | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $Output 'integration-tests.json') -Encoding UTF8
} catch {
    @{passed=$false;checks=$checks;error=$_.Exception.ToString()} | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $Output 'integration-tests.json') -Encoding UTF8
    throw
} finally { if (Test-Path $root) { Remove-Item -LiteralPath $root -Recurse -Force } }
