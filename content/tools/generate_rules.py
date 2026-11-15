"""Validate shared rules and produce one freestanding C header and native JSON.

These outputs are build inputs, not a game patch or NPC installation.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / 'content/pokemon/battle-rules.json'


def validate(data):
    policy = data['policy']
    if policy['npc_pool_max'] != 20 or policy['active_moves'] != 4:
        raise ValueError('Expected 4 active moves and 20 pool moves')
    if policy.get('status_moves_in_pool') != 6 or policy.get('offensive_moves_in_pool') != 14:
        raise ValueError('Expected 14 offensive and 6 status moves')
    if policy.get('minimum_offensive_moves', 0) not in (0, 1):
        raise ValueError('Unsupported offensive-move minimum')
    if policy['ev_total'] != 508 or policy['ev_per_stat_max'] != 252:
        raise ValueError('This sampler requires the validated 508/252 EV budget')
    if not 0 <= policy['iv_min'] <= policy['iv_max'] <= 31:
        raise ValueError('Invalid IV range')
    seen = set()
    slots = set()
    for entry in data['entries']:
        if entry['key'] in seen:
            raise ValueError('Duplicate Pokemon key')
        seen.add(entry['key'])
        base = [entry['base_stats'][name] for name in data['stat_order']]
        if len(base) != 6 or any(type(v) is not int or not 1 <= v <= 255 for v in base):
            raise ValueError('Invalid base stats')
        if entry['mega_legendary_strength_tier']:
            lo, hi = policy['mega_base_stat_budget']
            if not lo <= sum(base) <= hi:
                raise ValueError('Mega needs a reviewed legendary-tier stat budget')
        moves = entry['npc_move_pool']
        ids = [m['native_id'] for m in moves]
        if len(ids) != 20 or len(ids) != len(set(ids)) or any(not 1 <= m <= 467 for m in ids):
            raise ValueError('Invalid move pool')
        if sum(m['category'] == 'status' for m in moves) != 6:
            raise ValueError('Every pool must contain 14 offensive and 6 status moves')
        for move in moves:
            if move['category'] not in ('physical', 'special', 'status') or not move['body_action'] or not move['effect_emitter']:
                raise ValueError('Every move requires an animation/effect contract')
            if not 1 <= move['native_pp'] <= 40:
                raise ValueError('Invalid native PP')
        if entry['player_moves'] is not None and (len(entry['player_moves']) != 4 or not set(entry['player_moves']) <= set(ids)):
            raise ValueError('Player set outside pool')
        placement = entry['rental_pass']
        slot = (placement['index'], placement['slot'])
        if slot in slots or (placement['slot'] in placement['preserve_slots'] and placement.get('action') != 'preserve_existing'):
            raise ValueError('Pass placement collision or protected slot')
        slots.add(slot)
    return data


def header(data):
    validate(data)
    lines = ['/* Generated from shared battle-rules.json. No game assets. */',
             f"#define SHARED_IV_MIN {data['policy']['iv_min']}u",
             f"#define SHARED_IV_SPAN {data['policy']['iv_max'] - data['policy']['iv_min'] + 1}u",
             '#define SHARED_POOL_CAPACITY 20',
             f"#define SHARED_MIN_OFFENSIVE {data['policy'].get('minimum_offensive_moves', 0)}u",
             'struct SharedProfile { unsigned short base[6], moves[SHARED_POOL_CAPACITY]; unsigned char categories[SHARED_POOL_CAPACITY], pp[SHARED_POOL_CAPACITY], count; };',
             'static const struct SharedProfile shared_profiles[] = {']
    for entry in data['entries']:
        pool = entry['npc_move_pool']
        vectors = ([entry['base_stats'][name] for name in data['stat_order']],
                   [m['native_id'] for m in pool],
                   [('physical', 'special', 'status').index(m['category']) for m in pool],
                   [m['native_pp'] for m in pool])
        lines.append(' {' + ','.join('{' + ','.join(map(str, v)) + '}' for v in vectors) + ',' + str(len(pool)) + '},')
    lines += ['};', '#define SHARED_PROFILE_COUNT (sizeof(shared_profiles)/sizeof(shared_profiles[0]))']
    return '\n'.join(lines) + '\n'


def generate(source, output):
    payload = source.read_bytes()
    data = validate(json.loads(payload))
    output.mkdir(parents=True, exist_ok=True)
    (output / 'battle_rules.h').write_text(header(data), encoding='utf-8')
    (output / 'battle-rules.json').write_bytes(payload)
    report = dict(source_sha256=hashlib.sha256(payload).hexdigest(), profiles=len(data['entries']),
                  native_and_dolphin_share_same_input=True, game_integration=False)
    (output / 'generation-proof.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEFAULT)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.source, args.output), indent=2))
