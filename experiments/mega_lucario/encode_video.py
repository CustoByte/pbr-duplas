"""Render decoded Mega candidate frames through EGL and encode a private MP4.

Lighting is simplified. No video frame interpolation is added.
"""
import argparse,json,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import moderngl

def normalized(v):return v/np.linalg.norm(v)

def render(directory,output):
 data=np.load(directory/'decoded-video.npz');report=json.loads((directory/'video-samples.json').read_text())
 poses=data['positions'];width,height=960,720
 ends={}
 for state in report['frames']:ends[state['action']]=max(ends.get(state['action'],0),state['source_frame'])
 all_points=poses.reshape(-1,3);center=(all_points.min(0)+all_points.max(0))/2
 eye=center+normalized(np.array([0.8,-2,0.48]))*50
 forward=normalized(center-eye);side=normalized(np.cross(forward,[0,0,1]));up=np.cross(side,forward)
 view=np.eye(4);view[:3,:3]=[side,up,-forward];view[:3,3]=-view[:3,:3]@eye
 # One fixed framing per chapter; close-up for the eye demonstrations.
 labels=[state['label'] for state in report['frames']]
 eye_vertices=np.unique(data['faces'][data['materials']==report['material_names'].index('Material #193')])
 projections={}
 for label in dict.fromkeys(labels):
  chosen=poses[np.array([i for i,text in enumerate(labels) if text==label])]
  if label.startswith('Olhos'):chosen=chosen[:,eye_vertices]
  cp=chosen.reshape(-1,3)@view[:3,:3].T+view[:3,3];lo,hi=cp.min(0),cp.max(0)
  vertical=max((hi[1]-lo[1])*1.38,(hi[0]-lo[0])*height/width*1.15)
  horizontal=vertical*width/height;cx,cy=(lo[0]+hi[0])/2,(lo[1]+hi[1])/2
  left,right,bottom,top=cx-horizontal/2,cx+horizontal/2,cy-vertical/2,cy+vertical/2
  projections[label]=np.array([[2/(right-left),0,0,-(right+left)/(right-left)],
  [0,2/(top-bottom),0,-(top+bottom)/(top-bottom)],[0,0,-2/199,-201/199],[0,0,0,1]],dtype='f4')
 ctx=moderngl.create_standalone_context(backend='egl')
 program=ctx.program(vertex_shader='''#version 330
uniform mat4 mvp;in vec3 position;in vec3 normal;in vec2 uv;
out vec3 N;out vec2 UV;
void main(){gl_Position=mvp*vec4(position,1);N=normal;UV=uv;}
''',fragment_shader='''#version 330
uniform sampler2D tex;uniform vec2 uv_offset;in vec3 N;in vec2 UV;out vec4 color;
void main(){vec4 c=texture(tex,UV+uv_offset);if(c.a<0.15)discard;
vec3 n=normalize(N);float light=0.5+0.48*max(0,dot(n,normalize(vec3(1,-2,3))))+0.1*max(0,dot(n,normalize(vec3(-2,-0.5,1))));color=vec4(c.rgb*light,c.a);}
''')
 program['tex'].value=0
 fbo=ctx.simple_framebuffer((width,height),components=3);fbo.use();ctx.enable(moderngl.DEPTH_TEST)
 faces=data['faces'];uv=data['uv'];mats=data['materials'];order=np.argsort(mats,kind='stable')
 sorted_faces=faces[order];sorted_uv=uv.reshape(-1,3,2)[order].reshape(-1,2);sorted_mats=mats[order]
 buf=ctx.buffer(reserve=faces.size*8*4);vao=ctx.vertex_array(program,[(buf,'3f 3f 2f','position','normal','uv')]);textures=[]
 for i in range(len(report['material_names'])):
  image=data['texture_'+str(i)];texture=ctx.texture((image.shape[1],image.shape[0]),4,image.tobytes());texture.filter=(moderngl.LINEAR,moderngl.LINEAR);textures.append(texture)
 fontdir=Path('/usr/share/fonts/truetype/dejavu')
 titlefont=ImageFont.truetype(str(fontdir/'DejaVuSans-Bold.ttf'),26)
 font=ImageFont.truetype(str(fontdir/'DejaVuSans.ttf'),19);small=ImageFont.truetype(str(fontdir/'DejaVuSans.ttf'),15)
 output.parent.mkdir(parents=True,exist_ok=True)
 encoder=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{width}x{height}','-r','30','-i','-','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(output)],stdin=subprocess.PIPE)
 snapshots=[]
 try:
  for i,positions in enumerate(poses):
   state=report['frames'][i]
   program['mvp'].write(np.array(projections[state['label']]@view,dtype='f4').T.tobytes())
   fbo.clear(0.075,0.105,0.145,1,depth=1)
   n=np.cross(positions[faces[:,1]]-positions[faces[:,0]],positions[faces[:,2]]-positions[faces[:,0]])
   normals=np.zeros_like(positions)
   for j in range(3):np.add.at(normals,faces[:,j],n)
   normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-8)
   vertices=np.concatenate((positions[sorted_faces].reshape(-1,3),normals[sorted_faces].reshape(-1,3),sorted_uv),axis=1).astype('f4');buf.write(vertices.tobytes())
   for mi,texture in enumerate(textures):
    chosen=np.flatnonzero(sorted_mats==mi)
    if not len(chosen):continue
    shift=0.0
    if report['material_names'][mi]=='Material #193':
     if state['action']=='tx_sleep':shift=-0.75
     elif state['action']=='tx_wakeup':shift=-0.75*(1-state['source_frame']/ends['tx_wakeup'])
     elif state['action']=='tx_wink' and 1<=state['source_frame']<ends['tx_wink']:shift=-0.75
    program['uv_offset'].value=(0,shift);texture.use(0)
    vao.render(moderngl.TRIANGLES,vertices=len(chosen)*3,first=int(chosen[0])*3)
   image=Image.frombytes('RGB',(width,height),fbo.read(components=3,alignment=1)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
   draw=ImageDraw.Draw(image);draw.rectangle((0,0,width,85),fill='#111c2a');draw.rectangle((0,height-66,width,height),fill='#111c2a')
   draw.text((width//2,12),'MEGA LUCARIO — PRÉVIA DAS ANIMAÇÕES',font=titlefont,fill='#a9e6da',anchor='mt')
   draw.text((width//2,50),state['label'],font=font,fill='white',anchor='mt')
   draw.text((width//2,height-55),'Arquivo SDR convertido • 30 fps • fora do Dolphin',font=small,fill='#c0ccd9',anchor='mt')
   draw.text((width//2,height-30),'Sem os efeitos dos golpes e da Pokébola • integração no jogo pendente',font=small,fill='#c0ccd9',anchor='mt')
   if i in (0,220,425,740,760):image.save(output.with_name(output.stem+f'-frame-{i:04d}.png'));snapshots.append(i)
   encoder.stdin.write(image.tobytes())
   if i%100==0:print('ENCODED',i,len(poses),flush=True)
  encoder.stdin.close()
  if encoder.wait()!=0:raise RuntimeError('ffmpeg failed')
 finally:
  if encoder.poll() is None:encoder.kill()
 result=dict(frames=len(poses),fps=30,seconds=len(poses)/30,resolution=[width,height],renderer=ctx.info['GL_RENDERER'],source_sha256=report['source_sha256'],native_game_render=False,frame_interpolation=False,snapshots=snapshots)
 output.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('output',type=Path);a=p.parse_args();print(json.dumps(render(a.directory,a.output)))
