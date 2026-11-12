"""Expand compatible native DCKP pools; no invented acquisition mechanics.

All stock records/trainers stay at their original indices. New variants append
behind them, using the native rank/level/theme selector. Fixed trainer ranges,
AI, progression flags and Trade Battle code are not changed by this module.
This does not prove full trade/save/gameplay behavior.
"""
import argparse,collections,json,struct,random
from pathlib import Path
from prepare_campaign_doubles import read_archive,word,sha,DECK_SHA256,COMMON_SHA256,file_offset
from lzss_encode import encode
from team_series_asm import d

MYTHICAL_LEGENDARY={144,145,146,150,151,243,244,245,249,250,251,377,378,379,380,381,382,383,384,385,386,
                   480,481,482,483,484,485,486,487,488,489,490,491,492,493}
EXTRA_MOVES={251:(94,105,246,202),489:(57,58,240,182),491:(399,464,138,182),
             492:(465,412,235,182),493:(449,105,414,182)}
# All three native scratch-list constructors use capacity 500 / 500*4 bytes.
# Both must grow together; no instruction encoding or trainer count truncation.
CAPACITY_EDITS={0x8017C78C:(d(14,31,0,500),d(14,31,0,2048)),
 0x8017C7A0:(d(14,3,0,2000),d(14,3,0,8192)),
 0x8017E36C:(d(14,31,0,500),d(14,31,0,2048)),
 0x8017E390:(d(14,3,0,2000),d(14,3,0,8192)),
 0x8017E5D4:(d(14,0,0,500),d(14,0,0,2048)),
 0x8017E5FC:(d(14,3,0,2000),d(14,3,0,8192))}


def rebuild_archive(archive,replacements):
    before=read_archive(archive);pointers=word(archive,word(archive,0x18))
    headers=[word(archive,pointers+4*i) for i in range(len(before))]
    first=min(word(archive,h+4) for h in headers);out=bytearray(archive[:first])
    for header,(key,payload) in zip(headers,before):
        out.extend(bytes((-len(out))%32));offset=len(out)
        if key in replacements:payload=replacements[key];stored=encode(payload)
        else:
            at=word(archive,header+4);stored=archive[at:at+word(archive,header+0x14)]
        out.extend(stored)
        for field,value in ((4,offset),(8,len(payload)),(0x14,len(stored))):struct.pack_into('>I',out,header+field,value)
    out.extend(bytes((-len(out))%32));out.extend(bytes(28)+b'FSYS');struct.pack_into('>I',out,0x20,len(out))
    after=read_archive(bytes(out))
    assert [(k,p) for k,p in after]==[(k,replacements.get(k,p)) for k,p in before]
    return bytes(out)


def build(deck,common):
    if sha(deck)!=DECK_SHA256 or sha(common)!=COMMON_SHA256:raise ValueError('Original USA resources required')
    decks=read_archive(deck);cm=read_archive(common);stats=cm[8][1];evo=cm[9][1];rules=cm[11][1]
    if (word(stats,0),word(stats,4),word(stats,16))!=(501,52,48):raise ValueError('Unexpected base stats')
    originals=collections.defaultdict(list)
    for key,b in decks:
        if b[:4]!=b'DCKP':continue
        assert len(b)==16+56*word(b,8)
        for i in range(word(b,8)):
            row=b[16+56*i:72+56*i];species=int.from_bytes(row[6:8],'big')
            if 1<=species<=493:originals[species].append((key,i,row))
    missing=sorted(set(range(1,494))-originals.keys())
    if missing!=sorted(EXTRA_MOVES):raise ValueError('Unexpected original species coverage')
    children={s:[int.from_bytes(evo[48+s*42+j+4:48+s*42+j+6],'big') for j in range(0,42,6)] for s in range(1,494)}
    parents={target for values in children.values() for target in values if target}
    catalog={};metadata={}
    for species in range(1,494):
        st=stats[48+species*52:48+(species+1)*52];bst=sum(st[30:36])
        if species in originals:
            # Prefer a real supported form and concrete moves over dynamic
            # selectors, retaining native selectors where a species needs them.
            _,_,template=min(originals[species],key=lambda x:(x[2][13]!=0,
                sum(m>=0x8000 for m in struct.unpack('>4H',x[2][32:40])),-x[2][14]))
            row=bytearray(template)
        else:
            row=bytearray(originals[151][0][2])
            struct.pack_into('>H',row,6,species);row[8:10]=st[36:38]
            flags=(int.from_bytes(row[2:4],'big') & ~0x0873) | 2
            struct.pack_into('>H',row,2,flags);row[13]=0
            row[12]={251:5,489:15,491:10,492:10,493:10}[species]
            row[16:22]=bytes([31]*6)
            struct.pack_into('>H',row,22,508)
            row[24:30]=bytes([252,0,252,0,4,0] if species==251 else
                              [252,0,0,4,252,0] if species==489 else [4,0,0,252,252,0])
            struct.pack_into('>4H',row,32,*EXTRA_MOVES[species])
            row[40:48]=bytes(8) # No item/form dependency for the new mythical sets.
        # Eligibility bits used by native Level 30 Open / Level 50 All
        # filters. Dedicated Little Battle pools remain unchanged.
        flags=(int.from_bytes(row[2:4],'big') | 0x0300) & ~0x0400
        struct.pack_into('>H',row,2,flags)
        row[15]=0
        struct.pack_into('>H',row,4,1) # Native battle level remains chosen by the tournament (Gateway 50).
        # Native eligibility compares a rank with AverageRank +/- 1.
        tier=0 if bst<350 else 2 if bst<420 else 3 if bst<480 else 4 if bst<530 else 5 if bst<580 else 6
        if species in parents and not any(children[species]):tier=min(6,tier+1)
        if species in MYTHICAL_LEGENDARY:tier=7
        metadata[species]={'bst':bst,'average_rank':tier,'advanced_weight':1 if species in MYTHICAL_LEGENDARY or bst<480 else 4,
                           'stock_template':species in originals,'first_ability':st[48]}
        catalog[species]=bytes(row)
    targets=set()
    for record in range(39):
        at=48+92*record
        for field in (32,40): # Main pool only; boss-only resources stay untouched.
            key=word(rules,at+field)
            if key:targets.add(key)
    # Dedicated Little Battle, tutorial and empty resources are not expanded.
    targets-={0x20712800,0x20722800,0x21662800,0x1E002800}
    replacements={};reports=[]
    for key,b in decks:
        if key not in targets or b[:4]!=b'DCKP' or not word(b,8):continue
        rows=[];base=word(b,8)
        for species in range(1,494):
            m=metadata[species]
            if m['average_rank']<6:
                row=bytearray(catalog[species]);row[14]=m['average_rank'];rows.append(row)
            for _ in range(m['advanced_weight']):
                row=bytearray(catalog[species]);row[14]=7;rows.append(row)
        random.Random(0x49300000+key).shuffle(rows) # Stable data order; native RNG still selects each team.
        assert base+len(rows)<32768
        extra=bytearray()
        for index,row in enumerate(rows,base):
            struct.pack_into('>H',row,0,index);extra.extend(row)
        out=bytearray(b)+extra;struct.pack_into('>I',out,4,len(out));struct.pack_into('>I',out,8,base+len(rows))
        replacements[key]=bytes(out)
        counts=collections.Counter(row[14] for row in rows)
        candidate_upper=max(sum(int(abs(row[14]-rank)<=1) for row in rows)+base for rank in range(8))
        if candidate_upper>2048:raise ValueError('Expanded native list may exceed patched capacity')
        reports.append({'deck':f'{key:08x}','original_records':base,'added_records':len(rows),
                        'original_prefix_preserved':bytes(out[16:len(b)])==b[16:],
                        'added_average_rank_counts':dict(sorted(counts.items())),
                        'native_candidate_upper_bound':candidate_upper})
    expanded=rebuild_archive(deck,replacements)
    report={'status':'expanded-data-awaiting-native-path-and-gameplay-validation','original_species_count':len(originals),
            'new_species_ids':missing,'catalog_species_count':len(catalog),'expanded_pools':reports,
            'all_species_in_advanced_variants':True,'advanced_weak_weight':1,'advanced_strong_weight':4,'legendary_weight':1,
            'rank_filter':'Original rank eligibility is AverageRank +/- 1; zero-based native rank',
            'fixed_original_records_and_trainers_preserved':True,'dedicated_little_pools_preserved':True,
            'trade_unlock_eligibility_storage_code_changed':False,'source_deck_sha256':sha(deck),'output_deck_sha256':sha(expanded),
            'dolphin_tested':False,'trade_persistence_tested':False,
            'warning':'Catalog inclusion is not proof of complete trainer-generation, trade eligibility or save persistence'}
    return expanded,report,metadata

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('deck','common','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();out,report,meta=build(a.deck.read_bytes(),a.common.read_bytes());a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'deck.fsys').write_bytes(out);(a.output/'expansion-data.json').write_text(json.dumps(report,indent=2)+'\n')
    (a.output/'species-policy.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(report,indent=2))
