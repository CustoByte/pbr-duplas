extends Node

# Offline, fixed-clock animation review. It does not run Dolphin or move effects.
var laboratory: Node3D
var timeline: Array = []
var index := -1
var clock := 0.0
var heading := Label.new()
var caption := Label.new()
var detail := Label.new()
var ticks := 0
var tracking_skeleton: Skeleton3D
var tracking_bone := -1
var tracking_origin := Vector3.ZERO

func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	var path := ""
	for i in range(args.size()):
		if args[i] == "--preview-plan" and i + 1 < args.size(): path = args[i + 1]
	var plan = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not plan is Dictionary or not plan.has("segments"):
		push_error("Missing animation preview plan")
		get_tree().quit(2)
		return
	timeline = plan.segments
	laboratory = Node3D.new()
	laboratory.set_script(load("res://main.gd"))
	add_child(laboratory)
	for child in laboratory.get_children():
		if child is CanvasLayer: child.hide()
	if not is_instance_valid(laboratory.player):
		get_tree().quit(2)
		return
	laboratory.player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	laboratory.player.animation_finished.disconnect(laboratory.on_animation_finished)
	var layer := CanvasLayer.new()
	add_child(layer)
	var panel := ColorRect.new()
	panel.color = Color(0.04,0.07,0.12,0.88)
	panel.position = Vector2(0,0)
	panel.size = Vector2(1280,100)
	layer.add_child(panel)
	heading.text = plan.title + " — PRÉVIA DE ANIMAÇÕES"
	heading.position = Vector2(22,12)
	heading.add_theme_font_size_override("font_size",24)
	layer.add_child(heading)
	caption.position = Vector2(22,48)
	caption.add_theme_font_size_override("font_size",21)
	layer.add_child(caption)
	detail.text = plan.get("footer", "Render de revisão • 30 quadros/s • Não é captura do Dolphin\nEfeitos dos golpes e integração em batalha ainda não validados.")
	detail.position = Vector2(22,650)
	detail.add_theme_font_size_override("font_size",18)
	layer.add_child(detail)
	var rigs: Array[Node] = laboratory.model.find_children("*", "Skeleton3D", true, false)
	if not rigs.is_empty():
		tracking_skeleton = rigs[0]
		tracking_bone = tracking_skeleton.find_bone("Waist")
		if tracking_bone >= 0:
			tracking_skeleton.force_update_all_bone_transforms()
			tracking_origin = tracking_skeleton.global_transform * tracking_skeleton.get_bone_global_pose(tracking_bone).origin
	next_segment()

func next_segment() -> void:
	index += 1
	clock = 0.0
	if index >= timeline.size():
		get_tree().quit(0)
		return
	var segment: Dictionary = timeline[index]
	laboratory.yaw = float(segment.get("yaw", laboratory.yaw))
	laboratory.distance = float(segment.get("distance", laboratory.distance))
	caption.text = "%02d/%02d • %s" % [index+1,timeline.size(),segment.label]
	var clip: String = laboratory.resolve_role(segment.action)
	if clip.is_empty():
		push_error("Preview action missing: " + str(segment.action))
		get_tree().quit(2)
		return
	laboratory.player.play(clip,0.18 if index > 0 else 0.0)
	laboratory.player.advance(0.0)
	print("PREVIEW_SEGMENT " + JSON.stringify(segment))

func _process(delta: float) -> void:
	if index < 0 or index >= timeline.size(): return
	laboratory.player.advance(delta)
	if tracking_bone >= 0:
		tracking_skeleton.force_update_all_bone_transforms()
		var position := tracking_skeleton.global_transform * tracking_skeleton.get_bone_global_pose(tracking_bone).origin
		var target := Vector3(0.0,1.0,0.0) + position - tracking_origin
		laboratory.camera.position = target + Vector3(sin(laboratory.yaw)*cos(laboratory.pitch),sin(laboratory.pitch),cos(laboratory.yaw)*cos(laboratory.pitch))*laboratory.distance
		laboratory.camera.look_at(target)
	clock += delta
	ticks += 1
	if clock >= float(timeline[index].seconds): next_segment()
