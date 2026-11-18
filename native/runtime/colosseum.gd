extends Control

## Menu de Coliseu / Torneio.
## Lista os coliseus disponíveis, mostra progresso salvo e inicia batalhas.

signal colosseum_selected(colosseum_data: Dictionary)

const SAVE_PATH = "user://savegame.json"

var colosseums: Array = [
	{"id": "main_gate", "name": "Portão Principal", "battles": 3, "difficulty": 1, "unlocked": true},
	{"id": "waterfall", "name": "Catarata", "battles": 4, "difficulty": 2, "unlocked": false},
	{"id": "crystal", "name": "Coliseu Cristal", "battles": 5, "difficulty": 3, "unlocked": false},
	{"id": "sunset", "name": "Coliseu Entardecer", "battles": 5, "difficulty": 4, "unlocked": false},
	{"id": "final", "name": "Coliseu Final", "battles": 6, "difficulty": 5, "unlocked": false},
]

var list_container: VBoxContainer
var status_label: Label

func _ready():
	_load_progress()
	_build_ui()

func _load_progress():
	if not SaveManager.has_save():
		return
	var save = SaveManager.load_game()
	var cleared = save.get("colosseums_cleared", [])
	for c in colosseums:
		if c["id"] in cleared:
			c["cleared"] = true
	# Desbloqueia o próximo coliseu após cada um concluído
	for i in range(1, colosseums.size()):
		if colosseums[i - 1].get("cleared", false):
			colosseums[i]["unlocked"] = true

func _build_ui():
	var bg = ColorRect.new()
	bg.color = Color("#140a0a")
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
	title.text = "COLISEU"
	title.add_theme_font_size_override("font_size", 28)
	title.add_theme_color_override("font_color", Color("#c9a227"))
	root.add_child(title)

	var sep = HSeparator.new()
	root.add_child(sep)

	var scroll = ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(scroll)

	list_container = VBoxContainer.new()
	list_container.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	list_container.add_theme_constant_override("separation", 8)
	scroll.add_child(list_container)

	_refresh_list()

	status_label = Label.new()
	status_label.add_theme_color_override("font_color", Color("#8a7a6a"))
	status_label.add_theme_font_size_override("font_size", 12)
	root.add_child(status_label)

	var btn_row = HBoxContainer.new()
	btn_row.add_theme_constant_override("separation", 10)
	root.add_child(btn_row)

	var back_btn = Button.new()
	back_btn.text = "VOLTAR"
	back_btn.custom_minimum_size = Vector2(120, 40)
	back_btn.pressed.connect(func(): get_tree().change_scene_to_file("res://main.tscn"))
	btn_row.add_child(back_btn)

func _refresh_list():
	for c in list_container.get_children():
		c.queue_free()
	for col in colosseums:
		var btn = Button.new()
		var cleared_mark = " ✓" if col.get("cleared", false) else ""
		var lock_mark = "" if col["unlocked"] else " 🔒"
		btn.text = "%s%s (Batalhas: %d | Dif: %d)%s" % [
			col["name"], cleared_mark, col["battles"], col["difficulty"], lock_mark
		]
		btn.custom_minimum_size = Vector2(0, 44)
		btn.disabled = not col["unlocked"]
		var col_data = col
		btn.pressed.connect(_on_select.bind(col_data))
		list_container.add_child(btn)

func _on_select(col: Dictionary):
	if not col["unlocked"]:
		status_label.text = "Coliseu bloqueado. Conclua o anterior."
		return
	status_label.text = "Iniciando %s..." % col["name"]
	colosseum_selected.emit(col)