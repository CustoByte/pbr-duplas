"""Generate an owned animated triangle for CI; no Pokémon/game assets."""
import json
from pathlib import Path
import struct
import sys


def generate(path):
    binary = bytearray()
    views, accessors = [], []
    def add(raw, component, count, kind, **extra):
        while len(binary) % 4:
            binary.append(0)
        view = len(views)
        views.append(dict(buffer=0, byteOffset=len(binary), byteLength=len(raw)))
        binary.extend(raw)
        accessors.append(dict(bufferView=view, componentType=component, count=count, type=kind, **extra))
        return len(accessors) - 1
    position = add(struct.pack('<9f', -.5, 0, 0, .5, 0, 0, 0, 1, 0), 5126, 3, 'VEC3', min=[-.5, 0, 0], max=[.5, 1, 0])
    joints = add(bytes(24), 5123, 3, 'VEC4')
    weights = add(struct.pack('<12f', *([1, 0, 0, 0] * 3)), 5126, 3, 'VEC4')
    indices = add(struct.pack('<3H', 0, 1, 2), 5123, 3, 'SCALAR')
    bind = add(struct.pack('<16f', *[1 if i % 5 == 0 else 0 for i in range(16)]), 5126, 1, 'MAT4')
    times = add(struct.pack('<2f', 0, 1), 5126, 2, 'SCALAR', min=[0], max=[1])
    motion = add(struct.pack('<6f', 0, 0, 0, 0, .25, 0), 5126, 2, 'VEC3')
    animations = [dict(name='Mega_' + role, samplers=[dict(input=times, output=motion, interpolation='LINEAR')], channels=[dict(sampler=0, target=dict(node=1, path='translation'))]) for role in ('wait', 'run', 'punch', 'kick', 'kime', 'kime_a', 'kime_b', 'damage', 'down')]
    doc = dict(asset=dict(version='2.0', generator='PBR Native owned CI fixture'), scene=0,
               scenes=[dict(nodes=[0])], nodes=[dict(name='TestRoot', children=[1, 2]), dict(name='TestBone'), dict(name='TestMesh', mesh=0, skin=0)],
               meshes=[dict(primitives=[dict(attributes=dict(POSITION=position, JOINTS_0=joints, WEIGHTS_0=weights), indices=indices, material=0)])],
               skins=[dict(joints=[1], skeleton=1, inverseBindMatrices=bind)],
               materials=[dict(doubleSided=True, pbrMetallicRoughness=dict(baseColorFactor=[.1, .8, .6, 1], metallicFactor=0, roughnessFactor=1))],
               animations=animations, buffers=[dict(byteLength=len(binary))], bufferViews=views, accessors=accessors)
    text = json.dumps(doc, separators=(',', ':')).encode()
    text += b' ' * (-len(text) % 4)
    binary.extend(bytes(-len(binary) % 4))
    result = struct.pack('<III', 0x46546c67, 2, 28 + len(text) + len(binary)) + struct.pack('<II', len(text), 0x4e4f534a) + text + struct.pack('<II', len(binary), 0x004e4942) + binary
    Path(path).write_bytes(result)


if __name__ == '__main__':
    generate(sys.argv[1])
