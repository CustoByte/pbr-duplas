"""Private visual review of a re-imported SDR and its decoded eye tracks."""
import argparse,json,os,subprocess
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--work',type=Path,required=True);p.add_argument('--body-plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args();root=Path(__file__).resolve().parents[2];report=json.loads((a.work/'roundtrip.json').read_text());native=json.loads((a.work/'native-loading.json').read_text());assert report['passed'] and native['passed']
 d=json.loads(a.body_plan.read_text());assert {s['action'] for s in d['segments']}<=set(report['actions'])
 d.update(title='Mega Charizard Y — conjunto nativo',eye_material_tracks=report['eye_review_tracks'],footer='Movimentos e olhos do SDR candidato • Mandíbula corrigida\nChama: efeito aprovado do visualizador • Batalha no Dolphin ainda não validada.')
 for state,label,seconds in [('tx_wink','Piscar — animação de material',1),('tx_sleep','Dormir — olhos fechados',2),('tx_wakeup','Acordar — retorno dos olhos',1),('','Retorno à espera',1)]:d['segments'].append(dict(action='wait',eye_state=state,label=label,seconds=seconds,camera_focus_bone='head neck upper',camera_focus_offset=[0,.15,0],yaw=.65,distance=1.3))
 plan=a.work/'native-set-preview-plan.json';plan.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');a.output.parent.mkdir(parents=True,exist_ok=True);avi=a.output.with_suffix('.avi');env=os.environ.copy()
 for kind in ('CACHE','CONFIG','DATA'):env.setdefault('XDG_'+kind+'_HOME','/tmp/pbr-godot-'+kind.lower())
 for script in ('preview.gd','eye_state_review.gd'):
  subprocess.run(['godot','--headless','--path',str(root/'native/runtime'),'--check-only','--script',script],env=env,check=True,timeout=30)
 with (a.work/'native-set-preview.log').open('w') as log:
  subprocess.run(['godot','--audio-driver','Dummy','--path',str(root/'native/runtime'),'res://preview.tscn','--write-movie',str(avi),'--fixed-fps','30','--','--model',str(a.work/'native-roundtrip.glb'),'--preview-plan',str(plan)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600,check=True)
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(avi),'-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(a.output)],check=True,timeout=150)
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(a.output),'-f','null','-'],check=True,timeout=150)
 avi.unlink();print('NATIVE_SET_PREVIEW_READY',flush=True)

if __name__=='__main__':main()
