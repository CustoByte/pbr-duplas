"""Regression checks for the selected battle set and export rotation conversion."""
import json,math,unittest
from pathlib import Path
from battle_set import describe
from rotation_math import stable_euler

def quaternion(x,y,z):
 cx,sx=math.cos(x/2),math.sin(x/2)
 cy,sy=math.cos(y/2),math.sin(y/2)
 cz,sz=math.cos(z/2),math.sin(z/2)
 return (cx*cy*cz+sx*sy*sz,sx*cy*cz-cx*sy*sz,cx*sy*cz+sx*cy*sz,cx*cy*sz-sx*sy*cz)

class CandidateTests(unittest.TestCase):
 def test_gimbal_roundtrip(self):
  for x in (-2.8,-0.4,0,1.7):
   for y in (-math.pi/2,-math.pi/2+1e-5,math.pi/2-1e-5,math.pi/2):
    for z in (-2.1,0.3,2.5):
     q=quaternion(x,y,z);again=quaternion(*stable_euler(q))
     self.assertGreater(abs(sum(a*b for a,b in zip(q,again))),1-1e-10)
 def test_requested_set(self):
  p=json.loads(Path(__file__).with_name('profile.json').read_text())
  self.assertEqual(describe(p)['stats'],dict(hp=146,attack=181,defense=108,special_attack=176,special_defense=90,speed=163))
  self.assertEqual(p['pass_placement']['replace_species'],'Ivysaur')
 def test_training_budget_rejected(self):
  p=json.loads(Path(__file__).with_name('profile.json').read_text())
  p['evs']['hp']=252
  with self.assertRaises(ValueError):describe(p)

if __name__=='__main__':unittest.main()
