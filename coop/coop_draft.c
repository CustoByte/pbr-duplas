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

#define D ((volatile Draft *)0x8063EB00u)
#define S ((volatile u8 *)0x8063C6C0u)
#define WORD(p) (*(volatile u32 *)(p))
#define HALF(p) (*(volatile u16 *)(p))
#define BYTE(p) (*(volatile u8 *)(p))
#define DRFT 0x44524654u
#define COOP 0x434F4F50u
#define UI_PTR 0x806258C8u
#define REGISTRY 0x804E60F0u

extern void original_reset(void);
extern u32 original_choose(u32 slot, u32 side, u32 sound, u32 details);
extern u32 original_pack(void);
extern void original_cleanup(void);

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
