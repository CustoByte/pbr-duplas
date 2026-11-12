"""Package mod-owned scripts and binary delta patches only; no game files."""
import argparse,hashlib,io,json,gzip,zipfile
from pathlib import Path
TAG='v0.11.0-full493-test.8'
REPO='https://github.com/CustoByte/pbr-duplas'
FEED='https://raw.githubusercontent.com/CustoByte/pbr-duplas/feat/full493-waterfall/expansion/update-test.json'

def sha(data):return hashlib.sha256(data).hexdigest()
def zipped(files):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(files.items()):
            i=zipfile.ZipInfo(name,(2026,11,12,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16
            z.writestr(i,data)
    data=out.getvalue()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert z.testzip() is None
        assert all(z.read(n)==d for n,d in files.items())
    return data

def package(root,output):
    e=root/'expansion';manifest=json.loads((e/'manifesto.json').read_text())
    core={name:(e/name).read_bytes() for name in ('Aplicar-Mod.ps1','Aplicar-Delta.ps1','manifesto.json')}
    for entry in manifest['replacements']:
        data=(e/'prebuilt'/Path(entry['package_path']).name).read_bytes();doc=json.loads(gzip.decompress(data))
        assert sha(data)==entry['patch_sha256'] and doc['target_sha256']==entry['sha256']
        assert doc['source_sha256']==manifest['original_sha256'][entry['installed_path']]
        core[entry['package_path']]=data
    assert all(not n.endswith(('.dol','.fsys','.sav','.iso','.rvz','.bin')) for n in core)
    core_data=zipped(core)
    feed={'schema':1,'version':TAG,'package_url':REPO+'/releases/download/'+TAG+'/aplicador-core.zip',
          'package_sha256':sha(core_data),'save_policy':'Original image read only; same normal Dolphin save directory',
          'channel':'full493-test','dolphin_tested':False}
    cmd=('@echo off\r\nsetlocal\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Atualizar-Iniciar.ps1" -FeedUrl "'+FEED+'"\r\nif errorlevel 1 pause\r\nendlocal\r\n').encode('ascii')
    readme=('PBR FULL493 - TESTE WINDOWS\r\n\r\n'
      'Se ja tem o aplicador: copie INICIAR-TESTE-WINDOWS.cmd para a mesma pasta de Atualizar-Iniciar.ps1.\r\n'
      'Abra esse CMD. Os caminhos da ROM original, Dolphin e saida ja salvos serao reutilizados.\r\n'
      'Este CMD escolhe o canal novo de teste; o CMD antigo continua no canal anterior.\r\n'
      'Nao precisa baixar o aplicador inteiro outra vez. Use o mesmo CMD de teste nas proximas atualizacoes.\r\n\r\n'
      'Se nao tem o aplicador neste PC: extraia PBR-Full493-Windows.zip e abra INICIAR-TESTE-WINDOWS.cmd.\r\n'
      'Na primeira vez selecione a pasta da ROM original USA RPBE01 revisao 0 e o DolphinTool.exe do Dolphin.\r\n'
      'Feche o Dolphin antes de atualizar. Carregue o save DO JOGO; nao use save state de outra versao.\r\n'
      'A ROM original e os saves nao sao alterados pelo aplicador. A RVZ anterior e preservada em uma atualizacao.\r\n\r\n'
      'Candidata single-player com Full493, Waterfall, shinies, chefes e traducao parcial.\r\n'
      'Inclui anuncios de golpes, textos aprovados e 19 nomes de treinadores; traducao incompleta.\r\n'
      'Os testes nativos passaram; batalhas reais, visual, trocas e salvar/carregar ainda precisam do Dolphin.\r\n'
      'Leia TESTAR.md na release. O canal estavel/Mac anterior nao foi substituido.\r\n').encode('ascii')
    starter={'PBR-Full493/INICIAR-TESTE-WINDOWS.cmd':cmd,
             'PBR-Full493/Atualizar-Iniciar.ps1':(root/'src/Atualizar-Iniciar.ps1').read_bytes(),
             'PBR-Full493/base.zip':core_data,'PBR-Full493/base.sha256':(sha(core_data)+'\n').encode(),
             'PBR-Full493/LEIA-ME.txt':readme}
    files={'aplicador-core.zip':core_data,'update.json':(json.dumps(feed,indent=2)+'\n').encode(),
           'INICIAR-TESTE-WINDOWS.cmd':cmd,'PBR-Full493-Windows.zip':zipped(starter),'LEIA-ME.txt':readme,
           'TESTAR.md':(e/'TESTAR.md').read_bytes()}
    files['SHA256SUMS.txt']=''.join(sha(d)+'  '+n+'\n' for n,d in sorted(files.items())).encode()
    output.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():(output/name).write_bytes(data)
    return {'tag':TAG,'core_sha256':sha(core_data),'assets':{n:{'bytes':len(d),'sha256':sha(d)} for n,d in files.items()},'feed':feed}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(package(a.root,a.output),indent=2))
