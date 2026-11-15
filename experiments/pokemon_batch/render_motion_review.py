"""Render private, labeled animation reviews, without distributing game assets.

Requires Godot 4.6, ffmpeg and a graphical display (software Mesa is supported).
Movie recording uses a fixed 30 Hz clock; it is not a performance benchmark.
"""
import argparse,json,os,subprocess
from pathlib import Path

TITLES={'mega-charizard-y':'Mega Charizard Y','ash-greninja':'Ash-Greninja','hydreigon':'Hydreigon','rillaboom':'Rillaboom'}
LABELS={'wait':'Espera — ciclo contínuo','run':'Deslocamento','damage':'Receber dano e recuperar a postura','down':'Desmaio','hikkaku':'Ataque físico — garras / braços','kick':'Ataque físico — pernas','kime':'Ataque especial / postura de ação','kime_a':'Ataque alternativo','tackle':'Investida física','takeoff':'Decolagem — rascunho','kuchu_wait':'Espera aérea','kyukoka':'Mergulho aéreo','kuchu_down':'Desmaio no ar','kime_phy':'Ataque físico alternativo'}

def plan_for(key,report):
    names=list(report['body_actions'])
    names=[n for n in names if n not in ('down','kuchu_down')]+[n for n in names if n in ('down','kuchu_down')]
    segments=[]
    for name in names:
        action=report['body_actions'][name]
        seconds=action['duration_seconds']*2 if name in ('wait','kuchu_wait','run') else action['duration_seconds']+.25
        label=LABELS.get(name,name)
        if key=='hydreigon' and name=='run':label='Voo estacionário — deslocamento ainda pendente'
        segments.append(dict(action=name,label=label,seconds=seconds))
        if name not in ('wait','run','kuchu_wait','down','kuchu_down'):
            segments.append(dict(action='wait',label='Retorno à espera — transição de 0,18 s',seconds=.65))
    segments.append(dict(action='wait',label='Pendentes: Poké Bola, efeitos e validação dos 20 golpes no Dolphin',seconds=3.5))
    return dict(title=TITLES[key],segments=segments)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--motion-dir',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--tail-flame',action='store_true',help='Review Charizard Y with the approved preview flame')
    parser.add_argument('--godot',default='godot')
    parser.add_argument('--ffmpeg',default='ffmpeg')
    parser.add_argument('--keys',nargs='+',choices=list(TITLES),default=list(TITLES))
    args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[2]
    env=os.environ.copy()
    for kind in ('CACHE','CONFIG','DATA'):
        env.setdefault('XDG_'+kind+'_HOME','/tmp/pbr-godot-'+kind.lower())
    subprocess.run([args.godot,'--headless','--path',str(root/'native/runtime'),'--check-only','--script','preview.gd'],env=env,check=True,timeout=30)
    for key in args.keys:
        report=json.loads((args.motion_dir/(key+'-motion.json')).read_text())
        plan=args.motion_dir/(key+'-preview-plan.json')
        review=plan_for(key,report)
        if args.tail_flame:
            if key!='mega-charizard-y' or report['source_donor']!='pkx_006.fsys':
                raise ValueError('Approved flame review expects Mega Charizard Y with original Charizard motion')
            review.update(title='Charizard original → Mega Charizard Y',tail_flame=True,ground_reference='wait',footer='Movimentos do Charizard original adaptados ao Y • Chama aprovada\nPrévia de revisão; integração no Dolphin ainda pendente.')
            names=['wait','run','hikkaku','kick','tackle','kime','kime_a','damage','takeoff','kuchu_wait','kyukoka','down']
            segments=[]
            for name in names:
                clip=report['body_actions'][name]
                seconds=clip['duration_seconds']*(2 if name in ('wait','run','kuchu_wait') else 1)+(.25 if name not in ('wait','run','kuchu_wait') else 0)
                segments.append(dict(action=name,label=LABELS.get(name,name)+' — original',seconds=seconds,distance=6.8,yaw=.65))
                if name not in ('wait','run','takeoff','kuchu_wait','down'):
                    segments.append(dict(action='wait',label='Retorno à espera original',seconds=.65))
            review['segments']=segments
        plan.write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
        avi=args.output_dir/(key+'-review.avi');mp4=args.output_dir/(key+'-animacoes.mp4')
        with (args.motion_dir/(key+'-movie.log')).open('w') as log:
            subprocess.run([args.godot,'--path',str(root/'native/runtime'),'res://preview.tscn','--audio-driver','Dummy','--write-movie',str(avi),'--fixed-fps','30','--','--model',str(args.motion_dir/(key+'-motion.glb')),'--preview-plan',str(plan)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600,check=True)
        subprocess.run([args.ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(avi),'-an','-c:v','libx264','-preset','fast','-crf','21','-pix_fmt','yuv420p','-movflags','+faststart',str(mp4)],timeout=120,check=True)
        avi.unlink()
        print('VIDEO_READY',key,mp4.stat().st_size,flush=True)

if __name__=='__main__':main()
