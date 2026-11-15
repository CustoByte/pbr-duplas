"""Validate the requested set and calculate Gen IV stats; no game writes."""

import json
from pathlib import Path

KEYS = ('hp', 'attack', 'defense', 'special_attack', 'special_defense', 'speed')
MOVES = (418, 370, 396, 182)


def describe(profile):
    if tuple(m['native_id'] for m in profile['moveset']) != MOVES:
        raise ValueError('Moves must match the user-selected set')
    if profile['ability']['native_id'] != 91 or profile['item']['native_id'] != 0:
        raise ValueError('Expected Adaptability and no held item')
    if profile['nature']['native_id'] != 0:
        raise ValueError('This calculation requires the neutral Hardy nature')
    evs, ivs = profile['evs'], profile['ivs']
    if sum(evs.values()) > 510 or any(not 0 <= evs[k] <= 252 for k in KEYS):
        raise ValueError('Invalid EV allocation')
    if any(not 0 <= ivs[k] <= 31 for k in KEYS):
        raise ValueError('Invalid IV allocation')
    placement = profile['pass_placement']
    if placement['replace_national_id'] != 2 or placement['level'] != 50:
        raise ValueError('Expected Ivysaur replacement at level 50')
    stats = {}
    for key in KEYS:
        core = (2 * profile['base_stats'][key] + ivs[key] + evs[key] // 4) * 50 // 100
        stats[key] = core + (60 if key == 'hp' else 5)
    return dict(level=50, stats=stats, ev_total=sum(evs.values()),
                installed=False, gameplay_verified=False)


if __name__ == '__main__':
    profile = json.loads(Path(__file__).with_name('profile.json').read_text())
    print(json.dumps(describe(profile), indent=2))
