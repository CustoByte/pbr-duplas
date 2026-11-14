"""Assemble the owned native prototype + hash-pinned MIT Godot engine.

No model, ISO, textures, saves or other game assets may enter this package.
"""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def build(engine, pack, output):
    expected = json.loads((ROOT / 'native/runtime/godot-build.json').read_text())
    exe = engine / 'Godot_v4.6.3-stable_win64.exe'
    if hashlib.sha256(exe.read_bytes()).hexdigest() != expected['windows_exe_sha256']:
        raise ValueError('Godot engine hash mismatch')
    if not pack.read_bytes().startswith(b'GDPC'):
        raise ValueError('Not a Godot resource pack')
    files = {'PBRNative.exe': exe.read_bytes(), 'PBRNative.pck': pack.read_bytes(),
             'GODOT-LICENSE.txt': (engine / 'LICENSE.txt').read_bytes(),
             'THIRD-PARTY-NOTICES.txt': (engine / 'COPYRIGHT.txt').read_bytes(),
             'LEIA-ME.txt': (ROOT / 'native/runtime/LEIA-ME.txt').read_bytes(),
             'INICIAR-CENA-NATIVA.cmd': (ROOT / 'native/runtime/INICIAR-CENA-NATIVA.cmd').read_bytes()}
    if any(Path(name).suffix.lower() in ('.glb', '.fbx', '.sdr', '.fsys', '.iso', '.rvz', '.sav', '.png') for name in files):
        raise ValueError('Private game asset in public package')
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in files.items():
            entry = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data)
    report = dict(bytes=output.stat().st_size, sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                  public_files=list(files), game_assets_distributed=False,
                  engine='Godot 4.6.3 MIT — editor binary used as runtime for initial prototype',
                  native_scene_only=True, full_battle_engine=False)
    output.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    print(json.dumps(build(*map(Path, sys.argv[1:])), indent=2))
