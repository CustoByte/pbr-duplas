"""Audit native generated sets against Gen 3/4 learn sources and native abilities.

Reads cached Pokemon Showdown data as text only (never executes TypeScript).
Gen 3 sources are accepted via Pal Park; Gen 1/2-only and Gen 5+ sources are not.
This checks each move's learnability, not simultaneous event/egg constraints.
"""
import argparse,json,re
from pathlib import Path
from prepare_campaign_doubles import read_archive,sha
from verify_sets import verify as construct

def blocks(path):
    source=path.read_text()
    starts=list(re.finditer(r'^\t(?:"([a-z0-9]+)"|([a-z0-9]+)): \{\s*$',source,re.M))
    return {(m[1] or m[2]):source[m.end():starts[i+1].start() if i+1<len(starts) else len(source)] for i,m in enumerate(starts)}

def normalize(name):return re.sub('[^a-z0-9]','',name.lower())

def verify(capture,dol,deck,common,policy,reference):
    dex=blocks(reference/'pokedex.ts');learn=blocks(reference/'learnsets.ts');moves=blocks(reference/'moves.ts')
    species={};move_ids={}
    for key,body in dex.items():
        n=re.search(r'^\t\tnum: (\d+),',body,re.M)
        if n and not re.search(r'^\t\tforme:',body,re.M):species[int(n[1])]=key
    for key,body in moves.items():
        n=re.search(r'^\t\tnum: (\d+),',body,re.M)
        if n and (int(n[1]) not in move_ids or key=='hiddenpower'):move_ids[int(n[1])]=key
    assert all(s in species for s in range(1,494))
    def legal_moves(key,visited=None):
        visited=set() if visited is None else visited
        if key in visited:return set()
        visited.add(key);allowed=set()
        for m in re.finditer(r'^\t\t\t([a-z0-9]+): \[([^\n]*)\]',learn.get(key,''),re.M):
            if re.search(r'"[34][A-Z]',m[2]):allowed.add(m[1])
        pre=re.search(r'^\t\tprevo: "([^"]+)"',dex[key],re.M)
        if pre:allowed|=legal_moves(normalize(pre[1]),visited)
        return allowed
    table=dict(read_archive(common))[0x00810200];failures=[];checked=0;slots=0
    def observer(h,mon,s):
        nonlocal checked,slots
        learned=legal_moves(species[s]);allowed=set(table[48+s*52+48:48+s*52+50])
        ability=h.call(0x803DE52C,(mon,0xA,0))
        if ability not in allowed:failures.append({'species':s,'ability':ability,'allowed':sorted(allowed)})
        for field in range(0x36,0x3A):
            move=h.call(0x803DE52C,(mon,field,0))
            if not move:continue
            slots+=1;name=move_ids.get(move)
            if name not in learned and not (s==235 and 1<=move<=467 and move not in (165,448)):failures.append({'species':s,'move':move,'move_key':name})
        checked+=1
    construct(capture,dol,deck,policy,constructed=observer)
    return {'status':'passed-individual-move-sources' if not failures else 'needs-legality-review',
            'species_checked':checked,'occupied_move_slots_checked':slots,'failures':failures,
            'reference':'https://github.com/smogon/pokemon-showdown/tree/master/data',
            'reference_file_sha256':{name:sha((reference/(name+'.ts')).read_bytes()) for name in ('pokedex','learnsets','moves')},
            'dol_sha256':sha(dol),'deck_sha256':sha(deck),
            'limits':['One native generated set per species','Does not prove simultaneous egg/event-source compatibility',
                      'Original dynamic move resolver remains native; additional seeds can choose other legal moves',
                      'No rendered battle or save/load']}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('capture','dol','deck','common','policy','reference','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=verify(a.capture,a.dol.read_bytes(),a.deck.read_bytes(),a.common.read_bytes(),json.loads(a.policy.read_text()),a.reference)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
