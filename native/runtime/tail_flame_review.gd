extends Node3D

# Procedural review effect. The Wii engine does not execute this Godot shader.
var rig: Skeleton3D
var camera: Camera3D
var bone := -1
var clock := 0.0
var tip_local := Vector3.ZERO
var attachment_verified := false
var material := ShaderMaterial.new()
var embers: Array[MeshInstance3D] = []

func configure(skeleton: Skeleton3D, view_camera: Camera3D, body_meshes: Array[Node]) -> void:
	rig = skeleton
	camera = view_camera
	bone = rig.find_bone("Tail8")
	var terminal := rig.find_bone("EndTail8")
	if bone < 0 or terminal < 0:
		push_error("Tail-flame review requires Charizard Y tail joints")
		get_tree().quit(2)
		return
	rig.force_update_all_bone_transforms()
	var anchor := rig.global_transform * rig.get_bone_global_pose(bone)
	var direction: Vector3 = ((rig.global_transform * rig.get_bone_global_pose(terminal)).origin-anchor.origin).normalized()
	var best := -INF
	for node in body_meshes:
		var mesh := node as MeshInstance3D
		if mesh.skin == null or "003" in String(mesh.name): continue
		for surface in range(mesh.mesh.get_surface_count()):
			var arrays: Array = mesh.mesh.surface_get_arrays(surface)
			var points: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var bones = arrays[Mesh.ARRAY_BONES]
			var weights = arrays[Mesh.ARRAY_WEIGHTS]
			if bones == null or weights == null or points.is_empty(): continue
			var count: int = bones.size()/points.size()
			for i in range(points.size()):
				for j in range(count):
					if weights[i*count+j] < .999: continue
					var bind: int = bones[i*count+j]
					var bound := mesh.skin.get_bind_bone(bind)
					if bound < 0: bound = rig.find_bone(mesh.skin.get_bind_name(bind))
					if bound != bone: continue
					var point: Vector3 = mesh.global_transform * rig.get_bone_global_pose(bone) * mesh.skin.get_bind_pose(bind) * points[i]
					var along: float = (point-anchor.origin).dot(direction)
					if along > best:
						best = along
						tip_local = anchor.affine_inverse()*point
						attachment_verified = true
	if not attachment_verified:
		push_error("Cannot locate the visible tail-tip surface")
		get_tree().quit(2)
		return
	print("FLAME_SURFACE_ATTACHMENT ",tip_local)
	var shader := Shader.new()
	shader.code = """
shader_type spatial;
render_mode unshaded, cull_disabled, blend_add, depth_draw_never;
uniform float simulation_time = 0.0;
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float noise(vec2 p){vec2 i=floor(p);vec2 f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x),f.y);}
float fbm(vec2 p){return noise(p)*.57+noise(p*2.03)*.28+noise(p*4.11)*.15;}
void fragment(){
 float y=(1.0-UV.y)/(.92+.05*sin(simulation_time*8.0)+.025*sin(simulation_time*15.1));
 float x=(UV.x-.5)*2.0;
 float n=fbm(vec2(x*3.0,y*5.0-simulation_time*3.8));
 float drift=sin(y*8.0-simulation_time*5.3)*.13*y;
 float width=.80*pow(max(0.0,1.0-y),.67)*smoothstep(0.0,.17,y)+(n-.5)*.34*y;
 float field=width-abs(x+drift+(n-.5)*.28*y);
 float alpha=smoothstep(0.0,.16,field)*smoothstep(0.0,.05,y)*(1.0-smoothstep(.93,1.0,y));
 float core=smoothstep(.06,.62,field)*(1.0-y*.65);
 vec3 color=mix(vec3(1.0,.09,.005),vec3(1.0,.55,.015),smoothstep(0.0,.20,field));
 color=mix(color,vec3(1.0,.96,.53),core);
 ALBEDO=color;
 EMISSION=color*(1.6+.6*n);
 ALPHA=alpha;
}
"""
	material.shader = shader
	var flame := MeshInstance3D.new()
	var quad := QuadMesh.new()
	quad.size = Vector2(1.6,2.8)
	flame.mesh = quad
	flame.position.y = 1.18
	flame.material_override = material
	flame.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(flame)
	var spark_shader := Shader.new()
	spark_shader.code = """
shader_type spatial;
render_mode unshaded,cull_disabled,blend_add,depth_draw_never;
void fragment(){float d=length((UV-.5)*2.0);ALBEDO=vec3(1,.45,.04);EMISSION=vec3(2,1,.1);ALPHA=(1.0-smoothstep(.1,1.0,d))*.8;}
"""
	var spark_material := ShaderMaterial.new()
	spark_material.shader = spark_shader
	for i in range(7):
		var spark := MeshInstance3D.new()
		var mesh := QuadMesh.new()
		mesh.size = Vector2(.045,.10)
		spark.mesh = mesh
		spark.material_override = spark_material
		spark.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(spark)
		embers.append(spark)

func advance(delta: float) -> void:
	if bone < 0: return
	clock += delta
	rig.force_update_all_bone_transforms()
	var anchor := rig.global_transform * rig.get_bone_global_pose(bone)
	global_position = anchor * tip_local
	scale = Vector3.ONE * absf(anchor.basis.get_scale().x)
	if global_position.distance_to(camera.global_position) > .01:
		look_at(camera.global_position,Vector3.UP)
	material.set_shader_parameter("simulation_time",clock)
	for i in range(embers.size()):
		var age := fmod(clock*.75+float(i)*.143,1.0)
		embers[i].position = Vector3(sin(float(i)*2.4+age*4.0)*age*.35,.3+age*2.0,0.01)
		embers[i].scale = Vector3.ONE*(1.0-age)
