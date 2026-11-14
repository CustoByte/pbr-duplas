"""Append a Mega runtime layer to the exact existing Snivy runtime, cumulatively."""
import struct,json,base64,os,subprocess,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'mod-source'),str(ROOT/'expansion'),str(ROOT/'experiments/snivy')]
from prepare_campaign_doubles import file_offset,word,sha
from team_series_asm import branch,d
from species_guards import SITES
from runtime_build import row_bridge,AI_CODE,AI_HOOK,AI_ROW
BASE,PAYLOAD,END=0x8064C000,0x8064E000,0x80652000

def target(address,instruction):
 if instruction>>26!=18 or instruction&2:raise ValueError('Expected relative branch')
 delta=instruction&0x03FFFFFC
 if delta&0x02000000:delta-=0x04000000
 return (address+delta)&0xffffffff

def compile_payload(dol,output,toolchain):
 previous=target(0x800E85B4,word(dol,file_offset(dol,0x800E85B4)))
 if not 0x80648000<=previous<0x8064C000:raise ValueError('Expected Snivy accessor')
 source=Path(__file__).with_name('pass_delivery.c');output.mkdir(parents=True,exist_ok=True)
 prefix=str(toolchain/'usr/bin/powerpc-linux-gnu-');env=os.environ.copy();env['LD_LIBRARY_PATH']=str(toolchain/'usr/lib/x86_64-linux-gnu')
 def run(*args):return subprocess.check_output(list(map(str,args)),env=env,text=True,stderr=subprocess.STDOUT)
 if run(prefix+'gcc-14','-dumpfullversion').strip()!='14.2.0':raise ValueError('Requires pinned GCC')
 script=output/'mega.ld';script.write_text(f'SECTIONS {{ . = {PAYLOAD}; .payload : {{ *(.text*) *(.rodata*) *(.data*) *(.bss*) }} /DISCARD/ : {{ *(.eh_frame*) *(.comment*) *(.note*) }} }}')
 obj,elf,binary=[output/name for name in ('mega.o','mega.elf','mega.bin')]
 flags=['-mcpu=750','-m32','-mbig-endian','-msoft-float','-mno-altivec','-msdata=none','-O2','-ffreestanding','-fno-builtin','-fno-pic','-fno-pie','-fno-stack-protector','-fno-asynchronous-unwind-tables','-fno-unwind-tables','-fno-tree-loop-distribute-patterns','-Wall','-Wextra','-Werror',f'-DSNIVY_ACCESSOR=0x{previous:x}u']
 run(prefix+'gcc-14',*flags,'-c',source,'-o',obj)
 run(prefix+'ld','-m','elf32ppc','--build-id=none','--no-undefined','-T',script,'-o',elf,obj)
 run(prefix+'objcopy','-O','binary','--only-section=.payload',elf,binary)
 body=binary.read_bytes()
 if PAYLOAD+len(body)>END:raise ValueError('Payload exceeds reservation')
 symbols={parts[2]:int(parts[0],16) for line in run(prefix+'nm','-n',elf).splitlines() if len(parts:=line.split())==3 and parts[1].lower() in ('t','d','b','r')}
 result=dict(address=PAYLOAD,bytes=len(body),source_sha256=sha(source.read_bytes()),payload_sha256=sha(body),payload_base64=base64.b64encode(body).decode(),symbols=symbols,previous_accessor=previous)
 (output/'mega-payload.json').write_text(json.dumps(result,indent=2)+'\n');return result

def patch(dol,payload):
 if sha(Path(__file__).with_name('pass_delivery.c').read_bytes())!=payload['source_sha256']:raise ValueError('Payload source differs')
 body=base64.b64decode(payload['payload_base64'],validate=True)
 if sha(body)!=payload['payload_sha256'] or payload['address']!=PAYLOAD:raise ValueError('Invalid payload')
 offset,address,size=(word(dol,o+6*4) for o in (0,0x48,0x90))
 if address!=0x80646200 or address+size!=BASE or offset+size!=len(dol):raise ValueError('Requires installed Snivy last section')
 out=bytearray(dol);out.extend(bytes(END-BASE));struct.pack_into('>I',out,0xA8,END-address)
 cursor=BASE;bridges=[]
 def put(at,data):
  if not address<=at<END or at+len(data)>END:raise ValueError('Code outside reservation')
  out[offset+at-address:offset+at-address+len(data)]=data
 def install(site,words):
  nonlocal cursor
  start=cursor;put(start,b''.join(struct.pack('>I',w) for w in words));cursor+=len(words)*4
  struct.pack_into('>I',out,file_offset(dol,site),branch(site,start));return start
 # Name lookup: fully restore scratch state before chaining to the Snivy layer.
 site=0x803E3478;old=target(site,word(dol,file_offset(dol,site)));a=cursor
 words=[d(37,1,1,-32),d(36,0,1,8),0x7C000026,d(36,0,1,12),d(11,0,4,502),0x40820020,
        d(14,3,0,21776),d(32,0,1,12),0x7C0FF120,d(32,0,1,8),d(14,1,1,32),branch(a+44,site+4),
        d(32,0,1,12),0x7C0FF120,d(32,0,1,8),d(14,1,1,32),branch(a+64,old)]
 # bne at +20 goes to the legacy restore at +48.
 words[5]=0x4082001C
 install(site,words)
 for site in SITES:
  if site<0x80030000:continue
  old=target(site,word(dol,file_offset(dol,site)));compare=word(dol,file_offset(dol,old))
  if compare&65535!=501:raise ValueError('Unexpected preceding menu bridge')
  a=cursor;install(site,[(compare&0xffff0000)|502,0x40820008,branch(a+8,site+4),branch(a+12,old)])
  bridges.append(dict(site=site,register=(compare>>16)&31,entry=a))
 # Prediction lookup: a new species may not index the fixed legacy table.
 a=cursor;code=bytearray(row_bridge(a,AI_HOOK,AI_ROW));struct.pack_into('>I',code,8,d(11,0,4,502));struct.pack_into('>I',code,len(code)-8,branch(a+len(code)-8,AI_CODE));code=code[:-4]
 put(a,code);cursor+=len(code);struct.pack_into('>I',out,file_offset(dol,AI_HOOK),branch(AI_HOOK,a))
 # Narrator fixed-table lookup uses the same safe blank row as Snivy.
 site=0x803987E4;old=target(site,word(dol,file_offset(dol,site)));a=cursor
 code=bytearray(row_bridge(a,site,0x80646660,voice=True));struct.pack_into('>I',code,8,d(11,0,4,502));struct.pack_into('>I',code,len(code)-8,branch(a+len(code)-8,old));code=code[:-4]
 put(a,code);cursor+=len(code);struct.pack_into('>I',out,file_offset(dol,site),branch(site,a))
 for site,failure in ((0x80026F40,0x80026F74),(0x80026FCC,0x80026FEC),(0x80027098,0x800270B8)):
  old=target(site,word(dol,file_offset(dol,site)));compare=word(dol,file_offset(dol,old));a=cursor
  register=(compare>>16)&31
  # Mega Lucario shares Lucario's original cry bank. Route only this new
  # species to an existing bank; no out-of-range sound index is admitted.
  install(site,[(compare&0xffff0000)|502,0x40820008,d(14,register,0,448),branch(a+12,old)])
 # Same species' original summary camera: route only the new index through 448.
 for site in (0x80104DAC,0x80104EA4):
  old=target(site,word(dol,file_offset(dol,site)));a=cursor
  install(site,[d(11,0,0,502),0x40820008,d(14,0,0,448),branch(a+12,old)])
 # Grow heap String objects requested for Gen4 nicknames. The constructor
 # allocates the larger backing buffer; no pointer/party record layout changes.
 site=0x803E2604
 if word(dol,file_offset(dol,site))!=d(37,1,1,-16):raise ValueError('Unexpected String constructor')
 a=cursor;install(site,[d(11,0,3,11),0x40820008,d(14,3,0,16),d(37,1,1,-16),branch(a+16,site+4)])
 # The unchecked getter has already established checksum/lock state. Expand
 # only default Mega names in its dynamic String output, not raw PK4 fields.
 site=0x803DE978
 if word(dol,file_offset(dol,site))!=0x7FC3F378:raise ValueError('Unexpected nickname String getter')
 a=cursor
 install(site,[0x7F23CB78,0x7FC4F378,branch(a+8,payload['symbols']['mega_display_name'],True),
               d(11,0,3,0),0x41820008,branch(a+20,0x803DE984),
               0x7FC3F378,branch(a+28,site+4)])
 if cursor>PAYLOAD:raise ValueError('Trampolines exceed reservation')
 # Preserve the forced-rental-shiny policy for every pre-existing species.
 # Only the new Mega uses the native PID/OT appearance predicate.
 site=0x803DF700
 original=word(dol,file_offset(dol,site))
 if original!=d(37,1,1,-0x30):raise ValueError('Unexpected shiny appearance prologue')
 put(0x8064D800,struct.pack('>II',original,branch(0x8064D804,site+4)))
 struct.pack_into('>I',out,file_offset(dol,site),branch(site,payload['symbols']['mega_appearance']))
 put(PAYLOAD,body)
 for site in (0x800E85B4,0x800E85D0,0x800E8908):
  if target(site,word(dol,file_offset(dol,site)))!=payload['previous_accessor']:raise ValueError('Accessor chain differs')
  struct.pack_into('>I',out,file_offset(dol,site),branch(site,payload['symbols']['mega_accessor']))
 struct.pack_into('>I',out,file_offset(dol,0x8063C700),d(15,4,0,0x8065))
 struct.pack_into('>I',out,file_offset(dol,0x8063C704),d(14,4,4,0x2000))
 return bytes(out),dict(menu_bridges=bridges,trampoline_bytes=cursor-BASE,payload_bytes=len(body),arena_floor=END)
