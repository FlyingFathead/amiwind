# SPDX-License-Identifier: GPL-3.0-only
"""Actual resident voice writes must not depend on an earlier prototype stage."""
import contextlib
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
import prepare_area as area
from player_hull import pack_lumps
from chim.frame_map import empty_world


class AreaVoiceDirectoryTests(unittest.TestCase):
    def run_fixture(self,root,existing):
        (root/'Morrowind.esm').write_bytes(b'fictional master fixture')
        scene=root/'scene';(scene/'id1/maps').mkdir(parents=True);(scene/'id1/progs').mkdir()
        (scene/'id1/gfx').mkdir();(scene/'id1/gfx/palette.lmp').write_bytes(bytes(768))
        chunks=empty_world([-32.,-32.,-32.],[32.,32.,32.]);chunks[0]=b'{"classname" "worldspawn"}'+bytes([0])
        (scene/'id1/maps/seyda.bsp').write_bytes(pack_lumps(chunks))
        identifier='fargoth';stem='a_'+hashlib.sha256(identifier.encode()).hexdigest()[:12]
        voice=scene/'id1/sound/npc'/(stem+'.wav')
        if existing:
            voice.parent.mkdir(parents=True);voice.write_bytes(b'old voice');(voice.parent/'unchanged.bin').write_bytes(b'keep')
        self.assertEqual(voice.parent.exists(),existing)
        stream=io.BytesIO()
        with wave.open(stream,'wb') as sound:
            sound.setnchannels(1);sound.setsampwidth(1);sound.setframerate(11025);sound.writeframes(bytes([127,128,129]))
        payload=stream.getvalue();rawmodel=b'fictional encoded model'
        ref={'id':identifier,'number':17,'scale':1.,'position':[-11264.,-71680.,64.],
             'rotation_radians':[0.,0.,0.]}
        appearance={'id':identifier,'name':'Fixture Resident','female':False,'skeleton':'fixture'}
        def producer(function,tasks,workers):
            self.assertEqual(len(tasks),1)
            return [(identifier,rawmodel,payload,{'appearance':tasks[0][2],'step':.25,
                     'greeting':{'text':'Fixture greeting'},'sha256':hashlib.sha256(rawmodel).hexdigest()})]
        with contextlib.ExitStack() as stack:
            for name,value in {'load_master':({'NPC_':{identifier:[]}},[{'refs':[ref]}],{}),
                               'outfit':appearance,'first':b'', 'foot_class':'bare','voices_of':{},
                               'greeting_fixture':{},'behavior_record':{},
                               'greeting_settings':{'distance':10,'reset_distance':20,'duration':1}}.items():
                stack.enter_context(patch.object(area,name,return_value=value))
            stack.enter_context(patch.object(area,'ordered_map',side_effect=producer))
            stack.enter_context(patch.object(area.npc_items,'attach_items',side_effect=lambda k,i,a:a))
            stack.enter_context(patch.object(area.npc_lod,'publish',return_value={'mode':'off'}))
            report=area.populate(root,scene,rooms={},reports=[],jobs=1,doors=False)
        self.assertEqual(voice.read_bytes(),payload)
        self.assertEqual((scene/'id1/progs'/(stem+'.mdl')).read_bytes(),rawmodel)
        self.assertEqual(report['cast'],[{'map':'seyda','reference':17,'id':identifier,'position':[0.,0.,16.]}])
        self.assertEqual((scene/'seyda.bsp').read_bytes(),(scene/'id1/maps/seyda.bsp').read_bytes())
        self.assertFalse(list(scene.rglob('*.replacing')))
        if existing:self.assertEqual((voice.parent/'unchanged.bin').read_bytes(),b'keep')

    def test_absent_voice_directory_is_created_for_actual_write(self):
        with tempfile.TemporaryDirectory() as root:self.run_fixture(Path(root),False)

    def test_existing_voice_directory_keeps_atomic_replacement_and_siblings(self):
        with tempfile.TemporaryDirectory() as root:self.run_fixture(Path(root),True)


if __name__=='__main__':unittest.main()
