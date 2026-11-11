"""Layer the rental-shiny appearance hook on an exact verified v7 DOL."""
import json,struct
from pathlib import Path
from prepare_campaign_doubles import file_offset,sha,word
from rental_shiny_asm import assemble,WRAPPER

V7_DOL_SHA256='607aeae6ece4a393dc0794552801ae05c8bfa1e59de95b594a5d01349a7d9fdd'

def prepare_shiny(dol):
    if sha(dol)!=V7_DOL_SHA256:raise ValueError('Rental shiny requires exact RPBE01 v7 source')
    words=assemble();output=bytearray(dol);edits=[]
    for a,w in sorted(words.items()):
        off=file_offset(dol,a);before=word(dol,off)
        if not WRAPPER<=a<0x803DF75C and before!=0x60000000:
            raise ValueError('Rental shiny helper overlaps live v7 code')
        if before==w:continue
        struct.pack_into('>I',output,off,w)
        edits.append({'address':f'{a:08x}','before':f'{before:08x}','after':f'{w:08x}'})
    return bytes(output),{'source_sha256':sha(dol),'output_sha256':sha(output),
        'scope':'Appearance of Pokemon identities currently assigned to Cyndy/Nate rental passes, slots 37 and 38',
        'save_bytes_modified':False,'pokemon_bytes_modified':False,'edits':edits}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();new,report=prepare_shiny(a.source.read_bytes());a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'main.dol').write_bytes(new);(a.output/'shiny-audit.json').write_text(json.dumps(report,indent=2)+'\n')
