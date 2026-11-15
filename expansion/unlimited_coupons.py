"""Virtual maximum Poké Coupons and capped native writes, RPBE01 rev 0.

Only save property 8 is affected. Existing saves need no external editing.
Shop availability, inventory and progression checks remain native.
"""
import struct
from prepare_campaign_doubles import file_offset, sha, word
from team_series_asm import branch

SOURCE_SHA256 = '91d0ceacd6a138948d3519f37b7f1715f143481c7148f1f57e3f84750db50189'
GET = 0x801675BC
SET = 0x8016746C
GET_BRIDGE = 0x80645F00
SET_BRIDGE = 0x80645F40
MAXIMUM = 999999


def prepare(dol):
    if sha(dol) != SOURCE_SHA256:
        raise ValueError('Unlimited coupons requires the verified Full493 candidate')
    out = bytearray(dol)
    bridges = {
        # cmpwi r3,8; bne native; lis/addi r3,999999; blr;
        # native: replay the displaced stack allocation, continue original getter.
        GET_BRIDGE: [0x2C030008, 0x40820010, 0x3C60000F, 0x3863423F,
                     0x4E800020, 0x9421FFE0, branch(GET_BRIDGE + 24, GET + 4)],
        # Only the coupon property replaces r4. The actual setter and save
        # serialization still own bit packing, active profile and persistence.
        SET_BRIDGE: [0x2C030008, 0x4082000C, 0x3C80000F, 0x3884423F,
                     0x9421FFE0, branch(SET_BRIDGE + 20, SET + 4)],
    }
    ranges = []
    for start, instructions in bridges.items():
        at = file_offset(out, start)
        size = len(instructions) * 4
        if any(out[at:at + size]):
            raise ValueError('Coupon bridge overlaps existing code')
        for i, instruction in enumerate(instructions):
            struct.pack_into('>I', out, at + 4 * i, instruction)
        ranges.append((start, start + size))
    for entry, bridge in ((GET, GET_BRIDGE), (SET, SET_BRIDGE)):
        at = file_offset(out, entry)
        if word(out, at) != 0x9421FFE0:
            raise ValueError('Save accessor prologue mismatch')
        struct.pack_into('>I', out, at, branch(entry, bridge))
        ranges.append((entry, entry + 4))
    return bytes(out), {
        'status': 'implemented-awaiting-Dolphin-shop-validation',
        'source_dol_sha256': sha(dol), 'output_dol_sha256': sha(out),
        'property': 8, 'displayed_balance': MAXIMUM,
        'behavior': 'Coupon reads return 999999; native coupon writes store 999999',
        'existing_save_supported': True, 'external_save_edits': False,
        'availability_and_inventory_checks_changed': False,
        'dolphin_tested': False,
        'changed_address_ranges': [[hex(a), hex(b)] for a, b in ranges],
    }
