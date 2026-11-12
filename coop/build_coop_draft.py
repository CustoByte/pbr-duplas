"""Build the freestanding draft payload using PowerPC GCC/binutils.

Use a system cross compiler or an extracted Debian toolchain root. The compiler
is a development dependency, never a dependency of a player's applicator.
"""
import argparse,hashlib,json,os,subprocess
from pathlib import Path

BASE=0x8063D400
LIMIT=0x80640000
SCRIPT='''SECTIONS {
 . = 0x8063D400;
 .payload : { *(.text*) *(.rodata*) }
 /DISCARD/ : { *(.eh_frame*) *(.comment*) *(.note*) }
}
original_reset = 0x80640000;
original_choose = 0x80640008;
original_pack = 0x80640010;
original_cleanup = 0x80640018;
cooperative_read = 0x80640140;
original_validate_switch = 0x80640150;
original_read_result = 0x80640160;
original_deliver_result = 0x80640168;
original_text = 0x80640170;
'''

def build(source,output,toolchain=None):
    output.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy()
    if toolchain:
        bindir=toolchain/'usr/bin';cc=bindir/'powerpc-linux-gnu-gcc-14'
        prefix=str(bindir/'powerpc-linux-gnu-')
        env['LD_LIBRARY_PATH']=str(toolchain/'usr/lib/x86_64-linux-gnu')+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
    else:cc='powerpc-linux-gnu-gcc-14';prefix='powerpc-linux-gnu-'
    def run(args):return subprocess.check_output([str(x) for x in args],env=env,text=True)
    version=run([cc,'-dumpfullversion']).strip()
    if version!='14.2.0':raise ValueError('Reproducible payload requires GCC 14.2.0')
    script=output/'draft.ld';script.write_text(SCRIPT)
    obj=output/'draft.o';elf=output/'draft.elf';binary=output/'draft.bin'
    flags=['-mcpu=750','-mtune=750','-m32','-mbig-endian','-msoft-float','-mno-altivec','-msdata=none','-O2',
           '-ffreestanding','-fno-builtin','-fno-pic','-fno-pie','-fno-stack-protector',
           '-fno-asynchronous-unwind-tables','-fno-unwind-tables','-fno-tree-loop-distribute-patterns',
           '-Wall','-Wextra','-Werror']
    run([cc,*flags,'-c',source,'-o',obj])
    run([prefix+'ld','-m','elf32ppc','--build-id=none','--no-undefined','-T',script,'-o',elf,obj])
    run([prefix+'objcopy','-O','binary','--only-section=.payload',elf,binary])
    if BASE+binary.stat().st_size>LIMIT:raise ValueError('Draft payload exceeds reserved code space')
    symbols={}
    for line in run([prefix+'nm','-n',elf]).splitlines():
        parts=line.split()
        if len(parts)==3 and parts[1].upper()=='T':symbols[parts[2]]=int(parts[0],16)
    manifest={'compiler':version,'address':BASE,'bytes':binary.stat().st_size,'symbols':symbols,
              'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'payload_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
    (output/'draft-symbols.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path(__file__).with_name('coop_draft.c'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--toolchain',type=Path)
    args=parser.parse_args();print(json.dumps(build(args.source,args.output,args.toolchain),indent=2))
