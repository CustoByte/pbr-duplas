"""Sample the actual decoded candidate SDR into a private video intermediate.

Blender: -- candidate.sdr pbr-addon output-directory
Skinning is vectorized, but no frame interpolation or smoothing is added here.
"""
import bpy,json,sys,os,contextlib,copy,hashlib,bisect
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from mathutils import Matrix,Vector,Euler
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'experiments/snivy'),str(ROOT/'mod-source')]
from graphics_common import load_pbr_addon
from pkx_reference import scene_inventory
source,addon,output=map(Path,sys.argv[sys.argv.index('--')+1:]);output.mkdir(parents=True,exist_ok=True)
sdk=load_pbr_addon(SimpleNamespace(pbr_addon=addon,native_contract=None),register=False)
raw=source.read_bytes();meta={a['name']:a for a in scene_inventory(raw)['actions']}
with open(os.devnull,'w') as quiet,contextlib.redirect_stdout(quiet):model=sdk.importer.parseModel(str(source))
actions={a['name']:copy.deepcopy(a) for a in sdk.importer.anim_dict.values()}
bones=model['skeletons'][0].bones;mesh=model['meshes'][0]
points=np.column_stack((np.array(mesh.vertices,dtype='float32'),np.ones(len(mesh.vertices),dtype='float32')))
ids=np.zeros((len(points),4),dtype='int32');weights=np.zeros((len(points),4),dtype='float32')
for i in range(len(points)):
 for j,(bone,weight) in enumerate(mesh.weights[i].items()):
  if j>=4:raise ValueError('Skin exceeds four weights')
  ids[i,j]=bone;weights[i,j]=weight
bind=np.array([b.inverseBindMatrix if b.type!=3 else Matrix.Identity(4) for b in bones],dtype='float32')
C=np.array(Matrix.Rotation(np.pi/2,4,'X'),dtype='float32')
cache={}
def sample(name,frame):
 key=(name,frame)
 if key in cache:return cache[key]
 world=[];time=frame/30
 for b in bones:
  if b.type==3:world.append(Matrix.Identity(4));continue
  values=dict(location=list(b.initialTrans),rotation_euler=list(b.initialRot),scale=list(b.initialScale))
  for curve in actions.get(name,{}).get('bones',{}).get(b.name,[]):
   keys=curve['keyframes'];index=bisect.bisect_right([k['time'] for k in keys],time+1e-6)-1
   if index>=0:values[curve['component']][curve['axis']-1]=keys[index]['value']
  m=Matrix.Translation(Vector(values['location']))@Euler(values['rotation_euler'],'XYZ').to_matrix().to_4x4()@Matrix.Diagonal((*values['scale'],1))
  if b.parentIndex is not None:m=world[b.parentIndex]@m
  world.append(m)
 skin=(C@np.array(world,dtype='float32'))@bind
 transformed=np.einsum('vwij,vj->vwi',skin[ids],points)
 result=np.einsum('vwi,vw->vi',transformed,weights)[:,:3]
 cache[key]=result
 return result
sequence=[]
def add(label,action,frames):
 for f in frames:sequence.append(dict(label=label,action=action,source_frame=int(f)))
def idle(label,count=24):add(label,'wait',[i%40 for i in range(count)])
add('Espera','wait',list(range(40))*2)
add('Corrida — ciclo','run',list(range(15))*3)
for label,action in [('Soco — referência para Bullet Punch','punch'),('Chute — referência para Close Combat','kick'),('Ataque especial — referência para Aura Sphere','kime_b'),('Dano → recuperação → espera','damage')]:
 idle(label,15);add(label,action,range(round(meta[action]['length']*30)+1));idle(label,30)
add('Desmaio','down',range(round(meta['down']['length']*30)+1))
add('Desmaio','down',[round(meta['down']['length']*30)]*30)
# Body remains in the verified waiting pose while eye UVs use material actions.
for label,action in [('Olhos — piscar','tx_wink'),('Olhos — dormir','tx_sleep'),('Olhos — acordar','tx_wakeup')]:
 frames=range(round(meta[action]['length']*30)+1)
 add(label,action,frames)
 if action=='tx_sleep':add(label,action,[round(meta[action]['length']*30)]*15)
positions=[]
for i,state in enumerate(sequence):
 action=state['action'];frame=state['source_frame']
 positions.append(sample('wait',0) if action.startswith('tx_') else sample(action,frame))
 if i%100==0:print('SAMPLED',i,len(sequence),flush=True)
faces=[];uv=[];materials=[]
for part in mesh.parts:
 for face in part.faces:
  if len(face.vertexIndices)!=3:raise ValueError('Expected triangles')
  faces.append(face.vertexIndices);uv.extend(mesh.texCoords[j] for j in face.texCoordIndices);materials.append(part.materialIndex)
payload=dict(positions=np.array(positions,dtype='float32'),faces=np.array(faces,dtype='int32'),uv=np.array(uv,dtype='float32'),materials=np.array(materials,dtype='int32'))
for i,m in enumerate(model['materials']):
 image=model['images'][model['textures'][m.textureIndex].imageIndex]
 payload['texture_'+str(i)]=np.array(image.pixels,dtype='uint8').reshape(image.height,image.width,4)
np.savez_compressed(output/'decoded-video.npz',**payload)
report=dict(fps=30,frames=sequence,source='decoded candidate SDR',source_sha256=hashlib.sha256(raw).hexdigest(),native_game_render=False,extra_frame_interpolation=False,material_names=[m.name for m in model['materials']],transition_assumption='Declared full clip followed by wait; actual game timing still requires validation',not_shown=['native move effects','Pokeball effects','Dolphin lighting and cameras'])
(output/'video-samples.json').write_text(json.dumps(report,indent=2)+'\n')
print('VIDEO_SAMPLES_READY',len(sequence),flush=True)
