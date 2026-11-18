extends Node3D

## Batalha dupla nativa: modelos e animações originais do PBR,
## arena de estádio, IA nos oponentes e fórmula de dano da Gen 4.

const PLAYER_POS := [Vector3(-1.7, 0, -2.8), Vector3(-3.6, 0, -0.8)]
const ENEMY_POS := [Vector3(1.7, 0, 2.8), Vector3(3.6, 0, 0.8)]

var player_team: Array = []
var enemy_team: Array = []
var pending_commands: Array = []
var turn := 1
var player_slot := 0
var busy := false
var battle_over := false
var type_chart: Dictionary = {}

var log_label: Label
var command_panel: VBoxContainer
var status_label: Label
var hud_player: VBoxContainer
var hud_enemy: VBoxContainer


func _ready() -> void:
	var roster := _load_json("res://roster.json")
	var rules := _load_json("res://data/battle-rules.json")
	type_chart = rules.get("type_chart", {})
	if type_chart.is_empty():
		type_chart = _gen4_type_chart()
	_build_teams(roster)
	_build_world()
	_build_ui()
	_refresh_hud()
	_log("Batalha dupla — turno %d" % turn)
	_begin_turn()


## Tabela de efetividade da Gen 4 (chave "Atacante>Defensor").
## Só as relações diferentes de 1x são listadas.
func _gen4_type_chart() -> Dictionary:
	var strong := {
		"Normal": [],
		"Fire": ["Grass", "Ice", "Bug", "Steel"],
		"Water": ["Fire", "Ground", "Rock"],
		"Electric": ["Water", "Flying"],
		"Grass": ["Water", "Ground", "Rock"],
		"Ice": ["Grass", "Ground", "Flying", "Dragon"],
		"Fighting": ["Normal", "Ice", "Rock", "Dark", "Steel"],
		"Poison": ["Grass"],
		"Ground": ["Fire", "Electric", "Poison", "Rock", "Steel"],
		"Flying": ["Grass", "Fighting", "Bug"],
		"Psychic": ["Fighting", "Poison"],
		"Bug": ["Grass", "Psychic", "Dark"],
		"Rock": ["Fire", "Ice", "Flying", "Bug"],
		"Ghost": ["Psychic", "Ghost"],
		"Dragon": ["Dragon"],
		"Dark": ["Psychic", "Ghost"],
		"Steel": ["Ice", "Rock"],
	}
	var weak := {
		"Normal": ["Rock", "Steel"],
		"Fire": ["Fire", "Water", "Rock", "Dragon"],
		"Water": ["Water", "Grass", "Dragon"],
		"Electric": ["Electric", "Grass", "Dragon"],
		"Grass": ["Fire", "Grass", "Poison", "Flying", "Bug", "Dragon", "Steel"],
		"Ice": ["Fire", "Water", "Ice", "Steel"],
		"Fighting": ["Poison", "Flying", "Psychic", "Bug"],
		"Poison": ["Poison", "Ground", "Rock", "Ghost"],
		"Ground": ["Grass", "Bug"],
		"Flying": ["Electric", "Rock", "Steel"],
		"Psychic": ["Psychic", "Steel"],
		"Bug": ["Fire", "Fighting", "Poison", "Flying", "Ghost", "Steel"],
		"Rock": ["Fighting", "Ground", "Steel"],
		"Ghost": ["Dark", "Steel"],
		"Dragon": ["Steel"],
		"Dark": ["Fighting", "Dark", "Steel"],
		"Steel": ["Fire", "Water", "Electric", "Steel"],
	}
	var chart := {}
	for atk in strong:
		for def in strong[atk]:
			chart[atk + ">" + def] = 2.0
	for atk in weak:
		for def in weak[atk]:
			chart[atk + ">" + def] = 0.5
	var immune := {
		"Normal": ["Ghost"],
		"Fighting": ["Ghost"],
		"Poison": ["Steel"],
		"Ground": ["Flying"],
		"Psychic": ["Dark"],
		"Ghost": ["Normal"],
		"Electric": ["Ground"],
		"Dragon": ["Steel"],
	}
	for atk in immune:
		for def in immune[atk]:
			chart[atk + ">" + def] = 0.0
	return chart


# ----------------------------------------------------------------- setup

func _build_teams(roster: Dictionary) -> void:
	var entries: Array = roster.get("entries", [])
	if entries.is_empty():
		push_error("roster.json vazio")
		return

	var chosen: Array = get_meta("player_team", [])
	if chosen.is_empty():
		chosen = entries.slice(0, mini(4, entries.size()))

	var used := {}
	for e in chosen:
		used[str(e.get("key", e.get("name", "")))] = true

	var pool: Array = []
	for e in entries:
		if not used.has(str(e.get("key", e.get("name", "")))):
			pool.append(e)
	if pool.size() < 2:
		pool = entries.duplicate()

	for i in range(2):
		player_team.append(_combatant(chosen[i % chosen.size()], "player"))
		enemy_team.append(_combatant(pool[i % pool.size()], "enemy"))


func _combatant(src: Dictionary, side: String) -> Dictionary:
	var data := src.duplicate(true)
	data["side"] = side
	var max_hp := float(data.get("hp", 100))
	return {
		"data": src,
		"name": str(src.get("name", "?")),
		"types": src.get("types", ["Normal"]),
		"moves": src.get("moves", []),
		"level": float(src.get("level", 50)),
		"atk": float(src.get("atk", 60)),
		"def": float(src.get("def", 60)),
		"spatk": float(src.get("spatk", 60)),
		"spdef": float(src.get("spdef", 60)),
		"spe": float(src.get("spe", 60)),
		"max_hp": max_hp,
		"hp": max_hp,
		"side": side,
		"alive": true,
		"unit": null,
	}


func _build_world() -> void:
	var arena := preload("res://arena.gd").new()
	add_child(arena)
	arena.build()

	var cam := Camera3D.new()
	cam.position = Vector3(0.0, 5.0, 10.0)
	cam.rotation_degrees = Vector3(-18, 0, 0)
	cam.fov = 55.0
	add_child(cam)
	cam.current = true

	for i in range(player_team.size()):
		_spawn_unit(player_team[i], PLAYER_POS[i])
	for i in range(enemy_team.size()):
		_spawn_unit(enemy_team[i], ENEMY_POS[i])

	_play_music()


func _spawn_unit(u: Dictionary, pos: Vector3) -> void:
	var holder := preload("res://battle_unit.gd").new()
	add_child(holder)
	holder.setup(u["data"])
	holder.position = pos
	holder.play_idle()
	u["unit"] = holder


func _play_music() -> void:
	for path in ["res://audio/Battletopia01.wav", "res://audio/Battletopia01.ogg"]:
		if not ResourceLoader.exists(path):
			continue
		var stream: AudioStream = load(path)
		if stream == null:
			continue
		var player := AudioStreamPlayer.new()
		player.stream = stream
		player.volume_db = -10.0
		add_child(player)
		player.play()
		return


# ----------------------------------------------------------------- turn flow

func _begin_turn() -> void:
	pending_commands = [null, null]
	player_slot = 0
	busy = false
	_show_command_menu(0)


func _show_command_menu(slot: int) -> void:
	for c in command_panel.get_children():
		c.queue_free()
	var u: Dictionary = player_team[slot]
	status_label.text = "%s — escolha o comando" % u["name"]
	var mv_idx := 0
	for mv in u["moves"]:
		var btn := Button.new()
		btn.text = "%s  (%s, poder %d)" % [mv.get("name", "?"), mv.get("type", "?"), int(mv.get("power", 0))]
		var target := (0 if slot == 0 else 1)
		btn.pressed.connect(_on_move_selected.bind(slot, mv_idx, target))
		command_panel.add_child(btn)
		mv_idx += 1


func _on_move_selected(slot: int, mv_idx: int, target: int) -> void:
	var u: Dictionary = player_team[slot]
	var move: Dictionary = u["moves"][mv_idx]
	pending_commands[slot] = {"slot": slot, "move": move, "target": target}
	player_slot += 1
	if player_slot < 2:
		_show_command_menu(player_slot)
	else:
		_resolve_turn()


func _resolve_turn() -> void:
	busy = true
	for c in command_panel.get_children():
		c.queue_free()
	status_label.text = ""

	var actions: Array = []
	for cmd in pending_commands:
		if cmd != null:
			actions.append({"side": "player", "cmd": cmd})
	for i in range(2):
		if pending_commands[i] == null:
			actions.append({
				"side": "enemy",
				"cmd": {"slot": i, "move": _ai_pick(enemy_team[i]), "target": randi() % 2},
			})

	actions.sort_custom(_speed_order)

	for action in actions:
		if battle_over:
			return
		await _execute(action)

	if not battle_over:
		turn += 1
		_log("--- Turno %d ---" % turn)
		_begin_turn()


func _speed_order(a: Dictionary, b: Dictionary) -> bool:
	return _speed_of(a) >= _speed_of(b)


func _speed_of(action: Dictionary) -> float:
	var list: Array = player_team if action["side"] == "player" else enemy_team
	var slot: int = action["cmd"]["slot"]
	if slot >= list.size():
		return 0.0
	return float(list[slot]["spe"])


func _ai_pick(u: Dictionary) -> Dictionary:
	var moves: Array = u["moves"]
	if moves.is_empty():
		return {"name": "Struggle", "power": 40, "type": "Normal"}
	# IA simples: 70% escolhe o movimento de maior dano esperado
	if randf() < 0.7:
		var best: Dictionary = moves[0]
		var best_score := -1.0
		for mv in moves:
			var eff := _effectiveness(str(mv.get("type", "Normal")), u["types"])
			var score: float = float(mv.get("power", 40)) * eff
			if score > best_score:
				best_score = score
				best = mv
		return best
	return moves[randi() % moves.size()]


# ----------------------------------------------------------------- execution

func _execute(action: Dictionary) -> void:
	var side: String = action["side"]
	var cmd: Dictionary = action["cmd"]
	var atk_list: Array = player_team if side == "player" else enemy_team
	var def_list: Array = enemy_team if side == "player" else player_team
	var atk_slot: int = cmd["slot"]
	var def_slot: int = cmd["target"]

	if atk_slot >= atk_list.size() or def_slot >= def_list.size():
		return
	var attacker: Dictionary = atk_list[atk_slot]
	var defender: Dictionary = def_list[def_slot]
	if not attacker["alive"] or not defender["alive"]:
		return

	var a_unit: Node3D = attacker["unit"]
	if a_unit and is_instance_valid(a_unit):
		a_unit.play_attack(str(cmd["move"].get("type", "Normal")))
		await get_tree().create_timer(0.5).timeout

	var dmg := _damage(attacker, defender, cmd["move"])
	defender["hp"] = maxf(0.0, float(defender["hp"]) - float(dmg))

	var d_unit: Node3D = defender["unit"]
	if d_unit and is_instance_valid(d_unit):
		d_unit.play_damage()
	_log("%s usou %s — %d de dano (%s: %d/%d)" % [
		attacker["name"], cmd["move"].get("name", "?"), dmg,
		defender["name"], int(defender["hp"]), int(defender["max_hp"])])
	_refresh_hud()

	if float(defender["hp"]) <= 0.0:
		defender["alive"] = false
		if d_unit and is_instance_valid(d_unit):
			d_unit.play_faint()
		_log("%s desmaiou!" % defender["name"])
		await get_tree().create_timer(0.7).timeout

	await get_tree().create_timer(0.3).timeout
	_check_end()


func _damage(attacker: Dictionary, defender: Dictionary, move: Dictionary) -> int:
	var level: float = attacker["level"]
	var power: float = float(move.get("power", 40))
	var move_class := str(move.get("class", "physical"))
	var is_special := move_class == "special" or str(move.get("category", "")) == "special"
	var atk: float = attacker["spatk"] if is_special else attacker["atk"]
	var dfn: float = defender["spdef"] if is_special else defender["def"]

	var base := ((2.0 * level / 5.0 + 2.0) * power * atk / maxf(dfn, 1.0)) / 50.0 + 2.0
	var eff := _effectiveness(str(move.get("type", "Normal")), defender["types"])
	var crit := 1.5 if randf() < 0.0625 else 1.0
	var roll := randf_range(0.85, 1.0)
	var stab := 1.5 if str(move.get("type", "")) in attacker["types"] else 1.0
	return int(maxf(1.0, base * eff * crit * roll * stab))


func _effectiveness(move_type: String, def_types) -> float:
	var mult := 1.0
	if typeof(def_types) != TYPE_ARRAY:
		return mult
	for t in def_types:
		mult *= float(type_chart.get(move_type + ">" + str(t), 1.0))
	return mult


func _check_end() -> void:
	var alive_p := 0
	var alive_e := 0
	for u in player_team:
		if u["alive"]:
			alive_p += 1
	for u in enemy_team:
		if u["alive"]:
			alive_e += 1
	if alive_p == 0 or alive_e == 0:
		battle_over = true
		_log("Vitória!" if alive_p > 0 else "Derrota.")
		_record_result(alive_p > 0)


func _record_result(victory: bool) -> void:
	var save := SaveManager.load_game()
	if save.is_empty():
		save = SaveManager.get_default_save()
	save["battles_played"] = int(save.get("battles_played", 0)) + 1
	if victory:
		save["battles_won"] = int(save.get("battles_won", 0)) + 1
	save["last_saved"] = Time.get_datetime_string_from_system()
	SaveManager.save_game(save)


# ----------------------------------------------------------------- UI

func _build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)

	# HUD dos times (topo)
	var top := HBoxContainer.new()
	top.set_anchors_preset(Control.PRESET_TOP_WIDE)
	top.offset_left = 16
	top.offset_right = -16
	top.offset_top = 10
	layer.add_child(top)

	hud_player = VBoxContainer.new()
	hud_player.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(hud_player)

	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(spacer)

	hud_enemy = VBoxContainer.new()
	hud_enemy.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(hud_enemy)

	# log (baixo esquerda)
	var log_panel := PanelContainer.new()
	log_panel.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	log_panel.offset_left = 16
	log_panel.offset_top = -210
	log_panel.offset_bottom = -16
	log_panel.custom_minimum_size = Vector2(430, 0)
	layer.add_child(log_panel)
	var lv := VBoxContainer.new()
	log_panel.add_child(lv)
	log_label = Label.new()
	log_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	lv.add_child(log_label)

	# comandos (baixo direita)
	var cmd_panel := PanelContainer.new()
	cmd_panel.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	cmd_panel.offset_right = -16
	cmd_panel.offset_top = -230
	cmd_panel.offset_bottom = -16
	cmd_panel.custom_minimum_size = Vector2(360, 0)
	layer.add_child(cmd_panel)
	var cv := VBoxContainer.new()
	cmd_panel.add_child(cv)
	status_label = Label.new()
	cv.add_child(status_label)
	command_panel = VBoxContainer.new()
	cv.add_child(command_panel)


func _refresh_hud() -> void:
	if hud_player == null:
		return
	for c in hud_player.get_children():
		c.queue_free()
	for c in hud_enemy.get_children():
		c.queue_free()
	for side_list in [player_team, enemy_team]:
		var box: VBoxContainer = hud_player if side_list == player_team else hud_enemy
		for u in side_list:
			var lbl := Label.new()
			var pct := int(100.0 * float(u["hp"]) / maxf(float(u["max_hp"]), 1.0))
			lbl.text = "%s  %d/%d (%d%%)" % [u["name"], int(u["hp"]), int(u["max_hp"]), pct]
			lbl.add_theme_color_override("font_color",
				Color(0.5, 1.0, 0.5) if float(u["hp"]) > 0 else Color(0.6, 0.6, 0.6))
			box.add_child(lbl)


func _log(msg: String) -> void:
	print(msg)
	if log_label:
		var lines := log_label.text.split("\n")
		if lines.size() > 6:
			lines = lines.slice(lines.size() - 6)
		lines.append(msg)
		log_label.text = "\n".join(lines)


func _load_json(path: String) -> Dictionary:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return {}
	var text := file.get_as_text()
	file.close()
	var parsed = JSON.parse_string(text)
	if parsed is Dictionary:
		return parsed
	return {}
