/* Experimental RPBE01 cooperative draft. No save-file or network access.
 * All native selection predicates, marking and packing remain in the game.
 * Freestanding PowerPC code; enabled only by an explicit development fixture.
 */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

typedef struct {
    u32 magic;
    u8 enabled, active, owner, count0, count1, committed, reserved[2];
    u32 session, ui;
    u8 owners[6];
} Draft;

#define D ((volatile Draft *)0x80640100u)
#define S ((volatile u8 *)0x8063C6C0u)
#define WORD(p) (*(volatile u32 *)(p))
#define HALF(p) (*(volatile u16 *)(p))
#define BYTE(p) (*(volatile u8 *)(p))
#define DRFT 0x44524654u
#define COOP 0x434F4F50u
#define UI_PTR 0x806258C8u
#define REGISTRY 0x804E60F0u
#define BATTLE_UI 0x8044DF88u

extern void original_reset(void);
extern u32 original_choose(u32 slot, u32 side, u32 sound, u32 details);
extern u32 original_pack(void);
extern void original_cleanup(void);
extern u32 original_validate_switch(u32 row, u32 selector);
extern u32 cooperative_read(u32 flags, u32 focus, u32 pad, u32 assist);
extern u32 original_read_result(void);
extern void original_deliver_result(u32 result);
extern u32 original_text(u32 manager, u32 id);

typedef struct {
    u32 context, living, active[2];
} Battle;

static int battle_enabled(void) {
    return WORD(S) == COOP && S[4] == 1 && S[8] == 1;
}

static int battle_snapshot(Battle *out) {
    u32 i, counts[2] = {0, 0}, ctx;
    if (!S[9] || WORD(BATTLE_UI + 0xB4) != WORD(S + 0x1C)) return 0;
    for (i = 0; i < 6; ++i) {
        u8 owner = S[10+i];
        if (i < 4) {
            if (owner > 1) return 0;
            ++counts[owner];
        } else if (owner != 255) return 0;
    }
    if (counts[0] != 2 || counts[1] != 2) return 0;
    ctx = ((u32 (*)(void))0x803B0008u)();
    if (!ctx || ((u32 (*)(u32,u32))0x803B00E0u)(ctx,0) != 4) return 0;
    out->context = ctx; out->living = 0;
    for (i = 0; i < 4; ++i) {
        u32 mon = ((u32 (*)(u32,u32,u32))0x803B0184u)(ctx,0,i);
        if (!((u32 (*)(u32,u32,u32))0x803E100Cu)(mon,5,0)) return 0;
        if (((u32 (*)(u32,u32,u32))0x803E100Cu)(mon,0xA2,0)) out->living |= 1u << i;
    }
    out->active[0] = ((u32 (*)(u32,u32))0x803CC838u)(0,0);
    out->active[1] = ((u32 (*)(u32,u32))0x803CC838u)(0,1);
    return out->active[0] < 4 && out->active[1] < 4 && out->active[0] != out->active[1];
}

/* A fainted member keeps its owner. Transfer the vacant position only after
 * that owner has no living member left, never merely because its reserve died. */
static u32 switch_owner(const Battle *battle, u32 position) {
    u32 i, owner = S[10+battle->active[position]];
    for (i = 0; i < 4; ++i)
        if (S[10+i] == owner && (battle->living & (1u << i))) return owner;
    return owner ^ 1u;
}

static int switch_allowed(const Battle *battle, u32 position, u32 candidate) {
    if (candidate >= 4 || !(battle->living & (1u << candidate)) ||
        candidate == battle->active[0] || candidate == battle->active[1]) return 0;
    return S[10+candidate] == switch_owner(battle,position);
}

static void route_choice(u32 phase, u32 owner) {
    if (S[5] != phase || S[6] != owner) {
        S[7] = 1; WORD(S + 0x10) += 1;
    }
    S[5] = (u8)phase; S[6] = (u8)owner;
}

/* Separate input paths used by the battle shortcuts and Pokemon details.
 * Details opened from campaign menus keep their original controller. */
u32 coop_aux_read(u32 flags, u32 focus, u32 pad, u32 assist, u32 caller) {
    Battle battle; u32 context, handle, position, mode, family, phase, owner;
    if (!battle_enabled()) goto native;
    switch (caller) {
    case 0x8006B4DCu: case 0x8006B4F4u: case 0x8006B514u: case 0x8006B530u:
    case 0x8006C39Cu: case 0x8006C3B8u:
        handle = WORD(0x806257E8u);
        if (handle >= 32 || !BYTE(REGISTRY+0x12C+handle) ||
            WORD(REGISTRY+0x2C+4*handle) != 0x8006B468u) goto native;
        break;
    case 0x800FC880u: case 0x800FD554u: case 0x800FE0D4u:
    case 0x800FECD4u: case 0x800FF2C8u: case 0x800FF9ACu:
        context = WORD(0x80625860u); /* SDA -0x7DA0, details controller. */
        if (context < 0x80000000u || context > 0x93FFFF00u) goto native;
        handle = WORD(context+0x64);
        if (handle >= 32 || !BYTE(REGISTRY+0x12C+handle) ||
            WORD(REGISTRY+0x2C+4*handle) != 0x800FC1B4u) goto native;
        break;
    default: goto native;
    }
    if (!S[9]) {
        if (D->magic==DRFT && D->enabled==1 && D->active &&
            D->ui==WORD(UI_PTR) && D->session==WORD(D->ui+0xD8u) && D->owner<2) {
            route_choice(1,D->owner);
            if (flags & 0xDF000000u) focus=0;
            return cooperative_read(flags,focus,0,assist);
        }
        if (S[5]) return 0;
        goto native;
    }
    if (HALF(BATTLE_UI+0x6E) != 0) goto native;
    position = HALF(BATTLE_UI+0x64); mode = BYTE(0x80626EE4u);
    if (position > 1 || !battle_snapshot(&battle)) return 0;
    if (mode == 4*position) family = 0;
    else if (mode >= 1+5*position && mode <= 3+5*position) family = mode-5*position;
    else return 0;
    if (family == 3) {
        owner = switch_owner(&battle,position);
        phase = battle.living & (1u << battle.active[position]) ? 4 : 5;
    } else {
        if (!(battle.living & (1u << battle.active[position]))) return 0;
        owner = S[10+battle.active[position]]; phase = family == 2 ? 3 : 2;
    }
    route_choice(phase,owner);
    /* These calls belong to the shared battle side even if the details
     * controller retained an explicit physical index from a previous view. */
    if (flags & 0xDF000000u) focus = 0;
    return cooperative_read(flags,focus,0,assist);
native:
    return ((u32 (*)(u32,u32,u32,u32))0x8005B5ECu)(flags,focus,pad,assist);
}

static void result_to_menu(int clear) {
    u32 i;
    if (!battle_enabled()) return;
    if (S[5] || S[6] || (clear && S[9])) {
        S[5] = S[6] = 0; S[7] = 1; WORD(S+0x10) += 1;
    }
    if (clear) {
        S[9] = 0; WORD(S+0x1C) = 0;
        for (i=0;i<6;++i) S[10+i] = 255;
        D->active = D->committed = 0;
    }
}

void coop_deliver_result(u32 result) {
    /* A pending best-of-series result retains ownership for its next round.
     * The native abort code cancels ownership immediately. */
    result_to_menu(result == 0x80);
    original_deliver_result(result);
}

u32 coop_read_result(void) {
    u32 result = original_read_result();
    if (result <= 2) result_to_menu(1);
    return result;
}

/* Prefix the four native battle choice prompts without changing message
 * archives, Pokemon nicknames or saves. Preserve the native control stream. */
u32 coop_text(u32 manager, u32 id) {
    u32 text = original_text(manager,id), kind, position, mode, owner, head, i, length;
    volatile u16 *out; const volatile u16 *in; Battle battle;
    if (!text || manager != 0x8048062Cu || !battle_enabled()) return text;
    switch (id) {
    case 0x2ECBu: kind=0; head=7; break;
    case 0x2ECCu: kind=1; head=7; break;
    case 0x3123u: kind=2; head=4; break;
    case 0x3124u: kind=3; head=4; break;
    default: return text;
    }
    position=HALF(BATTLE_UI+0x64); mode=BYTE(0x80626EE4u);
    if (position>1 || HALF(BATTLE_UI+0x6E) || !battle_snapshot(&battle)) return text;
    if (mode==3+5*position) owner=switch_owner(&battle,position);
    else if (mode==4*position || mode==1+5*position || mode==2+5*position)
        owner=S[10+battle.active[position]];
    else return text;
    in=(const volatile u16 *)text;
    if (in[0]!=0xFFFF || in[1]!=0xF000 || in[2]!=0xFFFF || in[3]!=0xF101) return text;
    /* Reject unexpected/oversized resources before writing any output. */
    for (length=head;length<120;++length)
        if (in[length]==0xFFFF && in[length+1]==0xFFFF) break;
    if (length==120) return text;
    out=(volatile u16 *)(0x80640400u+(kind*2+owner)*256);
    for (i=0;i<head;++i) out[i]=in[i];
    out[head]='P'; out[head+1]=(u16)('1'+owner); out[head+2]=':'; out[head+3]=' ';
    for (i=head;i<length+2;++i) out[i+4]=in[i];
    return (u32)out;
}

/* Native main-command, move and target callbacks share the actor field.
 * Scope by callsite AND live registration: a target belongs to the attacker,
 * including when the target itself belongs to the other player. */
static u32 battle_input_scope(u32 caller) {
    Battle battle; u32 callback, family, handle, position, owner, phase;
    if (!battle_enabled()) return 0;
    switch (caller) {
    case 0x80061118u: case 0x8006113Cu: case 0x80061154u: case 0x8006143Cu:
        callback = 0x80060EECu; family = 0; break;
    case 0x8006180Cu: callback = 0x80061598u; family = 1; break;
    case 0x80062180u: callback = 0x80061C98u; family = 2; break;
    default: return 0;
    }
    handle = WORD(0x806257E4u);
    if (handle >= 32 || !BYTE(REGISTRY + 0x12C + handle) ||
        WORD(REGISTRY + 0x2C + 4*handle) != callback || HALF(BATTLE_UI + 0x6E) != 0)
        return 0;
    position = HALF(BATTLE_UI + 0x64);
    if (position > 1 || BYTE(0x80626EE4u) != (family ? family + 5*position : 4*position) ||
        !battle_snapshot(&battle) || !(battle.living & (1u << battle.active[position]))) {
        S[5] = 255; return 1;
    }
    owner = S[10+battle.active[position]]; phase = family == 2 ? 3 : 2;
    if (S[5] != phase || S[6] != owner) {
        S[7] = 1; WORD(S + 0x10) += 1;
    }
    S[5] = (u8)phase; S[6] = (u8)owner;
    return 1;
}

u32 coop_party_read(u32 flags, u32 focus, u32 pad, u32 assist) {
    Battle battle; u32 handle, position, mode, owner, phase, result, button, member;
    if (!battle_enabled())
        return ((u32 (*)(u32,u32,u32,u32))0x8005B5ECu)(flags,focus,pad,assist);
    mode = BYTE(0x80626EE4u); position = HALF(BATTLE_UI + 0x64);
    handle = WORD(0x806257E4u); /* SDA -0x7E1C, primary command callback. */
    if (position > 1 || mode != 3 + 5*position || HALF(BATTLE_UI + 0x6E) != 0 ||
        handle >= 32 || !BYTE(REGISTRY + 0x12C + handle) ||
        WORD(REGISTRY + 0x2C + 4*handle) != 0x80062B50u)
        return ((u32 (*)(u32,u32,u32,u32))0x8005B5ECu)(flags,focus,pad,assist);
    if (!battle_snapshot(&battle)) return 0;
    owner = switch_owner(&battle,position);
    phase = battle.living & (1u << battle.active[position]) ? 4 : 5;
    if (S[5] != phase || S[6] != owner) {
        S[7] = 1; WORD(S + 0x10) += 1;
    }
    S[5] = (u8)phase; S[6] = (u8)owner;
    result = cooperative_read(flags,focus,pad,assist);
    button = result & 0xFFFFu;
    if (!(result & 0x80000000u) || button < 1 || button > 6) return result;
    member = ((u32 (*)(u32,u32))0x803CC838u)(0,button-1);
    /* Retain hover/focus but suppress confirmation of an unavailable member. */
    return switch_allowed(&battle,position,member) ? result : button;
}

u32 coop_validate_switch(u32 row, u32 selector) {
    Battle battle; u32 result, client, candidate;
    if (!battle_enabled()) return original_validate_switch(row,selector);
    client = WORD(selector + 0x1C);
    /* Clients 0/2 are the two positions on our shared side. Enemy and other
     * native selection contexts keep their original validation. */
    if (client != 0 && client != 2) return original_validate_switch(row,selector);
    if (row >= 6) return 0x505Au;
    result = original_validate_switch(row,selector);
    if (result) return result; /* Keep native HP, active, pending and trap errors. */
    if (!battle_snapshot(&battle) || WORD(selector + 4) != battle.context) return 0x505Au;
    candidate = BYTE(selector + 0x20 + row);
    if (!switch_allowed(&battle,client/2,candidate)) {
        BYTE(selector + 0xD) = (u8)row;
        return 0x505Au; /* Existing native disallowed-trainer selection message. */
    }
    return 0;
}

static int enabled(void) { return D->magic == DRFT && D->enabled == 1; }
static int binding(void) {
    return D->ui == WORD(UI_PTR) && D->session == WORD(D->ui + 0xD8u);
}
static void invalidate(void) { S[9] = 0; }
static void decision(u8 owner) {
    D->owner = owner;
    S[5] = 1; S[6] = owner; S[7] = 1;
    WORD(S + 0x10) += 1;
}
static int recount(void) {
    u32 i; u8 counts[2] = {0, 0};
    for (i = 0; i < 6; ++i) {
        u8 rank = BYTE(D->ui + 0xDCu + i);
        if (rank && rank != 7) {
            u8 owner = D->owners[i];
            if (rank > 4 || owner > 1) return 0;
            ++counts[owner];
        }
    }
    D->count0 = counts[0]; D->count1 = counts[1];
    return counts[0] <= 2 && counts[1] <= 2;
}

void coop_reset(void) {
    u32 i, ui, session;
    original_reset();
    if (!enabled()) return;
    D->active = D->committed = 0;
    invalidate();
    S[4] = S[8] = 0;
    ui = WORD(UI_PTR);
    if (ui < 0x80000000u || ui > 0x81FFFF00u) return;
    session = WORD(ui + 0xD8u);
    /* Four-entry campaign selection only. Other rule sets stay native. */
    if (session < 0x90000000u || session > 0x93FF0000u ||
        WORD(session + 8) != 1 || HALF(session + 0x90u) != 4) return;
    D->ui = ui; D->session = session;
    D->count0 = D->count1 = 0;
    for (i = 0; i < 6; ++i) D->owners[i] = 255;
    WORD(S) = COOP; S[4] = S[8] = 1;
    WORD(S + 0x1C) = session;
    for (i = 0; i < 6; ++i) S[10 + i] = 255;
    ((void (*)(u32,u32))0x80159C44u)(0,0);
    D->active = 1;
    decision(0);
}

u32 coop_choose(u32 slot, u32 side, u32 sound, u32 details, u32 caller) {
    u32 result; u8 rank, after, owner;
    if (!enabled() || !D->active || side != 0)
        return original_choose(slot, side, sound, details);
    if (!binding() || S[7] || slot >= 6 || !recount()) return 0;
    rank = BYTE(D->ui + 0xDCu + slot);
    owner = D->owner;
    if (!rank && !((u32 (*)(u32))0x80058C34u)(D->session + 0x1FFCu + 0x1FCu + slot * 0x8Cu))
        return 0;
    if (rank && rank != 7) {
        u8 selected_owner = D->owners[slot];
        if (selected_owner > 1) return 0;
        /* Native Back/No undoes the last pick and returns to that owner.
         * Clicking another player's selected Pokemon is never allowed. */
        if (selected_owner != owner && caller != 0x80157774u && caller != 0x80157ADCu)
            return 0;
        owner = selected_owner;
    } else if (!rank && ((owner == 0 ? D->count0 : D->count1) >= 2)) {
        return 0;
    }
    result = original_choose(slot, side, sound, details);
    after = BYTE(D->ui + 0xDCu + slot);
    if (!rank && after && after <= 4) D->owners[slot] = owner;
    else if (rank && rank <= 4 && (!after || after == 7)) D->owners[slot] = 255;
    else return result; /* Details, blocked eligibility or no selection change. */
    invalidate();
    if (!recount()) { S[5] = 255; return result; }
    decision(D->count0 < 2 ? 0 : D->count1 < 2 ? 1 : 0);
    return result;
}

u32 coop_pack(void) {
    u32 i, rank, result, seen = 0; u8 order[2][2], counts[2] = {0, 0}, old[6];
    if (!enabled() || !D->active) return original_pack();
    invalidate();
    if (!binding() || S[7] || !recount() || D->count0 != 2 || D->count1 != 2) return 0;
    for (i = 0; i < 6; ++i) {
        u8 value = BYTE(D->ui + 0xDCu + i);
        old[i] = value;
        if (value && value != 7) {
            if (value > 4 || (seen & (1u << value))) return 0;
            seen |= 1u << value;
        }
    }
    if (seen != 0x1Eu) return 0;
    /* Preserve each owner's relative order, including after editing picks. */
    for (rank = 1; rank <= 4; ++rank)
        for (i = 0; i < 6; ++i)
            if (old[i] == rank) {
                u8 owner = D->owners[i];
                order[owner][counts[owner]++] = (u8)i;
            }
    BYTE(D->ui + 0xDCu + order[0][0]) = 1;
    BYTE(D->ui + 0xDCu + order[1][0]) = 2;
    BYTE(D->ui + 0xDCu + order[0][1]) = 3;
    BYTE(D->ui + 0xDCu + order[1][1]) = 4;
    result = original_pack();
    /* Native packing must leave exactly four present entries on our side. */
    for (i = 0; i < 6; ++i)
        if (!!(BYTE(D->session + 0x44Cu + i * 0x8Cu + 0x286u) & 0x80) != (i < 4)) {
            for (rank = 0; rank < 6; ++rank) BYTE(D->ui + 0xDCu + rank) = old[rank];
            S[5] = 255;
            return 0;
        }
    for (i = 0; i < 6; ++i) S[10 + i] = i < 4 ? (i & 1) : 255;
    WORD(S + 0x1C) = D->session;
    D->active = 0; D->committed = 1;
    S[9] = 1; S[5] = S[6] = 0; S[7] = 1;
    WORD(S + 0x10) += 1;
    return result;
}

void coop_cleanup(void) {
    original_cleanup();
    if (!enabled()) return;
    D->active = 0;
    if (!D->committed) invalidate();
    S[5] = S[6] = 0; S[7] = 1;
    WORD(S + 0x10) += 1;
}

u32 coop_input_scope(u32 caller) {
    u32 ui, handle;
    if (battle_input_scope(caller)) return 1;
    if (!enabled() || !D->active) return 0;
    switch (caller) {
    case 0x80156458u: case 0x80156478u: case 0x801569D8u:
    case 0x80157074u: case 0x801570B4u: case 0x80157624u: case 0x80157930u:
        break;
    default: return 0;
    }
    ui = WORD(UI_PTR);
    if (ui < 0x80000000u || ui > 0x81FFFF00u) return 0;
    if (HALF(ui + 0x140u) != 0) return 0;
    handle = WORD(ui + 0xC0u);
    if (handle >= 32 || !BYTE(REGISTRY + 0x12Cu + handle) ||
        WORD(REGISTRY + 0x2Cu + 4 * handle) != 0x80156414u) return 0;
    if (!binding() || D->owner > 1) { S[5] = 255; return 1; }
    S[5] = 1; S[6] = D->owner;
    return 1;
}
