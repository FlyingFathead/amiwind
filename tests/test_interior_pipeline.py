import sys,unittest,struct,tempfile
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from interior_lighting import bake_surface
from prepare_hand_sprites import render_frame,pack_frame
from mesh_geometry import shell_collision_parts

class InteriorPipelineTests(unittest.TestCase):
 def test_owned_cell_integer_and_float_water_heights(self):
  from mwad.interior import read_interior
  def sub(tag,data):return tag.encode()+struct.pack('<I',len(data))+data
  for tag,water,expected,flags in [('INTV',struct.pack('<i',-760),-760,3),('WHGT',struct.pack('<f',12.5),12.5,3),('INTV',struct.pack('<i',99),None,1)]:
   body=sub('NAME',b'Fixture\0')+sub('DATA',struct.pack('<Iii',flags,0,0))+sub(tag,water)+sub('AMBI',bytes(16))
   with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp)/'master.esm';p.write_bytes(b'CELL'+struct.pack('<III',len(body),0,0)+body)
    self.assertEqual(read_interior(p,'Fixture')['water_height'],expected)
 def test_scripted_room_architecture_is_retained_without_admitting_unknown_activators(self):
  from mwad.interior import select_geometry
  room={'number':172861,'id':'CharGen Stuff Room','type':'ACTI','model':'i\\In_C_plain_room_side.NIF'}
  unknown=dict(room,number=2,id='unknown activator')
  deleted=dict(room,number=3,deleted=True)
  wrong_model=dict(room,number=4,model='EditorMarker.NIF')
  selected,omitted=select_geometry({'refs':[room,unknown,deleted,wrong_model]})
  self.assertEqual(selected,[room]);self.assertEqual(len(omitted),3)
 def test_constant_uv_lighting_has_finite_face_sample(self):
  p=np.array([[0.,0,0],[16.,0,0],[0,16.,0]])
  light={'ambient':[80,80,80],'lights':[]}
  self.assertEqual(bake_surface(p,np.zeros((3,2)),np.zeros(2),np.eye(3),np.zeros(3),light),bytes([80]))
 def test_lamp_falloff_is_baked_not_a_runtime_light(self):
  p=np.array([[0.,0,0],[16.,0,0],[0,16.,0]])
  light={'ambient':[20,20,20],'lights':[{'position':[0,0,0],'radius':128,'color':[100,100,100]}]}
  out=bake_surface(p,np.array([[1.,0],[0,1],[0,0]]),np.zeros(2),np.eye(3),np.zeros(3),light)
  self.assertEqual(len(out),4);self.assertGreater(out[0],out[-1]);self.assertLess(out[-1],120)
 def test_original_falloff_reaches_past_the_radius_and_fades_by_twice_it(self):
  from interior_lighting import original_weight
  self.assertEqual(original_weight(0,16),1.0);self.assertEqual(original_weight(5,16),1.0)
  self.assertAlmostEqual(original_weight(16,16),1/3)
  self.assertGreater(original_weight(27,16),0);self.assertEqual(original_weight(32,16),0)
  p=np.array([[0.,0,0],[16.,0,0],[0,16.,0]])
  light={'ambient':[64,64,64],'lights':[{'position':[0,0,4*27],'radius':64,'color':[245,140,40]}]}
  axes=np.array([[1.,0],[0,1],[0,0]])
  self.assertEqual(bake_surface(p,axes,np.zeros(2),np.eye(3),np.zeros(3),light)[0],64)
  out=bake_surface(p,axes,np.zeros(2),np.eye(3),np.zeros(3),dict(light,falloff='original'))
  self.assertGreater(out[0],64)
 def test_off_by_default_lights_give_no_light(self):
  p=np.array([[0.,0,0],[16.,0,0],[0,16.,0]])
  lit={'position':[0,0,0],'radius':128,'color':[100,100,100],'flags':0x1}
  axes=np.array([[1.,0],[0,1],[0,0]])
  self.assertGreater(bake_surface(p,axes,np.zeros(2),np.eye(3),np.zeros(3),{'ambient':[20,20,20],'lights':[lit]})[0],20)
  off=dict(lit,flags=0x21)
  self.assertEqual(bake_surface(p,axes,np.zeros(2),np.eye(3),np.zeros(3),{'ambient':[20,20,20],'lights':[off]})[0],20)
 def test_box_zone_scales_inside_with_a_soft_edge(self):
  from interior_lighting import zone_scale
  zone=[{'box':[[0,0,0],[64,64,64]],'scale':.6,'soft':16}]
  self.assertEqual(zone_scale(np.array([-1.,32,32]),zone),1.0)
  self.assertAlmostEqual(zone_scale(np.array([32.,32,32]),zone),.6)
  self.assertAlmostEqual(zone_scale(np.array([8.,32,32]),zone),.8)
  p=np.array([[0.,0,0],[16.,0,0],[0,16.,0]])+32
  light={'ambient':[100,100,100],'lights':[],'zones':zone}
  self.assertEqual(bake_surface(p,np.zeros((3,2)),np.zeros(2),np.eye(3),np.zeros(3),light),bytes([60]))
 def test_hollow_surface_does_not_fill_room_centre(self):
  v=np.array([[-20,-20,0,0,0],[20,-20,0,1,0],[20,20,0,1,1],[-20,20,0,0,1]],float)
  f=np.array([[0,1,2,0],[0,2,3,0]])
  pieces=shell_collision_parts(v,f);self.assertEqual(len(pieces),1)
  h=pieces[0][1];self.assertTrue(np.any(np.array([0,0,5])@h.equations[:,:3].T+h.equations[:,3]>0))
 def test_hand_bake_clips_behind_camera_and_writes_opaque_spans(self):
  p=np.array([[10,-2,0],[10,2,0],[10,0,2]],float);f=np.array([[0,1,2]]);uv=np.zeros((3,2));skin=np.array([[7]],np.uint8)
  im=render_frame(p,f,uv,skin);self.assertGreater(int((im==7).sum()),0)
  self.assertEqual(set(np.unique(im)),{7,255});self.assertLess(len(pack_frame(im)),16000)
  p[:,0]=-10;self.assertTrue((render_frame(p,f,uv,skin)==255).all())
