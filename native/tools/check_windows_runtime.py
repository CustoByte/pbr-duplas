"""Download the published owned runtime and execute its actual Windows self-test."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'native/launcher'), str(ROOT / 'native/tools')]
import core
from make_test_model import generate


def check():
    if os.name != 'nt':
        raise RuntimeError('This check executes the Windows binary on Windows.')
    feed = json.loads((ROOT / 'native/update.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory(prefix='pbr-native-ci-') as temporary:
        home = Path(temporary)
        core.install_runtime(home, feed)
        exe = core.runtime_path(home)
        model = home / 'owned-test.glb'
        generate(model)
        result = subprocess.run([str(exe), '--headless', '--audio-driver', 'Dummy',
                                 '--main-pack', str(exe.with_suffix('.pck')), '--',
                                 '--data-dir', str(home / 'user-data'),
                                 '--model', str(model), '--report', str(home / 'native-self-test.json'), '--self-test'],
                                capture_output=True, encoding='utf-8', errors='replace', timeout=90)
        print(result.stdout)
        print(result.stderr)
        proof_path = home / 'native-self-test.json'
        if result.returncode or not proof_path.is_file():
            raise RuntimeError('Windows native scene self-test failed')
        proof = json.loads(proof_path.read_text(encoding='utf-8'))
        if not proof.get('bone_animation_moves') or proof.get('dolphin_used') or len(proof.get('body_actions', [])) != 9:
            raise RuntimeError('Native scene did not verify skin/animation behavior')
        print(json.dumps(proof))
        print('Verified published Windows binary, code pack, GLB skin and animations; no Dolphin.')


if __name__ == '__main__':
    check()
