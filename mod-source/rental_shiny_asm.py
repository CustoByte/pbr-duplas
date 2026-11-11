"""RPBE01 rev0: shiny appearance for identities on rental passes 37 and 38.

Uses only NOPs already owned by the v7 replacement of the obsolete pair
dispatcher, plus the native shiny wrapper. The raw shiny formula, Pokemon
payloads, save code, DOL sections and exception/initialization tables stay intact.
"""
from team_series_asm import d, mr, branch, NOP

WRAPPER=0x803DF700
SCAN=0x80076FFC
MATCH=0x80077070
MATCH_GET=0x803DF744
MATCH_CHECK=0x80076F10
HIT=0x80077054
EPILOGUE=WRAPPER+11*4
GET=0x803DE52C
RAW_SHINY=0x803DF75C
PASS_BASE_GLOBAL=0x80453184
PASS_STRIDE=0x6EC
POKEMON_OFFSET=0x1FC
POKEMON_STRIDE=0x8C
RENTAL_INDICES=(37,38)

def conditional(a,target,condition):
    distance=target-a
    if distance%4 or not -32768<=distance<=32764:raise ValueError('Conditional branch out of range')
    return {'eq':0x41820000,'ne':0x40820000}[condition]|(distance&0xFFFC)

def assemble():
    words={}
    def block(start,instructions):
        for n,w in enumerate(instructions):
            a=start+n*4
            if a in words:raise ValueError('Overlapping shiny code')
            words[a]=w
    block(WRAPPER,[
        d(37,1,1,-0x30),0x7C0802A6,d(36,0,1,0x34),
        d(36,29,1,0x14),d(36,31,1,0x1C),d(32,29,3,0),
        d(14,4,0,7),d(14,5,0,0),branch(WRAPPER+8*4,GET,True),mr(31,3),
        branch(WRAPPER+10*4,SCAN),
        d(32,29,1,0x14),d(32,31,1,0x1C),d(32,0,1,0x34),
        0x7C0803A6,d(14,1,1,0x30),0x4E800020])
    first=37*PASS_STRIDE+POKEMON_OFFSET
    if first>>16!=1:raise AssertionError('Unexpected pass layout')
    advance=SCAN+11*4;fallback=SCAN+18*4;loop=SCAN+7*4;skip=SCAN+16*4
    block(SCAN,[
        d(15,5,0,0x8045),d(32,5,5,0x3184),d(11,0,5,0),
        conditional(SCAN+3*4,fallback,'eq'),
        d(15,5,5,1),d(14,5,5,first&0xFFFF),d(14,7,0,12),
        d(32,0,5,0),0x7C00E800, # cmpw r0,r29
        conditional(SCAN+9*4,advance,'ne'),branch(SCAN+10*4,MATCH),
        d(14,5,5,POKEMON_STRIDE),d(14,7,7,-1),d(11,0,7,6),
        conditional(SCAN+14*4,skip,'ne'),d(14,5,5,PASS_STRIDE-6*POKEMON_STRIDE),
        d(11,0,7,0),conditional(SCAN+17*4,loop,'ne'),
        mr(3,31),mr(4,29),branch(SCAN+20*4,RAW_SHINY,True),branch(SCAN+21*4,EPILOGUE)])
    # Getter calls may clobber every volatile register and LR; counters are
    # saved in this wrapper's frame. All paths return through its epilogue.
    block(MATCH,[d(36,5,1,8),d(36,7,1,12),branch(MATCH+8,MATCH_GET)])
    block(MATCH_GET,[mr(3,5),d(14,4,0,7),d(14,5,0,0),
        branch(MATCH_GET+12,GET,True),d(32,5,1,8),branch(MATCH_GET+20,MATCH_CHECK)])
    block(MATCH_CHECK,[d(32,7,1,12),0x7C03F800, # cmpw r3,r31
        conditional(MATCH_CHECK+8,HIT,'eq'),branch(MATCH_CHECK+12,advance)])
    block(HIT,[d(14,3,0,1),branch(HIT+4,EPILOGUE),NOP])
    return words
