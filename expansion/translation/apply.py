"""Apply reviewed battle text only; reject mismatched source archives."""
import argparse, json
from pathlib import Path
from encounter_expansion import rebuild_archive
from prepare_campaign_doubles import read_archive, sha
from translation.messages import RESOURCE, read_messages, write_messages, readable, validate_target


def prepare(archive, approval_path=None):
    approval_path = approval_path or Path(__file__).with_name('approved.json')
    approval = json.loads(approval_path.read_text())
    if sha(archive) != approval['archive_sha256']:
        raise ValueError('Unsupported original battle message archive')
    entries = dict(read_archive(archive))
    resource = entries[RESOURCE]
    if sha(resource) != approval['resource_sha256']:
        raise ValueError('Unsupported original battle message resource')
    header, original = read_messages(resource)
    rows = list(original)
    changed = set()
    for batch in approval['batches']:
        if batch['status'] != 'approved-by-user':
            continue
        for entry in batch['entries']:
            for index in entry['ids']:
                if index in changed:
                    raise ValueError('Duplicate translation ID')
                target = entry['target']
                for name in entry.get('protected_names', []):
                    if readable(original[index]).count(name) != target.count(name):
                        raise ValueError('A protected name was changed')
                rows[index] = validate_target(original[index], target)
                changed.add(index)
    updated = write_messages(header, rows)
    output = rebuild_archive(archive, {RESOURCE: updated})
    result = dict(read_archive(output))
    assert all(result[key] == value for key, value in entries.items() if key != RESOURCE)
    assert all(row == original[i] for i, row in enumerate(rows) if i not in changed)
    return output, {
        'status': 'applied-approved-battle-text-awaiting-Dolphin-visual-check',
        'language': 'pt-BR', 'approved_batches': [b['batch'] for b in approval['batches'] if b['status']=='approved-by-user'],
        'changed_message_ids': sorted(changed), 'changed_message_count': len(changed),
        'untouched_message_count': len(rows)-len(changed),
        'untouched_archive_resources': len(entries)-1,
        'dynamic_variables_formatting_and_pause_markers_preserved': True,
        'unapproved_text_changed': False, 'names_translated': False,
        'source_sha256': sha(archive), 'target_sha256': sha(output),
        'approval_sha256': sha(approval_path.read_bytes()),
        'dolphin_visual_tested': False,
    }


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    a = p.parse_args()
    if a.original.resolve() == a.output.resolve() or a.output.exists():
        raise ValueError('Choose a new output; never overwrite the original')
    output, report = prepare(a.original.read_bytes())
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_bytes(output)
    a.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
