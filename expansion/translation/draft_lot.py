"""Collect protected translation drafts; never apply or publish them.

Caches each source independently, retains all control tokens and names,
and rejects damaged responses. Editorial and native layout review follow.
"""
import argparse,concurrent.futures,json,re,time,urllib.parse,urllib.request,urllib.error
from pathlib import Path
from translation.messages import TOKEN,read_messages,readable
from prepare_campaign_doubles import read_archive

def collect(inventory,common,cache_path,prior_paths):
    rows=read_messages(dict(read_archive(common))[0x27C10000])[1]
    names=set()
    for lo,hi in [(10,503),(506,973),(1991,2455),(2990,3113)]:
        for row in rows[lo:hi]:
            name=TOKEN.sub('',readable(row)).strip()
            if name and name!='-':names.add(name)
    names.update(['Pokémon','Pokétopia','Pokédex','Poké Ball','Nintendo DS','Wii Remote',
                  'Adamant','Bashful','Bold','Brave','Calm','Careful','Docile','Gentle','Hardy',
                  'Hasty','Impish','Jolly','Lax','Lonely','Mild','Modest','Naive','Naughty',
                  'Quiet','Quirky','Rash','Relaxed','Sassy','Serious','Timid'])
    pattern=re.compile(r'(?<!\w)(?:'+'|'.join(map(re.escape,sorted(names,key=len,reverse=True)))+r')(?!\w)')
    cache=json.loads(cache_path.read_text()) if cache_path.exists() else {}
    for p in prior_paths:
        prior=json.loads(p.read_text())
        for source,value in prior.items():
            target=value.get('target') if isinstance(value,dict) else value
            if isinstance(target,str):cache.setdefault(source,{'target':target,'status':'prior-draft-requires-review'})
    work={}
    for e in inventory['entries']:
        source=e['source'];prefix=re.match(r'^(?:\{F[0-9A-F]{3}\})+',source)[0]
        body=re.sub(r'\s+',' ',source[len(prefix):]).strip()
        if body in cache:continue
        normalized=re.sub('[▼▽]','',body)
        normalized=re.sub(r"((?:The|the) (?:foe's|wild) \{[0-9A-F]{4}\})'s (\{[0-9A-F]{4}\})",r'\2 of \1',normalized)
        saved=[]
        def mask(m):
            saved.append(m[0]);return 'ZXQ%03dQXZ'%(len(saved)-1)
        masked=TOKEN.sub(mask,normalized)
        # A sentence-opening command such as 'Return to...' is ordinary
        # UI language, while literal move names retain their English spelling.
        def proper(m):
            if m.start()==0 and m[0]=='Return' and normalized[m.end():].startswith(' to'):return m[0]
            return mask(m)
        masked=pattern.sub(proper,masked)
        work[body]=(masked,saved)
    batches=[];batch=[];size=0
    for source,(masked,saved) in work.items():
        if size+len(masked)>1400 and batch:batches.append(batch);batch=[];size=0
        batch.append((source,masked,saved));size+=len(masked)+8
    if batch:batches.append(batch)
    def request(text):
        url='https://translate.googleapis.com/translate_a/single?'+urllib.parse.urlencode({'client':'gtx','sl':'en','tl':'pt','dt':'t','q':text})
        for attempt in range(3):
            try:
                data=json.load(urllib.request.urlopen(url,timeout=30))
                return ''.join(x[0] or '' for x in data[0])
            except urllib.error.HTTPError as error:
                if attempt==2 or error.code!=429:raise
                time.sleep(min(60,max(10,int(error.headers.get("Retry-After","30")))))
            except Exception:
                if attempt==2:raise
    def translate(batch):
        response=request('\n'.join(f'{i+1:03d} | {e[1]}' for i,e in enumerate(batch)))
        found={}
        for line in response.splitlines():
            m=re.match(r'^\s*(\d{3})\s*[|｜]\s*(.*)',line)
            if m:found[int(m[1])]=m[2]
        out={}
        for i,(source,masked,saved) in enumerate(batch,1):
            target=found.get(i,'')
            if not target or any(target.count('ZXQ%03dQXZ'%k)!=masked.count('ZXQ%03dQXZ'%k) for k in range(len(saved))):
                target=request(masked)
            if any(target.count('ZXQ%03dQXZ'%k)!=masked.count('ZXQ%03dQXZ'%k) for k in range(len(saved))):
                out[source]={'status':'requires-manual-translation','reason':'protected-fields-not-preserved'};continue
            for k,name in enumerate(saved):target=target.replace('ZXQ%03dQXZ'%k,name)
            target+=''.join(re.findall('[▼▽]',source))
            out[source]={'target':target,'status':'machine-draft-awaiting-editorial-and-layout-review'}
        return out
    print('New requests:',len(batches),'new unique drafts:',len(work),flush=True)
    cache_path.write_text(json.dumps(cache,ensure_ascii=False,indent=2)+'\n')
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        for number,result in enumerate(pool.map(translate,batches),1):
            cache.update(result)
            cache_path.write_text(json.dumps(cache,ensure_ascii=False,indent=2)+'\n')
            print('Draft requests:',number,'/',len(batches),'cache:',len(cache),flush=True)
    print('Draft collection complete. Nothing applied or published.',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('inventory','common','cache'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--prior',type=Path,action='append',default=[])
    a=p.parse_args();collect(json.loads(a.inventory.read_text()),a.common.read_bytes(),a.cache,a.prior)
