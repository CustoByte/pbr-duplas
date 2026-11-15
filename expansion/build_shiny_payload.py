"""Compile only the mod's own shiny code; no game input or game bytes included."""
import argparse,base64,hashlib,json,os,subprocess
from pathlib import Path
BASE=0x80642200;LIMIT=0x80646000
SCRIPT=f'''SECTIONS {{ . = {BASE}; .payload : {{ *(.text*) *(.rodata*) *(.data*) *(.bss*) }}
 /DISCARD/ : {{ *(.eh_frame*) *(.comment*) *(.note*) }} }}'''
def build(source,output,toolchain):
    output.mkdir(parents=True,exist_ok=True);env=os.environ.copy()
    from prepare_boss_sets import render
    sets=source.with_name('boss_sets.json');header=source.with_name('boss_sets.h')
    header.write_text(render(sets))
    prefix=str(toolchain/'usr/bin/powerpc-linux-gnu-') if toolchain else 'powerpc-linux-gnu-'
    if toolchain:env['LD_LIBRARY_PATH']=str(toolchain/'usr/lib/x86_64-linux-gnu')
    def run(args):return subprocess.check_output([str(x) for x in args],env=env,text=True)
    compiler=run([prefix+'gcc-14','-dumpfullversion']).strip()
    if compiler!='14.2.0':raise ValueError('GCC 14.2.0 required for reproducibility')
    flags=['-mcpu=750','-mtune=750','-m32','-mbig-endian','-msoft-float','-mno-altivec','-msdata=none','-O2',
           '-ffreestanding','-fno-builtin','-fno-pic','-fno-pie','-fno-stack-protector',
           '-fno-asynchronous-unwind-tables','-fno-unwind-tables','-fno-tree-loop-distribute-patterns',
           '-Wall','-Wextra','-Werror']
    obj=output/'shiny.o';elf=output/'shiny.elf';binary=output/'shiny.bin';script=output/'shiny.ld';script.write_text(SCRIPT)
    run([prefix+'gcc-14',*flags,'-c',source,'-o',obj])
    run([prefix+'ld','-m','elf32ppc','--build-id=none','--no-undefined','-T',script,'-o',elf,obj])
    run([prefix+'objcopy','-O','binary','--only-section=.payload',elf,binary]);data=binary.read_bytes()
    if BASE+len(data)>LIMIT:raise ValueError('Payload exceeds reserved section')
    symbols={}
    for line in run([prefix+'nm','-n',elf]).splitlines():
        p=line.split()
        if len(p)==3 and p[1] in ('T','D','B','R'):symbols[p[2]]=int(p[0],16)
    result={'compiler':compiler,'address':BASE,'bytes':len(data),'symbols':symbols,
            'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'inputs_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,sets,header)},
            'payload_sha256':hashlib.sha256(data).hexdigest(),'payload_base64':base64.b64encode(data).decode()}
    (output/'shiny-payload.json').write_text(json.dumps(result,indent=2)+'\n')
    return {k:v for k,v in result.items() if k!='payload_base64'}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=Path(__file__).with_name('tournament_shiny.c'))
    p.add_argument('--output',type=Path,required=True);p.add_argument('--toolchain',type=Path)
    a=p.parse_args();print(json.dumps(build(a.source,a.output,a.toolchain),indent=2))
