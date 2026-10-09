"""Missing gallery content must fail image assembly instead of shipping silently."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

from build_gallery import DISABLED_MARKER, FORMAT, catalogue_files, sha, stage_required, validate_payload, omit_gallery


class GalleryBuildTests(unittest.TestCase):
    def fixture(self, root):
        gallery=root/'converted'
        for name in ('gfx','gallery','maps'):(gallery/name).mkdir(parents=True)
        (gallery/'gfx/palette.lmp').write_bytes(bytes(768))
        key='m'+'1'*16
        raw=bytearray(84);raw[:8]=b'IDPO\x06\0\0\0';struct.pack_into('<ii',raw,60,3,1)
        for name in (key,'f'+key[1:]):(gallery/'gallery'/(name+'.mdl')).write_bytes(raw)
        (gallery/'gallery/catalog.txt').write_text(f'AWG1 1\n1\tNPC_\t{key}\t{key}\t1\t1\t1\tsource\tSource\n')
        (gallery/'gallery/poses.txt').write_text('AWGP1\n')
        (gallery/'gallery/inspection.tsv').write_text('inspection\nunreviewed\n')
        (gallery/'model-budgets.txt').write_text('AWPB1\n')
        (gallery/'maps/charplane.bsp').write_bytes(b'synthetic-map')
        result={'status':'ready','sha256':hashlib.sha256(raw).hexdigest()}
        (gallery/'gallery-audit.json').write_text(json.dumps({'models':{key:result},'entries':[{'number':1,'models':[key,key],'id':'source','name':'Source'}]}))
        count,files=catalogue_files(gallery/'gallery/catalog.txt')
        receipt={'format':FORMAT,'records':count,'models':1,'palette_sha256':sha(gallery/'gfx/palette.lmp'),
                 'files':{n:{'bytes':(gallery/n).stat().st_size,'sha256':sha(gallery/n)} for n in files}}
        (gallery/'gallery-build.json').write_text(json.dumps(receipt))
        return gallery,receipt,key

    def test_stage_includes_catalogue_models_footprints_map_and_greetings_index(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);gallery,receipt,key=self.fixture(root);id1=root/'id1'
            (id1/'gfx').mkdir(parents=True);(id1/'maps').mkdir()
            (id1/'gfx/palette.lmp').write_bytes(bytes(768))
            (id1/DISABLED_MARKER).write_text('stale marker from an earlier gallery-less image\n')
            report=stage_required(gallery,id1)
            self.assertEqual(report['status'],'passed')
            self.assertEqual(report['records'],1)
            # Default builds carry no marker, so the engine's gallery commands work as normal.
            self.assertFalse((id1/DISABLED_MARKER).exists())
            self.assertNotIn('marker',report)
            self.assertEqual((id1/'gallery/voices.txt').read_text(),'AWGV1\n')
            self.assertEqual((id1/'maps/charplane.bsp').read_bytes(),b'synthetic-map')
            self.assertTrue((id1/'gallery'/('f'+key[1:]+'.mdl')).is_file())

    def test_legacy_crlf_allowances_preserve_verified_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);gallery,receipt,key=self.fixture(root);id1=root/'id1'
            budgets=gallery/'model-budgets.txt'
            budgets.write_bytes(b'AWPB1\r\n')
            receipt['files']['model-budgets.txt']={'bytes':budgets.stat().st_size,'sha256':sha(budgets)}
            (gallery/'gallery-build.json').write_text(json.dumps(receipt))
            (id1/'gfx').mkdir(parents=True);(id1/'maps').mkdir()
            (id1/'gfx/palette.lmp').write_bytes(bytes(768))
            self.assertEqual(stage_required(gallery,id1)['status'],'passed')
            self.assertEqual((id1/'model-budgets.txt').read_bytes(),b'AWPB1\r\n')

    def test_authenticated_but_inconsistent_allowances_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);gallery,receipt,key=self.fixture(root);id1=root/'id1'
            budgets=gallery/'model-budgets.txt'
            budgets.write_bytes(b'AWPB1\ninvalid allowance\n')
            receipt['files']['model-budgets.txt']={'bytes':budgets.stat().st_size,'sha256':sha(budgets)}
            (gallery/'gallery-build.json').write_text(json.dumps(receipt))
            (id1/'gfx').mkdir(parents=True);(id1/'maps').mkdir()
            (id1/'gfx/palette.lmp').write_bytes(bytes(768))
            with self.assertRaisesRegex(ValueError,'regenerated model allowances differ'):
                stage_required(gallery,id1)

    def test_missing_model_and_incomplete_receipt_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            gallery,receipt,key=self.fixture(Path(temp))
            model=gallery/'gallery'/(key+'.mdl');model.unlink()
            with self.assertRaisesRegex(ValueError,'payload'):validate_payload(gallery,receipt)
            del receipt['files']['gallery/'+key+'.mdl']
            with self.assertRaisesRegex(ValueError,'omits'):validate_payload(gallery,receipt)

    def test_wrong_palette_and_changed_inspection_map_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            gallery,receipt,key=self.fixture(Path(temp))
            (gallery/'gfx/palette.lmp').write_bytes(bytes([1])*768)
            with self.assertRaisesRegex(ValueError,'palette'):validate_payload(gallery,receipt)
            (gallery/'gfx/palette.lmp').write_bytes(bytes(768))
            (gallery/'maps/charplane.bsp').write_bytes(b'changed-map!!')
            with self.assertRaisesRegex(ValueError,'payload'):validate_payload(gallery,receipt)

    def test_unresolved_record_remains_a_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            gallery,receipt,key=self.fixture(Path(temp));path=gallery/'gallery/catalog.txt'
            path.write_text(path.read_text().replace(key,'-'))
            with self.assertRaisesRegex(ValueError,'Unresolved'):validate_payload(gallery,receipt)

    def test_explicit_omission_removes_old_gallery_and_keeps_unrelated_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            gallery,receipt,key=self.fixture(Path(temp))
            (gallery/'maps/keep.bsp').write_bytes(b'keep')
            (gallery/'progs').mkdir();(gallery/'progs/required-npc.mdl').write_bytes(b'world NPC')
            (gallery/'model-budgets.txt').write_text('AWPB1\ngallery/m111 3 1 84 abc\nprogs/other.mdl 3 1 84 abc\n')
            report=omit_gallery(gallery)
            self.assertEqual(report['status'],'disabled')
            self.assertFalse((gallery/'gallery').exists())
            self.assertFalse((gallery/'maps/charplane.bsp').exists())
            self.assertEqual((gallery/'maps/keep.bsp').read_bytes(),b'keep')
            self.assertEqual((gallery/'progs/required-npc.mdl').read_bytes(),b'world NPC')
            self.assertIn('progs/other.mdl',(gallery/'model-budgets.txt').read_text())
            self.assertNotIn('gallery/',(gallery/'model-budgets.txt').read_text())
            self.assertIn('--no-npc-gallery',(gallery/'npc-gallery-disabled.txt').read_text())
            # The engine's friendly notice keys on this exact file name; build.json records it.
            self.assertEqual(DISABLED_MARKER,'npc-gallery-disabled.txt')
            self.assertEqual(report['marker'],'id1/npc-gallery-disabled.txt')
            engine=(Path(__file__).resolve().parents[1]/'engine/aga/src/aw_gallery.c').read_text(encoding='utf-8')
            self.assertIn('COM_FOpenFile("%s"' % DISABLED_MARKER,engine)
            self.assertIn('build without --no-npc-gallery',engine)
