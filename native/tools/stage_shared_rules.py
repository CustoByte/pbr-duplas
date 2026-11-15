"""Stage the canonical Pokemon rules into native builds without copying assets."""
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'content/tools'))
from generate_rules import DEFAULT, generate


def stage(destination):
    with tempfile.TemporaryDirectory(prefix='pbr-shared-rules-') as temporary:
        temporary = Path(temporary)
        report = generate(DEFAULT, temporary)
        destination.mkdir(parents=True, exist_ok=True)
        (destination/'battle-rules.json').write_bytes((temporary/'battle-rules.json').read_bytes())
        return report


if __name__ == '__main__':
    print(json.dumps(stage(ROOT/'native/runtime/data'), indent=2))
