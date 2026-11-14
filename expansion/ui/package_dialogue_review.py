"""Build a local Windows translation-review candidate from owned code/deltas.

Never publishes or changes the player feed. Original game archives stay local.
"""
import argparse
import gzip
import io
import json
import zipfile
from pathlib import Path
from binary_delta import apply,create,sha
from package_release import zipped

ROOT=Path(__file__).resolve().parents[2]
CORE_SHA='0120afc47a08b539a4d27351c4a5ef8eba332ca757433645c094efd225dbd4c2'


def package(review,originals,output,version='v0.12.1-dialogue-review.1'):
    source=ROOT/'expansion/packages/snivy-test4/aplicador-core.zip'
    if sha(source.read_bytes())!=CORE_SHA:
        raise ValueError('Unexpected Snivy baseline core')
    with zipfile.ZipFile(source) as archive:
        files={name:archive.read(name) for name in archive.namelist()}
    plan=json.loads((review/'plan.json').read_text())
    report=json.loads((review/'audit.json').read_text())
    manifest=json.loads(files['manifesto.json'])
    manifest['mod_version']=version
    manifest['dialogue_review']={'changed_messages':report['changed_count'],'new_translations':0,
        'extra_continuations':report['extra_pages'],'review_complete':False,'dolphin_visual_tested':False}
    reviewed=set(plan['resources'])|set(plan['aliases'])
    checks=[]
    for entry in manifest['replacements']:
        name=Path(entry['installed_path']).name
        old_patch=files[entry['package_path']]
        document=json.loads(gzip.decompress(old_patch))
        candidates=list(originals.rglob(name))
        matches=[p for p in candidates if sha(p.read_bytes())==document['source_sha256']]
        if not matches:
            raise ValueError('Missing exact original '+name)
        original=matches[0].read_bytes()
        previous=apply(original,old_patch)
        if name in reviewed:
            expected=plan['resources'].get(name,plan['aliases'].get(name))
            if sha(previous)!=expected['base_sha256']:
                raise ValueError('Review does not match installed baseline '+name)
            target=(review/name).read_bytes()
            if sha(target)!=expected['target_sha256']:
                raise ValueError('Review result changed '+name)
            patch=create(original,target)
            files[entry['package_path']]=patch
            entry['patch_sha256']=sha(patch);entry['sha256']=sha(target)
        else:
            target=previous
        assert apply(original,files[entry['package_path']])==target
        checks.append(dict(name=name,delta_roundtrip=True,changed=previous!=target))
    files['manifesto.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
    # Same saved original/tool/output/source paths as the existing applicator.
    # A managed output is backed up by the applicator; saves are never opened.
    files['INICIAR-TESTE-WINDOWS.cmd']=(
        '@echo off\r\nsetlocal\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Aplicar-Mod.ps1" '
        '-StatePath "%LOCALAPPDATA%\\PBR-Duplas\\estado.json"\r\nif errorlevel 1 pause\r\nendlocal\r\n').encode('ascii')
    readme=f'''PBR — REVISÃO LOCAL DOS DIÁLOGOS\nVersão: {version}\n\nExtraia toda a pasta, feche o Dolphin e abra INICIAR-TESTE-WINDOWS.cmd.\nOs caminhos salvos pelo aplicador anterior serão reutilizados.\nSe não houver configuração neste PC, escolha a imagem ORIGINAL do PBR USA r0 e o Dolphin.\nA imagem original não é substituída. A cópia modificada gerenciada recebe backup.\nOs saves normais do Dolphin não são abertos ou modificados. Evite estados rápidos de outras builds.\n\nEsta candidata reúne {report['changed_count']} correções de textos já traduzidos,\ncom {report['extra_pages']} continuações adicionais. Nenhuma tradução inédita.\nInclui revisão contextual das falas da Anna e dos menus principais.\nA revisão global ainda está em andamento; não equivale a todo texto visualmente validado.\n\nO modelo, animações e passes da Snivy e os demais mods da base test.4 permanecem.\nA conversão local já existente pode ser reutilizada pelo cache; se necessário, o\naplicador pede seu Tsutarja.brres. Não há ROMs, modelos ou texturas neste pacote.\n\nEste pacote local não publica no GitHub nem altera o canal automático.\nUse o CMD desta pasta para testar esta candidata. O atualizador antigo ainda consulta\no canal publicado anterior e pode restaurar aquela versão se executado.\n'''
    files['LEIA-ME-REVISAO.txt']=readme.replace('\n','\r\n').encode('utf-8-sig')
    forbidden=('.dol','.fsys','.brres','.sdr','.blend','.sav','.iso','.rvz','.png','.jpg','.bin')
    if any(name.lower().endswith(forbidden) for name in files):
        raise ValueError('Protected game asset in public package')
    data=zipped({'PBR-Revisao-Dialogos/'+name:value for name,value in files.items()})
    output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(data)
    proof=dict(version=version,package_sha256=sha(data),archive_checks=checks,
               changed_messages=report['changed_count'],extra_pages=report['extra_pages'],new_translations=0,
               game_assets_distributed=False,published=False,review_complete=False,dolphin_visual_tested=False)
    output.with_suffix('.json').write_text(json.dumps(proof,indent=2)+'\n')
    return proof


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('review','originals','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();print(json.dumps(package(a.review,a.originals,a.output),indent=2))
