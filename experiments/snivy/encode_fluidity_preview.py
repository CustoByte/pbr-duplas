"""Render private decoded SDR frame data with EGL and encode a comparison MP4.

Simplified preview only: not a Dolphin capture and no game assets are published.
"""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import moderngl


def normalized(v):
    return v / np.linalg.norm(v)


def render(data_path, report_path, output):
    data = np.load(data_path)
    report = json.loads(report_path.read_text())
    poses = data['positions']
    width, height = 960, 540
    direction = normalized(np.array([0.85, -1.6, 0.48]))
    right = normalized(np.array([1.6, 0.85, 0.]))
    offsets = [np.zeros(3), np.zeros(3)]
    panel_width = width // 2
    all_points = poses.reshape(-1, 3)
    center = (all_points.min(0) + all_points.max(0)) / 2
    eye = center + direction * 20
    forward = normalized(center - eye)
    side = normalized(np.cross(forward, [0, 0, 1]))
    up = np.cross(side, forward)
    view = np.eye(4)
    view[:3, :3] = np.array([side, up, -forward])
    view[:3, 3] = -view[:3, :3] @ eye
    camera_points = all_points @ view[:3, :3].T + view[:3, 3]
    lo, hi = camera_points.min(0), camera_points.max(0)
    vertical = max(hi[1] - lo[1] + 1.7, (hi[0] - lo[0] + 0.8) * height / panel_width)
    horizontal = vertical * panel_width / height
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2 + 0.18
    left, right_edge, bottom, top = cx - horizontal / 2, cx + horizontal / 2, cy - vertical / 2, cy + vertical / 2
    projection = np.array([[2/(right_edge-left),0,0,-(right_edge+left)/(right_edge-left)],
                           [0,2/(top-bottom),0,-(top+bottom)/(top-bottom)],
                           [0,0,-2/99,-101/99], [0,0,0,1]],dtype='f4')
    ctx = moderngl.create_standalone_context(backend='egl')
    program = ctx.program(vertex_shader='''#version 330
uniform mat4 mvp;
in vec3 position; in vec3 normal; in vec2 uv;
out vec3 N; out vec2 UV;
void main(){gl_Position=mvp*vec4(position,1); N=normal; UV=uv;}
''',fragment_shader='''#version 330
uniform sampler2D tex; in vec3 N; in vec2 UV; out vec4 color;
void main(){vec4 c=texture(tex,UV); if(c.a<0.15)discard;
vec3 n=normalize(N); float light=0.5+0.48*max(0,dot(n,normalize(vec3(1,-2,3))))+0.1*max(0,dot(n,normalize(vec3(-2,-0.5,1))));
color=vec4(c.rgb*light,c.a);}
''')
    program['mvp'].write(np.array(projection @ view, dtype='f4').T.tobytes())
    program['tex'].value = 0
    fbo = ctx.simple_framebuffer((width,height),components=3)
    fbo.use();ctx.enable(moderngl.DEPTH_TEST)
    buffers, arrays, textures = [], [], []
    for actor in range(2):
        faces = data[f'faces_{actor}']
        count = faces.size
        buf = ctx.buffer(reserve=count*8*4)
        vao = ctx.vertex_array(program,[(buf,'3f 3f 2f','position','normal','uv')])
        buffers.append(buf);arrays.append(vao)
        mats = []
        for material in range(int(data[f'materials_{actor}'].max())+1):
            pixels = data[f'texture_{actor}_{material}']
            texture = ctx.texture((pixels.shape[1],pixels.shape[0]),4,pixels.tobytes())
            texture.filter = (moderngl.LINEAR,moderngl.LINEAR)
            texture.repeat_x = texture.repeat_y = True
            mats.append(texture)
        textures.append(mats)
    fontdir=Path('/usr/share/fonts/truetype/dejavu')
    bold=ImageFont.truetype(str(fontdir/'DejaVuSans-Bold.ttf'),22)
    font=ImageFont.truetype(str(fontdir/'DejaVuSans.ttf'),16)
    small=ImageFont.truetype(str(fontdir/'DejaVuSans.ttf'),14)
    output.parent.mkdir(parents=True,exist_ok=True)
    log=output.with_suffix('.ffmpeg.log').open('w')
    encoder=subprocess.Popen(['ffmpeg','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{width}x{height}','-r','30','-i','-',
                              '-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(output)],stdin=subprocess.PIPE,stderr=log)
    try:
        for frame, pair in enumerate(poses):
            fbo.clear(0.075,0.105,0.145,1,depth=1)
            for actor in range(2):
                ctx.viewport = (actor * panel_width, 0, panel_width, height)
                positions=pair[actor]
                faces=data[f'faces_{actor}']
                n=np.cross(positions[faces[:,1]]-positions[faces[:,0]],positions[faces[:,2]]-positions[faces[:,0]])
                normals=np.zeros_like(positions)
                for i in range(3):np.add.at(normals,faces[:,i],n)
                lengths=np.linalg.norm(normals,axis=1,keepdims=True)
                normals/=np.maximum(lengths,1e-8)
                vertices=np.concatenate([(positions+offsets[actor])[faces].reshape(-1,3),normals[faces].reshape(-1,3),data[f'uv_{actor}']],axis=1).astype('f4')
                buffers[actor].write(vertices.tobytes())
                mats=data[f'materials_{actor}']
                # Native exporter keeps the triangles for each material together.
                for material,texture in enumerate(textures[actor]):
                    chosen=np.flatnonzero(mats==material)
                    if not len(chosen):continue
                    assert np.all(np.diff(chosen)==1)
                    texture.use(0)
                    arrays[actor].render(moderngl.TRIANGLES,vertices=len(chosen)*3,first=int(chosen[0])*3)
            img=Image.frombytes('RGB',(width,height),fbo.read(components=3,alignment=1)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            draw=ImageDraw.Draw(img)
            draw.rectangle((0,0,width,67),fill='#111c2a')
            draw.rectangle((0,height-40,width,height),fill='#111c2a')
            draw.line((width//2,67,width//2,height-40),fill='#53667a',width=2)
            labels=report['frames'][frame]
            title='SELEÇÃO → ESPERA' if labels['section']=='selection' else 'DANO → RECUPERAÇÃO'
            draw.text((width//2,6),title,font=small,fill='#c0ccd9',anchor='mt')
            draw.text((width//4,27),'ATUAL — teste 3',font=bold,fill='#ffb783',anchor='mt')
            draw.text((3*width//4,27),'PROPOSTA — não publicada',font=bold,fill='#92e4bc',anchor='mt')
            for actor,state in enumerate(labels['states']):draw.text((width//4+actor*width//2,height-57),state,font=font,fill='white',anchor='mt')
            draw.text((width//2,height-29),'Prévia dos arquivos SDR • 30 fps • iluminação simplificada • fora do Dolphin',font=small,fill='#c0ccd9',anchor='mt')
            encoder.stdin.write(img.tobytes())
            if frame==0:img.save(output.with_suffix('.png'))
        encoder.stdin.close()
        assert encoder.wait()==0
    finally:
        if encoder.poll() is None:encoder.kill()
        log.close()
    return dict(frames=len(poses),fps=30,seconds=len(poses)/30,resolution=[width,height],renderer=ctx.info['GL_RENDERER'],native_game_render=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('data','report','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    print(json.dumps(render(args.data,args.report,args.output),indent=2))
