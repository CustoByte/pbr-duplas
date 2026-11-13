"""Native-reference Snivy asset profile; gameplay bindings remain unverified."""

SLOTS = {
    "wait": "NorIdle0",
    "run": "Run0",
    "damage": "DamF0",
    "down": "Faint0",
    "tackle": "Atk0_0",
    "kime": "Atk2_0",
    "kime_a": "Atk3_0",
    "tx_wink": "NorIdle0",
    "tx_sleep": "Sleep0_1",
    "tx_wakeup": "Sleep0_2",
    "mamoru": "Charge0",
    "kime_phy": "Atk4_0",
}

ANCHORS = {
    "origin": "PBR_StaticRoot",
    "direct_set": "PBR_StaticRoot",
    "center": "Waist",
    "ef_leye": "Head",
    "ef_reye": "Head",
    "ef_mouth": "Nose",
    "ef_damage": "Spine02",
    "ef_head": "Head",
    "ef_lfhand": "LHand",
    "ef_lrhand": "LHand",
    "ef_rfhand": "RHand",
    "ef_rrhand": "RHand",
    "ef_lffoot": "LFoot",
    "ef_lrfoot": "LFoot",
    "ef_rffoot": "RFoot",
    "ef_rrfoot": "RFoot",
    "ef_o": "Waist",
    "ct_bust": "Spine02",
    "ct_bust_move": "Spine02",
    "ct_all": "SnivyMotion",
    "ct_all_move": "SnivyMotion",
}


def configure(exporter, contract):
    import bpy

    exporter.SNIVY_ACTION_IDS = list(SLOTS)
    for name in SLOTS:
        for cls in (bpy.types.Armature, bpy.types.Material):
            if not hasattr(cls, "prop_" + name):
                setattr(
                    cls,
                    "prop_" + name,
                    bpy.props.PointerProperty(type=bpy.types.Action),
                )
    reference = {a["name"]: a for a in contract["resources"][0]["actions"]}
    if tuple(reference) != tuple(SLOTS):
        raise ValueError("Reference action ordering differs")

    def write_action(file, address, name):
        # Never copy native pointers, masks or node/material indices.
        source = reference[name]
        length = max(
            exporter.actions[name]["length"] / exporter.FRAME_RATE,
            1 / exporter.FRAME_RATE,
        )
        for offset, value in (
            (4, source["start"] / source["length"] * length),
            (8, source["end"] / source["length"] * length),
            (12, length),
        ):
            file.write("float", value, address, offset=offset)
        for i, value in enumerate(source["flags"]):
            file.write("uchar", value, address, offset=40 + i)
        return address + 48

    exporter.writeAction = write_action
