extends Control

## Lobby: seleção do time (até 6 Pokémon, 4 ativos na dupla).
## Emite battle_started com os dados do time do jogador.

signal battle_started(team_data: Array)

const MAX_TEAM := 6
const ACTIVE := 4

var roster: Array = []
var selected: Array = []
var grid: GridContainer

func _ready():
	roster = _load_roster()
	_build_ui()
	_refresh()

func _load_roster() -> Array:
	var file = FileAccess.open("res://roster.json", FileAccess.READ)
	if file == null:
		return []
	var parsed = JSON.parse_string(file.get_as_text())
	file.close()
	if parsed is Dictionary and parsed.has("entries"):
		return parsed["entries"]
	return []

func _build_ui():
	var bg = ColorRect.new()
	bg.color = Color(0.06, 0.07, 0.1)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	var root = VBoxContainer.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_theme_constant_override("separation", 12)
	root.offset_left = 40
	root.offset_top = 30
	root.offset_right = -40
	root.offset_bottom = -30
	add_child(root)

	var title = Label.new()
	title.text = "SELECIONE SEU TIME"
	title.add_theme_font_size_override("font_size", 26)
	title.add_theme_color_override("font_color", Color(0.95, 0.85, 0.4))
	root.add_child(title)

	var scroll = ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(scroll)

	grid = GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 10)
	grid.add_theme_constant_override("v_separation", 10)
	grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(grid)

	var btn_row = HBoxContainer.new()
	btn_row.add_theme_constant_override("separation", 10)
	root.add_child(btn_row)

	var start = Button.new()
	start.text = "INICIAR BATALHA"
	start.custom_minimum_size = Vector2(200, 44)
	start.pressed.connect(_on_start)
	btn_row.add_child(start)

	var back = Button.new()
	back.text = "VOLTAR"
	back.custom_minimum_size = Vector2(120, 44)
	back.pressed.connect(func(): get_tree().change_scene_to_file("res://main.tscn"))
	btn_row.add_child(back)

func _refresh():
	for c in grid.get_children():
		c.queue_free()
	for i in range(roster.size()):
		var entry = roster[i]
		var btn = Button.new()
		var mark = "✓ " if selected.has(i) else ""
		btn.text = "%s%s  (HP %d / ATK %d)" % [mark, entry.get("name", "?"), int(entry.get("hp", 100)), int(entry.get("atk", 50))]
		btn.custom_minimum_size = Vector2(320, 40)
		btn.pressed.connect(_on_pick.bind(i))
		grid.add_child(btn)

func _on_pick(index: int):
	if selected.has(index):
		selected.erase(index)
	elif selected.size() < MAX_TEAM:
		selected.append(index)
	_refresh()

func _on_start():
	if selected.size() < ACTIVE:
		_show_warning("Selecione pelo menos %d Pokémon." % ACTIVE)
		return
	var team: Array = []
	for i in selected:
		team.append(roster[i])
	battle_started.emit(team)

var warning_label: Label = null

func _show_warning(msg: String):
	if warning_label == null:
		warning_label = Label.new()
		warning_label.add_theme_color_override("font_color", Color(1, 0.4, 0.4))
		warning_label.add_theme_font_size_override("font_size", 14)
		add_child(warning_label)
		warning_label.position = Vector2(40, 8)
	warning_label.text = msg