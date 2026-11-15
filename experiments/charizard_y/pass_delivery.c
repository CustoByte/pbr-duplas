/* Layered RPBE01 delivery: preserve Snivy and Mega Lucario accessors and every unrelated pass. */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
#ifndef PREVIOUS_ACCESSOR
#error Missing audited preceding accessor
#endif
#ifndef PREVIOUS_APPEARANCE
#error Missing prior appearance hook
#endif
#define GET ((u32 (*)(void *,u32,u32))0x803DE52Cu)
#define SET ((void (*)(void *,u32,const void *))0x803DECA8u)
#define PARTY_GET ((u32 (*)(void *,u32,u32))0x803E100Cu)
#define UNCHECKED_GET ((u32 (*)(void *,u32,u32))0x803DE5C4u)
#define CTOR ((void (*)(void *,void *,const void *,void *,u32))0x8017D750u)
#define BASE_STATS ((void (*)(u32,void *))0x803E052Cu)
#define WORD(p) (*(volatile u32 *)(p))
#define HALF(p) (*(volatile u16 *)(p))
static volatile u32 busy;
/* Keep the serialized Gen4 nickname at its native 10-character size. The
 * display getter expands this private marker to the complete species name. */
static const u16 name_marker[11]={0x012D,0x0132,0x012B,0x013C,0x0133,0x0144,0x012B,0x013C,0x012E,0x0143,0xFFFF};
static const u16 display_name[17]={0x0137,0x012F,0x0131,0x012B,0x01DE,0x012D,0x0132,0x012B,0x013C,0x0133,0x0144,0x012B,0x013C,0x012E,0x01DE,0x0143,0xFFFF};
static void repair_name(u8 *mon) {
 u16 raw[11];
 GET(mon,116,(u32)raw);
 if(raw[0]==0 || raw[0]==0xFFFF) SET(mon,116,name_marker);
}

static void zero(u8 *p,u32 n) { while(n--) *p++=0; }
static int ready(void) {
 u32 *stats=(u32 *)WORD(0x80625184u), *models=(u32 *)WORD(0x80625174u);
 u32 *faces=(u32 *)WORD(0x80625178u), *icons=(u32 *)WORD(0x806251D8u);
 u8 *row;
 if(!stats||!models||!faces||!icons||stats[0]<504||models[0]<673||faces[0]<504||icons[0]<565) return 0;
 row=(u8 *)stats[4]+503u*52u;
 if(HALF(row+24)!=21777||HALF(row+28)!=672||row[30]!=78||row[31]!=104||row[33]!=90||row[34]!=135||row[35]!=95||row[48]!=70) return 0;
 if(WORD((u8 *)models[4]+672u*72u+4)!=0x2002u) return 0;
 return ((void *(*)(u32))0x8024C32Cu)(0x2002u)!=0 && WORD(0x80453184u)!=0;
}
static int construct(u8 *out) {
 u32 ctx[64],trainer[64],party[16],i;
 u8 row[56],stats[44];
 const u16 moves[4]={53,403,76,182};
 zero((u8 *)ctx,sizeof(ctx));zero((u8 *)trainer,sizeof(trainer));zero((u8 *)party,sizeof(party));zero(row,sizeof(row));zero(out,0x8C);
 ctx[0x14/4]=6;ctx[0x60/4]=(u32)trainer;ctx[0x6C/4]=50;ctx[0x7C/4]=39;
 party[0xC/4]=0x01000000u;party[0x28/4]=0x13572468u^(503u<<8)^(50u<<16);
 BASE_STATS(503,stats);
 *(u16 *)(row+2)=0x1002;*(u16 *)(row+4)=1;*(u16 *)(row+6)=503;
 row[8]=stats[6];row[9]=stats[7];row[10]=4;row[12]=10;
 for(i=0;i<6;i++)row[16+i]=20;
 /* A rental-scale preset: no competitive EV training and moderate IVs. */
 *(u16 *)(row+22)=0;
 for(i=0;i<4;i++)*(u16 *)(row+32+i*2)=moves[i];
 CTOR(ctx,out,row,party,255);
 /* Request a normal Mega. The existing mod grants a bonus to shinies; the
  * zeroed native trainer fixture otherwise makes this fixed set shiny.
  * Change only the secret trainer-ID half, preserving PID/nature and checksum. */
 {
  u32 pid=GET(out,0,0),ot=GET(out,7,0);
  if(((pid^(pid>>16)^ot^(ot>>16))&65535u)<8u) {
   ot^=0x00080000u;SET(out,7,&ot);
  }
 }
 repair_name(out);
 if(GET(out,5,0)!=503||GET(out,160,0)!=50||GET(out,173,0)!=503||GET(out,10,0)!=70||GET(out,6,0)!=0) return 0;
 for(i=0;i<4;i++)if(GET(out,0x36+i,0)!=moves[i])return 0;
 return 1;
}
/* Migrate only the exact IV/EV/nature signature delivered by test.1.
 * Keep PID, OT, nickname, moves, item and every user-edited training spread.
 * These are boxed rental records: the native party conversion recalculates
 * battle stats from the updated species table, instead of patching cached HP. */
static void migrate_legacy_preset(u8 *mon) {
 const u8 old_evs[6]={4,0,0,252,252,0};u32 i,value;
 if(GET(mon,160,0)!=50 || GET(mon,0,0)%25u!=10u) return;
 for(i=0;i<6;i++) if(GET(mon,0x46u+i,0)!=31u || GET(mon,0xDu+i,0)!=old_evs[i]) return;
 value=20u;for(i=0;i<6;i++) SET(mon,0x46u+i,&value);
 value=0u;for(i=0;i<6;i++) SET(mon,0xDu+i,&value);
}
u32 charizard_accessor(u32 address) {
 address=((u32 (*)(u32))PREVIOUS_ACCESSOR)(address);
 if(!busy && ready()) {
  u8 generated[0x8C];u8 *slot=(u8 *)WORD(0x80453184u)+37u*0x6ECu+0x1FCu+2u*0x8Cu;u32 i;
  busy=1;
  /* Only the original level-50 Wartortle in the requested starter slot. */
  if(GET(slot,5,0)==8 && GET(slot,160,0)==50 && construct(generated)) {
   for(i=0;i<0x8C;i++)slot[i]=generated[i];
  } else if(GET(slot,5,0)==503) {
   repair_name(slot);
   migrate_legacy_preset(slot);
  }
  busy=0;
 }
 return address;
}

/* The pre-existing mod forces rental identities to look shiny and grants its
 * shiny stat bonus. Keep that policy for every old Pokemon, but use the native
 * PID/OT predicate for the newly delivered normal Mega so its agreed set stays
 * at 148/107/93/115/150/110. Naturally shiny Mega records still receive the bonus.
 */
u32 charizard_appearance(void *mon) {
 if(PARTY_GET(mon,5,0)==503) {
  u32 pid=PARTY_GET(mon,0,0),ot=PARTY_GET(mon,7,0);
  return ((u32 (*)(u32,u32))0x803DF75Cu)(ot,pid);
 }
 return ((u32 (*)(void *))PREVIOUS_APPEARANCE)(mon);
}

/* Called only from the native nickname-to-String-object getter. Never copy
 * sixteen characters into the fixed serialized PK4 nickname buffer. */
u32 charizard_display_name(void *mon,u16 *text) {
 u16 raw[11];u32 i,marker=1,empty=1;
 if(!text || text[0]<17 || UNCHECKED_GET(mon,5,0)!=503) return 0;
 UNCHECKED_GET(mon,116,(u32)raw);
 for(i=0;i<10;i++) {
  if(raw[i]!=name_marker[i]) marker=0;
  if(raw[i]!=0 && raw[i]!=0xFFFF) empty=0;
 }
 if(!marker && !empty) return 0; /* Respect player-selected nicknames. */
 text[1]=16;
 for(i=0;i<17;i++)text[4+i]=display_name[i];
 return 1;
}
