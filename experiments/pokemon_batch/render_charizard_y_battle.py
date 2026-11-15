"""Render private donor-free Y motion and flame reviews; no game publishing."""
import argparse,json,os,subprocess
from pathlib import Path

ROWS=[('takeoff',2.4,'Decolagem própria',.55),('wait',6,'Voo contínuo e chama ativa — vista lateral',1.15),('run',2.4,'Voo de aproximação — movimento corporal',.8),('hikkaku',2.4,'Ataque físico — preparação, golpe e recuperação',.55),('kime',2.4,'Ataque especial — postura e abertura da boca',.55),('tackle',2.4,'Investida aérea',1.1),('guard',2.4,'Defesa — postura corporal',.55),('ground_impact',2.4,'Impacto no solo — ação corporal',.8),('recover',3.6,'Pouso e recuperação — ação corporal',.8),('damage',2.4,'Receber dano e recuperar o voo',.55),('ball_return',2.4,'Recolhimento corporal — efeito da Poké Bola pendente',1.1),('ball_exit',2.4,'Saída corporal — efeito da Poké Bola pendente',1.1),('wait',2.4,'Retorno à espera aérea',.55),('land',2.4,'Pouso controlado',1.1),('takeoff',2.4,'Nova decolagem',1.1),('down',4.4,'Desmaio e pose final',.8)]

def plans():
    return [('mega-charizard-y-voo-chama-estados',dict(title='Mega Charizard Y',tail_flame=True,ground_reference='land',footer='Movimentos próprios • Chama e partículas: teste visual\nIntegração no Dolphin, efeitos dos golpes e Poké Bola ainda pendentes.',segments=[dict(action=a,seconds=t,label=l,yaw=y,distance=6.8) for a,t,l,y in ROWS])),('mega-charizard-y-chama-detalhe',dict(title='Mega Charizard Y — chama',tail_flame=True,ground_reference='land',camera_focus_bone='Feeler1',footer='Chama procedural em teste visual • Sem captura do Dolphin\nEfeito ligado ao osso da cauda; adaptação ao motor original ainda pendente.',segments=[dict(action='wait',label='Detalhe: chama, turbulência e brasas',seconds=6,yaw=1.3,distance=2.5)]))]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[2];env=os.environ.copy()
    for kind in ('CACHE','CONFIG','DATA'):env.setdefault('XDG_'+kind+'_HOME','/tmp/pbr-godot-'+kind.lower())
    subprocess.run(['godot','--headless','--path',str(root/'native/runtime'),'--check-only','--script','preview.gd'],env=env,check=True,timeout=30)
    subprocess.run(['godot','--headless','--path',str(root/'native/runtime'),'--check-only','--script','tail_flame_review.gd'],env=env,check=True,timeout=30)
    for name,plan in plans():
        file=args.assets/(name+'-plan.json');file.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
        avi=args.output/(name+'.avi');mp4=args.output/(name+'.mp4')
        with (args.assets/(name+'.log')).open('w') as log:
            subprocess.run(['godot','--audio-driver','Dummy','--path',str(root/'native/runtime'),'res://preview.tscn','--write-movie',str(avi),'--fixed-fps','30','--','--model',str(args.assets/'mega-charizard-y-battle.glb'),'--preview-plan',str(file)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600,check=True)
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(avi),'-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(mp4)],timeout=150,check=True)
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(mp4),'-f','null','-'],timeout=120,check=True)
        avi.unlink();print('PREVIEW_READY',mp4,flush=True)

if __name__=='__main__':main()
