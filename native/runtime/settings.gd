extends Control

## Tela de configurações: FPS, vsync, volume, caminho da ISO.

signal settings_closed

const SETTINGS_PATH = "user://settings.json"

var fps_options = [30, 60, 120]
var current_fps_index = 1
var vsync_enabled = true
var master_volume = 1.0
var iso_path = ""

func _ready():
	_load_settings()
	_build_ui()

func _load_settings():
	if not FileAccess.file_exists(SETTINGS_PATH):
		return
	var file = FileAccess.open(SETTINGS_PATH, FileAccess.READ)
	if file == null:
		return
	var text = file.get_as_text()
	file.close()
	var data = JSON.parse_string(text)
	if data is Dictionary:
		current_fps_index = clampi(data.get("fps_index", 1), 0, fps_options.size() - 1)
		vsync_enabled = data.get("vsync", true)
		master_volume = clampf(data.get("volume", 1.0), 0.0, 1.0)
		iso_path = data.get("iso_path", "")
	_apply_settings()

func _apply_settings():
	Engine.max_fps = fps_options[current_fps_index]
	DisplayServer.window_set_vsync_mode(
		DisplayServer.VSYNC_ENABLED if vsync_enabled else DisplayServer.VSYNC_DISABLED
	)
	AudioServer.set_bus_volume_db(0, linear_to_db(master_volume))

func _save_settings():
	var data = {
		"fps_index": current_fps_index,
		"vsync": vsync_enabled,
		"volume": master_volume,
		"iso_path": iso_path
	}
	var file = FileAccess.open(SETTINGS_PATH, FileAccess.WRITE)
	if file:
		file.store_string(JSON.stringify(data, "\t"))
		file.close()
	_apply_settings()

func _build_ui():
	var bg = ColorRect.new()
	bg.color = Color("#140a0a")
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	var panel = PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.position = Vector2(-200, -180)
	panel.custom_minimum_size = Vector2(400, 360)
	add_child(panel)

	var vbox = VBoxContainer.new()
	panel.add_child(vbox)

	var title = Label.new()
	title.text = "CONFIGURAÇÕES"
	title.add_theme_color_override("font_color", Color("#c9a227"))
	title.add_theme_font_size_override("font_size", 24)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(title)

	var sep = HSeparator.new()
	vbox.add_child(sep)

	# FPS
	var fps_row = HBoxContainer.new()
	vbox.add_child(fps_row)
	var fps_label = Label.new()
	fps_label.text = "FPS Máximo:"
	fps_label.custom_minimum_size.x = 140
	fps_row.add_child(fps_label)
	var fps_btn = Button.new()
	fps_btn.text = str(fps_options[current_fps_index])
	fps_btn.custom_minimum_size.x = 100
	fps_btn.pressed.connect(_cycle_fps.bind(fps_btn))
	fps_row.add_child(fps_btn)

	# VSync
	var vsync_row = HBoxContainer.new()
	vbox.add_child(vsync_row)
	var vsync_label = Label.new()
	vsync_label.text = "VSync:"
	vsync_label.custom_minimum_size.x = 140
	vsync_row.add_child(vsync_label)
	var vsync_check = CheckButton.new()
	vsync_check.button_pressed = vsync_enabled
	vsync_check.toggled.connect(func(on): vsync_enabled = on; _save_settings())
	vsync_row.add_child(vsync_check)

	# Volume
	var vol_row = HBoxContainer.new()
	vbox.add_child(vol_row)
	var vol_label = Label.new()
	vol_label.text = "Volume:"
	vol_label.custom_minimum_size.x = 140
	vol_row.add_child(vol_label)
	var vol_slider = HSlider.new()
	vol_slider.min_value = 0.0
	vol_slider.max_value = 1.0
	vol_slider.step = 0.05
	vol_slider.value = master_volume
	vol_slider.custom_minimum_size.x = 180
	vol_slider.value_changed.connect(func(v): master_volume = v; _save_settings())
	vol_row.add_child(vol_slider)

	# ISO Path
	var iso_row = HBoxContainer.new()
	vbox.add_child(iso_row)
	var iso_label = Label.new()
	iso_label.text = "ISO:"
	iso_label.custom_minimum_size.x = 140
	iso_row.add_child(iso_label)
	var iso_display = Label.new()
	iso_display.text = iso_path if iso_path != "" else "(não definido)"
	iso_display.add_theme_color_override("font_color", Color("#8a7a6a"))
	iso_display.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	iso_display.custom_minimum_size.x = 200
	iso_row.add_child(iso_display)

	var spacer = Control.new()
	spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	vbox.add_child(spacer)

	var back_btn = Button.new()
	back_btn.text = "VOLTAR"
	back_btn.custom_minimum_size = Vector2(120, 36)
	back_btn.pressed.connect(func(): settings_closed.emit())
	vbox.add_child(back_btn)

func _cycle_fps(btn: Button):
	current_fps_index = (current_fps_index + 1) % fps_options.size()
	btn.text = str(fps_options[current_fps_index])
	_save_settings()