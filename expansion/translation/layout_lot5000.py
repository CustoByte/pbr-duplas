"""Native font measurements and source-family envelopes for the large lot.

This checks stored text and frame references without running a GPU or UI.
"""
import argparse,collections,functools,json,re
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn import ppc_const as ppc
from verify_coop_draft import DraftReplay
from prepare_campaign_doubles import read_archive
from translation.messages import RESOURCE,TOKEN,read_messages,readable,encoded,validate_target

RANGES=((974,1054),(1523,1990),(2634,2989),(3114,3237),(3237,3706),
        (3706,3890),(3890,4570),(5744,6354),(6731,6866),(6866,7000),
        (7000,7100),(7100,7450),(7450,7830),(7830,8000),(8000,8100),(8100,8282),
        (8307,8380),(8380,8600),(8600,9400),(9400,9995))

def measure(capture,dol,original_common,original_battle,candidates):
    h=DraftReplay(capture,dol);pointer=0x81AC0000;gid=0x70000001
    def lookup(u,address,size,data):
        if u.reg_read(ppc.UC_PPC_REG_4)==gid:
            u.reg_write(ppc.UC_PPC_REG_3,pointer)
            u.reg_write(ppc.UC_PPC_REG_PC,u.reg_read(ppc.UC_PPC_REG_LR))
    h.uc.hook_add(UC_HOOK_CODE,lookup,begin=0x8024FB34,end=0x8024FB34)
    originals={'mes_common.fsys':read_messages(dict(read_archive(original_common))[0x27C10000])[1],
               'menu_fight_s.fsys':read_messages(dict(read_archive(original_battle))[RESOURCE])[1]}
    def parts(text):
        m=re.match(r'^(?:\{F[0-9A-F]{3}\})+',text)
        return m[0],text[m.end():]
    def fixture(text):
        def token(m):
            code=int(m[0][1:5],16)
            if code>=0xF000:return m[0]
            if code in {0xF,0x15,0x20,0x21,0x25,0x2C,0x31}:return 'WWWWWWWWWW'
            if code in {0xE,0x17,0x18,0x26}:return '9999'
            return ''
        return TOKEN.sub(token,text)
    @functools.lru_cache(None)
    def metric(prefix,text):
        h.uc.mem_write(pointer,encoded(prefix+fixture(text)))
        value=h.call(0x8024FBBC,(0x8048062C,gid,1,0),limit=3000000);h.abi()
        return value&65535,value>>16
    def family(name,index,source):
        prefix,body=parts(source)
        if name=='menu_fight_s.fsys':return (name,prefix,'trainer' if prefix.startswith('{F006}') else 'command')
        block=next((lo for lo,hi in RANGES if lo<=index<hi),index)
        rich=bool(re.search(r'\{000[35]:',body))
        return (name,prefix,block,rich)
    bounds={};label_bounds={}
    for name,rows in originals.items():
        for index,row in enumerate(rows):
            text=readable(row)
            if not re.match(r'^(?:\{F[0-9A-F]{3}\})+',text):continue
            prefix,body=parts(text)
            if not re.search('[A-Za-z]',TOKEN.sub('',body)):continue
            if re.search(r'[\u3040-\u30ff\u4e00-\u9fff]',TOKEN.sub('',body)):continue
            key=family(name,index,text);width,height=metric(prefix,body)
            if '\n' not in body:
                old=label_bounds.get(key,(0,None))
                if width>old[0]:label_bounds[key]=(width,index)
            # Only paragraph-style text establishes a reusable paragraph
            # envelope; a caption never inherits a large tutorial panel.
            if '\n' not in body or len(TOKEN.sub('',body).split())<4:continue
            old=bounds.get(key,(0,0,None,None))
            bounds[key]=(max(old[0],width),max(old[1],height),index if width>old[0] else old[2],index if height>old[1] else old[3])
    passed=[];failures=[]
    for entry in candidates['entries']:
        name,index=entry['archive'],entry['id'];source=readable(originals[name][index])
        prefix,body=parts(source);_,target=parts(entry['target'])
        source_width,source_height=metric(prefix,body);line_height=metric(prefix,'M')[1]
        max_width=source_width;max_height=source_height;reference=None
        if name=='menu_fight_s.fsys' and prefix.startswith('{F006}'):
            max_width=max(240,source_width);max_height=max(line_height*2,source_height);reference=10
        elif '\n' in body and len(TOKEN.sub('',body).split())>=4:
            bound=bounds.get(family(name,index,source))
            if bound:max_width=max(max_width,bound[0]);max_height=max(max_height,bound[1]);reference=bound[2:]
        elif name=='mes_common.fsys':
            # Single-line entries use an existing single-line width reference
            # in the same source/font family; never inherit paragraph height.
            bound=label_bounds.get(family(name,index,source))
            if bound:max_width=max(max_width,bound[0]);reference=bound[1]
        if not max_width or not max_height:
            failures.append({**entry,'reason':'no-measurable-source-frame'});continue
        # Reflow text while retaining each explicit wait/page marker.
        page_markers=re.findall('[▼▽]',target)
        raw_pages=re.split('[▼▽]',target);formatted=[]
        for page in raw_pages:
            lines=['']
            for word in page.split():
                text=(lines[-1]+' '+word).strip()
                if metric(prefix,text)[0]>max_width and lines[-1]:lines.append(word)
                else:lines[-1]=text
            formatted.append('\n'.join(lines))
        out=''
        for n,page in enumerate(formatted):
            out+=page
            if n<len(page_markers):out+=page_markers[n]+'\n'
        full=prefix+out;validate_target(originals[name][index],full)
        width,height=metric(prefix,out)
        result={**entry,'target':full,'font_metrics':{'width':width,'height':height,
                'max_width':max_width,'max_height':max_height,'reference':reference}}
        if width>max_width or height>max_height:
            failures.append({**result,'reason':'needs-shorter-wording'})
        else:passed.append(result)
    return {'requested_new_messages':5000,'passed':passed,'failures':failures,
            'dolphin_visual_tested':False,
            'limits':['Uses source text families and native font metrics; actual frames and rendering need Dolphin.']}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('capture','dol','common','battle','candidates','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=measure(a.capture,a.dol.read_bytes(),a.common.read_bytes(),a.battle.read_bytes(),json.loads(a.candidates.read_text()))
    a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print('Passed',len(r['passed']),'need revision',len(r['failures']))
