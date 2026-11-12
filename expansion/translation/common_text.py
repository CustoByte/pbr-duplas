"""Apply the delegated, reviewed campaign/menu messages with exact source gates."""
import json,re
from pathlib import Path
from translation.trainer_names import prepare as rename_trainers,plan
from translation.messages import read_messages,write_messages,readable,validate_target
from translation.compatible_text import compatible
from prepare_campaign_doubles import read_archive,sha
from encounter_expansion import rebuild_archive

def prepare(archive):
    # Trainer-name preparation verifies the exact original archive and MESG.
    renamed,names=rename_trainers(archive)
    resource=int(plan()['common_resource_id'],16)
    entries=dict(read_archive(renamed))
    header,rows=read_messages(entries[resource]);before=list(rows)
    config=json.loads(Path(__file__).with_name('review-common-next2000.json').read_text())
    if config['status']!='approved-by-user-delegation':raise ValueError('Common translations not ready for publication')
    for key,body in config['targets_by_id'].items():
        i=int(key);source=readable(rows[i]);prefix=re.match(r'^(?:\{F[0-9A-F]{3}\})+',source)[0]
        rows[i]=validate_target(rows[i],prefix+compatible(body))
    changed=[i for i,(a,b) in enumerate(zip(before,rows)) if a!=b]
    assert len(changed)==len(config['targets_by_id'])
    output=rebuild_archive(renamed,{resource:write_messages(header,rows)})
    actual=dict(read_archive(output))
    assert all(actual[k]==v for k,v in entries.items() if k!=resource)
    return output,{'status':'applied-reviewed-full-game-text-awaiting-Dolphin','trainer_names':names,
                   'new_common_messages':len(changed),'changed_message_ids':changed,
                   'controls_preserved':True,'other_resources_unchanged':True,
                   'source_sha256':sha(archive),'target_sha256':sha(output),'dolphin_visual_tested':False}
