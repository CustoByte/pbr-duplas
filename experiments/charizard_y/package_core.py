"""Build cumulative owned-code/delta core on the latest published Mega release."""
import gzip,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'expansion'),str(ROOT/'mod-source')]
from binary_delta import create,apply,sha
from package_release import zipped
VERSION='v0.14.0-charizard-y-test.1'

def package(integrated,originals,output):
 source=ROOT/'expansion/packages/mega-lucario-test3/aplicador-core.zip'
 if sha(source.read_bytes())!='caae464c41998e4c5243b96b97ef271096eb955380934dfec1bce4ad20722063':raise ValueError('Published baseline differs')
 for name in ('pass-proof.json','runtime-proof.json','selection-proof.json','names-proof.json','loading-proof.json'):
  if not json.loads((integrated/name).read_text()).get('passed'):raise ValueError('Missing proof: '+name)
 with zipfile.ZipFile(source) as z:files={n:z.read(n) for n in z.namelist()}
 manifest=json.loads(files['manifesto.json']);manifest.update(mod_version=VERSION,local_charizard_y_assets=True)
 manifest['charizard_y']=dict(internal_id=503,national_id=6,form='mega_y',pass_index=37,slot=2,replaces='Wartortle',level=50,moves=['Flamethrower','Air Slash','Solar Beam','Protect'],ability='Drought',nature='Timid',item=None,stats_hp_atk_def_spatk_spdef_speed=[154,111,98,211,135,167],npc_randomization_enabled=False,dolphin_tested=False,tail_flame_matches_preview_verified=False)
 checks=[];changed={'main.dol','common.fsys','mes_common.fsys','GSfsys.toc'}
 for e in manifest['replacements']:
  name=Path(e['installed_path']).name;old=json.loads(gzip.decompress(files[e['package_path']]))
  candidates=list(originals.rglob(name));before=next((p.read_bytes() for p in candidates if sha(p.read_bytes())==old['source_sha256']),None)
  if before is None:raise ValueError('Missing audited original: '+name)
  if name in changed:
   target=(integrated/name).read_bytes();patch=create(before,target);files.pop(e['package_path']);e.update(package_path='patches/charizard-y-'+name.replace('.','-')+'.pbrdelta',sha256=sha(target),patch_sha256=sha(patch));files[e['package_path']]=patch
  result=apply(before,files[e['package_path']]);assert sha(result)==e['sha256'];checks.append(dict(path=e['installed_path'],sha256=sha(result),patched=name in changed))
 manifest['original_sha256']['files/pkx_006.fsys']='ada980b34af54f99c4db863db050605c9f8376de0591735c4c60b04b2de5639b'
 files['manifesto.json']=(json.dumps(manifest,indent=2)+'\n').encode()
 for n in ('Aplicar-Mod.ps1','Preparar-Charizard-Y.ps1'):files[n]=(ROOT/'expansion'/n).read_bytes()
 for p in Path(__file__).resolve().parent.glob('*'):
  if p.suffix in ('.py','.c','.json','.md'):files[p.relative_to(ROOT).as_posix()]=p.read_bytes()
 for n in ('import_models.py','import_donor.py','retarget_motion.py','retarget-plan.json','export_charizard_y.py','verify_charizard_y_sdr.py'):files['experiments/pokemon_batch/'+n]=(ROOT/'experiments/pokemon_batch'/n).read_bytes()
 files['LEIA-ME-CHARIZARD-Y.txt']=('''MEGA CHARIZARD Y — CANDIDATA WINDOWS\nUse o mesmo INICIAR-TESTE-WINDOWS.cmd. Selecione seu ZIP mega-charizard-y-pokemon.zip quando solicitado.\nNo passe da Cyndy, substitui Wartortle; Snivy e Mega Lucario permanecem.\nNivel 50 / Timid / Drought / sem item.\nFlamethrower / Air Slash / Solar Beam / Protect.\nHP154 / ATK111 / DEF98 / SPATK211 / SPDEF135 / SPEED167.\nAleatoriedade de NPCs NAO foi habilitada. Traducoes anteriores preservadas.\nModelo convertido localmente; nenhum modelo, ROM ou save e distribuido.\nTestes offline: entrega, nomes, retratos, selecao e alocacao dos tres modelos.\nAinda sem teste de batalha/renderizacao real no Dolphin do Windows.\nA chama procedural da previa nao tem equivalencia visual confirmada no jogo.\nAbra a imagem pelo inicio normal, sem carregar estados rapidos de builds anteriores.\n''').replace('\n','\r\n').encode('utf-8-sig')
 forbidden=('.dol','.fsys','.brres','.fbx','.sdr','.blend','.sav','.iso','.rvz','.png','.jpg','.bin','.gltf','.glb')
 if any(n.lower().endswith(forbidden) for n in files):raise ValueError('Protected assets in core')
 data=zipped(files);output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(data)
 proof=dict(version=VERSION,package_sha256=sha(data),bytes=len(data),archive_checks=checks,translation_replacements_preserved=True,game_assets_distributed=False,dolphin_tested=False,published=False)
 output.with_suffix('.json').write_text(json.dumps(proof,indent=2)+'\n');return proof
if __name__=='__main__':
 i,o,out=map(Path,sys.argv[1:]);print(json.dumps(package(i,o,out),indent=2))
