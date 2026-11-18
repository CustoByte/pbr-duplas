class_name IsoLoader

## Extrai assets da ISO/RVZ original do PBR usando DolphinTool.
## Caminho da ISO vem de user://settings.json (passado pelo launcher via --iso).

const SETTINGS_PATH = "user://settings.json"
const EXTRACT_DIR = "res://extracted_iso"
const FILES_SUBDIR = "DATA/files"

static func get_iso_path() -> String:
	if not FileAccess.file_exists(SETTINGS_PATH):
		return ""
	var file = FileAccess.open(SETTINGS_PATH, FileAccess.READ)
	if file == null:
		return ""
	var text = file.get_as_text()
	file.close()
	var data = JSON.parse_string(text)
	if data is Dictionary:
		return data.get("iso_path", "")
	return ""

static func has_extracted_assets() -> bool:
	return DirAccess.dir_exists_absolute(EXTRACT_DIR)

static func extract_iso(dolphin_tool_path: String) -> Dictionary:
	var iso = get_iso_path()
	if iso.is_empty():
		return {"ok": false, "error": "Caminho da ISO não configurado."}
	if not FileAccess.file_exists(iso):
		return {"ok": false, "error": "ISO não encontrada: " + iso}
	if dolphin_tool_path.is_empty() or not FileAccess.file_exists(dolphin_tool_path):
		return {"ok": false, "error": "DolphinTool não encontrado."}

	DirAccess.make_dir_recursive_absolute(EXTRACT_DIR)

	var args = [
		"extract", "-i", iso, "-o", ProjectSettings.globalize_path(EXTRACT_DIR), "--gameonly"
	]
	var output = []
	var exit_code = OS.execute(dolphin_tool_path, args, output, true)
	if exit_code != 0:
		return {"ok": false, "error": "DolphinTool falhou (código %d): %s" % [exit_code, "\n".join(output)]}

	return {"ok": true, "path": EXTRACT_DIR}

static func find_dolphin_tool() -> String:
	var candidates = [
		"D:/download/dolphin-2609b-x64/Dolphin-x64/DolphinTool.exe",
		"C:/Program Files/Dolphin/DolphinTool.exe",
		"C:/Program Files (x86)/Dolphin/DolphinTool.exe",
	]
	for c in candidates:
		if FileAccess.file_exists(c):
			return c
	return ""

## Verifica se os assets já foram extraídos; se não, extrai automaticamente.
## Chama on_progress(msg) para reportar status na UI.
## Retorna true se os assets estão prontos.
static func ensure_assets(on_progress: Callable = Callable()) -> bool:
	if has_extracted_assets():
		return true

	var iso = get_iso_path()
	if iso.is_empty():
		if on_progress.is_valid():
			on_progress.call("ISO não configurada. Defina em CONFIGURAÇÕES.")
		return false

	if not FileAccess.file_exists(iso):
		if on_progress.is_valid():
			on_progress.call("ISO não encontrada: " + iso)
		return false

	var dolphin_tool = find_dolphin_tool()
	if dolphin_tool.is_empty():
		if on_progress.is_valid():
			on_progress.call("DolphinTool não encontrado. Instale o Dolphin.")
		return false

	if on_progress.is_valid():
		on_progress.call("Extraindo assets da ISO...")

	var result = extract_iso(dolphin_tool)
	if not result.get("ok", false):
		if on_progress.is_valid():
			on_progress.call("Erro: " + result.get("error", "desconhecido"))
		return false

	if on_progress.is_valid():
		on_progress.call("Assets extraídos com sucesso.")
	return true