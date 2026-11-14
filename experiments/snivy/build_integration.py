"""Build private integrated files from the audited test13 installation.

This does not publish assets, touch saves, or claim successful Dolphin gameplay.
"""
import argparse
import json
from pathlib import Path

from prepare_campaign_doubles import read_archive, sha
from encounter_expansion import rebuild_archive
from integration_data import prepare
from names import MESSAGE_RESOURCE
from catalog import append_archive
from runtime_build import build

BASELINE = {
    'main.dol': 'da02a1232240e139ec14a26ee8b4c2818c56f3c2907f5c2391bd81e2dc0842f6',
    'common.fsys': 'a3667703d2bf2e6733c6d40e4709869982f98e45b9ad029a9f7d7d9fec883d57',
}
CATALOG_SHA = 'da886839e93a719a04833795f2407417cccded696d7e92e49087065dbf3ee26e'


def assemble(baseline, catalog_path, sdr_path, payload_path, output):
    if output.exists():
        raise ValueError('Use a fresh private output directory')
    sources = {name: (baseline / name).read_bytes() for name in (*BASELINE, 'mes_common.fsys')}
    for name, digest in BASELINE.items():
        if sha(sources[name]) != digest:
            raise ValueError('Expected audited test13 ' + name)
    catalog = catalog_path.read_bytes()
    if sha(catalog) != CATALOG_SHA:
        raise ValueError('Expected audited original catalog')
    common = dict(read_archive(sources['common.fsys']))
    messages = dict(read_archive(sources['mes_common.fsys']))
    replacements, new_messages = prepare(common, messages[MESSAGE_RESOURCE], sdr_path.read_bytes())
    results = {
        'main.dol': build(sources['main.dol'], json.loads(payload_path.read_text())),
        'common.fsys': rebuild_archive(sources['common.fsys'], replacements),
        'mes_common.fsys': rebuild_archive(sources['mes_common.fsys'], {MESSAGE_RESOURCE: new_messages}),
        'GSfsys.toc': append_archive(catalog),
    }
    # Every unmodified resource must be byte-identical after decompression.
    for name, changed_ids in (('common.fsys', set(replacements)), ('mes_common.fsys', {MESSAGE_RESOURCE})):
        before, after = dict(read_archive(sources[name])), dict(read_archive(results[name]))
        assert before.keys() == after.keys()
        assert all(before[k] == after[k] for k in before.keys() - changed_ids)
    report = dict(kind='private integrated build; no gameplay or save validation',
                  outputs={name: dict(bytes=len(data), sha256=sha(data)) for name, data in results.items()},
                  modified_common_resources=[f'{key:08x}' for key in sorted(replacements)],
                  unchanged_resources_preserved=True, updater_changed=False,
                  dolphin_gameplay_verified=False,
                  limits=['Local graphics conversion and installer integration required',
                          'Snivy cry and spoken name deliberately silent: no supplied recording',
                          'Manual Dolphin battle, camera and save/load checks required'])
    output.mkdir(parents=True)
    for name, data in results.items():
        (output / name).write_bytes(data)
    (output / 'integration-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'catalog', 'sdr', 'payload', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    print(json.dumps(assemble(a.baseline, a.catalog, a.sdr, a.payload, a.output), indent=2))
