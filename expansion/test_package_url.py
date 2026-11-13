"""Run the updater's actual URL validation with the published feed and hostile URLs."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

PWSH = shutil.which('pwsh') or '/tmp/pbr-pwsh/pwsh'
ROOT = Path(__file__).resolve().parents[1]


class PackageURLTests(unittest.TestCase):
    def test_real_function_accepts_published_package_and_rejects_other_sources(self):
        feed = json.loads((ROOT / 'expansion/update-test.json').read_text())
        allowed = [feed['package_url'],
                   'https://github.com/CustoByte/pbr-duplas/releases/download/v0.11.0-full493-test.13/aplicador-core.zip']
        rejected = [
            feed['package_url'].replace('CustoByte', 'SomeoneElse'),
            feed['package_url'].replace('/pbr-duplas/', '/pbr-duplas-evil/'),
            feed['package_url'].replace('/v0.12.0-snivy-test.1/', '/main/'),
            feed['package_url'].replace('raw.githubusercontent.com', 'raw.githubusercontent.com.evil.test'),
            feed['package_url'].replace('https://', 'http://'),
            feed['package_url'] + '?redirect=evil', feed['package_url'] + '#other',
            feed['package_url'].replace('/aplicador-core.zip', '/other.zip'),
            feed['package_url'].replace('https://', 'https://user:pass@'),
            feed['package_url'].replace('raw.githubusercontent.com', 'raw.githubusercontent.com:444'),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'cases.json').write_text(json.dumps(dict(allowed=allowed, rejected=rejected)))
            script = root / 'test.ps1'
            script.write_text('''param($Updater, $Cases)
$ErrorActionPreference = 'Stop'
$tokens = $null; $errors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($Updater, [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw 'Updater syntax error' }
$fn = $ast.Find({ param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Assert-PackageUrl' }, $true)
Invoke-Expression $fn.Extent.Text
$cases = Get-Content -LiteralPath $Cases -Raw | ConvertFrom-Json
foreach ($url in $cases.allowed) { Assert-PackageUrl $url }
foreach ($url in $cases.rejected) {
    $rejected = $false
    try { Assert-PackageUrl $url } catch { $rejected = $true }
    if (-not $rejected) { throw "Unauthorized URL accepted: $url" }
}
Write-Output 'Published package accepted; unrelated hosts/repos, mutable branches, credentials and other paths rejected'
''')
            env = dict(os.environ, XDG_CACHE_HOME=tmp, XDG_CONFIG_HOME=tmp, XDG_DATA_HOME=tmp)
            result = subprocess.run([PWSH, '-NoProfile', '-File', str(script),
                                     str(ROOT / 'src/Atualizar-Iniciar.ps1'), str(root / 'cases.json')],
                                    env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
