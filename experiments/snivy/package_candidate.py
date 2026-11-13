"""Prepare a candidate updater core: own tools and original-file deltas only.

Does not update a feed or upload a release. Full assets remain private locally.
"""
import argparse
import json
from pathlib import Path
import shutil
import tempfile

from convert_local import ROOT, digest


def package(integrated, originals, payload, output):
    import sys
    sys.path[:0] = [str(ROOT / 'expansion')]
    from binary_delta import create, sha
    from package_release import zipped
    manifest = json.loads((ROOT / 'expansion/manifesto.json').read_text())
    manifest['mod_version'] = 'v0.12.0-snivy-test.1'
    manifest['local_snivy_assets'] = True
    manifest['dolphin_tested'] = False
    manifest['snivy_limitations'] = ['Snivy cry and spoken name silent: no recording supplied',
                                    'Dolphin visual, battle and save/load checks still required']
    core = {name: (ROOT / 'expansion' / name).read_bytes() for name in
            ('Aplicar-Mod.ps1', 'Aplicar-Delta.ps1', 'Preparar-Snivy.ps1')}
    modified = {'sys/main.dol': 'main.dol', 'files/common.fsys': 'common.fsys',
                'files/mes_common.fsys': 'mes_common.fsys', 'files/GSfsys.toc': 'GSfsys.toc'}
    entries = {e['installed_path']: e for e in manifest['replacements']}
    for installed, filename in modified.items():
        source = (originals / installed).read_bytes()
        expected = manifest['original_sha256'].get(installed)
        if expected and sha(source) != expected:
            raise ValueError('Unexpected original: ' + installed)
        manifest['original_sha256'][installed] = sha(source)
        target = (integrated / filename).read_bytes()
        patch = create(source, target)
        path = 'patches/snivy-' + filename.replace('.', '-') + '.pbrdelta'
        entries[installed] = dict(package_path=path, installed_path=installed,
                                  sha256=sha(target), patch_sha256=sha(patch), format='pbr-delta-v1')
        core[path] = patch
    manifest['replacements'] = list(entries.values())
    for entry in manifest['replacements']:
        if entry['package_path'] not in core:
            data = (ROOT / 'expansion/prebuilt' / Path(entry['package_path']).name).read_bytes()
            if sha(data) != entry['patch_sha256']:
                raise ValueError('Existing package hash mismatch')
            core[entry['package_path']] = data
    core['manifesto.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    for directory in ('experiments/snivy', 'mod-source', 'expansion'):
        for p in (ROOT / directory).glob('*.py'):
            if p.name.startswith(('test_', 'verify_')) and p.name != 'verify_native_asset.py':
                continue
            core[p.relative_to(ROOT).as_posix()] = p.read_bytes()
    for name in ('sdk-downloads.json', 'supported-learnset.json', 'pass_delivery.c'):
        core['experiments/snivy/' + name] = (ROOT / 'experiments/snivy' / name).read_bytes()
    core['experiments/snivy/pass-payload.json'] = payload.read_bytes()
    core['mac-aplicador/INICIAR-SNIVY-MAC.command'] = (ROOT / 'mac-aplicador/INICIAR-SNIVY-MAC.command').read_bytes()
    core['LEIA-ME-SNIVY.txt'] = (
        'Candidata experimental Snivy. Nao validada em batalha real no Dolphin.\n'
        'O primeiro uso pede Tsutarja.brres extraido do seu PokePark 2 USA.\n'
        'Baixa Blender 3.3.21 portatil (~300 MB Windows) e ferramentas com SHA256 fixo.\n'
        'Converte modelo, animacoes e retratos localmente e guarda cache privado.\n'
        'Nao abre saves. Use o save normal do jogo; nao use estados de outras builds.\n'
        'Cria passe Little Battle em um espaco pessoal vazio e nao personalizado.\n'
        'Troca somente Charmeleon original do passe vermelho por Snivy nivel 50.\n'
        'Snivy: Timid, Overgrow, Lum Berry; conjunto proprio para cada nivel.\n'
        'O grito e o nome falado da Snivy ficam silenciosos nesta candidata.\n'
        'Movimentos/impactos usam o motor nativo; sincronizacao visual requer teste.\n'
        'Dependencias: Blender GPL, BerryBush GPL-3.0-or-later, Pillow HPND.\n'
        'Fontes e revisoes das ferramentas: experiments/snivy/sdk-downloads.json.\n'
        'Adaptacoes BerryBush: experiments/snivy/prepare_graphics_tools.py.\n'
    ).encode()
    forbidden = ('.dol', '.fsys', '.sav', '.sdr', '.blend', '.brres', '.png', '.iso', '.rvz', '.bin')
    assert not any(name.lower().endswith(forbidden) for name in core)
    output.mkdir(parents=True, exist_ok=False)
    data = zipped(core)
    (output / 'aplicador-core.zip').write_bytes(data)
    (output / 'core.sha256').write_text(sha(data) + '\n')
    # Separate extraction makes local installer verification possible before upload.
    import zipfile
    with zipfile.ZipFile(output / 'aplicador-core.zip') as z:
        z.extractall(output / 'core')
    return dict(version=manifest['mod_version'], core_sha256=sha(data), bytes=len(data),
                public_game_assets=False, published=False, dolphin_tested=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('integrated', 'originals', 'payload', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(package(a.integrated, a.originals, a.payload, a.output), indent=2))
