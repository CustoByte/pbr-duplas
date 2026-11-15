extends Node

# Review UV values decoded from the exported SDR, not invented eye frames.
var tracks: Dictionary = {}
var materials: Array[StandardMaterial3D] = []
var state := ""
var clock := 0.0

func configure(meshes: Array[Node], decoded_tracks: Dictionary) -> void:
	tracks = decoded_tracks
	for node in meshes:
		if not String(node.name).begins_with("7_CharizardMegaY"): continue
		var mesh := node as MeshInstance3D
		for surface in range(mesh.mesh.get_surface_count()):
			var original := mesh.get_active_material(surface) as StandardMaterial3D
			if original == null: continue
			var material := original.duplicate() as StandardMaterial3D
			mesh.set_surface_override_material(surface,material)
			materials.append(material)
	if materials.is_empty():
		push_error("No Charizard Y eye surface found")
		get_tree().quit(2)

func set_state(name: String) -> void:
	state = name
	clock = 0.0
	apply_frame()

func advance(delta: float) -> void:
	clock += delta
	apply_frame()

func apply_frame() -> void:
	var offset := 0.0
	if tracks.has(state):
		for point in tracks[state].points:
			if float(point.time) <= clock + .000001: offset = float(point.offset_v)
	for material in materials: material.uv1_offset = Vector3(0,offset,0)
