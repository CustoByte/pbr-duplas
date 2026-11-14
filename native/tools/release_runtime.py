"""Build and self-test the Windows release on a Windows GitHub runner."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request
import zipfile
from make_test_model import generate
from package_runtime import build

ROOT = Path(__file__).resolve().parents[2]


def release(destination):
    if os.name != 'nt':
        raise RuntimeError('Release verification must execute on Windows')
    destination.mkdir(parents=True, exist_ok=True)
    engine = destination / 'engine'
    engine.mkdir(exist_ok=True)
    metadata = json.loads((ROOT / 'native/runtime/godot-build.json').read_text())
    archive = destination / 'godot.zip'
    url = 'https://github.com/godotengine/godot-builds/releases/download/4.6.3-stable/Godot_v4.6.3-stable_win64.exe.zip'
    urllib.request.urlretrieve(url, archive)
    if hashlib.sha512(archive.read_bytes()).hexdigest() != metadata['windows_zip_sha512']:
        raise ValueError('Official Godot ZIP hash mismatch')
    with zipfile.ZipFile(archive) as z:
        z.extractall(engine)
    for name in ('LICENSE.txt', 'COPYRIGHT.txt'):
        urllib.request.urlretrieve('https://raw.githubusercontent.com/godotengine/godot/4.6.3-stable/' + name, engine / name)
    exe = engine / 'Godot_v4.6.3-stable_win64.exe'
    pack = destination / 'PBRNative.pck'
    subprocess.run([str(exe), '--headless', '--path', str(ROOT / 'native/runtime'),
                    '--export-pack', 'Windows', str(pack)], check=True, timeout=180)
    if not pack.exists():
        raise RuntimeError('Resource pack was not generated')
    model = destination / 'owned-test.glb'
    generate(model)
    proof_path = destination / 'windows-native-proof.json'
    subprocess.run([str(exe), '--headless', '--audio-driver', 'Dummy', '--main-pack', str(pack), '--',
                    '--model', str(model), '--report', str(proof_path), '--self-test'], check=True, timeout=90)
    proof = json.loads(proof_path.read_text(encoding='utf-8'))
    if not proof.get('bone_animation_moves') or proof.get('dolphin_used') or len(proof.get('body_actions', [])) != 9:
        raise RuntimeError('Windows scene did not pass skin/animation verification')
    report = build(engine, pack, destination / 'PBR-Native-Runtime-Windows.zip')
    feed_path = ROOT / 'native/update.json'
    feed = json.loads(feed_path.read_text(encoding='utf-8'))
    feed['windows_x64']['sha256'] = report['sha256']
    feed_path.write_text(json.dumps(feed, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (ROOT / 'native/runtime/package-proof.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    proof.update(kind='Windows headless, owned animated triangle, not private Mega or GPU benchmark',
                 published_exe_sha256=metadata['windows_exe_sha256'])
    (ROOT / 'native/runtime/windows-ci-proof.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    release(Path(sys.argv[1]).resolve())
