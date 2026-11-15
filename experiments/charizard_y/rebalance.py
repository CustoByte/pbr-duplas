"""Rebuild balance/data layers, preserving the last verified graphics verbatim."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(HERE),str(ROOT/'mod-source'),str(ROOT/'expansion'),str(ROOT/'experiments/snivy')]
from registrations import prepare,ARCHIVE
from runtime_layer import compile_payload,patch
from prepare_campaign_doubles import read_archive,sha
from encounter_expansion import rebuild_archive
from catalog import append_archive

def build(baseline,previous,reference,toolchain,output):
 if output.exists():raise ValueError('Use a fresh output directory')
 graphics=(previous/'pkx_503.fsys').read_bytes();scenes=dict(read_archive(graphics));assert set(scenes)=={0x73EC0400,0x63EC0400}
 common=(baseline/'common.fsys').read_bytes();mes=(baseline/'mes_common.fsys').read_bytes();old=dict(read_archive(common))
 updates,message=prepare(old,dict(read_archive(mes))[0x27C10000],scenes[0x73EC0400],reference.read_bytes())
 output.mkdir(parents=True);payload=compile_payload((baseline/'main.dol').read_bytes(),output/'payload',toolchain);dol,runtime=patch((baseline/'main.dol').read_bytes(),payload)
 files={'main.dol':dol,'common.fsys':rebuild_archive(common,updates),'mes_common.fsys':rebuild_archive(mes,{0x27C10000:message}),'GSfsys.toc':append_archive((baseline/'GSfsys.toc').read_bytes(),ARCHIVE,'pkx_503')}
 for n in ('pkx_503.fsys','menu_face.fsys','menu_pokemon.fsys'):files[n]=(previous/n).read_bytes()
 # A balance-only update changes no model, atlas, text, catalog or animation row.
 for n in files.keys()-{'main.dol','common.fsys'}:assert files[n]==(previous/n).read_bytes(),n
 prior=dict(read_archive((previous/'common.fsys').read_bytes()));now=dict(read_archive(files['common.fsys']))
 assert all(now[k]==v for k,v in prior.items() if k!=0x00810200)
 before=prior[0x00810200];after=now[0x00810200];at=48+503*52
 assert before[:at]==after[:at] and before[at+52:]==after[at+52:]
 for n,data in files.items():(output/n).write_bytes(data)
 report=dict(outputs={n:dict(bytes=len(b),sha256=sha(b)) for n,b in files.items()},runtime=runtime,graphics_and_translation_unchanged=True,only_species_503_base_stats_changed=True,npc_randomization_enabled=False,gameplay_verified=False)
 (output/'integration-report.json').write_text(json.dumps(report,indent=2)+'\n')
 return report
if __name__=='__main__':
 b,p,r,t,o=map(Path,sys.argv[1:]);print(json.dumps(build(b,p,r,t,o),indent=2))
