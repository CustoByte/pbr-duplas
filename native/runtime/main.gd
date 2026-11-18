extends Node3D

## Cena raiz do PBR Nativo.
## Gerencia fluxo: Menu -> Seleção de Equipe -> Batalha.
## Recebe --iso <caminho> via argumentos de linha de comando.

var iso_path := ""
var current_scene: Node = null

func _ready():
	Engine.max_fps = 120
	_parse_args()
	_show_menu()

func _parse_args():
	var args = OS.get_cmdline_user_args()
	for i in range(args.size()):
		if args[i] == "--iso" and i + 1 < args.size():
			iso_path = args[i + 1]
			_save_iso_path(iso_path)

func _save_iso_path(path: String):
	var settings_path = "user://settings.json"
	var data = {}
	if FileAccess.file_exists(settings_path):
		var file = FileAccess.open(settings_path, FileAccess.READ)
		if file:
			var parsed = JSON.parse_string(file.get_as_text())
			if parsed is Dictionary:
				data = parsed
			file.close()
	data["iso_path"] = path
	var file = FileAccess.open(settings_path, FileAccess.WRITE)
	if file:
		file.store_string(JSON.stringify(data, "\t"))
		file.close()

func _show_menu():
	_clear_scene()
	var menu = preload("res://menu.tscn").instantiate()
	menu.start_new_game.connect(_on_start_new_game)
	menu.continue_game.connect(_on_continue_game)
	menu.open_colosseum.connect(_on_open_colosseum)
	menu.open_settings.connect(_on_open_settings)
	add_child(menu)
	current_scene = menu

func _on_start_new_game():
	_clear_scene()
	var lobby = preload("res://lobby.tscn").instantiate()
	lobby.battle_started.connect(_on_battle_started)
	add_child(lobby)
	current_scene = lobby

func _on_continue_game():
	if not SaveManager.has_save():
		_log("Nenhum save encontrado.")
		return
	_on_start_new_game()

func _on_open_colosseum():
	_clear_scene()
	var colosseum = preload("res://colosseum.tscn").instantiate()
	colosseum.colosseum_selected.connect(_on_colosseum_selected)
	add_child(colosseum)
	current_scene = colosseum

func _on_colosseum_selected(col_data: Dictionary):
	_log("Coliseu selecionado: %s" % col_data.get("name", "?"))
	_on_start_new_game()

func _on_open_settings():
	_clear_scene()
	var settings = preload("res://settings.tscn").instantiate()
	settings.settings_closed.connect(_show_menu)
	add_child(settings)
	current_scene = settings

func _on_battle_started(team_data: Array):
	_clear_scene()
	var battle = preload("res://battle.tscn").instantiate()
	battle.set_meta("player_team", team_data)
	var rules = _load_json("res://data/battle-rules.json")
	battle.set_meta("rules", rules)
	add_child(battle)
	current_scene = battle

func _clear_scene():
	if is_instance_valid(current_scene):
		current_scene.queue_free()
		current_scene = null

func _log(msg: String):
	print("[PBR Native] ", msg)

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