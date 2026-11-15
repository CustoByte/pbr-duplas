"""Reproduce a local layout candidate; never promotes an unfinished review."""
import json
from pathlib import Path
from prepare_campaign_doubles import read_archive,sha
from encounter_expansion import rebuild_archive
from translation.messages import read_messages,write_messages,readable
from ui.dialogue_layout import validate_layout
from ui.dialogue_editorial import validate_editorial
from ui.review_existing_layout import RESOURCES,ALIASES,protected_names


def apply(files,plan,original_common):
    output=dict(files)
    names=protected_names(read_messages(dict(read_archive(original_common))[0x27C10000])[1])
    resources={}
    for filename,entry in plan['resources'].items():
        archive=files[filename]
        if sha(archive)!=entry['base_sha256']:
            raise ValueError('Unexpected layout baseline: '+filename)
        rid=int(entry['resource'],16);data=dict(read_archive(archive))
        header,rows=read_messages(data[rid]);rows=list(rows)
        for index,change in entry['targets_by_id'].items():
            i=int(index)
            if sha(rows[i])!=change['source_sha256'] or change['status'] not in ('bounded','reviewed-no-size-increase'):
                raise ValueError('Unreviewed or changed source row')
            before=readable(rows[i]);after=change['target']
            if change['editorial_rules']:
                rows[i]=validate_editorial(before,after,names,allow_pages=bool(change['extra_pages']))
            else:
                rows[i]=validate_layout(before,after,allow_pages=bool(change['extra_pages']))
        resource=write_messages(header,rows)
        result=rebuild_archive(archive,{rid:resource}) if entry['targets_by_id'] else archive
        if sha(result)!=entry['target_sha256']:
            raise ValueError('Layout candidate is not reproducible: '+filename)
        output[filename]=result;resources[entry['kind']]=resource
    for kind,filenames in ALIASES.items():
        rid=RESOURCES[kind][1]
        for filename in filenames:
            expected=plan['aliases'][filename]
            if sha(files[filename])!=expected['base_sha256']:
                raise ValueError('Unexpected synchronized layout baseline: '+filename)
            archive=output[filename];data=dict(read_archive(archive))
            if data[rid]!=resources[kind]:
                output[filename]=rebuild_archive(archive,{rid:resources[kind]})
    for filename,entry in plan['aliases'].items():
        if sha(output[filename])!=entry['target_sha256']:
            raise ValueError('Synchronized layout differs: '+filename)
    return output
