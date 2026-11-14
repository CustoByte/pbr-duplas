"""Select the first thousand new short trainer message IDs for editorial review."""
import json
from pathlib import Path
from prepare_campaign_doubles import read_archive
from translation.messages import RESOURCE, read_messages, readable, TOKEN

def select(original, drafts, approval):
    rows = read_messages(dict(read_archive(original))[RESOURCE])[1]
    used = {rows[i] for b in approval['batches'] for e in b['entries'] for i in e['ids']}
    used.update(rows[i] for i in (3923,3925,4359,4361,4362,4375,4377,4378,
                                8276,4940,7416,7808,5848,5960,8036))
    candidates = [(s, x) for s, x in drafts.items()
                  if all(rows[i] not in used for i in x['ids']) and len(x['target']) < 100]
    candidates.sort(key=lambda pair: len(pair[1]['target']))
    selected = []
    count = 0
    for source, draft in candidates:
        if count + len(draft['ids']) > 1000:
            continue
        selected.append((source, draft))
        count += len(draft['ids'])
        if count == 1000:
            break
    assert count == 1000
    return rows, selected
