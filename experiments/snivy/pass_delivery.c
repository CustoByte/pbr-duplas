/* RPBE01 test13: native in-memory delivery, never direct save-file writes.
 * Compiled independently of protected assets. Requires all new registries.
 */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
#define GET ((u32 (*)(void *,u32,u32))0x803DE52Cu)
#define FLAGS ((u32 (*)(u32,int))0x800E7CE8u)
#define SET_FLAGS ((void (*)(u32,u32,int))0x800E7F24u)
#define HEADER ((void (*)(u32,void *,u32))0x800E7338u)
#define COPY_PASS ((void (*)(void *,const void *))0x800CD764u)
#define CTOR ((void (*)(void *,void *,const void *,void *,u32))0x8017D750u)
#define BASE_STATS ((void (*)(u32,void *))0x803E052Cu)
#define WORD(p) (*(volatile u32 *)(p))
#define HALF(p) (*(volatile u16 *)(p))
#define BASE_PTR 0x80453184u
#define STRIDE 0x6ECu
#define MON_AT 0x1FCu
#define MON_SIZE 0x8Cu

static volatile u32 busy;
static const u16 species[6]={501,4,7,387,390,393};
/* Companion configurations use concrete moves from the original Little pool.
 * IV/EV balance is fixed for the player, not rewritten as difficulty changes.
 */
static const u16 little_moves[6][4]={
    {33,43,345,182}, {337,83,187,156}, {145,39,207,229},
    {75,110,92,241}, {83,154,339,241}, {54,250,61,31}
};
static const u16 starter_moves[4]={412,137,73,182};

static void zero(u8 *p,u32 n) { while(n--) *p++=0; }
static void copy(u8 *d,const u8 *s,u32 n) { while(n--) *d++=*s++; }
static u8 *mon(u8 *pass,u32 slot) { return pass+MON_AT+slot*MON_SIZE; }

static int ready(void) {
    u32 *stats=(u32 *)WORD(0x80625184u), *models=(u32 *)WORD(0x80625174u);
    u32 *faces=(u32 *)WORD(0x80625178u), *icons=(u32 *)WORD(0x806251D8u);
    u8 *row;
    if(!stats || !models || !faces || !icons || stats[0]<502 || models[0]<671 ||
       faces[0]<502 || icons[0]<563) return 0;
    row=(u8 *)stats[4]+501u*52u;
    if(HALF(row+24)!=21775 || HALF(row+28)!=670 || row[30]!=45 || row[48]!=65) return 0;
    if(WORD((u8 *)models[4]+670u*72u+4)!=0x2000u) return 0;
    if(!((void *(*)(u32))0x8024C32Cu)(0x2000u)) return 0;
    return WORD(BASE_PTR)!=0;
}

static int construct(u8 *out,u32 index,u32 level) {
    u32 ctx[64], trainer[64], party[16];
    u8 row[56], stats[44];
    u32 i, sp=level==50 ? 501u : species[index];
    const u16 *moves=level==50 ? starter_moves : little_moves[index];
    zero((u8 *)ctx,sizeof(ctx));zero((u8 *)trainer,sizeof(trainer));
    zero((u8 *)party,sizeof(party));zero(row,sizeof(row));zero(out,MON_SIZE);
    ctx[0x10/4]=0;ctx[0x14/4]=6;ctx[0x60/4]=(u32)trainer;ctx[0x6C/4]=level;
    ctx[0x7C/4]=39; /* Player delivery is outside campaign CPU shiny rolls. */
    party[0xC/4]=0x01000000u;party[0x28/4]=0x13572468u^(sp<<8)^(level<<16);
    BASE_STATS(sp,stats);
    *(u16 *)(row+2)=(u16)(level==5 ? 0x1402u : 0x1002u);
    *(u16 *)(row+4)=1;*(u16 *)(row+6)=(u16)sp;
    row[8]=stats[6];row[9]=stats[7];row[10]=4;row[12]=(u8)(sp==501 ? 10 : 0);
    for(i=0;i<6;i++) row[16+i]=(u8)(level==50 ? 31 : 15);
    if(level==50) {
        *(u16 *)(row+22)=508;row[24]=4;row[27]=252;row[28]=252;
    }
    for(i=0;i<4;i++) {
        *(u16 *)(row+32+i*2)=moves[i];
        *(u16 *)(row+40+i*2)=(u16)(sp==501 ? 157 : 0);
    }
    CTOR(ctx,out,row,party,255);
    if(GET(out,5,0)!=sp || GET(out,160,0)!=level || GET(out,173,0)!=sp) return 0;
    for(i=0;i<4;i++) if(GET(out,0x36+i,0)!=moves[i]) return 0;
    return 1;
}

static int vacant(u8 *pass,u32 index) {
    u32 i;
    if(FLAGS(2,(int)index)!=0 || FLAGS(4,(int)index) || !FLAGS(5,(int)index)) return 0;
    /* A customized-but-empty pass still belongs to its player. Do not replace
     * its trainer/name/profile merely because it contains no Pokémon. */
    for(i=0;i<0x1C;i++) if(pass[i]) return 0;
    for(i=0;i<6;i++) if(GET(mon(pass,i),5,0)) return 0;
    return 1;
}

static void deliver(u8 *base) {
    u8 temporary[STRIDE], generated[MON_SIZE];
    u32 i,j,found=37;
    /* Replace only the requested original Charmeleon slot. No repeated resets
     * of a Snivy that has already been delivered or a slot changed by player. */
    u8 *starter=mon(base+37u*STRIDE,1);
    if(GET(starter,5,0)==5 && construct(generated,0,50)) copy(starter,generated,MON_SIZE);
    for(i=0;i<37;i++) {
        u8 *pass=base+i*STRIDE;
        if(FLAGS(2,(int)i)==0 && FLAGS(4,(int)i)) {
            for(j=0;j<6;j++) if(GET(mon(pass,j),5,0)==501 && GET(mon(pass,j),160,0)<=5) return;
        }
        if(found==37 && vacant(pass,i)) found=i;
    }
    if(found==37) return; /* Full/locked/customized roster: preserve everything. */
    copy(temporary,base+found*STRIDE,STRIDE);
    HEADER(1,temporary,0); /* Native trainer/header construction; flags retained. */
    for(i=0;i<12;i++) ((u16 *)(temporary+4))[i]=0xFFFFu;
    ((u16 *)(temporary+4))[0]='L';((u16 *)(temporary+4))[1]='i';
    ((u16 *)(temporary+4))[2]='t';((u16 *)(temporary+4))[3]='t';
    ((u16 *)(temporary+4))[4]='l';((u16 *)(temporary+4))[5]='e';
    for(i=0;i<6;i++) if(!construct(mon(temporary,i),i,5)) return;
    COPY_PASS(base+found*STRIDE,temporary);
    SET_FLAGS(4,1,(int)found); /* Native ownership + auxiliary initialization. */
    SET_FLAGS(1,1,(int)found); /* Native dirty flag refreshes the pass display. */
}

u32 snivy_accessor(u32 address) {
    address=((u32 (*)(u32))0x8063C000u)(address); /* Preserve Monferno migration. */
    if(!busy && ready()) {
        busy=1;deliver((u8 *)WORD(BASE_PTR));busy=0;
    }
    return address;
}

/* Called only at the existing between-battles held-item restore hook. Native
 * in-battle item reads/setters are not intercepted, so a used Berry stays used
 * for the rest of that battle. Respect a changed item in the original pass. */
void snivy_carry(void *party,u32 field,const u32 *value) {
    u32 restored=157,i,j;
    u8 *base=(u8 *)WORD(BASE_PTR);
    if(base && field==6 && GET(party,5,0)==501) {
        u32 pid=GET(party,0,0),ot=GET(party,7,0);
        for(i=0;i<159;i++) for(j=0;j<6;j++) {
            u8 *source=mon(base+i*STRIDE,j);
            if(GET(source,5,0)==501 && GET(source,0,0)==pid && GET(source,7,0)==ot && GET(source,6,0)==157) {
                value=&restored;
                goto done;
            }
        }
    }
done:
    ((void (*)(void *,u32,const u32 *))0x8063C300u)(party,field,value);
}
