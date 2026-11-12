"""Package an opt-in cooperative test candidate using the verified stable core.

No ROM, save, capture or RAM is accepted/exported. The development default stays
disabled; activation is an explicit five-byte change in the mod's own state.
The stable/latest update channel is never changed by this script.
"""
import argparse,io,json,zipfile
from pathlib import Path
from prepare_campaign_doubles import sha
from prepare_coop_draft import prepare_draft
REPO='https://github.com/CustoByte/pbr-duplas'

def zip_bytes(contents):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in contents.items():
            info=zipfile.ZipInfo(name,date_time=(2026,11,12,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=(0o100755 if name.endswith('.command') else 0o100644)<<16
            z.writestr(info,data)
    result=stream.getvalue()
    with zipfile.ZipFile(io.BytesIO(result)) as z:
        assert not z.testzip() and len(z.namelist())==len(contents)
        for name,data in contents.items():assert z.read(name)==data
    return result

FEED='https://raw.githubusercontent.com/CustoByte/pbr-duplas/feat/coop-input-foundation/coop/update-test.json'

def package(stable_core,build,public,output,release):
    with zipfile.ZipFile(stable_core) as z:
        assert not z.testzip();core={name:z.read(name) for name in z.namelist()}
    base=core['mod/main.dol'];manifest=json.loads(core['manifesto.json'])
    payload=(build/'draft.bin').read_bytes();symbols=json.loads((build/'draft-symbols.json').read_text())
    disabled=prepare_draft(base,payload,symbols)
    enabled=prepare_draft(base,payload,symbols,activate=True)
    assert disabled==(build/'main.dol').read_bytes()
    assert enabled==(build/'main-enabled.dol').read_bytes()
    reports={}
    for name in ('draft','switch','target','finish','activation'):
        report=json.loads((build/f'verification-{name}.json').read_text())
        assert report['status']=='passed'
        assert report.get('prototype_sha256',report.get('disabled_sha256'))==sha(disabled)
        reports[name]=report
    assert reports['activation']['activated_sha256']==sha(enabled)
    core['mod/main.dol']=enabled
    manifest['mod_version']=release
    manifest['coop_experimental']=True
    manifest['dolphin_gameplay_tested']=False
    for item in manifest['replacements']:
        item['sha256']=sha(core[item['package_path']])
    core['manifesto.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    ps=core['Aplicar-Mod.ps1'].decode('utf-8-sig')
    assert " + '-Duplas.rvz'" in ps and 'coop_included = $false' in ps
    ps=ps.replace(" + '-Duplas.rvz'"," + '-Duplas-Coop-Teste.rvz'").replace('coop_included = $false','coop_included = $true')
    core['Aplicar-Mod.ps1']=ps.encode('utf-8-sig')
    for key,report in reports.items():core[f'verificacao/{key}.json']=(json.dumps(report,indent=2)+'\n').encode()
    core['LEIA-ME-COOP.md']=(public/'coop/TESTAR-COOP.md').read_bytes()
    archive=zip_bytes(core)
    feed={'schema':1,'version':release,'package_url':f'{REPO}/releases/download/{release}/aplicador-core.zip',
          'package_sha256':sha(archive),'save_policy':'Same RPBE01 game identity; original ROM and Dolphin user data preserved by applicator',
          'coop_experimental':True,'dolphin_gameplay_tested':False,'netplay_tested':False}
    cmd='''@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Atualizar-Iniciar.ps1" -FeedUrl "'''+FEED+'''" -DataRoot "%LOCALAPPDATA%\\PBR-Duplas-Coop-Teste"
if errorlevel 1 pause
endlocal
'''
    windows={'PBR-Coop-Teste/INICIAR-COOP-WINDOWS.cmd':cmd.replace('\n','\r\n').encode('ascii'),
             'PBR-Coop-Teste/Atualizar-Iniciar.ps1':(public/'src/Atualizar-Iniciar.ps1').read_bytes(),
             'PBR-Coop-Teste/base.zip':archive,'PBR-Coop-Teste/base.sha256':(sha(archive)+'\n').encode(),
             'PBR-Coop-Teste/LEIA-ME-COOP.md':core['LEIA-ME-COOP.md']}
    starter=(public/'mac-aplicador/INICIAR-MAC.command').read_text()
    starter=starter.replace('Support/PBR-Duplas}', 'Support/PBR-Duplas-Coop-Teste}')
    starter=starter.replace('https://github.com/CustoByte/pbr-duplas/releases/latest/download/update.json',FEED)
    assert '  /bin/bash "$PBR_RUN/aplicar-mac.sh" "$@"' in starter
    starter=starter.replace('  /bin/bash "$PBR_RUN/aplicar-mac.sh" "$@"','  export PBR_DATA_ROOT="$PBR_DATA"\n  /bin/bash "$PBR_RUN/aplicar-mac.sh" "$@"')
    mac={'PBR-Coop-Teste-Mac/INICIAR-COOP-MAC.command':starter.encode(),
         'PBR-Coop-Teste-Mac/base.zip':archive,'PBR-Coop-Teste-Mac/base.sha256':(sha(archive)+'\n').encode(),
         'PBR-Coop-Teste-Mac/LEIA-ME-COOP.md':core['LEIA-ME-COOP.md']}
    files={'aplicador-core.zip':archive,'PBR-Coop-Teste-Windows.zip':zip_bytes(windows),
           'PBR-Coop-Teste-Mac.zip':zip_bytes(mac),'update.json':(json.dumps(feed,indent=2)+'\n').encode()}
    audit={'status':'packaged-for-manual-validation','release':release,'activated_sha256':sha(enabled),
           'disabled_sha256':sha(disabled),'stable_common_preserved':True,'stable_feed_unchanged':True,
           'dolphin_gameplay_tested':False,'netplay_tested':False,
           'files':{n:{'bytes':len(d),'sha256':sha(d)} for n,d in files.items()},
           'limits':['Underlying applicators previously tested; this candidate package has structural checks only',
                     'No full ROM, rendering, physical-controller or NetPlay validation in this environment']}
    files['VERIFICACAO-PACOTE.json']=(json.dumps(audit,indent=2)+'\n').encode()
    files['SHA256SUMS.txt']=''.join(sha(d)+'  '+n+'\n' for n,d in files.items()).encode()
    output.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():(output/name).write_bytes(data)
    return feed,audit

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('stable-core','build','public','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--release',required=True);a=p.parse_args()
    feed,audit=package(a.stable_core,a.build,a.public,a.output,a.release)
    print(json.dumps(audit,indent=2))
