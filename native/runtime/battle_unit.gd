extends Node3D

## Um Pokémon em campo: modelo GLB real do PBR, escalado e apoiado no chão,
## com as animações originais do jogo (wait / tackle / punch / kime / damage / down).

const TARGET_HEIGHT := 2.6
## Recuo/diagonal curta ao atacar, relativa à posição inicial.
const LUNGE := 1.1

var anim_player: AnimationPlayer = null
var clips: Array[String] = []
var home := Vector3.ZERO
var side := "player"


func setup(entry: Dictionary) -> void:
	side = str(entry.get("side", "player"))
	var model_path := str(entry.get("model_path", ""))
	if model_path == "" or not ResourceLoader.exists(model_path):
		_build_fallback()
		return

	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	if doc.append_from_file(ProjectSettings.globalize_path(model_path), state) != OK:
		_build_fallback()
		return
	var scene := doc.generate_scene(state)
	if scene == null:
		_build_fallback()
		return

	add_child(scene)
	_scale_and_ground(scene)
	_face_center()
	_collect(scene)


func _scale_and_ground(root: Node) -> void:
	var box := _bounds(root)
	if box.size.y <= 0.001:
		return
	var factor := TARGET_HEIGHT / box.size.y
	root.scale = Vector3.ONE * factor
	root.position.y = -box.position.y * factor


func _bounds(root: Node) -> AABB:
	var out := AABB()
	var first := true
	for node in _mesh_nodes(root):
		var mi := node as MeshInstance3D
		if mi.mesh == null:
			continue
		var box: AABB = mi.global_transform * mi.mesh.get_aabb()
		if first:
			out = box
			first = false
		else:
			out = out.merge(box)
	return out


func _mesh_nodes(root: Node) -> Array:
	var found: Array = []
	if root is MeshInstance3D:
		found.append(root)
	for c in root.get_children():
		found.append_array(_mesh_nodes(c))
	return found


func _face_center() -> void:
	# no PBR, os dois times ficam de frente um para o outro
	rotation_degrees.y = 180.0 if side == "player" else 0.0


func _collect(root: Node) -> void:
	anim_player = _find_player(root)
	if anim_player == null:
		return
	for n in anim_player.get_animation_list():
		clips.append(String(n))


func _find_player(node: Node) -> AnimationPlayer:
	if node is AnimationPlayer:
		return node as AnimationPlayer
	for c in node.get_children():
		var f := _find_player(c)
		if f != null:
			return f
	return null


func play_idle() -> void:
	_play(["wait", "kuchu_wait"], true)


func play_attack(move_type: String) -> void:
	var physical_types := ["Normal", "Fighting", "Flying", "Poison", "Ground", "Rock", "Bug", "Ghost", "Steel", "Dark"]
	var special_types := ["Fire", "Water", "Electric", "Grass", "Ice", "Psychic", "Dragon"]
	var order: Array
	if move_type in physical_types:
		order = ["tackle", "punch", "kick", "kime_a", "kime_b"]
	else:
		order = ["kime", "kime_a", "tackle"]
	if _play(order, false) != "":
		_lunge()


func play_damage() -> void:
	_play(["damage"], false)


func play_faint() -> void:
	_play(["down"], false)
	var tw := create_tween()
	tw.tween_property(self, "position:y", position.y - 0.25, 0.5)


## Toca a primeira animação existente da lista; devolve o nome ou "".
func _play(candidates: Array, loop: bool) -> String:
	if anim_player == null:
		return ""
	for want in candidates:
		for have in clips:
			if have.to_lower() == String(want).to_lower():
				anim_player.play(have)
				var anim := anim_player.get_animation(have)
				if anim:
					anim.loop_mode = Animation.LOOP_LINEAR if loop else Animation.LOOP_NONE
				return have
	return ""


func _lunge() -> void:
	var dir := (Vector3.ZERO - home).normalized()
	var target := home + dir * LUNGE
	var tw := create_tween()
	tw.tween_property(self, "position", target, 0.18).set_ease(Tween.EASE_OUT)
	tw.tween_property(self, "position", home, 0.30).set_ease(Tween.EASE_IN)


func _build_fallback() -> void:
	var body := MeshInstance3D.new()
	body.mesh = CapsuleMesh.new()
	var cap := body.mesh as CapsuleMesh
	cap.height = TARGET_HEIGHT
	cap.radius = 0.55
	body.position.y = TARGET_HEIGHT * 0.5
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.35, 0.40, 0.55)
	body.material_override = mat
	add_child(body)
