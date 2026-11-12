"""Rebuild distributable candidate from public stable core and own PPC payload.

No ROM download or private capture is used. Native replay reports are published
separately; this release step checks identity/packaging, not gameplay.
"""
import argparse,base64,io,json,shutil,zipfile
from pathlib import Path
from prepare_campaign_doubles import sha
from prepare_coop_draft import prepare_draft
from package_coop_candidate import package

STABLE_SHA='5808b2f055209d09b3170b29b27fd36216bb4f3dd473bfaaf0a32c9cfc925c0e'

def run(stable,root,work,output):
    assert sha(stable.read_bytes())==STABLE_SHA,'Unexpected stable core'
    coop=root/'coop';manifest=json.loads((coop/'prebuilt/draft-symbols.json').read_text())
    assert sha((coop/'coop_draft.c').read_bytes())==manifest['source_sha256']
    payload=base64.b64decode((coop/'prebuilt/payload.base64').read_text(),validate=False)
    assert sha(payload)==manifest['payload_sha256']
    with zipfile.ZipFile(stable) as z:source=z.read('mod/main.dol')
    work.mkdir(parents=True,exist_ok=True)
    (work/'draft.bin').write_bytes(payload)
    (work/'draft-symbols.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for enabled,name in ((False,'main.dol'),(True,'main-enabled.dol')):
        (work/name).write_bytes(prepare_draft(source,payload,manifest,activate=enabled))
    for key,name in (('draft','SELECAO'),('switch','TROCAS'),('target','ALVOS'),('finish','ENCERRAMENTO'),('activation','ATIVACAO')):
        shutil.copyfile(coop/f'VERIFICACAO-{name}-COOP.json',work/f'verification-{key}.json')
    feed,audit=package(stable,work,root,output,'v0.10.0-coop-test.1')
    assert feed==json.loads((coop/'update-test.json').read_text()),'Published feed differs from packaged candidate'
    print(json.dumps(audit,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('stable-core','root','work','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();run(a.stable_core,a.root,a.work,a.output)
