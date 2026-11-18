import json, struct, os

def make_glb(path):
    positions = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.5, 1.0, 0.0]
    indices = [0, 1, 2]
    pos_data = struct.pack('<9f', *positions)
    idx_data = struct.pack('<3H', *indices)
    bin_data = pos_data + idx_data
    if len(bin_data) % 4:
        bin_data += b'\x00' * (4 - len(bin_data) % 4)
    gltf = {
        "asset": {"version": "2.0", "generator": "pbr-native"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "TestPokemon"}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3",
             "min": [0.0, 0.0, 0.0], "max": [1.0, 1.0, 0.0]},
            {"bufferView": 1, "componentType": 5123, "count": 3, "type": "SCALAR"}
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_data), "target": 34962},
            {"buffer": 0, "byteOffset": len(pos_data), "byteLength": len(idx_data), "target": 34963}
        ],
        "buffers": [{"byteLength": len(bin_data)}]
    }
    json_str = json.dumps(gltf, separators=(',', ':'))
    json_bytes = json_str.encode('utf-8')
    if len(json_bytes) % 4:
        json_bytes += b' ' * (4 - len(json_bytes) % 4)
    total_length = 12 + 8 + len(json_bytes) + 8 + len(bin_data)
    header = struct.pack('<III', 0x46546C67, 2, total_length)
    json_chunk = struct.pack('<II', len(json_bytes), 0x4E4F534A) + json_bytes
    bin_chunk = struct.pack('<II', len(bin_data), 0x004E4942) + bin_data
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(header + json_chunk + bin_chunk)
    print(f"GLB created: {path} ({total_length} bytes)")

if __name__ == '__main__':
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'runtime', 'models', 'test_pokemon.glb')
    make_glb(out)