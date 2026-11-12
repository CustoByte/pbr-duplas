"""Apply reviewed battle text only; reject mismatched source archives."""
import argparse, json
from pathlib import Path
from encounter_expansion import rebuild_archive
from prepare_campaign_doubles import read_archive, sha
from translation.messages import RESOURCE, read_messages, write_messages, readable, validate_target


def prepare(archive, approval_path=None, trainer_names=False):
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
    approved_sources = {}
    for batch in approval['batches']:
        if batch['status'] not in ('approved-by-user', 'approved-by-user-delegation'):
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
                previous = approved_sources.get(original[index])
                if previous and previous[1] != rows[index]:
                    raise ValueError('Identical source phrases have conflicting approved translations')
                approved_sources.setdefault(original[index], (index, rows[index]))
                changed.add(index)
    # An approved phrase also covers exact repetitions of its original bytes,
    # including identical font, parameters, pauses and line layout. No fuzzy
    # matching or translation of different wording is performed.
    duplicate_of = {}
    for index, source in enumerate(original):
        if index not in changed and source in approved_sources:
            canonical, translated = approved_sources[source]
            rows[index] = translated
            changed.add(index)
            duplicate_of[index] = canonical
    references = set()
    if trainer_names:
        from translation.trainer_names import rename_references
        rows, references = rename_references(rows, 'battle_dialogue_reference_ids')
        changed.update(references)
    updated = write_messages(header, rows)
    output = rebuild_archive(archive, {RESOURCE: updated})
    result = dict(read_archive(output))
    assert all(result[key] == value for key, value in entries.items() if key != RESOURCE)
    assert all(row == original[i] for i, row in enumerate(rows) if i not in changed)
    return output, {
        'status': 'applied-approved-battle-text-awaiting-Dolphin-visual-check',
        'language': 'pt-BR', 'approved_batches': [b['batch'] for b in approval['batches'] if b['status'] in ('approved-by-user', 'approved-by-user-delegation')],
        'changed_message_ids': sorted(changed), 'changed_message_count': len(changed),
        'exact_duplicate_count': len(duplicate_of),
        'exact_duplicate_of': {str(k): v for k, v in sorted(duplicate_of.items())},
        'untouched_message_count': len(rows)-len(changed),
        'untouched_archive_resources': len(entries)-1,
        'dynamic_variables_formatting_and_pause_markers_preserved': True,
        'unapproved_text_changed': False, 'names_translated': bool(references),
        'trainer_reference_message_ids': sorted(references),
        'pokemon_move_nature_and_item_names_changed': False,
        'source_sha256': sha(archive), 'target_sha256': sha(output),
        'approval_sha256': sha(approval_path.read_bytes()),
        'dolphin_visual_tested': False,
    }


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--trainer-names', action='store_true', help='Pair with the reviewed mes_common build')
    a = p.parse_args()
    if a.original.resolve() == a.output.resolve() or a.output.exists():
        raise ValueError('Choose a new output; never overwrite the original')
    output, report = prepare(a.original.read_bytes(), trainer_names=a.trainer_names)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_bytes(output)
    a.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
