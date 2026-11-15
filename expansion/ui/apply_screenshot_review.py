"""Apply a source-gated screenshot hotfix, with unchanged controls and explicit layout review."""
import json
from pathlib import Path
from prepare_campaign_doubles import read_archive,sha
from encounter_expansion import rebuild_archive
from translation.messages import controls,encoded,readable,read_messages,write_messages,validate_target

PLAN=Path(__file__).with_name('screenshot-review-test13.json')

def validate(source,target,index,plan):
    # Alignment anchors are kept exactly; centering this caption uses
    # source-bounded native-font spacing rather than changing the draw origin.
    return validate_target(source,target)


def prepare(archive,plan_path=None):
    plan=json.loads((plan_path or PLAN).read_text())
    if plan['status']!='approved-for-publication':raise ValueError('Screenshot fixes not approved')
    if sha(archive)!=plan['base_archive_sha256']:raise ValueError('Wrong screenshot baseline')
    entries=dict(read_archive(archive));rid=int(plan['resource'],16);h,rows=read_messages(entries[rid])
    for i,target in plan['targets_by_id'].items():rows[int(i)]=validate(rows[int(i)],target,int(i),plan)
    result=rebuild_archive(archive,{rid:write_messages(h,rows)})
    if sha(result)!=plan['candidate_archive_sha256']:raise ValueError('Screenshot overlay is not reproducible')
    return result
