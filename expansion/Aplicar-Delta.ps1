function Apply-PbrDelta([string]$Original, [string]$Patch, [string]$Expected) {
    $source = [IO.File]::ReadAllBytes($Original)
    $stream = [IO.File]::OpenRead($Patch)
    $gz = New-Object IO.Compression.GZipStream($stream, [IO.Compression.CompressionMode]::Decompress)
    $reader = New-Object IO.StreamReader($gz, [Text.Encoding]::UTF8)
    try { $doc = $reader.ReadToEnd() | ConvertFrom-Json } finally { $reader.Dispose(); $gz.Dispose(); $stream.Dispose() }
    if ($doc.schema -ne 1 -or (Hash $Original) -ne $doc.source_sha256 -or $Expected -ne $doc.target_sha256 -or
        $doc.target_size -lt 0 -or $doc.target_size -gt 33554432) { throw 'Patch ou original incompativel.' }
    $output = New-Object IO.MemoryStream
    try {
        foreach ($op in $doc.ops) {
            if ($op.kind -eq 'copy') {
                [long]$offset = $op.offset; [long]$length = $op.length
                if ($offset -lt 0 -or $length -lt 0 -or $offset + $length -gt $source.Length) { throw 'Bloco de patch invalido.' }
                $output.Write($source, [int]$offset, [int]$length)
            } elseif ($op.kind -eq 'add') {
                $bytes = [Convert]::FromBase64String([string]$op.data)
                $output.Write($bytes, 0, $bytes.Length)
            } else { throw 'Operacao de patch desconhecida.' }
            if ($output.Length -gt $doc.target_size) { throw 'Tamanho de patch invalido.' }
        }
        if ($output.Length -ne $doc.target_size) { throw 'Patch incompleto.' }
        $bytes = $output.ToArray()
        $hasher = [Security.Cryptography.SHA256]::Create()
        try { $actual = ([BitConverter]::ToString($hasher.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant() } finally { $hasher.Dispose() }
        if ($actual -ne $Expected) { throw 'Resultado do patch corrompido.' }
        [IO.File]::WriteAllBytes($Original, $bytes)
    } finally { $output.Dispose() }
}
