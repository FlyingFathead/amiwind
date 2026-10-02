"""Synthetic archive and Amiga-script regressions, run on Windows and Linux."""
import contextlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import build_dry_run
import prepare_scenery as scenery
from mwad.scene import pack_geometry


class HostAssetFormats(unittest.TestCase):
    def test_scenery_finds_dds_archive_entry_for_tga_material(self):
        """BSA names are slash-separated even on Windows; retain DDS priority."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = io.BytesIO()
            Image.new('RGBA', (2, 2), (11, 22, 33, 255)).save(raw, format='PNG')
            texture = raw.getvalue()
            bsa_path = root / 'Morrowind.bsa'
            bsa_path.write_bytes(texture)
            bsa = SimpleNamespace(path=bsa_path, entries={
                'meshes/fictional.nif': {'offset': 0, 'bytes': 0},
                'textures/fictional.dds': {'offset': 0, 'bytes': len(texture)},
            })
            vertices = [(0., 0., 0., 0., 0., 255, 255, 255, 255),
                        (1., 0., 0., 1., 0., 255, 255, 255, 255),
                        (0., 1., 0., 0., 1., 255, 255, 255, 255)]
            geometry = pack_geometry(vertices, [(0, 1, 2, 0)], 1)
            result = (geometry, [{'texture_source': r'Textures\Fictional.tga'}],
                      [[0., 0., 0.], [1., 1., 0.]], [])
            ref = {'number': 1, 'model': 'fictional.nif', 'position': [0., 0., 0.],
                   'rotation_radians': [0., 0., 0.], 'scale': 1.}
            with patch.object(scenery, 'BSA', return_value=bsa), \
                 patch.object(scenery, 'ordered_map', return_value=[
                     ('meshes/fictional.nif', b'fictional model', result, None, None)]), \
                 contextlib.redirect_stdout(io.StringIO()):
                scenery.export_refs(root, root/'scene', [ref], {}, [0., 0., 0.], jobs=1)
            index = json.loads((root/'scene/scenery-index.json').read_text())
            self.assertEqual(index['errors'], [])
            self.assertEqual(len(index['references']), 1)
            self.assertEqual(index['textures'][0]['source'], 'textures/fictional.dds')

    def test_generated_amiga_startup_has_no_carriage_returns(self):
        """Exercise staging; external assemblers/disk tools are not needed."""
        class StagingComplete(Exception):
            pass

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine_root = root/'engine'
            binary = engine_root/'runtime/build/AmiQuakeGCC'
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b'fixture')
            (binary.parent/'AmiWindCheck').write_bytes(b'fixture')
            (engine_root/'engine-build.json').write_text(json.dumps({
                'version': build_dry_run.VERSION, 'binary_sha256': 'fixture',
                'bootcheck_sha256': 'fixture'}))
            def run(command, **kwargs):
                if '-Fhunkexe' in command:
                    Path(command[command.index('-o')+1]).write_bytes(b'fixture')
                else:
                    raise StagingComplete
            args = SimpleNamespace(out=root/'image', sdk=root/'sdk', engine=binary, vasm=root/'vasm')
            with patch.object(build_dry_run, 'check_binary'), \
                 patch.object(build_dry_run, 'digest', return_value='fixture'), \
                 patch.object(build_dry_run.subprocess, 'run', side_effect=run), \
                 self.assertRaises(StagingComplete):
                build_dry_run.build(args)
            script = (root/'image/boot/S/startup-sequence').read_bytes()
            self.assertTrue(script.startswith(b'FailAt 10\n'))
            self.assertNotIn(b'\r', script)
            self.assertIn(b'SYS:C/AmiWindDryRun\n', script)


if __name__ == '__main__':
    unittest.main()
