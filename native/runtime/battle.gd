extends Node3D

## Batalha dupla por turnos — núcleo do PBR Nativo.
## Regras lidas de data/battle-rules.json (formato do mod).
## Fluxo: seleção de 4 comandos -> resolução por velocidade -> dano.

const MAX_HP := 100.0

# Estado da batalha
var player_team: Array = []
var enemy_team: Array = []
var active_player: Array = []   # índices ativos (2)
var active_enemy: Array = []
var turn := 1
var awaiting_input := true
var pending_commands: Array = []  # cada: {slot, action, target}
var current_slot := 0

# Nós de UI
var log_label: Label
var command_panel: VBoxContainer
var slots_left_label: Label

var type_chart: Dictionary = {}


func _ready() -> void:
	var roster = _load_json("res://roster.json")
	var rules = _load_json("res://data/battle-rules.json")
	type_chart = rules.get("type_chart", {})
	_build_teams(roster)
	_build_world()
	_build_ui()
	_log("Batalha iniciada. Turno 1.")
	_begin_turn()


func _build_teams(roster) -> void:
	var list: Array = roster.get("entries", [])
	if list.size() < 4:
		push_warning("Roster insuficiente; usando duplicatas.")
		while list.size() < 4:
			list.append({"id": "placeholder", "name": "Placeholder",
				"types": ["Normal"], "hp": 100, "atk": 60, "def": 60, "spe": 60,
				"moves": [{"name": "Tackle", "power": 40, "type": "Normal"}]})
	for i in range(2):
		player_team.append(_make_combatant(list[i], "player"))
		enemy_team.append(_make_combatant(list[i + 2], "enemy"))
	active_player = [0, 1]
	active_enemy = [0, 1]


func _make_combatant(data: Dictionary, side: String) -> Dictionary:
	return {
		"name": data.get("name", "?"),
		"types": data.get("types", ["Normal"]),
		"max_hp": float(data.get("hp", 100)),
		"hp": float(data.get("hp", 100)),
		"atk": float(data.get("atk", 60)),
		"def": float(data.get("def", 60)),
		"spa": float(data.get("spatk", data.get("spa", 60))),
		"spd": float(data.get("spdef", data.get("spd", 60))),
		"spe": float(data.get("spe", 60)),
		"moves": data.get("moves", []),
		"side": side,
		"alive": true,
	}


func _build_world() -> void:
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-50, -40, 0)
	light.light_energy = 1.3
	add_child(light)

	var cam := Camera3D.new()
	cam.position = Vector3(0, 6.5, 9.0)
	cam.rotation_degrees = Vector3(-22, 0, 0)
	add_child(cam)

	var platform := MeshInstance3D.new()
	platform.mesh = CylinderMesh.new()
	platform.mesh.top_radius = 6.0
	platform.mesh.bottom_radius = 6.0
	platform.mesh.height = 0.4
	platform.mesh.radial_segments = 64
	platform.position = Vector3(0, -0.2, 0)
	var plat_mat := StandardMaterial3D.new()
	plat_mat.albedo_color = Color(0.12, 0.14, 0.22)
	plat_mat.metallic = 0.3
	plat_mat.roughness = 0.6
	platform.material_override = plat_mat
	add_child(platform)

	var ring := MeshInstance3D.new()
	ring.mesh = TorusMesh.new()
	ring.mesh.inner_radius = 5.8
	ring.mesh.outer_radius = 6.2
	ring.position = Vector3(0, 0.01, 0)
	ring.rotation_degrees = Vector3(90, 0, 0)
	var ring_mat := StandardMaterial3D.new()
	ring_mat.albedo_color = Color(0.85, 0.65, 0.15)
	ring_mat.emission_enabled = true
	ring_mat.emission = Color(0.85, 0.65, 0.15)
	ring_mat.emission_energy_multiplier = 0.6
	ring.material_override = ring_mat
	add_child(ring)

	var floor_plane := MeshInstance3D.new()
	floor_plane.mesh = PlaneMesh.new()
	floor_plane.mesh.size = Vector2(20, 20)
	floor_plane.position = Vector3(0, -0.41, 0)
	var floor_mat := StandardMaterial3D.new()
	floor_mat.albedo_color = Color(0.06, 0.07, 0.10)
	floor_mat.roughness = 0.9
	floor_plane.material_override = floor_mat
	add_child(floor_plane)

	_play_battle_music()
	_spawn_models()


func _play_battle_music() -> void:
	var path := "res://audio/Battletopia01.wav"
	if not ResourceLoader.exists(path):
		return
	var stream: AudioStream = load(path)
	if stream == null:
		return
	var player := AudioStreamPlayer.new()
	player.stream = stream
	player.volume_db = -8.0
	add_child(player)
	player.play()


func _spawn_models() -> void:
	var roster := _load_json("res://roster.json")
	var entries: Array = roster.get("entries", [])
	for idx in range(entries.size()):
		var entry: Dictionary = entries[idx]
		var model_path: String = entry.get("model_path", "")
		if model_path == "" or not ResourceLoader.exists(model_path):
			continue
		var doc := GLTFDocument.new()
		var state := GLTFState.new()
		if doc.append_from_file(ProjectSettings.globalize_path(model_path), state) != OK:
			continue
		var scene: Node = doc.generate_scene(state)
		if scene == null:
			continue
		var holder := Node3D.new()
		holder.add_child(scene)
		var is_player := idx < 2
		holder.position = Vector3(-2.0 + 4.0 * (idx % 2), 0.0, -2.5 if is_player else 2.5)
		holder.rotation_degrees = Vector3(0, 180 if is_player else 0, 0)
		holder.scale = Vector3(0.8, 0.8, 0.8)
		add_child(holder)


func _build_ui() -> void:
	var canvas := CanvasLayer.new()
	add_child(canvas)

	var panel := PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	panel.offset_top = -190
	canvas.add_child(panel)

	var vbox := VBoxContainer.new()
	panel.add_child(vbox)

	slots_left_label = Label.new()
	slots_left_label.text = "Selecione 4 comandos (slot 1 de 4)"
	vbox.add_child(slots_left_label)

	command_panel = VBoxContainer.new()
	vbox.add_child(command_panel)

	log_label = Label.new()
	log_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	log_label.custom_minimum_size = Vector2(0, 70)
	vbox.add_child(log_label)


func _begin_turn() -> void:
	pending_commands.clear()
	current_slot = 0
	awaiting_input = true
	_refresh_commands()


func _refresh_commands() -> void:
	for c in command_panel.get_children():
		c.queue_free()
	var all_units = active_player + active_enemy
	var attacker_index := current_slot % all_units.size()
	slots_left_label.text = "Slot %d de %d" % [current_slot + 1, all_units.size()]

	var attacker = all_units[attacker_index]
	var side_label = "ALIADO" if attacker["side"] == "player" else "INIMIGO"
	var head := Label.new()
	head.text = "%s (%s) — escolha um movimento" % [attacker["name"], side_label]
	command_panel.add_child(head)

	for move in attacker.get("moves", []):
		var b := Button.new()
		b.text = "%s (%s, %d)" % [move.get("name", "?"), move.get("type", "?"), int(move.get("power", 0))]
		var mv = move
		var atk_idx := attacker_index
		b.pressed.connect(func(): _choose_command(atk_idx, mv))
		command_panel.add_child(b)


func _choose_command(attacker_index: int, move: Dictionary) -> void:
	_log("%s usa %s!" % [pending_commands_attacker_name(attacker_index), move.get("name", "?")])
	pending_commands.append({"attacker": attacker_index, "move": move})
	current_slot += 1
	var total = (active_player + active_enemy).size()
	if current_slot < total:
		_refresh_commands()
	else:
		_resolve_turn()


func pending_commands_attacker_name(idx: int) -> String:
	var all_units = active_player + active_enemy
	return all_units[idx]["name"]


func _resolve_turn() -> void:
	awaiting_input = false
	for c in command_panel.get_children():
		c.queue_free()

	var all_units = active_player + active_enemy
	var order := pending_commands.duplicate()
	order.sort_custom(_compare_speed.bind(all_units))

	for cmd in order:
		var attacker = all_units[cmd["attacker"]]
		if not attacker["alive"]:
			continue
		var foe_idx = 0 if attacker["side"] == "enemy" else 2
		var defender = all_units[(cmd["attacker"] + foe_idx) % all_units.size()]
		if not defender["alive"]:
			continue
		_apply_damage(attacker, defender, cmd["move"])

	_check_end()
	if not _battle_over:
		turn += 1
		_begin_turn()


var _battle_over := false


func _apply_damage(attacker: Dictionary, defender: Dictionary, move: Dictionary) -> void:
	var power := float(move.get("power", 0))
	var atk: float = attacker["atk"]
	var dfn: float = defender["def"]
	var base: float = (atk / max(dfn, 1.0)) * power * 0.45
	var mult: float = _type_multiplier(move.get("type", "Normal"), defender["types"])
	var dmg: float = base * mult
	defender["hp"] = max(0.0, defender["hp"] - dmg)
	_log("  %s sofreu %d de dano (restam %d)." % [defender["name"], int(dmg), int(defender["hp"])])
	if defender["hp"] <= 0.0:
		defender["alive"] = false
		_log("  %s desmaiou!" % defender["name"])


func _type_multiplier(attack_type: String, defender_types: Array) -> float:
	var mult := 1.0
	var table = type_chart.get(attack_type, {})
	for t in defender_types:
		var key := str(t).to_lower()
		if table.has(key):
			mult *= float(table[key])
	return mult


func _check_end() -> void:
	var alive_player := 0
	var alive_enemy := 0
	for u in player_team:
		if u["alive"]:
			alive_player += 1
	for u in enemy_team:
		if u["alive"]:
			alive_enemy += 1
	if alive_player == 0 or alive_enemy == 0:
		_battle_over = true
		if alive_player > 0:
			_log("Vitória! Todos os inimigos desmaiaram.")
			_record_result(true)
		else:
			_log("Derrota. Sua equipe caiu.")
			_record_result(false)


func _record_result(victory: bool) -> void:
	var save := SaveManager.load_game()
	if save.is_empty():
		save = SaveManager.get_default_save()
	var battles: int = int(save.get("battles_played", 0)) + 1
	var wins: int = int(save.get("battles_won", 0)) + (1 if victory else 0)
	save["battles_played"] = battles
	save["battles_won"] = wins
	save["last_saved"] = Time.get_datetime_string_from_system()
	SaveManager.save_game(save)


func _log(msg: String) -> void:
	print(msg)
	if log_label:
		var existing := log_label.text
		var lines := existing.split("\n")
		if lines.size() > 5:
			lines = lines.slice(lines.size() - 5)
		lines.append(msg)
		log_label.text = "\n".join(lines)


func _compare_speed(a: Dictionary, b: Dictionary, units: Array) -> bool:
	return units[a["attacker"]]["spe"] > units[b["attacker"]]["spe"]


func _load_json(path: String) -> Dictionary:
	var file = FileAccess.open(path, FileAccess.READ)
	if file == null:
		return {}
	var text = file.get_as_text()
	file.close()
	var parsed = JSON.parse_string(text)
	if parsed is Dictionary:
		return parsed
	return {}
