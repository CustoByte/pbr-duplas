/* Shared deterministic sampler. Freestanding PPC-compatible; no game hooks here.
 * Order throughout: HP, Attack, Defense, SpAttack, SpDefense, Speed.
 * Caller invokes once for an encounter and retains the result for the battle.
 */
typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned char u8;
#include "battle_rules.h"
struct SharedSet {
 u32 state;
 u16 moves[4],stats[6];
 u8 pp[4],ivs[6],evs[6],nature,archetype;
};
static u32 bounded(u32 *state,u32 bound) {
 u32 value,limit=65536u-(65536u%bound);
 do { *state=*state*214013u+2531011u;value=*state>>16; } while(value>=limit);
 return value%bound;
}
static void stats(const struct SharedProfile *profile,struct SharedSet *out,u32 level) {
 static const u8 nature_order[5]={1,2,5,3,4};
 u32 i,value,up=out->nature/5u,down=out->nature%5u;
 for(i=0;i<6;i++) {
  value=((2u*profile->base[i]+out->ivs[i]+out->evs[i]/4u)*level)/100u;
  if(!i) value+=level+10u;
  else {
   value+=5u;
   if(up!=down) {
    if(i==nature_order[up]) value=value*110u/100u;
    if(i==nature_order[down]) value=value*90u/100u;
   }
  }
  out->stats[i]=(u16)value;
 }
}
u32 shared_generate(u32 profile_index,u32 seed,u32 level,struct SharedSet *out) {
 static const u8 natures[3][5]={{0,3,13,8,23},{0,15,10,5,20},{0,14,11,16,19}};
 /* EV units of four. Every row totals 127 units = 508 EVs. */
 static const u8 templates[3][4][6]={
  {{1,63,0,0,0,63},{63,63,0,0,1,0},{41,45,0,0,0,41},{21,45,21,0,19,21}},
  {{1,0,0,63,0,63},{63,0,0,63,1,0},{41,0,0,45,0,41},{21,0,21,45,19,21}},
  {{1,32,0,32,0,62},{41,25,0,25,0,36},{21,35,0,35,0,36},{63,25,0,25,0,14}}
 };
 u8 indices[SHARED_POOL_CAPACITY],points[6],sources[6],targets[6];
 u32 state=seed,i,j,tmp,physical=0,special=0,kind,row,ns,nt,src,dst,amount;
 const struct SharedProfile *profile;
 if(!out || profile_index>=SHARED_PROFILE_COUNT || level<1u || level>100u) return 0;
 profile=&shared_profiles[profile_index];
 /* Partial Fisher-Yates: 4 distinct moves; no modulo bias. Optional whole
  * draw rejection keeps all accepted four-move combinations equally likely. */
 {
  u32 required=SHARED_MIN_OFFENSIVE;
  do {
   physical=0;special=0;
   for(i=0;i<profile->count;i++)indices[i]=(u8)i;
   for(i=0;i<4;i++) {
    j=i+bounded(&state,profile->count-i);tmp=indices[i];indices[i]=indices[j];indices[j]=(u8)tmp;
    out->moves[i]=profile->moves[indices[i]];out->pp[i]=profile->pp[indices[i]];
    physical+=profile->categories[indices[i]]==0;special+=profile->categories[indices[i]]==1;
   }
  } while(physical+special<required);
 }
 kind=physical>special ? 0u : special>physical ? 1u : 2u;
 out->archetype=(u8)kind;out->nature=natures[kind][bounded(&state,5)];
 for(i=0;i<6;i++)out->ivs[i]=(u8)(SHARED_IV_MIN+bounded(&state,SHARED_IV_SPAN));
 row=bounded(&state,4);
 for(i=0;i<6;i++)points[i]=templates[kind][row][i];
 /* Small transfers vary every stat while preserving a coherent trained set. */
 for(i=0;i<16;i++) {
  ns=0;for(j=0;j<6;j++)if(points[j])sources[ns++]=(u8)j;
  src=sources[bounded(&state,ns)];nt=0;
  for(j=0;j<6;j++)if(j!=src && points[j]<63)targets[nt++]=(u8)j;
  dst=targets[bounded(&state,nt)];amount=1u+bounded(&state,8);
  if(amount>points[src])amount=points[src];
  if(amount>63u-points[dst])amount=63u-points[dst];
  points[src]-=(u8)amount;points[dst]+=(u8)amount;
 }
 for(i=0;i<6;i++)out->evs[i]=(u8)(points[i]*4u);
 out->state=state;stats(profile,out,level);return 1;
}
