"""Run the local graphics pipeline and cache only verified private outputs.

Source BRRES and original game FSYS archives remain on the player's computer.
No save files are opened. A failed stage never replaces a successful cache.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = Path(__file__).resolve().parent
SOURCE_SHA = '42ee39d351dc05e4f509267a2ce540286b134f6e8d024b776175a4c75c5a9308'
OUTPUTS = ('pkx_501.fsys', 'menu_face.fsys', 'menu_pokemon.fsys')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pipeline_key(source, originals):
    # Translation/runtime releases reuse graphics unless an actual conversion
    # dependency changes; package metadata and unrelated tests are not a recipe.
    local = ('convert_local', 'graphics_common', 'graphics_import', 'graphics_convert',
             'graphics_verify', 'native_graphics_profile', 'render_portraits',
             'prepare_graphics_tools', 'icon_textures', 'shiny_variant',
             'resource_packages', 'pkx_reference', 'verify_native_asset',
             'build_local_assets', 'model_registry', 'icon_registry', 'catalog', 'sdr_track_storage')
    files = [SCRIPTS / (name + '.py') for name in local]
    files += [ROOT / 'mod-source' / (name + '.py') for name in
              ('prepare_campaign_doubles', 'inspect_fsys', 'team_series_asm', 'lzss_encode')]
    files += [ROOT / 'expansion/encounter_expansion.py', SCRIPTS / 'sdk-downloads.json']
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in files}
    hashes['source'] = digest(source)
    hashes.update({name: digest(originals / name) for name in ('pkx_388.fsys', 'menu_face.fsys', 'menu_pokemon.fsys')})
    if hashes['source'] != SOURCE_SHA:
        raise ValueError('Expected the audited Tsutarja.brres source')
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def convert(blender, source, originals, berrybush, pbr_addon, cache):
    key = pipeline_key(source, originals)
    destination = cache / key
    marker = destination / 'verified-cache.json'
    if marker.is_file():
        report = json.loads(marker.read_text())
        if report.get('key') == key and all(digest(destination / name) == report['outputs'][name] for name in OUTPUTS):
            return destination
        raise ValueError('Existing private cache failed integrity validation')
    cache.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['PYTHONPATH'] = os.pathsep.join(str(p) for p in (SCRIPTS, ROOT / 'mod-source', ROOT / 'expansion')) + os.pathsep + env.get('PYTHONPATH', '')
    # The caller supplies pinned SDK clones prepared by prepare_graphics_tools.
    # Each Blender stage is a new background process, releasing memory at exit.
    with tempfile.TemporaryDirectory(prefix='snivy-', dir=cache) as temporary:
        work = Path(temporary)
        args = ['--source', str(source), '--workdir', str(work), '--berrybush', str(berrybush),
                '--pbr-addon', str(pbr_addon), '--native-reference', str(originals / 'pkx_388.fsys')]
        for script in ('graphics_import.py', 'graphics_convert.py', 'graphics_verify.py', 'render_portraits.py'):
            print('Snivy: ' + script, flush=True)
            with (work / (script + '.log')).open('wb') as log:
                process = subprocess.run([str(blender), '--background', '--threads', '2', '--factory-startup', '--python', str(SCRIPTS / script), '--', *args],
                                         env=env, stdout=log, stderr=subprocess.STDOUT)
            if process.returncode:
                import shutil
                failure = cache / 'last-failure.log'
                shutil.copyfile(work / (script + '.log'), failure)
                raise RuntimeError(f'Blender stage {script} failed; log: {failure}')
        import sys
        sys.path[:0] = [str(SCRIPTS), str(ROOT / 'mod-source'), str(ROOT / 'expansion')]
        from build_local_assets import build
        output = work / 'assets'
        build(work, originals / 'pkx_388.fsys', originals / 'menu_face.fsys', originals / 'menu_pokemon.fsys', output)
        report = dict(key=key, outputs={name: digest(output / name) for name in OUTPUTS},
                      source_sha256=SOURCE_SHA, dolphin_verified=False)
        (output / 'verified-cache.json').write_text(json.dumps(report, indent=2) + '\n')
        # Rename is on the same filesystem; unsuccessful runs leave no valid cache.
        output.rename(destination)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('blender', 'source', 'originals', 'berrybush', 'pbr-addon', 'cache'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--result', type=Path)
    a = parser.parse_args()
    result = convert(a.blender, a.source, a.originals, a.berrybush, a.pbr_addon, a.cache)
    report = json.dumps(dict(private_assets=str(result)), indent=2) + '\n'
    if a.result:
        a.result.write_text(report)
    print(report)
