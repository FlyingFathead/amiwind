import json
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
import wave

from prepare_media_assets import coverage, discover, key, lookups, convert_sound, resolve_sound, stage_catalogue


def field(tag, value):
    return tag.encode() + struct.pack('<I', len(value)) + value


def record(tag, *parts, flags=0):
    data = b''.join(parts)
    return tag.encode() + struct.pack('<III', len(data), 0, flags) + data


class MediaAssetsTests(unittest.TestCase):
    def test_all_available_audio_including_unreferenced_is_selected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in ('Sound/Vo/r/m/example.mp3', 'Sound/Fx/punch.wav', 'Sound/Cr/unreferenced.wav', 'Sound/Vo/r/m/Warnings.txt'):
                p = root/name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b'dummy')
            assets, ignored, _ = discover(root)
            self.assertEqual(len(assets), 3)
            self.assertEqual(ignored[0]['source'], 'Sound/Vo/r/m/Warnings.txt')

    def test_source_resolution_and_missing_output_are_distinct(self):
        assets = {'sound/vo/test.mp3': {}}
        self.assertEqual(resolve_sound('Vo\\TEST.wav', assets), 'sound/vo/test.mp3')
        self.assertIsNone(resolve_sound('Vo/missing.mp3', assets))
        rows = [{'category': 'voices', 'status': 'included'}, {'category': 'voices', 'status': 'missing_output'}]
        refs = [{'category': 'voices', 'requested': 'vo/missing.mp3', 'resolved': None}]*2
        self.assertEqual(coverage(rows, refs)['voices'], dict(included=1, missing_source=1, missing_output=1, available_sources=2))

    def test_lookup_includes_voice_and_effect_references_from_available_master(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            raw = record('DIAL', field('NAME', b'hello\0'))
            raw += record('INFO', field('INAM', b'line1\0'), field('SNAM', b'vo/test.mp3\0'), field('ONAM', b'actor\0'))
            raw += record('SOUN', field('NAME', b'Punch\0'), field('FNAM', b'Fx/punch.wav\0'), field('DATA', b'\xff\0\xff'))
            (root/'Morrowind.esm').write_bytes(raw)
            refs = lookups(root, {'sound/vo/test.mp3': {}, 'sound/fx/punch.wav': {}})
            self.assertEqual(refs['voiced_dialogue'][0]['resolved'], 'sound/vo/test.mp3')
            self.assertEqual(refs['sounds'][0]['id'], 'Punch')
            self.assertEqual(sum(m['status']=='missing_source' for m in refs['masters']), 2)

    def test_lookup_preserves_ordered_repeated_subrecords_and_source_positions(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            raw = record('DIAL', field('NAME', b'hello\0'))
            info_parts = (field('INAM', b'line1\0'), field('SNAM', b'vo/test.mp3\0'),
                          field('SCVR', b'first\0'), field('INTV', b'\x01\0\0\0'),
                          field('SCVR', b'second\0'), field('INTV', b'\x02\0\0\0'),
                          field('NAME', b'line text\0'))
            raw += record('INFO', *info_parts, flags=0x100)
            raw += record('SOUN', field('NAME', b'Punch\0'), field('FNAM', b'Fx/punch.wav\0'),
                          field('DATA', b'one'), field('DATA', b'two'), flags=0x40)
            (root/'Morrowind.esm').write_bytes(raw)
            refs = lookups(root, {'sound/vo/test.mp3': {}, 'sound/fx/punch.wav': {}})
            voice = refs['voiced_dialogue'][0]
            self.assertEqual((voice['master_order'], voice['record_order'], voice['record_flags']), (0, 1, 0x100))
            self.assertEqual((voice['topic'], voice['text'], voice['resolved']), ('hello', 'line text', 'sound/vo/test.mp3'))
            info = next(r for r in refs['record_provenance'] if r['record_type'] == 'INFO')
            self.assertEqual((info['master_order'], info['record_order'], info['record_flags']), (0, 1, 0x100))
            self.assertEqual([r['tag'] for r in info['subrecords']],
                             ['INAM', 'SNAM', 'SCVR', 'INTV', 'SCVR', 'INTV', 'NAME'])
            self.assertEqual([r['data_hex'] for r in info['subrecords'][2:6]],
                             ['666972737400', '01000000', '7365636f6e6400', '02000000'])
            sound = next(r for r in refs['record_provenance'] if r['record_type'] == 'SOUN')
            self.assertEqual(sound['record_order'], 2)
            self.assertEqual([r['data_hex'] for r in sound['subrecords'] if r['tag'] == 'DATA'], ['6f6e65', '74776f'])
            self.assertEqual(refs['sounds'][0]['parameters_hex'], '74776f')

    def test_deleted_records_are_separate_tombstones_with_or_without_paths(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            raw = record('DIAL', field('NAME', b'hello\0'))
            raw += record('INFO', field('INAM', b'deleted_voice\0'), field('SNAM', b'vo/test.mp3\0'), flags=0x20)
            raw += record('INFO', field('INAM', b'deleted_without_path\0'), field('DELE', b''))
            raw += record('SOUN', field('NAME', b'DeletedSound\0'), field('FNAM', b'Fx/test.wav\0'), field('DELE', b''))
            (root/'Morrowind.esm').write_bytes(raw)
            refs = lookups(root, {'sound/vo/test.mp3': {}, 'sound/fx/test.wav': {}})
            self.assertEqual(refs['voiced_dialogue'], [])
            self.assertEqual(refs['sounds'], [])
            self.assertEqual(len(refs['record_provenance']), 0)
            tombstones = refs['deletion_tombstones']
            self.assertEqual([r['record_id'] for r in tombstones],
                             ['deleted_voice', 'deleted_without_path', 'DeletedSound'])
            self.assertEqual(tombstones[0]['record_flags'], 0x20)
            self.assertEqual(tombstones[0]['sound_references'],
                             [{'requested': 'vo/test.mp3', 'resolved': 'sound/vo/test.mp3'}])
            self.assertEqual(tombstones[1]['sound_references'], [])
            self.assertEqual(tombstones[2]['sound_references'],
                             [{'requested': 'Fx/test.wav', 'resolved': 'sound/fx/test.wav'}])

    def test_deleted_dial_is_retained_and_supplies_its_own_info_context(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            raw = record('DIAL', field('NAME', b'previous_topic\0'))
            raw += record('DIAL', field('NAME', b'deleted_topic\0'), flags=0x20)
            raw += record('INFO', field('INAM', b'after_deleted_dial\0'),
                          field('SNAM', b'vo/test.mp3\0'))
            (root/'Morrowind.esm').write_bytes(raw)
            refs = lookups(root, {'sound/vo/test.mp3': {}})
            self.assertEqual([(r['id'], r['topic']) for r in refs['voiced_dialogue']],
                             [('after_deleted_dial', 'deleted_topic')])
            tombstone = refs['deletion_tombstones'][0]
            self.assertEqual((tombstone['record_type'], tombstone['record_id'],
                              tombstone['master_order'], tombstone['record_order'],
                              tombstone['record_flags'], tombstone['topic']),
                             ('DIAL', 'deleted_topic', 0, 1, 0x20, 'deleted_topic'))
            self.assertEqual(tombstone['subrecords'], [
                {'tag': 'NAME', 'data_hex': '64656c657465645f746f70696300'}])
            self.assertEqual(tombstone['sound_references'], [])

    def test_missing_master_keeps_fixed_master_order_for_later_records(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'Tribunal.esm').write_bytes(
                record('DIAL', field('NAME', b'tribunal_topic\0')) +
                record('INFO', field('INAM', b'tribunal_line\0'), field('SNAM', b'vo/t.mp3\0')))
            (root/'Bloodmoon.esm').write_bytes(
                record('DIAL', field('NAME', b'bloodmoon_topic\0')) +
                record('INFO', field('INAM', b'bloodmoon_line\0'), field('SNAM', b'vo/b.mp3\0')))
            refs = lookups(root, {'sound/vo/t.mp3': {}, 'sound/vo/b.mp3': {}})
            self.assertEqual([(r['file'], r['order'], r['status']) for r in refs['masters']], [
                ('Morrowind.esm', 0, 'missing_source'), ('Tribunal.esm', 1, 'available'),
                ('Bloodmoon.esm', 2, 'available')])
            self.assertEqual([(r['master'], r['master_order'], r['record_order']) for r in refs['voiced_dialogue']], [
                ('Tribunal.esm', 1, 1), ('Bloodmoon.esm', 2, 1)])

    def test_unsafe_path_rejected(self):
        for path in ('/absolute.wav', '../escape.wav', 'sound/../escape.wav', 'C:/private.wav'):
            with self.assertRaises(ValueError):key(path)

    def test_actual_ffmpeg_conversion_is_validated(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); source=root/'source.wav'
            with wave.open(str(source), 'wb') as f:
                f.setparams((1, 2, 22050, 0, 'NONE', 'not compressed'))
                f.writeframes(struct.pack('<h', 3000)*2205)
            result=convert_sound(({'source':'sound/fx/punch.wav','file':str(source)},root/'out','ffmpeg'))
            self.assertEqual(result['status'],'included')
            self.assertTrue((root/'out'/result['path']).is_file())
            self.assertEqual(result['rate'],11025)

    def test_decoder_failure_never_claims_included(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); source=root/'bad.mp3'; source.write_bytes(b'not audio')
            result=convert_sound(({'source':'sound/vo/bad.mp3','file':str(source)},root/'out','ffmpeg'))
            self.assertEqual(result['status'],'missing_output')

    def staged_fixture(self, root):
        media=root/'converted'; payload=root/'payload'
        media.mkdir();payload.mkdir()
        (media/'id1/sound/pool').mkdir(parents=True)
        source=media/'id1/sound/pool/a1.wav';source.write_bytes(b'validated converted sound')
        sound={'source':'sound/fx/test.wav','category':'effects','status':'included',
               'path':'sound/pool/a1.wav','sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
        refs={'sounds':[{'requested':'Fx/test.wav','resolved':sound['source'],'category':'effects'}],
              'voiced_dialogue':[]}
        report={'format':'AWMEDIA1','entries':[sound],'lookups':refs}
        (media/'media-coverage.json').write_text(json.dumps(report))
        original=root/'title.mp3';original.write_bytes(b'original music')
        (media/'source-inventory.json').write_text(json.dumps({'assets':{
            'music/special/title.mp3':{'file':str(original)}}}))
        (payload/'music').mkdir();(payload/'music/track00.mws').write_bytes(b'validated music')
        manifest={'tracks':[{'source':'Music/Special/Title.mp3','file':'track00.mws',
            'source_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),
            'sha256':hashlib.sha256(b'validated music').hexdigest()}]}
        return media,payload,manifest

    def test_staging_reconciles_all_output_and_original_music_digests(self):
        with tempfile.TemporaryDirectory() as d:
            media,payload,music=self.staged_fixture(Path(d))
            result=stage_catalogue(media,payload,music)
            self.assertEqual(result['categories']['effects']['included'],1)
            self.assertEqual(result['categories']['music']['included'],1)
            self.assertEqual(result['lookups']['sounds'][0]['output'],'sound/pool/a1.wav')
            self.assertEqual((payload/'sound/pool/a1.wav').read_bytes(),b'validated converted sound')

    def test_changed_missing_or_conflicting_output_never_claims_inclusion(self):
        for failure in ('changed','missing','conflict'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as d:
                media,payload,music=self.staged_fixture(Path(d))
                source=media/'id1/sound/pool/a1.wav'
                if failure=='changed':source.write_bytes(b'corrupt')
                elif failure=='missing':source.unlink()
                else:
                    dest=payload/'sound/pool/a1.wav';dest.parent.mkdir(parents=True);dest.write_bytes(b'preserve')
                result=stage_catalogue(media,payload,music)
                self.assertEqual(result['categories']['effects']['included'],0)
                self.assertEqual(result['categories']['effects']['missing_output'],1)
                self.assertIsNone(result['lookups']['sounds'][0]['output'])
                if failure=='conflict':self.assertEqual(dest.read_bytes(),b'preserve')

    def test_changed_original_music_is_not_matched_to_a_stale_conversion(self):
        with tempfile.TemporaryDirectory() as d:
            media,payload,music=self.staged_fixture(Path(d))
            (Path(d)/'title.mp3').write_bytes(b'new original')
            result=stage_catalogue(media,payload,music)
            self.assertEqual(result['categories']['music']['missing_output'],1)

    def test_existing_intro_requires_matching_provenance_and_is_preserved(self):
        from prepare_video import HEADER, RATE, FPS
        with tempfile.TemporaryDirectory() as d:
            media,payload,music=self.staged_fixture(Path(d))
            (media/'id1/intro').mkdir();(payload/'intro').mkdir()
            samples=(RATE+FPS-1)//FPS
            original=HEADER.pack(b'AWV1',160,100,FPS,RATE,1,samples)+bytes(768+16000+samples)
            retained=HEADER.pack(b'AWV1',320,200,FPS,RATE,1,samples)+bytes(768+64000+samples)
            (media/'id1/intro/mw_intro.awv').write_bytes(original)
            (payload/'intro/mw_intro.awv').write_bytes(retained)
            report=json.loads((media/'media-coverage.json').read_text())
            report['entries'].append({'category':'videos','source':'video/mw_intro.bik','id':15,
                'name':'mw_intro','path':'intro/mw_intro.awv','status':'included',
                'source_sha256':'a'*64,'sha256':hashlib.sha256(original).hexdigest()})
            (media/'media-coverage.json').write_text(json.dumps(report))
            result=stage_catalogue(media,payload,music,{'source_sha256':'a'*64})
            self.assertEqual(result['categories']['videos']['included'],1)
            self.assertEqual((payload/'intro/mw_intro.awv').read_bytes(),retained)
            self.assertEqual(result['entries'][1]['sha256'],hashlib.sha256(retained).hexdigest())
            result=stage_catalogue(media,payload,music,{'source_sha256':'b'*64})
            self.assertEqual(result['categories']['videos']['missing_output'],1)

    def test_normal_aga_pipeline_and_recovery_both_wait_for_complete_media(self):
        import build
        from build_parallel import stage_dependencies
        from recover_image import recovery_commands
        args=build.parser().parse_args([])
        args.data_files=Path('/data');args.sdk=Path('/sdk')
        tools={name:'/tools/'+name for name in ('ffmpeg','qbsp','vis','light','qcc','xdftool','rdbtool')}
        steps=build.commands(args,tools,Path('/new-run'))
        commands=dict(steps)
        self.assertIn('media',stage_dependencies(steps)['image'])
        self.assertEqual(stage_dependencies(steps)['media'],())
        self.assertEqual(commands['image'][commands['image'].index('--media')+1],'/new-run/media')
        recovery=recovery_commands(steps,Path('/previous'),Path('/new-run'))
        names=[name for name,_ in recovery]
        self.assertLess(names.index('media'),names.index('image'))


if __name__=='__main__':unittest.main()
