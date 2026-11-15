"""Package the verified Windows GUI over the current game core; no game changes."""
import argparse,hashlib,json,struct,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'expansion'))
from package_release import zipped
VERSION='v0.15.0-launcher-test.1';GAME='v0.14.0-charizard-y-test.2';APP='1.0.0'
def sha(data):return hashlib.sha256(data).hexdigest()
def matches_source(path,digest):
 data=path.read_bytes()
 # Windows checkout converts source text to CRLF; accept only that exact,
 # reversible line-ending change, never any other source-content difference.
 candidates=[data]
 if path.suffix in ('.cs','.xaml','.manifest','.ps1'):
  lf=data.replace(b'\r\n',b'\n');candidates.extend((lf,lf.replace(b'\n',b'\r\n')))
 return any(sha(b)==digest for b in candidates)
def package(build,output):
 base=ROOT/'expansion/packages/charizard-y-test2/aplicador-core.zip'
 if sha(base.read_bytes())!='78e90492bd1f0c97bd26de9c9d174e274a5a45f6dda42a5aa03ed12b21d8610e':raise ValueError('Latest game baseline differs')
 for name in ('tests.json','integration-tests.json'):
  if not json.loads((build/name).read_text(encoding='utf-8-sig'))['passed']:raise ValueError('Windows verification failed: '+name)
 identity=json.loads((build/'build.json').read_text(encoding='utf-8-sig'))
 for name,digest in identity['sources'].items():
  if not matches_source(ROOT/'launcher/windows'/name,digest):raise ValueError('Compiled launcher source changed: '+name)
 for name,digest in identity['installer_sources'].items():
  if not matches_source(ROOT/'expansion'/name,digest):raise ValueError('Tested installer changed: '+name)
 binary=(build/'PBR Launcher.exe').read_bytes()
 if sha(binary)!=identity['executable_sha256']:raise ValueError('Compiled executable differs')
 pe=struct.unpack_from('<I',binary,60)[0]
 if struct.unpack_from('<H',binary,pe+92)[0]!=2:raise ValueError('Requires a Windows GUI executable')
 with zipfile.ZipFile(base) as z:files={n:z.read(n) for n in z.namelist()}
 manifest=json.loads(files['manifesto.json']);assert manifest['mod_version']==GAME
 # The game payload/version remain unchanged; updating the launcher alone never
 # requires reconstructing an already verified RVZ or reading model source ZIPs.
 bootstrap=(build/'PBR Duplas.exe').read_bytes()
 if sha(bootstrap)!=identity['bootstrap_sha256']:raise ValueError('Bootstrap differs')
 manifest['launcher']=dict(version=APP,sha256=sha(binary),bootstrap_sha256=sha(bootstrap))
 manifest['local_graphics']=dict(revision='snivy4-mega3-charizard-y1',import_versions=['v0.14.0-charizard-y-test.1',GAME])
 files['manifesto.json']=(json.dumps(manifest,indent=2)+'\n').encode()
 for name in ('Aplicar-Mod.ps1','Iniciar-Launcher.ps1','Recuperar-Graficos.ps1'):files[name]=(ROOT/'expansion'/name).read_bytes()
 files['launcher/PBR Duplas.exe']=bootstrap
 files['launcher/PBR Launcher.exe']=binary;files['launcher/build-proof.json']=(build/'build.json').read_bytes()
 files['LEIA-ME-LAUNCHER.txt']=('''PBR DUPLAS — LAUNCHER WINDOWS 1.0.0
Execute uma ultima vez o mesmo INICIAR-TESTE-WINDOWS.cmd.
Ele instala a interface e cria atalhos PBR Duplas na Area de Trabalho e menu Iniciar.
Depois, use o atalho: verificar atualizacoes / atualizar / iniciar jogo.
O launcher roda como aplicativo Windows sem CMD, sem Python e sem instalacao administrativa.
A versao do jogo e preservada: nivel 50 balanceado do Charizard Y, Snivy e Mega Lucario.

Atualizacoes de interface nao reconstroem a RVZ. Para atualizacoes do jogo, modelos
ja instalados sao recuperados automaticamente da imagem gerenciada verificada e
guardados em uma biblioteca local persistente. Nenhum seletor de modelo e aberto.
Os caminhos do jogo e Dolphin sao importados do estado existente.
Caso arquivos essenciais estejam ausentes/corrompidos, a janela explica o problema;
o launcher nao baixa uma ROM e nao sobrescreve a instalacao anterior em caso de falha.

O jogo continua sendo executado pelo Dolphin. Os processos de atualizacao rodam
em segundo plano, com progresso e diagnostico na interface. Nao ha alteracao nos saves.
''').replace('\n','\r\n').encode('utf-8-sig')
 # Public core remains owned code/deltas, no ROM/model/texture/save payloads.
 forbidden=('.iso','.rvz','.dol','.fsys','.sdr','.blend','.brres','.fbx','.gltf','.glb','.sav','.png','.jpg')
 if any(n.lower().endswith(forbidden) for n in files):raise ValueError('Game data in public package')
 data=zipped(files);output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(data)
 proof=dict(version=VERSION,game_version=GAME,launcher_version=APP,package_sha256=sha(data),bytes=len(data),executable_sha256=sha(binary),game_replacements_unchanged=True,gameplay_tested=False,windows_verification={n:json.loads((build/n).read_text(encoding='utf-8-sig')) for n in ('tests.json','integration-tests.json')},source_identity=identity)
 output.with_suffix('.json').write_text(json.dumps(proof,indent=2)+'\n');return proof
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(package(a.build,a.output),indent=2))
