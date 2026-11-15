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


def build(dol,common,deck,coop_base=None,tournament_rules=True,battle_text=None,trainer_text=None,reviewed_ui=True):
    if trainer_text is not None and battle_text is None:
        raise ValueError('Trainer labels and battle name references must be built together')
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
        from unlimited_coupons import prepare as add_unlimited_coupons
        out,coupons=add_unlimited_coupons(bytes(out))
    report={'status':'implemented-awaiting-in-game-trade-and-campaign-validation',
        'singleplayer_default':coop_base is None,'waterfall':wf,'encounters':encounters,'tournament_rules':tournament,
        'unlimited_coupons':coupons if tournament_rules else None,
        'capacity_slots':2048,'capacity_patch_count':len(CAPACITY_EDITS),
        'output_sha256':{'main.dol':sha(out),'common.fsys':sha(base_common),'deck.fsys':sha(expanded)},
        'complete':False,'dolphin_tested':False,'trade_save_tested':False,
        'shiny_rank_and_bonus_change':'Included with native-verified rank/bonus/status/boss rules' if tournament_rules else 'Disabled for baseline development verification',
        'coop_waterfall_note':'Existing 2+2 cooperative draft does not cover six-member Waterfall; single-player remains supported'}
    files={'main.dol':bytes(out),'common.fsys':base_common,'deck.fsys':expanded}
    if battle_text is not None:
        from translation.apply import prepare as translate_battle
        files['menu_fight_s.fsys'],report['battle_translation']=translate_battle(battle_text,trainer_names=trainer_text is not None)
        report['output_sha256']['menu_fight_s.fsys']=sha(files['menu_fight_s.fsys'])
    if trainer_text is not None:
        from translation.common_text import prepare as translate_common
        files['mes_common.fsys'],report['common_translation']=translate_common(trainer_text)
        report['output_sha256']['mes_common.fsys']=sha(files['mes_common.fsys'])
    if reviewed_ui and trainer_text is not None:
        from ui.apply_review import prepare as apply_ui_review
        for name in ('menu_fight_s.fsys','mes_common.fsys'):
            files[name]=apply_ui_review(files[name],name)
            report['output_sha256'][name]=sha(files[name])
        from ui.apply_screenshot_review import prepare as apply_screenshot_fixes
        files['mes_common.fsys']=apply_screenshot_fixes(files['mes_common.fsys'])
        report['output_sha256']['mes_common.fsys']=sha(files['mes_common.fsys'])
        report['reviewed_ui']={'version':'test.13','native_font_tildes':True,'dolphin_visual_tested':False}
    return files,report,policy

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('original-dol','original-common','original-deck','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--coop-base',type=Path)
    p.add_argument('--original-battle-text',type=Path,help='Original menu_fight_s.fsys for user-approved battle translations')
    p.add_argument('--original-trainer-text',type=Path,help='Original mes_common.fsys for reviewed trainer names; requires battle text')
    p.add_argument('--ui-original-directory',type=Path,help='Extracted original files for synchronized menus, tutorial and title')
    a=p.parse_args();files,report,policy=build(a.original_dol.read_bytes(),a.original_common.read_bytes(),a.original_deck.read_bytes(),a.coop_base.read_bytes() if a.coop_base else None,battle_text=a.original_battle_text.read_bytes() if a.original_battle_text else None,trainer_text=a.original_trainer_text.read_bytes() if a.original_trainer_text else None)
    if a.ui_original_directory:
        from binary_delta import apply as apply_delta
        manifest=json.loads(Path(__file__).with_name('manifesto.json').read_text())
        for entry in manifest['replacements']:
            name=Path(entry['installed_path']).name
            if name in files:continue
            candidates=list(a.ui_original_directory.rglob(name))
            if len(candidates)!=1:raise ValueError('Need exactly one original '+name)
            patch=Path(__file__).with_name('prebuilt')/Path(entry['package_path']).name
            files[name]=apply_delta(candidates[0].read_bytes(),patch.read_bytes())
            report['output_sha256'][name]=sha(files[name])
    if a.output.exists() and any(a.output.iterdir()):raise ValueError('Output directory must be new/empty; original files are never overwritten')
    a.output.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():(a.output/name).write_bytes(data)
    (a.output/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
    (a.output/'species-policy.json').write_text(json.dumps(policy,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('encounters','waterfall')},indent=2))
