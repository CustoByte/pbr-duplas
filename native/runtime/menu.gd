extends Control

## Menu principal do PBR Nativo.
## Opções: Novo Jogo, Continuar, Configurações, Sair.

signal start_new_game
signal continue_game
signal open_colosseum
signal open_settings
signal quit_game

var save_exists := false
var status_label: Label

func _ready():
	_check_save()
	_build_ui()
	_verify_assets()

func _verify_assets():
	var assets_ok = IsoLoader.ensure_assets(func(msg):
		if status_label:
			status_label.text = msg
	)
	if assets_ok and status_label:
		status_label.text = "Assets prontos."

func _check_save():
	var path = "user://savegame.json"
	save_exists = FileAccess.file_exists(path)

func _build_ui():
	var bg = ColorRect.new()
	bg.color = Color("#140a0a")
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	var vbox = VBoxContainer.new()
	vbox.set_anchors_preset(Control.PRESET_CENTER)
	vbox.position = Vector2(-150, -120)
	vbox.custom_minimum_size = Vector2(300, 240)
	add_child(vbox)

	var title = Label.new()
	title.text = "POKÉMON BATTLE REVOLUTION"
	title.add_theme_color_override("font_color", Color("#c9a227"))
	title.add_theme_font_size_override("font_size", 28)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(title)

	var subtitle = Label.new()
	subtitle.text = "EDIÇÃO NATIVA"
	subtitle.add_theme_color_override("font_color", Color("#8a7a6a"))
	subtitle.add_theme_font_size_override("font_size", 14)
	subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(subtitle)

	var spacer = Control.new()
	spacer.custom_minimum_size = Vector2(0, 30)
	vbox.add_child(spacer)

	var btn_new = Button.new()
	btn_new.text = "NOVO JOGO"
	btn_new.custom_minimum_size = Vector2(260, 40)
	btn_new.pressed.connect(_on_new_game)
	vbox.add_child(btn_new)

	var btn_continue = Button.new()
	btn_continue.text = "CONTINUAR"
	btn_continue.custom_minimum_size = Vector2(260, 40)
	btn_continue.disabled = not save_exists
	btn_continue.pressed.connect(_on_continue)
	vbox.add_child(btn_continue)

	var btn_colosseum = Button.new()
	btn_colosseum.text = "COLISEU"
	btn_colosseum.custom_minimum_size = Vector2(260, 40)
	btn_colosseum.pressed.connect(_on_colosseum)
	vbox.add_child(btn_colosseum)

	var btn_settings = Button.new()
	btn_settings.text = "CONFIGURAÇÕES"
	btn_settings.custom_minimum_size = Vector2(260, 40)
	btn_settings.pressed.connect(_on_settings)
	vbox.add_child(btn_settings)

	var btn_quit = Button.new()
	btn_quit.text = "SAIR"
	btn_quit.custom_minimum_size = Vector2(260, 40)
	btn_quit.pressed.connect(_on_quit)
	vbox.add_child(btn_quit)

	status_label = Label.new()
	status_label.add_theme_color_override("font_color", Color("#8a7a6a"))
	status_label.add_theme_font_size_override("font_size", 12)
	status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	vbox.add_child(status_label)

func _on_new_game():
	start_new_game.emit()

func _on_continue():
	continue_game.emit()

func _on_colosseum():
	open_colosseum.emit()

func _on_settings():
	open_settings.emit()

func _on_quit():
	get_tree().quit()