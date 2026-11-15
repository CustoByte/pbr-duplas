"""Replace only reviewed trainer labels and explicit name references."""
import json, re
from pathlib import Path
from encounter_expansion import rebuild_archive
from prepare_campaign_doubles import read_archive, sha
from translation.messages import read_messages, write_messages, readable, validate_target

PLAN = Path(__file__).with_name('trainer-names.json')
APPROVED = {'approved-by-user', 'approved-by-user-delegation'}


def plan():
    return json.loads(PLAN.read_text())


def approved_entries():
    return [e for e in plan()['entries'] if e['approval'] in APPROVED and e['replacement'] is not None]


def rename_references(rows, field):
    output = list(rows)
    changed = set()
    for entry in approved_entries():
        if entry['replacement'] == entry['original']:
            continue
        pattern = re.compile(r'(?<!\w)' + re.escape(entry['original']) + r'(?!\w)')
        for index in entry.get(field, []):
            source = readable(output[index])
            target, count = pattern.subn(entry['replacement'], source)
            if not count:
                raise ValueError(f'Expected trainer reference absent at {field}:{index}')
            output[index] = validate_target(output[index], target)
            changed.add(index)
    return output, changed


def prepare(archive):
    config = plan()
    if sha(archive) != config['common_archive_sha256']:
        raise ValueError('Unsupported original mes_common.fsys')
    resource_id = int(config['common_resource_id'], 16)
    entries = dict(read_archive(archive))
    source = entries[resource_id]
    if sha(source) != config['common_resource_sha256']:
        raise ValueError('Unsupported original common MESG')
    header, original = read_messages(source)
    rows = list(original)
    changed = set()
    kept = []
    replacements = []
    for entry in approved_entries():
        index = entry['common_message_index']
        expected = '{F001}{F101}' + entry['original']
        if readable(original[index]) != expected:
            raise ValueError('Trainer label mismatch; refusing a broad text replacement')
        if entry['replacement'] == entry['original']:
            kept.append(index)
            continue
        if index in changed:
            raise ValueError('Duplicate trainer name mapping')
        rows[index] = validate_target(original[index], '{F001}{F101}' + entry['replacement'])
        changed.add(index)
        replacements.append({'original': entry['original'], 'replacement': entry['replacement'],
                             'message_index': index, 'native_message_id': entry['native_message_id']})
    rows, references = rename_references(rows, 'common_reference_ids')
    changed.update(references)
    output = rebuild_archive(archive, {resource_id: write_messages(header, rows)})
    actual = dict(read_archive(output))
    assert all(actual[key] == value for key, value in entries.items() if key != resource_id)
    assert all(row == original[i] for i, row in enumerate(rows) if i not in changed)
    assert all(rows[i] == original[i] for i in kept)
    return output, {
        'status': 'applied-reviewed-trainer-names-awaiting-Dolphin',
        'reviewed_names': len(approved_entries()), 'renamed_trainers': len(replacements),
        'replacements': replacements, 'kept_original_message_indices': kept,
        'changed_message_indices': sorted(changed), 'name_reference_indices': sorted(references),
        'untouched_messages': len(rows)-len(changed), 'other_resources_unchanged': True,
        'pokemon_move_nature_and_item_names_changed': False,
        'trainer_models_teams_and_progression_changed': False,
        'direct_save_file_edits': False, 'source_sha256': sha(archive), 'target_sha256': sha(output),
        'dolphin_visual_tested': False,
    }
