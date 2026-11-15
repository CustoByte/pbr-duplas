extends Node3D

# This is a native 3D laboratory, not the Battle Revolution battle engine.
var shared_rules: Dictionary = {}
var model: Node3D
var pivot := Node3D.new()
var camera := Camera3D.new()
var player: AnimationPlayer
var clips: Dictionary = {}
var clip_menu := OptionButton.new()
var status := Label.new()
var stats := Label.new()
var open_dialog := FileDialog.new()
var yaw := 0.45
var pitch := 0.08
var distance := 6.0
var dragging := false
var elapsed := 0.0
var boot_clock := Time.get_ticks_usec()
var frame_times: Array[float] = []
var warmup_frames := 0
var measurement_started := -1.0
var frame_clock := 0
var model_loaded_at := 0.0
var load_ms := 0.0
var benchmark_seconds := 0.0
var benchmark_next := 0.0
var benchmark_exit := true
var benchmark_index := 0
var report_path := "user://performance.json"
var capture_path := ""
var captured := false
var capture_quit := false
var self_test := false
var data_dir := ""
var action_buttons: Array[Button] = []

func _ready() -> void:
	# Metadata for future battles only; this scene still has no battle engine.
	if FileAccess.file_exists("res://data/battle-rules.json"):
		var rules = JSON.parse_string(FileAccess.get_file_as_string("res://data/battle-rules.json"))
		if rules is Dictionary and rules.get("kind") == "shared-battle-rules":
			shared_rules = rules
	Engine.max_fps = 60
	build_stage()
	build_interface()
	var args := OS.get_cmdline_user_args()
	var model_path := ""
	var initial_action := ""
	var pose_frame := -1.0
	for i in range(args.size()):
		match args[i]:
			"--model":
				if i + 1 < args.size(): model_path = args[i + 1]
			"--benchmark-seconds":
				if i + 1 < args.size(): benchmark_seconds = maxf(float(args[i + 1]), 3.0)
			"--report":
				if i + 1 < args.size(): report_path = args[i + 1]
			"--capture":
				if i + 1 < args.size(): capture_path = args[i + 1]
			"--initial-action":
				if i + 1 < args.size(): initial_action = args[i + 1]
			"--pose-frame":
				if i + 1 < args.size(): pose_frame = float(args[i + 1])
			"--self-test": self_test = true
			"--capture-and-quit": capture_quit = true
			"--data-dir":
				if i + 1 < args.size(): data_dir = args[i + 1]
	if data_dir.is_empty(): data_dir = ProjectSettings.globalize_path("user://")
	if model_path.is_empty() and not data_dir.is_empty():
		var saved := data_dir.path_join("native-model.json")
		if FileAccess.file_exists(saved):
			var remembered = JSON.parse_string(FileAccess.get_file_as_string(saved))
			if remembered is Dictionary: model_path = remembered.get("path", "")
	if not model_path.is_empty(): load_model(model_path)
	elif self_test:
		push_error("Self-test requires --model")
		get_tree().quit(2)
	if not initial_action.is_empty() and is_instance_valid(player):
		var selected := resolve_role(initial_action)
		if not selected.is_empty():
			player.play(selected, 0.0)
			player.advance(0.0)
			if pose_frame >= 0.0:
				player.seek(pose_frame / 30.0, true)
				player.pause()
	frame_clock = Time.get_ticks_usec()

func build_stage() -> void:
	var world := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color("101a2c")
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("d8e5ff")
	environment.ambient_light_energy = 0.65
	world.environment = environment
	add_child(world)
	var key := DirectionalLight3D.new()
	key.rotation_degrees = Vector3(-45, -35, 0)
	key.light_energy = 1.1
	key.shadow_enabled = true
	add_child(key)
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-25, 140, 0)
	fill.light_color = Color("8ce9ed")
	fill.light_energy = 0.45
	add_child(fill)
	var floor_mesh := MeshInstance3D.new()
	var cylinder := CylinderMesh.new()
	cylinder.top_radius = 1.65
	cylinder.bottom_radius = 1.65
	cylinder.height = 0.12
	cylinder.radial_segments = 64
	floor_mesh.mesh = cylinder
	floor_mesh.position.y = -0.065
	var material := StandardMaterial3D.new()
	material.albedo_color = Color("253b55")
	material.roughness = 0.8
	floor_mesh.material_override = material
	add_child(floor_mesh)
	add_child(pivot)
	add_child(camera)
	camera.fov = 36.0
	update_camera()

func build_interface() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", 26)
	margin.add_theme_constant_override("margin_top", 22)
	margin.add_theme_constant_override("margin_right", 26)
	margin.add_theme_constant_override("margin_bottom", 22)
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(margin)
	var column := VBoxContainer.new()
	column.mouse_filter = Control.MOUSE_FILTER_IGNORE
	margin.add_child(column)
	var heading := Label.new()
	heading.text = "PBR NATIVE  /  LABORATÓRIO 3D"
	heading.add_theme_color_override("font_color", Color("58dbc2"))
	heading.add_theme_font_size_override("font_size", 24)
	column.add_child(heading)
	var subtitle := Label.new()
	subtitle.text = "Cena em tempo real • Sem Dolphin • Ainda não inclui batalhas do jogo"
	column.add_child(subtitle)
	column.add_child(stats)
	var adapter := Label.new()
	adapter.text = "Renderizador: " + RenderingServer.get_video_adapter_name()
	adapter.add_theme_font_size_override("font_size", 13)
	column.add_child(adapter)
	var spacer := Control.new()
	spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	spacer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_child(spacer)
	status.text = "Abra o modelo GLB convertido localmente para começar."
	column.add_child(status)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	column.add_child(row)
	button(row, "Abrir modelo 3D", func(): open_dialog.popup_centered_ratio(0.75))
	row.add_child(clip_menu)
	clip_menu.disabled = true
	clip_menu.item_selected.connect(func(index): play_clip(clip_menu.get_item_text(index)))
	for choice in [["Espera", "wait"], ["Correr", "run"], ["Físico", "punch"], ["Especial", "kime_b"], ["Dano", "damage"]]:
		var role: String = choice[1]
		var control := button(row, choice[0], func(): play_role(role))
		control.disabled = true
		action_buttons.append(control)
	button(row, "Medir 10 s", start_measurement)
	var controls := Label.new()
	controls.text = "Arraste com o botão direito para girar • Roda do mouse: zoom • Animações com transição de 0,18 s"
	controls.add_theme_font_size_override("font_size", 14)
	column.add_child(controls)
	open_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
	open_dialog.access = FileDialog.ACCESS_FILESYSTEM
	open_dialog.filters = PackedStringArray(["*.glb ; Modelo convertido localmente"])
	open_dialog.use_native_dialog = true
	open_dialog.file_selected.connect(load_model)
	layer.add_child(open_dialog)

func button(parent: Node, text: String, callback: Callable) -> Button:
	var result := Button.new()
	result.text = text
	result.custom_minimum_size.y = 40
	result.pressed.connect(callback)
	parent.add_child(result)
	return result

func load_model(path: String) -> void:
	var start := Time.get_ticks_usec()
	var document := GLTFDocument.new()
	var state := GLTFState.new()
	var error := document.append_from_file(path, state)
	if error != OK:
		status.text = "Não foi possível ler o GLB: " + error_string(error)
		if self_test: get_tree().quit(2)
		return
	var candidate := document.generate_scene(state)
	if candidate == null:
		status.text = "O GLB não contém uma cena válida."
		if self_test: get_tree().quit(2)
		return
	if is_instance_valid(model):
		pivot.remove_child(model)
		model.queue_free()
	# Fit an unanimated parent; imported clips may animate their scene root.
	model = Node3D.new()
	model.name = "ModelFit"
	model.add_child(candidate)
	pivot.add_child(model)
	var meshes := model.find_children("*", "MeshInstance3D", true, false)
	if meshes.is_empty():
		status.text = "Não há geometria nesse arquivo."
		if self_test: get_tree().quit(2)
		return
	player = null
	clips.clear()
	clip_menu.clear()
	var players := model.find_children("*", "AnimationPlayer", true, false)
	if not players.is_empty():
		player = players[0]
		player.animation_finished.connect(on_animation_finished)
		for clip in player.get_animation_list():
			if clip == "RESET": continue
			clip_menu.add_item(clip)
			var role := String(clip).to_lower().trim_prefix("mega_").trim_prefix("body_")
			clips[role] = clip
			var animation := player.get_animation(clip)
			animation.loop_mode = Animation.LOOP_LINEAR if role in ["wait", "run", "kuchu_wait"] else Animation.LOOP_NONE
	if is_instance_valid(player) and clips.has("wait"):
		player.play(clips["wait"], 0.0)
		player.advance(0.0)
	for skeleton in model.find_children("*", "Skeleton3D", true, false):
		skeleton.force_update_all_bone_transforms()
	var bounds := posed_bounds(meshes)
	var factor := 2.0 / maxf(bounds.size.y, 0.01)
	model.scale *= factor
	model.position -= Vector3(bounds.get_center().x, bounds.position.y, bounds.get_center().z) * factor
	clip_menu.disabled = clips.is_empty()
	for control in action_buttons: control.disabled = clips.is_empty()
	load_ms = (Time.get_ticks_usec() - start) / 1000.0
	model_loaded_at = (Time.get_ticks_usec() - boot_clock) / 1000000.0
	warmup_frames = 0
	measurement_started = -1.0
	frame_times.clear()
	play_role("wait")
	status.text = "%s • %d malhas • %d animações • Carregamento: %.1f ms" % [path.get_file(), meshes.size(), clips.size(), load_ms]
	if not data_dir.is_empty():
		DirAccess.make_dir_recursive_absolute(data_dir)
		var saved := FileAccess.open(data_dir.path_join("native-model.json"), FileAccess.WRITE)
		if saved: saved.store_string(JSON.stringify({"path": path}))
	if self_test: verify_scene(meshes)

func posed_bounds(meshes: Array[Node]) -> AABB:
	# Imported bind-space AABBs need not enclose the animated character. Fit the
	# actual waiting pose once; rendering remains GPU skeletal skinning.
	var bounds := AABB()
	var first := true
	for node in meshes:
		var skeleton: Skeleton3D = node.get_node_or_null(node.skeleton) as Skeleton3D
		var skin: Skin = node.skin
		var transforms: Array[Transform3D] = []
		if skeleton != null and skin != null:
			for i in range(skin.get_bind_count()):
				var bone: int = skin.get_bind_bone(i)
				if bone < 0: bone = skeleton.find_bone(skin.get_bind_name(i))
				transforms.append(skeleton.get_bone_global_pose(bone) * skin.get_bind_pose(i) if bone >= 0 else Transform3D.IDENTITY)
		for surface in range(node.mesh.get_surface_count()):
			var arrays: Array = node.mesh.surface_get_arrays(surface)
			var points: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var bones = arrays[Mesh.ARRAY_BONES]
			var weights = arrays[Mesh.ARRAY_WEIGHTS]
			for i in range(points.size()):
				var point: Vector3 = points[i]
				if not transforms.is_empty() and bones != null and weights != null:
					point = Vector3.ZERO
					var count: int = bones.size() / points.size()
					for j in range(count):
						var index: int = bones[i * count + j]
						if index < transforms.size(): point += (transforms[index] * points[i]) * weights[i * count + j]
				point = node.global_transform * point
				if first:
					bounds = AABB(point, Vector3.ZERO)
					first = false
				else: bounds = bounds.expand(point)
	return bounds

func resolve_role(role: String) -> String:
	if clips.has(role): return clips[role]
	var alternatives := {"punch": ["hikkaku", "kime_phy", "tackle"], "kick": ["tackle", "kime_phy", "hikkaku"], "kime_b": ["kime", "kime_a"]}
	for candidate in alternatives.get(role, []):
		if clips.has(candidate): return clips[candidate]
	return ""

func play_role(role: String) -> void:
	var clip := resolve_role(role)
	if not clip.is_empty(): play_clip(clip)

func play_clip(clip: String) -> void:
	if is_instance_valid(player) and player.has_animation(clip):
		player.play(clip, 0.18)
		for i in range(clip_menu.item_count):
			if clip_menu.get_item_text(i) == clip: clip_menu.select(i)

func on_animation_finished(_clip: StringName) -> void:
	play_role("wait")

func verify_scene(meshes: Array[Node]) -> void:
	var required := ["wait", "run", "punch", "kick", "kime_b", "damage", "down"]
	for role in required:
		if resolve_role(role).is_empty():
			push_error("Missing body action: " + role)
			get_tree().quit(2)
			return
	var skeletons := model.find_children("*", "Skeleton3D", true, false)
	if skeletons.is_empty():
		push_error("Model has no skeleton")
		get_tree().quit(2)
		return
	var skeleton: Skeleton3D = skeletons[0]
	var pose_landmarks := {}
	for label in ["Head", "Hips", "LFoot", "RFoot"]:
		var bone_id := skeleton.find_bone(label)
		if bone_id >= 0: pose_landmarks[label] = str(skeleton.global_transform * skeleton.get_bone_global_pose(bone_id).origin)
	if skeleton.find_bone("Head") >= 0 and skeleton.find_bone("LFoot") >= 0:
		var head := skeleton.global_transform * skeleton.get_bone_global_pose(skeleton.find_bone("Head")).origin
		var foot := skeleton.global_transform * skeleton.get_bone_global_pose(skeleton.find_bone("LFoot")).origin
		if head.y - foot.y < 0.5:
			push_error("Character axis mismatch: head is not above feet")
			get_tree().quit(2)
			return
	var moved := false
	player.play(resolve_role("punch"))
	player.advance(0.0)
	var before: Array[Transform3D] = []
	for i in range(skeleton.get_bone_count()): before.append(skeleton.get_bone_pose(i))
	player.advance(0.5)
	for i in range(skeleton.get_bone_count()):
		if not before[i].is_equal_approx(skeleton.get_bone_pose(i)): moved = true
	if not moved:
		push_error("Animation did not move any bones")
		get_tree().quit(2)
		return
	var vertices := 0
	for node in meshes:
		for surface in range(node.mesh.get_surface_count()):
			vertices += node.mesh.surface_get_array_len(surface)
	var proof := {"skeleton_bones": skeleton.get_bone_count(), "vertices": vertices, "body_actions": clips.keys(), "bone_animation_moves": moved, "waiting_pose_landmarks": pose_landmarks, "dolphin_used": false, "full_battle_engine": false, "shared_content_profiles": shared_rules.get("entries", []).size()}
	print("NATIVE_SCENE_PROOF " + JSON.stringify(proof))
	var proof_file := FileAccess.open(report_path, FileAccess.WRITE)
	if proof_file: proof_file.store_string(JSON.stringify(proof, "\t"))
	play_role("wait")
	if benchmark_seconds == 0.0: get_tree().quit(0)

func update_camera() -> void:
	var target := Vector3(0.0, 1.0, 0.0)
	camera.position = target + Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch)) * distance
	camera.look_at(target)

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_RIGHT: dragging = event.pressed
		if event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_UP: distance = maxf(distance - 0.3, 2.0)
		if event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_DOWN: distance = minf(distance + 0.3, 12.0)
		update_camera()
	if event is InputEventMouseMotion and dragging:
		yaw -= event.relative.x * 0.008
		pitch = clampf(pitch + event.relative.y * 0.006, -0.3, 1.1)
		update_camera()

func _process(_delta: float) -> void:
	elapsed = (Time.get_ticks_usec() - boot_clock) / 1000000.0
	var now := Time.get_ticks_usec()
	var milliseconds := (now - frame_clock) / 1000.0 if frame_clock != 0 else 0.0
	frame_clock = now
	if model != null: warmup_frames += 1
	if model != null and elapsed - model_loaded_at > 2.0 and warmup_frames > 30:
		if measurement_started < 0: measurement_started = elapsed
		frame_times.append(milliseconds)
		if frame_times.size() > 36000: frame_times.pop_front()
	stats.text = "%.0f FPS • %.2f ms/quadro • Meta: 60 FPS • 3D em tempo real" % [Engine.get_frames_per_second(), milliseconds]
	if not capture_path.is_empty() and elapsed - model_loaded_at > 3.0 and warmup_frames > 60 and not captured:
		captured = true
		capture_frame.call_deferred()
	if benchmark_seconds > 0.0 and model != null:
		if elapsed > benchmark_next:
			var roles := ["wait", "run", "punch", "kick", "kime_b", "damage"]
			play_role(roles[benchmark_index % roles.size()])
			benchmark_index += 1
			benchmark_next = elapsed + 2.0
		if measurement_started >= 0 and elapsed - measurement_started >= maxf(benchmark_seconds - 2.0, 1.0):
			write_report()
			benchmark_seconds = 0.0
			if benchmark_exit: get_tree().quit(0)
			else: status.text = "Medição salva em: " + report_path

func start_measurement() -> void:
	if model == null:
		status.text = "Abra um modelo antes de medir."
		return
	frame_times.clear()
	benchmark_seconds = 10.0
	benchmark_exit = false
	model_loaded_at = elapsed
	warmup_frames = 0
	measurement_started = -1.0
	benchmark_next = elapsed
	report_path = data_dir.path_join("performance.json")
	status.text = "Medindo 10 segundos; os primeiros 2 são aquecimento."

func capture_frame() -> void:
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(capture_path)
	if capture_quit: get_tree().quit(0)

func write_report() -> void:
	var sorted := frame_times.duplicate()
	sorted.sort()
	var total := 0.0
	for sample in sorted: total += sample
	var mean := total / maxf(sorted.size(), 1)
	var p95: float = sorted[mini(int(sorted.size() * 0.95), sorted.size() - 1)] if not sorted.is_empty() else 0.0
	var result := {"kind": "native 3D scene, not full Battle Revolution", "engine": Engine.get_version_info().string, "renderer": RenderingServer.get_video_adapter_name(), "display_driver": DisplayServer.get_name(), "frames_measured": sorted.size(), "warmup_minimum_seconds": 2, "warmup_minimum_frames": 30, "warmup_actual_seconds": measurement_started - model_loaded_at, "mean_frame_ms": mean, "p95_frame_ms": p95, "measured_fps": 1000.0 / mean if mean > 0 else 0, "model_load_ms": load_ms, "memory_static_bytes": OS.get_static_memory_usage(), "animation_count": clips.size(), "dolphin_used": false, "windows_user_pc_verified": false}
	var file := FileAccess.open(report_path, FileAccess.WRITE)
	if file: file.store_string(JSON.stringify(result, "\t"))
	print("NATIVE_BENCHMARK " + JSON.stringify(result))
