/* RPBE01 revision 0. Freestanding code owned by this mod.
 * Native Pokemon creation/PK4 setter/shiny renderer/stat calculation stay in use.
 * Chance is per generated CPU Pokemon, once, with deterministic native RNG.
 */
typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned char u8;
#define GET ((u32 (*)(void *,u32,u32))0x803de52c)
#define SET ((void (*)(void *,u32,const void *))0x803deca8)
#define APPEARANCE ((u32 (*)(void *))0x803df700)
#define RNG ((u32 *(*)(void))0x802283b8)

u32 shiny_raw(u32 pid,u32 ot) {
    return ((pid ^ (pid >> 16) ^ ot ^ (ot >> 16)) & 65535u) < 8u;
}
u32 unown_letter(u32 pid) {
    return (((pid & 0x03000000u) >> 18) | ((pid & 0x00030000u) >> 12) |
            ((pid & 0x00000300u) >> 6) | (pid & 3u)) % 28u;
}
u32 shiny_threshold(u32 record,u32 rank) {
    u32 maximum=7;
    /* Masters have eight separately selected sets, not a stored rank flag. */
    if (record>=31 && record<=38) rank=record-31;
    /* Native Survival difficulty saturates at zero-based tier six. */
    if (record==29) maximum=6;
    if (rank>maximum) rank=maximum;
    return 300u + (200u * rank) / maximum;
}
u32 shiny_draw(u32 *ctx) {
    u32 *state=ctx[3] ? &ctx[0xa0/4] : RNG();
    u32 draw;
    do {
        *state=*state*214013u+2531011u;
        draw=*state>>16;
    } while (draw>=60000u); /* Remove modulo bias: 60000 is divisible by 10000. */
    return draw%10000u;
}
u32 shiny_ot(u32 pid,u32 ot,u32 wanted) {
    if (shiny_raw(pid,ot)==wanted) return ot;
    if (!wanted) return ot^0x00080000u;
    return (ot&65535u)|(((ot^pid^(pid>>16))&65535u)<<16);
}
void encounter_shiny(u32 *ctx,void *mon) {
    u32 record=ctx[0x7c/4],species,pid,ot,wanted,next;
    if (record>38) return; /* Campaign CPU generator only. */
    species=GET(mon,5,0);
    if (species<1 || species>493) return;
    wanted=shiny_draw(ctx)<shiny_threshold(record,ctx[0x10/4]);
    pid=GET(mon,0,0);ot=GET(mon,7,0);
    /* Preserve the PID exactly: PK4 block order, nature, gender, ability
     * parity, Unown letter and Spinda spots. Only the secret trainer-ID half
     * changes; the public trainer ID and trainer name remain unchanged.
     * The native setter updates the Pokemon checksum without touching saves. */
    next=shiny_ot(pid,ot,wanted);
    if (next!=ot) SET(mon,7,&next);
}
void shiny_bonus(u8 *mon,u32 *computed_hp) {
    static const u8 offsets[6]={0x90,0x92,0x94,0x98,0x9a,0x96};
    u32 index=0,maximum=0,i,value;
    if (!APPEARANCE(mon)) return;
    /* Each call follows the complete original stat recalculation. There is
     * no multiplier on top of a previously multiplied stat. HP is included;
     * ties use HP, Atk, Def, SpA, SpD, Spe, and integers round down. */
    for (i=0;i<6;i++) {
        value=*(u16 *)(mon+offsets[i]);
        if (value>maximum) { maximum=value;index=i; }
    }
    value=(maximum*110u)/100u;
    *(u16 *)(mon+offsets[index])=(u16)value;
    if (!index) *computed_hp=value; /* Native current-HP adjustment follows. */
}

/* Private messages are resolved by a narrowly gated hook in the native message
 * lookup. Keep each buffer alive after the draw is queued by the original UI. */
u16 shiny_ui_strings[6][32];
#define DRAW_MESSAGE ((u32 (*)(u32,int,int,int,int,u32))0x80254c6c)
#define MEASURE ((u32 (*)(void *,u32,u32,u32))0x8024fbbc)
#define PARTY_GET ((u32 (*)(void *,u32,u32))0x803e100c)
static u32 ui_digits(u16 *out,u32 n) {
    u16 reverse[10];u32 count=0,i;
    do { reverse[count++]=(u16)('0'+n%10u);n/=10u; } while(n);
    for(i=0;i<count;i++) out[i]=reverse[count-i-1];
    return count;
}
u32 shiny_ui_draw(u32 message,int x,int y,int width,int height,u32 color,u32 field) {
    static const u8 offsets[6]={0x90,0x92,0x94,0x98,0x9a,0x96};
    u8 *ui=*(u8 * volatile *)0x80625860;
    u8 *mon;
    u32 maximum=0,winner=0,i,value,base,bonus,n,space,metrics;
    u16 *text;
    if (!ui || field>5) return DRAW_MESSAGE(message,x,y,width,height,color);
    mon=*(u8 **)(ui+0x80);
    if (!mon || !APPEARANCE(mon)) return DRAW_MESSAGE(message,x,y,width,height,color);
    for(i=0;i<6;i++) {
        value=*(u16 *)(mon+offsets[i]);
        if(value>maximum) { maximum=value;winner=i; }
    }
    if(winner!=field) return DRAW_MESSAGE(message,x,y,width,height,color);
    base=(maximum*10u+10u)/11u;bonus=maximum-base;
    if(!bonus) return DRAW_MESSAGE(message,x,y,width,height,color);
    text=shiny_ui_strings[field];
    /* Reuse the stock HP/attribute font and alignment control prefixes.
     * Compact notation keeps the original row height, font and draw bounds. */
    text[0]=0xffff;text[1]=field ? 0xf001 : 0xf004;
    text[2]=0xffff;text[3]=0xf101;n=4;
    if(!field) {
        n+=ui_digits(text+n,PARTY_GET(mon,0xa2,0));text[n++]='/';
    }
    n+=ui_digits(text+n,base);
    space=n;text[n++]=' ';text[n++]='(';text[n++]='+';
    n+=ui_digits(text+n,bonus);text[n++]=')';
    text[n++]=0xffff;text[n]=0xffff;
    metrics=MEASURE((void *)0x8048062c,0x7fff0000u+field,1,0);
    if(width>0 && (metrics&65535u)>(u32)width) {
        /* Remove only the optional space; do not squash or shrink the font. */
        for(i=space;i<n;i++) text[i]=text[i+1];
        text[n-1]=0xffff;
        metrics=MEASURE((void *)0x8048062c,0x7fff0000u+field,1,0);
    }
    /* Unknown/narrow layouts retain the original effective value. Rendering
     * an unreadable or overlapping annotation would be misleading. */
    if(!metrics || (width>0 && (metrics&65535u)>(u32)width) ||
       (height>0 && (metrics>>16)>(u32)height))
        return DRAW_MESSAGE(message,x,y,width,height,color);
    return DRAW_MESSAGE(0x7fff0000u+field,x,y,width,height,color);
}

#include "boss_sets.h"
#define BASE_STATS ((void (*)(u32,void *))0x803e052c)
#define FORM_SPECIES ((u32 (*)(u32,u32))0x803e0f0c)
#define CONSTRUCT ((void (*)(u32 *,void *,const void *,void *,u32))0x8017d750)
static u32 last_mewtwo_combo=0xffffffffu;
static void field_set(void *mon,u32 field,u32 value) { SET(mon,field,&value); }
static u32 effective_rank(u32 *ctx) {
    u32 record=ctx[0x7c/4];
    return record>=31 && record<=38 ? record-31 : ctx[0x10/4];
}
static void force_shiny(void *mon,u32 wanted) {
    u32 pid=GET(mon,0,0),ot=GET(mon,7,0),next=shiny_ot(pid,ot,wanted);
    if(next!=ot) SET(mon,7,&next);
}
static void mewtwo_moves(u32 *ctx,void *mon,u32 vary,u32 boss) {
    u32 moves[4]={94,396,58,182},i,j,combo,count=0;
    u32 shiny=shiny_raw(GET(mon,0,0),GET(mon,7,0));
    if(vary) {
        combo=shiny_draw(ctx)%15u;
        if(combo==last_mewtwo_combo) combo=(combo+1u)%15u;
        last_mewtwo_combo=combo;
        for(i=0;i<6;i++) for(j=i+1;j<6;j++) {
            if(count++==combo) { moves[1]=mewtwo_coverage[i];moves[2]=mewtwo_coverage[j]; }
        }
    }
    for(i=0;i<4;i++) {
        u32 pp=moves[i]==396 || moves[i]==447 ? 20u :
               moves[i]==85 || moves[i]==53 || moves[i]==247 ? 15u : 10u;
        field_set(mon,0x36+i,moves[i]);field_set(mon,0x3a+i,pp);field_set(mon,0x3e + i,0);
    }
    if(boss) {
        u32 original=GET(mon,0,0),pid=original;
        /* Preserve the PK4 block order and low 20 bits while finding Timid. */
        for(i=0;i<50;i++,pid+=0x100000u) if(pid%25u==10u) break;
        if(i<50 && pid!=original) field_set(mon,0,pid);
        for(i=0;i<6;i++) {
            field_set(mon,0x46+i,31);
            field_set(mon,0xd+i,i==0 ? 4u : i==3 || i==4 ? 252u : 0u);
        }
        field_set(mon,6,270); /* Life Orb, legal in generation four. */
        force_shiny(mon,1);
    } else force_shiny(mon,shiny);
}
static void build_set(u32 *ctx,void *party,void *mon,u32 index) {
    u8 row[56],stats[44];u32 i;
    const struct BossSet *set=&boss_sets[index];
    for(i=0;i<56;i++) row[i]=0;
    BASE_STATS(set->species,stats);
    *(u16 *)(row+2)=0x0302;*(u16 *)(row+4)=1;*(u16 *)(row+6)=set->species;
    row[8]=stats[6];row[9]=stats[7];row[10]=4;row[11]=set->species==380 ? 1 : set->species==381 || set->species==485 ? 0 : 2;row[12]=set->nature;
    row[14]=7;
    for(i=0;i<6;i++) { row[16+i]=31;row[24+i]=set->evs[i]; }
    *(u16 *)(row+22)=508;
    for(i=0;i<4;i++) *(u16 *)(row+32+i*2)=set->moves[i];
    *(u16 *)(row+40)=set->item;
    CONSTRUCT(ctx,mon,row,party,255);
}
static u32 legend_index(u32 *ctx,u32 *species,u32 count,u32 exclude_mewtwo) {
    u32 candidates[26],n,i,j,pass,type_match;
    u8 stats[44];u8 *trainer=(u8 *)ctx[0x60/4];
    for(pass=0;pass<2;pass++) {
        n=0;
        for(i=0;i<sizeof(boss_sets)/sizeof(boss_sets[0]);i++) {
            if(exclude_mewtwo && boss_sets[i].species==150) continue;
            for(j=0;j<count;j++) if(species[j]==boss_sets[i].species) break;
            if(j<count) continue;
            if(!pass && trainer) {
                BASE_STATS(boss_sets[i].species,stats);type_match=0;
                for(j=0;j<4;j++) if(trainer[0x60+j]!=255 &&
                    (trainer[0x60+j]==stats[6] || trainer[0x60+j]==stats[7])) type_match=1;
                if(!type_match) continue;
            }
            candidates[n++]=i;
        }
        if(n) return candidates[shiny_draw(ctx)%n];
    }
    return 0; /* Six-member teams cannot exhaust this distinct 26-species pool. */
}
void tournament_roster(u32 *ctx,void *party) {
    u32 record=ctx[0x7c/4],rank=effective_rank(ctx),ids[12],i,j,count=0,pool_count,weak=0,total,minimum=0xffffffffu;
    u32 mewtwo=6,boss=((u8 *)ctx)[0],gateway=record<=4;
    u8 stats[44];u8 *mons[6];u32 index;
    if(record>38 || ctx[0x14/4]==6) return; /* Explicit Little Battle exception. */
    for(i=0;i<6;i++) {
        u8 *mon=*(u8 **)((u8 *)party+0x48+i*4);
        if(!mon || !(mon[0x8a]&0x80)) continue;
        ids[count]=GET(mon,5,0);mons[count]=mon;
        if(ids[count]==150 && gateway && rank!=7) {
            /* Fixed teams bypass the dynamic candidate filter. Preserve a
             * Psychic role using a legal nonlegendary generation-four set. */
            u8 row[56];u32 s=rank<3 ? 96u : 97u;
            for(j=0;j<56;j++) row[j]=0;
            *(u16 *)(row+2)=0x302;*(u16 *)(row+4)=1;*(u16 *)(row+6)=(u16)s;
            row[10]=4;row[12]=15;row[14]=(u8)rank;
            for(j=0;j<6;j++) row[16+j]=25;
            *(u16 *)(row+32)=94;*(u16 *)(row+34)=95;*(u16 *)(row+36)=113;*(u16 *)(row+38)=182;
            CONSTRUCT(ctx,mon,row,party,255);ids[count]=s;
        }
        if(ids[count]==150) {
            mewtwo=count;
            if(gateway && rank==7 && !boss) mewtwo_moves(ctx,mon,1,0);
        }
        count++;
    }
    if(!boss || rank<5 || !count) return;
    for(i=0;i<count;i++) {
        if(rank>=7 && i==mewtwo) continue; /* Approved existing-Mewtwo exception. */
        BASE_STATS(FORM_SPECIES(ids[i],GET(mons[i],0x70,0)),stats);total=0;
        for(j=0;j<6;j++) total+=stats[j];
        if(total<minimum) { minimum=total;weak=i; }
    }
    pool_count=count;
    if(((u8 *)ctx)[0x71]) for(i=0;i<6;i++) {
        u8 *mon=*(u8 **)((u8 *)party+0x30+i*4);
        if(mon && (mon[0x8a]&0x80)) ids[pool_count++]=GET(mon,5,0);
    }
    if(rank>=7 && mewtwo==6) {
        /* Sunset shares a twelve-Pokemon selection board. Move an existing
         * reserve Mewtwo into the CPU team rather than creating a duplicate. */
        if(pool_count>count) for(i=0;i<6;i++) {
            u8 *mon=*(u8 **)((u8 *)party+0x30+i*4);u8 temp[140];
            if(mon && (mon[0x8a]&0x80) && GET(mon,5,0)==150) {
                for(j=0;j<140;j++) temp[j]=mon[j];
                for(j=0;j<140;j++) mon[j]=mons[weak][j];
                for(j=0;j<140;j++) mons[weak][j]=temp[j];
                mewtwo_moves(ctx,mons[weak],gateway,1);return;
            }
        }
        for(index=0;index<sizeof(boss_sets)/sizeof(boss_sets[0]);index++) if(boss_sets[index].species==150) break;
        build_set(ctx,party,mons[weak],index);
        mewtwo_moves(ctx,mons[weak],gateway,1);
    } else {
        if(rank>=7 && mewtwo<count) mewtwo_moves(ctx,mons[mewtwo],gateway,1);
        index=legend_index(ctx,ids,pool_count,gateway || mewtwo<count);
        build_set(ctx,party,mons[weak],index);
    }
}
