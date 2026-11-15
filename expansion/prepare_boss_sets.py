"""Render mod-authored Gen 4 boss sets for the freestanding payload."""
import json
from pathlib import Path

def render(path):
    data=json.loads(path.read_text());rows=data['legendary_sets'];seen=set()
    lines=['/* Generated from boss_sets.json: mod-authored Gen 4 battle sets. */',
           'static const struct BossSet { u16 species,moves[4],item; u8 nature,evs[6]; } boss_sets[] = {']
    for row in rows:
        assert 1<=row['species']<=493 and row['species'] not in seen;seen.add(row['species'])
        assert len(set(row['moves']))==4 and all(1<=m<=467 for m in row['moves'])
        assert 0<=row['nature']<25 and len(row['evs'])==6 and sum(row['evs'])<=510
        lines.append(' {'+str(row['species'])+', {'+','.join(map(str,row['moves']))+'}, '+str(row['item'])+', '+str(row['nature'])+', {'+','.join(map(str,row['evs']))+'}},')
    lines+=['};','static const u16 mewtwo_coverage[6]={'+','.join(map(str,data['mewtwo_coverage_moves']))+'};']
    return '\n'.join(lines)+'\n'
if __name__=='__main__':
    p=Path(__file__).with_name('boss_sets.json');p.with_suffix('.h').write_text(render(p))
