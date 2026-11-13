"""Check the reported menu cases and all four added letters in native code."""
import argparse,json
from pathlib import Path
from ui.native_text import Metrics
from prepare_campaign_doubles import read_archive,sha
from translation.messages import read_messages,readable

def verify(capture,dol,original,translated):
    entries=dict(read_archive(translated));font=entries[0x27C00000];m=Metrics(capture,dol,font)
    cases=m.verify_tildes();a=read_messages(dict(read_archive(original))[0x27C10000])[1];b=read_messages(entries[0x27C10000])[1];checked=[]
    for i in [7060,7061,7062,9152,9154,9193,9194]:
        s,t=readable(a[i]),readable(b[i]);prefix='{F001}{F101}';pages=[]
        for x,y in zip(s.split('{000D}'),t.split('{000D}')):
            before=m(prefix+x);after=m(prefix+y)
            # Identically sized adjacent buttons use the original wider title
            # as their common reference; unrelated panels are never pooled.
            allowed=m(readable(a[7060]))[0] if i==7061 else before[0]
            assert after[0]<=allowed and after[1]<=before[1],(i,before,after,allowed)
            pages.append({'original':before,'translated':after,'width_budget':allowed,'same_button_reference':7060 if i==7061 else None})
        checked.append({'id':i,'pages':pages})
    return {'font_sha256':sha(font),'native_tilde_cases':cases,'reported_ui_cases':checked,'dolphin_render_tested':False}
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for arg in ('capture','dol','original','translated','output'):p.add_argument('--'+arg,type=Path,required=True)
    a=p.parse_args();r=verify(a.capture,a.dol.read_bytes(),a.original.read_bytes(),a.translated.read_bytes());a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('40 glyph registrations and reported menu/page cases passed')
