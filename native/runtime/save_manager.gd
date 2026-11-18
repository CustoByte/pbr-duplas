class_name SaveManager

## Gerenciador de saves para PBR Nativo.
## Salva progresso do jogador em user://savegame.json.

const SAVE_PATH = "user://savegame.json"

static func has_save() -> bool:
	return FileAccess.file_exists(SAVE_PATH)

static func save_game(data: Dictionary) -> bool:
	var file = FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if file == null:
		push_warning("Não foi possível abrir save para escrita.")
		return false
	file.store_string(JSON.stringify(data, "\t"))
	file.close()
	return true

static func load_game() -> Dictionary:
	if not has_save():
		return {}
	var file = FileAccess.open(SAVE_PATH, FileAccess.READ)
	if file == null:
		return {}
	var text = file.get_as_text()
	file.close()
	var parsed = JSON.parse_string(text)
	if parsed is Dictionary:
		return parsed
	return {}

static func delete_save() -> void:
	if has_save():
		DirAccess.remove_absolute(SAVE_PATH)

static func get_default_save() -> Dictionary:
	return {
		"version": 1,
		"player_name": "Treinador",
		"colosseums_cleared": [],
		"pokemon_caught": [],
		"team": [],
		"playtime_seconds": 0,
		"last_saved": Time.get_datetime_string_from_system()
	}