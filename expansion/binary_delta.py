"""Small COPY/ADD patch format. Requires the exact user-owned source file."""
import base64,gzip,hashlib,json
from collections import defaultdict

def sha(b):return hashlib.sha256(b).hexdigest()
def create(source,target):
    block=16;index=defaultdict(list)
    for at in range(0,len(source)-block+1,block):
        key=source[at:at+block]
        if len(index[key])<12:index[key].append(at)
    ops=[];literal=bytearray();pos=0
    def flush():
        if literal:ops.append({'kind':'add','data':base64.b64encode(literal).decode()});literal.clear()
    while pos<len(target):
        best=0;where=0
        for candidate in index.get(target[pos:pos+block],()):
            n=block;limit=min(len(source)-candidate,len(target)-pos)
            while n+256<=limit and source[candidate+n:candidate+n+256]==target[pos+n:pos+n+256]:n+=256
            while n<limit and source[candidate+n]==target[pos+n]:n+=1
            if n>best:best=n;where=candidate
        if best>=32:
            flush();ops.append({'kind':'copy','offset':where,'length':best});pos+=best
        else:literal.append(target[pos]);pos+=1
    flush();doc={'schema':1,'source_sha256':sha(source),'target_sha256':sha(target),'target_size':len(target),'ops':ops}
    encoded=gzip.compress(json.dumps(doc,separators=(',',':')).encode(),mtime=0)
    assert apply(source,encoded)==target
    return encoded

def apply(source,patch):
    d=json.loads(gzip.decompress(patch))
    if d['schema']!=1 or sha(source)!=d['source_sha256']:raise ValueError('Wrong original file')
    out=bytearray()
    for op in d['ops']:
        if op['kind']=='copy':
            at=op['offset'];n=op['length']
            if at<0 or n<0 or at+n>len(source):raise ValueError('Invalid source slice')
            out.extend(source[at:at+n])
        elif op['kind']=='add':out.extend(base64.b64decode(op['data'],validate=True))
        else:raise ValueError('Unknown operation')
        if len(out)>d['target_size']:raise ValueError('Invalid output size')
    if len(out)!=d['target_size'] or sha(out)!=d['target_sha256']:raise ValueError('Patch output mismatch')
    return bytes(out)
