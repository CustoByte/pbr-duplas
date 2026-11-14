"""Build a private Riivolution overlay from the player's extracted originals.

No original game assets are distributed. Dolphin supports file create=true for
an independent pkx_501.fsys and main.dol as a special executable replacement.
"""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
import xml.etree.ElementTree as ET

from convert_local import convert, digest, ROOT


def build(core, originals, blender, source, sdk, cache, output, image):
    import sys
    sys.path.insert(0, str(ROOT / 'expansion'))
    from binary_delta import apply
    manifest = json.loads((core / 'manifesto.json').read_text(encoding='utf-8-sig'))
    if not manifest.get('local_snivy_assets'):
        raise ValueError('This builder requires the integrated Snivy manifest')
    if not image.is_file():
        raise ValueError('Choose your original ISO/RVZ image')
    for name, expected in manifest['original_sha256'].items():
        if digest(originals / name) != expected:
            raise ValueError('Original game file differs: ' + name)
    assets = convert(blender, source, originals / 'files', sdk / 'berrybush', sdk / 'pbr-addon', cache)
    if output.exists():
        raise ValueError('Use a fresh overlay destination; previous installs are preserved')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        stage = Path(temporary) / 'overlay'
        stage.mkdir()
        xml = ET.Element('wiidisc', version='1')
        ET.SubElement(xml, 'id', game='RPBE', developer='01', disc='0', version='0')
        options = ET.SubElement(xml, 'options')
        section = ET.SubElement(options, 'section', name='PBR Duplas')
        option = ET.SubElement(section, 'option', name='PBR Duplas', id='pbr-duplas', default='1')
        choice = ET.SubElement(option, 'choice', name=manifest['mod_version'])
        ET.SubElement(choice, 'patch', id='pbr-snivy')
        patch = ET.SubElement(xml, 'patch', id='pbr-snivy')
        changes = {}
        for entry in manifest['replacements']:
            name = entry['installed_path']
            relative = Path(name)
            if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
                raise ValueError('Unsafe patch path')
            blob = core / entry['package_path']
            if digest(blob) != entry['patch_sha256'] or entry['format'] != 'pbr-delta-v1':
                raise ValueError('Invalid delta package')
            data = apply((originals / relative).read_bytes(), blob.read_bytes())
            target = stage / 'mod' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            if digest(target) != entry['sha256']:
                raise ValueError('Delta output failed validation')
            changes[name] = target
        for name in ('pkx_501.fsys', 'menu_face.fsys', 'menu_pokemon.fsys'):
            target = stage / 'mod/files' / name
            shutil.copyfile(assets / name, target)
            changes['files/' + name] = target
        for name, target in changes.items():
            disc = 'main.dol' if name == 'sys/main.dol' else '/' + name.removeprefix('files/')
            ET.SubElement(patch, 'file', disc=disc, external='/' + target.relative_to(stage).as_posix(),
                          resize='true', create='true' if name == 'files/pkx_501.fsys' else 'false')
        ET.indent(xml)
        ET.ElementTree(xml).write(stage / 'riivolution.xml', encoding='utf-8', xml_declaration=True)
        descriptor = {'type': 'dolphin-game-mod-descriptor', 'version': 1,
                      'base-file': str(image.resolve()), 'display-name': 'PBR Duplas — ' + manifest['mod_version'],
                      'maker': 'CustoByte', 'riivolution': {'patches': [{
                          'xml': str(output.resolve() / 'riivolution.xml'), 'root': str(output.resolve()),
                          'options': [{'section-name': 'PBR Duplas', 'option-id': 'pbr-duplas', 'choice': 1}]}]}}
        (stage / 'Jogar-PBR-Duplas.json').write_text(json.dumps(descriptor, indent=2) + '\n')
        (stage / 'installed-files.json').write_text(json.dumps({n: digest(p) for n, p in changes.items()}, indent=2) + '\n')
        stage.rename(output)
    return output / 'Jogar-PBR-Duplas.json'


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('core', 'originals', 'blender', 'source', 'sdk', 'cache', 'output', 'image'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    print(build(a.core, a.originals, a.blender, a.source, a.sdk, a.cache, a.output, a.image))
