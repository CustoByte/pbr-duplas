extends Node3D

## Arena de estádio no estilo do PBR: piso circular, arquibancadas,
## holofotes e câmera de batalha em ângulo baixo.


func build() -> void:
	_environment()
	_lights()
	_field()
	_stands()


func _environment() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.02, 0.03, 0.06)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.30, 0.34, 0.45)
	env.ambient_light_energy = 1.0
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.glow_enabled = true
	env.glow_intensity = 0.35
	var world := WorldEnvironment.new()
	world.environment = env
	add_child(world)


func _lights() -> void:
	var key := DirectionalLight3D.new()
	key.rotation_degrees = Vector3(-52, -35, 0)
	key.light_energy = 1.5
	key.shadow_enabled = true
	add_child(key)

	for spot_pos in [Vector3(-14, 12, -10), Vector3(14, 12, -10), Vector3(0, 14, 12)]:
		var spot := SpotLight3D.new()
		spot.position = spot_pos
		spot.light_energy = 4.0
		spot.light_color = Color(0.92, 0.95, 1.0)
		spot.spot_range = 40.0
		spot.spot_angle = 45.0
		spot.look_at(Vector3.ZERO, Vector3.UP)
		add_child(spot)


func _field() -> void:
	var field := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = 7.2
	cyl.bottom_radius = 7.2
	cyl.height = 0.5
	cyl.radial_segments = 96
	field.mesh = cyl
	field.position.y = -0.25
	var fm := StandardMaterial3D.new()
	fm.albedo_color = Color(0.10, 0.13, 0.20)
	fm.metallic = 0.25
	fm.roughness = 0.55
	field.material_override = fm
	add_child(field)

	# linha central e círculo de saída
	for radius in [2.2, 4.8]:
		var ring := MeshInstance3D.new()
		var torus := TorusMesh.new()
		torus.inner_radius = radius - 0.05
		torus.outer_radius = radius + 0.05
		torus.rings = 64
		ring.mesh = torus
		ring.rotation_degrees = Vector3(90, 0, 0)
		ring.position.y = 0.02
		var rm := StandardMaterial3D.new()
		rm.albedo_color = Color(0.85, 0.72, 0.25)
		rm.emission_enabled = true
		rm.emission = Color(0.85, 0.72, 0.25)
		rm.emission_energy_multiplier = 0.5
		ring.material_override = rm
		add_child(ring)

	var center := MeshInstance3D.new()
	var line := BoxMesh.new()
	line.size = Vector3(13.0, 0.02, 0.07)
	center.mesh = line
	center.position.y = 0.02
	var lm := StandardMaterial3D.new()
	lm.albedo_color = Color(0.55, 0.58, 0.66)
	center.material_override = lm
	add_child(center)


func _stands() -> void:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.07, 0.08, 0.12)
	mat.roughness = 0.9

	var ring := MeshInstance3D.new()
	var torus := TorusMesh.new()
	torus.inner_radius = 9.5
	torus.outer_radius = 13.0
	torus.rings = 96
	torus.ring_segments = 8
	ring.mesh = torus
	ring.rotation_degrees = Vector3(90, 0, 0)
	ring.position.y = 1.2
	ring.material_override = mat
	add_child(ring)

	# público: pontos coloridos nas arquibancadas
	var crowd := MultiMeshInstance3D.new()
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	var quad := QuadMesh.new()
	quad.size = Vector2(0.45, 0.75)
	mm.mesh = quad
	mm.instance_count = 320
	var palette := [
		Color(0.90, 0.25, 0.28), Color(0.25, 0.55, 0.90),
		Color(0.95, 0.80, 0.30), Color(0.35, 0.75, 0.45),
		Color(0.85, 0.45, 0.85), Color(0.95, 0.55, 0.20),
	]
	for i in range(mm.instance_count):
		var angle := TAU * float(i) / float(mm.instance_count)
		var radius := 9.9 + randf() * 2.6
		var pos := Vector3(cos(angle) * radius, 1.35 + randf() * 0.5, sin(angle) * radius)
		var basis := Basis.looking_at(-pos.normalized(), Vector3.UP)
		mm.set_instance_transform(i, Transform3D(basis, pos))
		mm.set_instance_color(i, palette[i % palette.size()])
	var mat_crowd := StandardMaterial3D.new()
	mat_crowd.vertex_color_use_as_albedo = true
	mat_crowd.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	crowd.multimesh = mm
	crowd.material_override = mat_crowd
	add_child(crowd)


func make_camera() -> Camera3D:
	var cam := Camera3D.new()
	cam.position = Vector3(0.0, 4.6, 9.4)
	cam.rotation_degrees = Vector3(-16, 0, 0)
	cam.fov = 55.0
	add_child(cam)
	return cam
