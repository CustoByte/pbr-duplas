"""Build owned-code/delta Windows core, preserving all published translation fixes."""
import json,gzip,zipfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'expansion'),str(ROOT/'mod-source')]
from binary_delta import create,apply,sha
from package_release import zipped
VERSION='v0.13.0-mega-lucario-test.1'

def package(integrated,originals,output):
 source=ROOT/'expansion/packages/dialogue-test2/aplicador-core.zip'
 if sha(source.read_bytes())!='032a15a4e80fb08dd8a6988ec061dffa530d4ca580f283bf5e33263568e01526':raise ValueError('Published baseline core differs')
 for name in ('native-proof.json','runtime-proof.json','loading-proof.json','selection-proof.json'):
  if not json.loads((integrated/name).read_text()).get('passed'):raise ValueError('Missing native proof: '+name)
 with zipfile.ZipFile(source) as z:files={n:z.read(n) for n in z.namelist()}
 manifest=json.loads(files['manifesto.json']);manifest.update(mod_version=VERSION,local_mega_assets=True)
 manifest['mega_lucario']=dict(internal_id=502,national_id=448,form='Mega',pass_index=37,slot=0,replaces='Ivysaur',level=50,moves=['Bullet Punch','Close Combat','Aura Sphere','Protect'],ability='Adaptability',item=None,dolphin_tested=False)
 changed={'main.dol','common.fsys','mes_common.fsys','GSfsys.toc'};checks=[]
 for e in manifest['replacements']:
  original_patch=json.loads(gzip.decompress(files[e['package_path']]))
  name=Path(e['installed_path']).name
  matches=[p for p in originals.rglob(name) if sha(p.read_bytes())==original_patch['source_sha256']]
  if not matches:raise ValueError('Missing original '+name)
  before=matches[0].read_bytes()
  if name in changed:
   target=(integrated/name).read_bytes();patch=create(before,target);files.pop(e['package_path'])
   e.update(package_path='patches/mega-'+name.replace('.','-')+'.pbrdelta',sha256=sha(target),patch_sha256=sha(patch));files[e['package_path']]=patch
  result=apply(before,files[e['package_path']]);assert sha(result)==e['sha256']
  checks.append(dict(path=e['installed_path'],target_sha256=sha(result),patched=name in changed))
 manifest['original_sha256']['files/pkx_448.fsys']='e77ee784794c9e24fad632437b8f63709084227848d4e162f8e05eeb2dbce85a'
 files['manifesto.json']=(json.dumps(manifest,indent=2)+'\n').encode()
 for name in ('Aplicar-Mod.ps1','Preparar-Mega-Lucario.ps1'):files[name]=(ROOT/'expansion'/name).read_bytes()
 for p in Path(__file__).resolve().parent.rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix.lower() in ('.py','.c','.json','.md','.txt','.exe'):files[p.relative_to(ROOT).as_posix()]=p.read_bytes()
 text='''MEGA LUCARIO — TESTE 1 — WINDOWS
Execute o mesmo INICIAR-TESTE-WINDOWS.cmd que voce ja utiliza.
O atualizador conserva as 433 correcoes de texto da versao anterior.

No passe inicial da Cyndy, o Mega Lucario ocupa o lugar do Ivysaur.
A Snivy continua no outro slot; o passe Little Battle e o Lucario normal permanecem.
Nivel 50, Adaptability, sem item, natureza neutra.
Golpes: Bullet Punch / Close Combat / Aura Sphere / Protect.
HP 146 / Ataque 181 / Defesa 108 / Atq. Esp. 176 / Def. Esp. 90 / Velocidade 163.
O novo Mega usa aparencia normal para preservar esses atributos; a regra de
shiny dos Pokemon antigos permanece. Nao ha uma textura shiny propria nesta candidata.

Na primeira conversao do Mega, selecione o mega-lucario.zip aprovado na previa.
O caminho e o cache sao lembrados. O Blender/dependencias da Snivy sao reutilizados.
Nao ha modelos/texturas/ROMs/saves neste pacote: a conversao usa seus arquivos locais.
O aplicador reconstrui a partir da imagem ORIGINAL; nao selecione a RVZ ja modificada.
A imagem modificada gerenciada recebe backup; o instalador nao escreve em saves.

Esta e uma candidata experimental. Houve verificacoes offline das rotinas nativas,
selecao de quatro Pokemon, carregamento e geometria. Ainda falta testar a batalha
real no Dolphin do Windows, incluindo efeitos, cameras e transicoes.
Abra a RVZ atualizada pelo inicio normal; estados rapidos antigos nao carregam o novo executavel.
'''
 files['LEIA-ME-MEGA-LUCARIO.txt']=text.replace('\n','\r\n').encode('utf-8-sig')
 forbidden=('.dol','.fsys','.brres','.fbx','.sdr','.blend','.sav','.iso','.rvz','.png','.jpg','.bin')
 if any(n.lower().endswith(forbidden) for n in files):raise ValueError('Protected asset in public core')
 data=zipped(files);output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(data)
 proof=dict(version=VERSION,package_sha256=sha(data),bytes=len(data),archive_checks=checks,game_assets_distributed=False,original_and_save_files_modified=False,dolphin_tested=False,published=False)
 output.with_suffix('.json').write_text(json.dumps(proof,indent=2)+'\n');return proof
if __name__=='__main__':
 integrated,originals,output=map(Path,sys.argv[1:]);print(json.dumps(package(integrated,originals,output),indent=2))
