"""Apply reviewed overlays over the exact test-10 translation baseline."""
from pathlib import Path
import json
from prepare_campaign_doubles import read_archive,sha
from encounter_expansion import rebuild_archive
from translation.messages import read_messages,write_messages,validate_target
from ui.font_ptbr import prepare as font_prepare

def prepare(archive,name,plans_path=None):
    plans=json.loads((plans_path or Path(__file__).with_name('reviewed-test11.json')).read_text())
    plan=plans[name]
    if sha(archive)!=plan['base_archive_sha256']:raise ValueError('Unexpected translation baseline')
    entries=dict(read_archive(archive));rid=int(plan['resource'],16);header,rows=read_messages(entries[rid])
    for index,target in plan['targets_by_id'].items():rows[int(index)]=validate_target(rows[int(index)],target)
    replacements={rid:write_messages(header,rows)}
    if name=='mes_common.fsys':replacements[0x27C00000]=font_prepare(entries[0x27C00000])[0]
    result=rebuild_archive(archive,replacements)
    if sha(result)!=plan['target_archive_sha256']:raise ValueError('Overlay did not reproduce reviewed archive')
    return result
