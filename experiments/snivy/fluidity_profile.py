"""Unpublished authored menu/damage transitions; source frames stay at 30 fps."""

SLOTS = {'kime_a': dict(source='NorIdle0', last_frame=30, blend_in=0, blend_out=8),
         'damage': dict(source='DamF0', last_frame=30, blend_in=2, blend_out=8)}


def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def idle_weight(slot, frame, last_frame):
    profile = SLOTS.get(slot)
    if not profile:
        return 0.0
    start = profile['blend_in']
    end = profile['blend_out']
    incoming = 1 - smoothstep(frame / start) if start and frame < start else 0
    outgoing = smoothstep((frame - (last_frame - end)) / end) if end else 0
    return max(incoming, outgoing)
