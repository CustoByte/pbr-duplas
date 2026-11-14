"""Native text metrics with the rebuilt font registered by the original loader."""
import functools,struct
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn import ppc_const as ppc
from verify_coop_draft import DraftReplay
from translation.messages import encoded,TOKEN
from ui.font_ptbr import blocks

class Metrics:
    def __init__(self,capture,dol,font):
        self.h=DraftReplay(Path(capture),dol);self.ctx=0x8048062C;self.pointer=0x81AC0000;gid=0x70000001
        at=0x92900000
        for index,block in enumerate(blocks(font)):
            self.h.uc.mem_write(at,block)
            self.h.call(0x8024F5B8,(self.ctx,at,index,0),limit=3000000)
            self.h.abi();at=(at+len(block)+31)&~31
        def lookup(u,address,size,data):
            if u.reg_read(ppc.UC_PPC_REG_4)==gid:
                u.reg_write(ppc.UC_PPC_REG_3,self.pointer)
                u.reg_write(ppc.UC_PPC_REG_PC,u.reg_read(ppc.UC_PPC_REG_LR))
        self.h.uc.hook_add(UC_HOOK_CODE,lookup,begin=0x8024FB34,end=0x8024FB34)
        self.gid=gid
    @functools.lru_cache(None)
    def __call__(self,text):
        # Fixed-width fixtures for names/values; presentation commands are kept.
        def fixture(m):
            c=int(m[0][1:5],16)
            if c>=0xF000 or c in {3,5}:return m[0]
            if c in {0xF,0x15,0x20,0x21,0x25,0x2C,0x31,0x50,0x51}:return 'WWWWWWWWWW'
            if c in {0xE,0x17,0x18,0x26}:return '9999'
            return ''
        self.h.uc.mem_write(self.pointer,encoded(TOKEN.sub(fixture,text)))
        result=self.h.call(0x8024FBBC,(self.ctx,self.gid,1,0),limit=3000000);self.h.abi()
        return result&65535,result>>16
    def verify_tildes(self):
        m=self.h.get(self.ctx+0xD2C);cases=[]
        for i in range(10):
            for c in 'ãõÃÕ':
                slot=struct.unpack('>H',self.h.uc.mem_read(m+ord(c)*2,2))[0]
                address=self.ctx+i*0xA004+0xD98+slot*8
                assert slot!=65535 and self.h.get(address)!=0,(i,c)
                top=bytes(self.h.uc.mem_read(address+5,1))[0]
                assert top<64,(i,c,'Invalid vertical glyph offset',top)
                cases.append({'font':i,'character':c,'native_glyph_slot':slot,'bitmap_registered':True,'native_top_offset':top})
        return cases
