"""Build locally from the user's original files; distribute own scripts only.

Default is single-player on the verified v0.9.1 base. An explicit experimental
coop base can be layered, with four-member coop only outside Waterfall.
"""
import argparse,json,struct
from pathlib import Path
from prepare_campaign_doubles import prepare,replace_archive_resource,file_offset,word,sha
from prepare_rental_shiny import prepare_shiny
from monferno_build import prepare_build
from waterfall_fix import prepare as fix_waterfall
from encounter_expansion import build as expand,CAPACITY_EDITS


def build(dol,common,deck,coop_base=None,tournament_rules=True):
    vanilla=dol
    base,table,_=prepare(dol,common,deck)
    base,_=prepare_shiny(base);base,_=prepare_build(base)
    base_common=replace_archive_resource(common,0x1D9C0200,table)
    if coop_base is not None:base=coop_base
    base,base_common,wf=fix_waterfall(base,vanilla,base_common)
    expanded,encounters,policy=expand(deck,common)
    out=bytearray(base)
    for address,(before,after) in CAPACITY_EDITS.items():
        at=file_offset(out,address)
        if word(out,at)!=before:raise ValueError('Candidate-list capacity instruction mismatch')
        struct.pack_into('>I',out,at,after)
    tournament=None
    if tournament_rules:
        from tournament_shiny import prepare as add_tournament_rules
        out,tournament=add_tournament_rules(bytes(out))
    report={'status':'implemented-awaiting-in-game-trade-and-campaign-validation',
        'singleplayer_default':coop_base is None,'waterfall':wf,'encounters':encounters,'tournament_rules':tournament,
        'capacity_slots':2048,'capacity_patch_count':len(CAPACITY_EDITS),
        'output_sha256':{'main.dol':sha(out),'common.fsys':sha(base_common),'deck.fsys':sha(expanded)},
        'complete':False,'dolphin_tested':False,'trade_save_tested':False,
        'shiny_rank_and_bonus_change':'Included with native-verified rank/bonus/status/boss rules' if tournament_rules else 'Disabled for baseline development verification',
        'coop_waterfall_note':'Existing 2+2 cooperative draft does not cover six-member Waterfall; single-player remains supported'}
    return {'main.dol':bytes(out),'common.fsys':base_common,'deck.fsys':expanded},report,policy

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('original-dol','original-common','original-deck','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--coop-base',type=Path)
    a=p.parse_args();files,report,policy=build(a.original_dol.read_bytes(),a.original_common.read_bytes(),a.original_deck.read_bytes(),a.coop_base.read_bytes() if a.coop_base else None)
    if a.output.exists() and any(a.output.iterdir()):raise ValueError('Output directory must be new/empty; original files are never overwritten')
    a.output.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():(a.output/name).write_bytes(data)
    (a.output/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
    (a.output/'species-policy.json').write_text(json.dumps(policy,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('encounters','waterfall')},indent=2))
