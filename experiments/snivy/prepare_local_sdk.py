"""Fetch hash-pinned converter dependencies for private local use.

No model assets are fetched. Blender itself is supplied by the platform launcher.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import tempfile
import urllib.request
import zipfile

MANIFEST = json.loads(Path(__file__).with_name('sdk-downloads.json').read_text())
REVISIONS = {'berrybush': '5ff000f7362a3b18cc55e871fc3e1f645eb5e206',
             'pbr-addon': 'ed18e4fd606bf66b670c71c2484bf9fc86ea5b7d'}


def fetch(entry, cache):
    cache.mkdir(parents=True, exist_ok=True)
    destination = cache / entry['sha256']
    if destination.is_file() and hashlib.sha256(destination.read_bytes()).hexdigest() == entry['sha256']:
        return destination
    with tempfile.NamedTemporaryFile(dir=cache, delete=False) as f:
        pending = Path(f.name)
        try:
            with urllib.request.urlopen(entry['url'], timeout=120) as response:
                shutil.copyfileobj(response, f)
            f.close()
            if hashlib.sha256(pending.read_bytes()).hexdigest() != entry['sha256']:
                raise ValueError('Dependency download digest mismatch')
            pending.replace(destination)
        finally:
            pending.unlink(missing_ok=True)
    return destination


def extract_zip(archive, destination, prefix=''):
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            name = member.filename
            if not name.startswith(prefix):
                continue
            relative = Path(name[len(prefix):])
            if relative.is_absolute() or '..' in relative.parts or '\\' in name:
                raise ValueError('Unsafe dependency archive path')
            if not relative.parts:
                continue
            target = destination / relative
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(member) as source, target.open('wb') as output:
                    shutil.copyfileobj(source, output)


def prepare(root):
    from prepare_graphics_tools import prepare as adapt
    for name, revision in REVISIONS.items():
        destination = root / name
        marker = destination / '.verified-sdk-revision'
        if marker.is_file() and marker.read_text().strip() == revision:
            continue
        archive = fetch(MANIFEST[name], root / 'downloads')
        with zipfile.ZipFile(archive) as z:
            prefixes = {n.split('/')[0] for n in z.namelist()}
        if len(prefixes) != 1:
            raise ValueError('Dependency archive must have one root')
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            prepared = Path(temporary) / 'source'
            extract_zip(archive, prepared, next(iter(prefixes)) + '/')
            (prepared / '.verified-sdk-revision').write_text(revision + '\n')
            if destination.exists():
                shutil.rmtree(destination)
            prepared.rename(destination)
    adapt(root / 'berrybush', root / 'pbr-addon')
    if platform.system() == 'Windows':
        tag = 'win_amd64'
    elif platform.system() == 'Darwin':
        tag = 'macosx_11_0_arm64' if platform.machine() == 'arm64' else 'macosx_10_10_x86_64'
    else:
        tag = 'manylinux_2_28_x86_64'
    wheel = next(x for x in MANIFEST['pillow'] if tag in x['filename'])
    destination = root / 'python-deps'
    archive = fetch(wheel, root / 'downloads')
    marker = destination / '.pillow-sha256'
    if not marker.is_file() or marker.read_text().strip() != wheel['sha256']:
        extract_zip(archive, destination)
        marker.write_text(wheel['sha256'] + '\n')
    return dict(berrybush=str(root / 'berrybush'), pbr_addon=str(root / 'pbr-addon'), python_deps=str(destination))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    a = p.parse_args()
    a.root.mkdir(parents=True, exist_ok=True)
    print(json.dumps(prepare(a.root), indent=2))
