"""The Halloween scene (docs/HALLOWEEN.md): dbg halloween, its cast file, the beat and the user's own soundtrack."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(Path(__file__).resolve().parent)]
import numpy as np  # noqa: E402
import halloween_cast as hc  # noqa: E402
import test_aga_native_source as native  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']


def clicks(bpm, seconds=40, rate=11025):
    """A click track: a short decaying noise burst on every beat, a softer one between (an off-beat)."""
    rng = np.random.default_rng(7)
    out = np.zeros(int((seconds + 1) * rate))
    burst = rng.standard_normal(400) * np.exp(-np.arange(400) / 60)
    beat = 60 / bpm
    t = 0.0
    while t < seconds - .1:
        i = int(t * rate)
        out[i:i + 400] += burst
        j = int((t + beat / 2) * rate)
        out[j:j + 400] += .3 * burst
        t += beat
    return out


class Rules(unittest.TestCase):
    def test_parser_cast_choreography_and_layout(self):
        native.NativeSourceTests().compile_run('aga_halloween_test.c', [SRC / 'aw_halloween_rules.c', SRC / 'mathlib.c'],
                                               cflags=UBSAN)
        # the engine's FPU-safe forms only (a 68040 does not implement libm's sin, cos and atan2 instructions)
        # (gate 4053: the engine step found libm's sin under the camera director)
        for name in ('aw_halloween_rules.c', 'aw_halloween.c'):
            self.assertNotRegex((SRC / name).read_text(encoding='utf-8'), r'[^_A-Za-z](sin|cos|tan|atan2|pow|exp)\(')

    def test_default_beat_is_the_same_number_in_the_builder_and_the_engine(self):
        header = (SRC / 'aw_halloween.h').read_text(encoding='utf-8')
        self.assertIn('#define AW_HALLOWEEN_BPM10\t\t%d' % round(hc.DEFAULT_BPM * 10), header)
        # the greeting, word for word: two centred lines
        self.assertIn('#define AW_HALLOWEEN_TEXT1\t\t"HAPPY HALLOWEEN"', header)
        self.assertIn('#define AW_HALLOWEEN_TEXT2\t\t"FROM AMIWIND"', header)
        engine = (SRC / 'aw_halloween.c').read_text(encoding='utf-8')
        self.assertIn('x=((int)vid.width-w)/2;y=((int)vid.height-h)/2;', engine)    # the box in the exact centre
        self.assertIn('if(hw.fps)AW_FpsCorner();', engine)                          # the dbg fps counter
        self.assertIn('AW_SmallString(2,vid.height-7,line);',                       # FPS small, bottom left
                      (SRC / 'aw_hud.c').read_text(encoding='utf-8'))
        self.assertIn('static void command(void) {command_with(0);}', engine)       # the show: FPS off
        self.assertIn('static void command_test(void) {command_with(1);}', engine)  # halloweentest: FPS on
        self.assertIn('AW_HalloweenCamera(r_refdef.vieworg,r_refdef.viewangles);',
                      (SRC / 'view.c').read_text(encoding='utf-8'))
        # the greeting alone on black and in silence first, the song with the first beat after it
        self.assertIn('hw.intro=!bench;', engine)
        # the custom OST player (CUSTOM-OST-SLOT-53): the playlist held for the whole scene, the custom track with the
        # first beat, a music check line; never a playlist track
        self.assertIn('AW_MusicCustomHold();hw.music_held=1;', engine)
        self.assertIn('AW_MusicCustomPlay();', engine)
        self.assertIn('Halloween music playing: track %02ld (custom)', engine)
        music = (SRC / 'aw_music.c').read_text(encoding='utf-8')
        self.assertIn('if(scene_hold)return 0;', music)          # no playlist advance while the custom player holds
        self.assertIn('id=manual_lookup("custom",&g);', music)
        self.assertIn('Cmd_AddCommand("aw_music_custom",music_custom);', music)
        # the dancers on their own dance, said per cast member; the fog kept; the sunset hour held
        self.assertIn('(her own dance, anim_dancingGirl)', engine)
        self.assertIn('Cvar_SetValue("aw_fog",fog);', engine)
        self.assertIn('static void hold_sunset(void) {AW_ClockSetTime(SUNSET_HOUR,0);}', engine)
        # photo mode's own UI hidden by its config flag while the scene runs
        self.assertIn('Cvar_SetValue("aw_photomode_ui",0);', engine)
        self.assertIn('static cvar_t photo_ui={"aw_photomode_ui","1",true};', (SRC / 'aw_photo.c').read_text(encoding='utf-8'))
        # the cast on one floor, settled as residents are, with a ground check printed
        self.assertIn('AW_NPCFloor(e);', engine)
        self.assertIn('ground check: %d of %d feet on the stage floor', engine)
        # the cast whoosh on the spellcast group's own release keys (the stage too)
        self.assertIn('AW_SkelKeyFrame(t,group,keys[k])', engine)
        self.assertIn('AW_SkelCastSound(e,f->table,f->group,was,(int)e->v.frame);',
                      (SRC / 'aw_animkit.c').read_text(encoding='utf-8'))
        # aw bench halloween, the standard benchmark, and the aw prefix
        self.assertIn('Cmd_AddCommand("aw_bench",bench_command);', engine)
        self.assertIn('Cmd_AddCommand("aw",dispatch);', (SRC / 'aw_console.c').read_text(encoding='utf-8'))
        self.assertIn('#define AW_HALLOWEEN_BOX_SECONDS\t5\t', header)


class Cast(unittest.TestCase):
    def test_cast_file_round_trip_and_checks(self):
        rows = [('lead', hc.DAGOTH_MODEL, 'Dagoth Ur'), ('dancer', 'progs/a_e5192b0aca1d.mdl', 'Marelle'),
                ('skeleton', hc.SKELETON_MODEL, 'Skeleton')]
        text = hc.cast_text(rows, 132.4, False)
        self.assertTrue(text.startswith('AWHW1 1324 0\n'))
        bpm, soundtrack, back = hc.read_cast(text)
        self.assertEqual((bpm, soundtrack), (132.4, False))
        self.assertEqual(back[0], ('lead', hc.DAGOTH_MODEL, 'Dagoth_Ur'))
        for bad in ([('ghost', 'progs/x.mdl', 'X')], [('lead', 'maps/x.bsp', 'X')]):
            with self.assertRaises(ValueError):
                hc.cast_text(bad, 132.4, False)
        with self.assertRaises(ValueError):
            hc.cast_text(rows, 10, False)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / hc.CAST_FILE).write_text(text, encoding='ascii')
            hc.set_beat(d, 120.0)
            self.assertEqual(hc.read_cast((Path(d) / hc.CAST_FILE).read_text())[:2], (120.0, True))
            self.assertEqual(hc.read_preroll((Path(d) / hc.CAST_FILE).read_text()), 0)
            # the soundtrack's pre-roll (its leading silence) on the first line
            hc.set_beat(d, 120.0, 1068)
            written = (Path(d) / hc.CAST_FILE).read_text()
            self.assertTrue(written.startswith('AWHW1 1200 1 1068\n'))
            self.assertEqual(hc.read_cast(written)[:2], (120.0, True))
            self.assertEqual(hc.read_preroll(written), 1068)
        self.assertNotIn(' 500', hc.cast_text(rows, 132.4, False, 500).splitlines()[0])   # none without a track
        with self.assertRaises(ValueError):
            hc.cast_text(rows, 132.4, True, hc.MAX_PREROLL_MS + 1)

    def test_leading_silence_of_a_converted_track(self):
        from prepare_music import RATE
        rng = np.random.default_rng(3)
        silent = int(1.068 * RATE)
        # 8-bit stereo as the image plays it: dithered silence (+-1 step), then a tone
        quiet = rng.integers(-1, 2, size=silent * 2)
        tone = (60 * np.sin(np.arange(RATE) * 2 * np.pi * 440 / RATE)).repeat(2)
        pcm = np.concatenate((quiet, tone)).astype(np.int8).tobytes()
        self.assertAlmostEqual(hc.leading_silence(pcm, RATE), 1068, delta=11)
        self.assertEqual(hc.leading_silence(tone.astype(np.int8).tobytes(), RATE), 0)

    def test_tempo_of_a_click_track(self):
        for bpm in (132.4, 100.0, 150.0):
            self.assertAlmostEqual(hc.tempo(clicks(bpm), 11025), bpm, delta=0.6)

    def test_the_rig_check_and_tables(self):
        # the first check (the maintainer, 26 October 2026): the skeleton creature rides the humanoid table only when
        # every bone of the table is in its rig; Dagoth Ur gets his own table
        source = (ROOT / 'tools/halloween_cast.py').read_text(encoding='utf-8')
        self.assertIn("The skeleton creature lacks bones of the humanoid table", source)
        self.assertEqual(hc.DAGOTH_TABLE, 'progs/dagothur.awsk')
        self.assertLess(len(hc.DAGOTH_TABLE), 32)       # aw_skel.h AW_SKEL_TABLE_NAME


class Soundtrack(unittest.TestCase):
    @unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg')
    def test_a_user_file_becomes_one_more_special_track(self):
        from prepare_music import unpack_stream
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            music = d / 'music'
            music.mkdir()
            manifest = {'format': 'MWA1', 'tracks': [{'file': 'track00.mws', 'source': 'Explore/a.mp3', 'seconds': 1,
                                                      'bytes': 1, 'sha256': '0' * 64}]}
            (music / 'soundtrack.json').write_text(json.dumps(manifest))
            wav = d / 'mine.wav'
            pcm = (clicks(120.0, 20) * 8000).clip(-32000, 32000).astype('<i2')
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 's16le', '-ar', '11025', '-ac', '1', '-i', 'pipe:0', str(wav)],
                           input=pcm.tobytes(), check=True)
            record, bpm = hc.soundtrack(wav, music)
            self.assertEqual(record['file'], 'track01.mws')
            self.assertEqual(record['source'], hc.SOUNDTRACK_SOURCE)
            self.assertTrue(unpack_stream((music / 'track01.mws').read_bytes()))
            self.assertAlmostEqual(bpm, 120.0, delta=0.6)
            self.assertLessEqual(record['leading_silence_ms'], 20)     # the click track starts at once
            written = json.loads((music / 'soundtrack.json').read_text())
            self.assertEqual(len(written['tracks']), 2)
            from music_catalogue import build_catalogue
            content, _ = build_catalogue(written)
            self.assertIn(b'01 2 custom\n', content)      # the custom OST player's track (aw music custom play)
            with self.assertRaises(ValueError):
                hc.soundtrack(wav, music)          # once only

    def test_the_repository_carries_no_audio(self):
        # the release file list is every file the repository ships
        shipped = json.loads((ROOT / 'tools/release-files.json').read_text(encoding='utf-8'))
        self.assertFalse([p for p in shipped if p.lower().endswith(('.mp3', '.mp4', '.mws', '.ogg', '.flac', '.wav'))])
        self.assertFalse([p for p in shipped if 'halloween' in p.lower()
                          and not p.endswith(('.py', '.c', '.h', '.md', '.json'))])


class Wiring(unittest.TestCase):
    def test_command_alias_preset_and_hooks(self):
        catalogue = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8')
        self.assertRegex(catalogue, r'(?m)^PLAYTESTING\|halloween\|aw_halloween\|\[dagoth / skeletons / bench \[skeletons\] '
                                    r'/ fps on/off / camera wide/director / stop / status\]')
        self.assertRegex(catalogue, r'(?m)^PLAYTESTING\|halloweentest\|aw_halloweentest\|')
        self.assertRegex(catalogue, r'(?m)^PLAYTESTING\|bench\|aw_bench\|\[halloween \[skeletons\]\]')
        self.assertIn('PLAYTESTING|halloweenbench|aw_bench|same as bench halloween', catalogue)
        self.assertRegex(catalogue, r'(?m)^VIDEO\|photomode ui\|aw_photomode_ui\|')
        self.assertIn('Cmd_AddCommand("aw_halloween",command);', (SRC / 'aw_halloween.c').read_text(encoding='utf-8'))
        self.assertIn('Cmd_AddCommand("aw_halloweentest",command_test);', (SRC / 'aw_halloween.c').read_text(encoding='utf-8'))
        self.assertIn('AW_HalloweenInit();', (SRC / 'aw_debug.c').read_text(encoding='utf-8'))
        self.assertIn('AW_HalloweenTick();', (SRC / 'host.c').read_text(encoding='utf-8'))
        self.assertIn('AW_HalloweenDraw();', (SRC / 'screen.c').read_text(encoding='utf-8'))
        self.assertIn('aw_halloween_rules.c aw_halloween.c', (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8'))
        import miniwind_presets
        row = miniwind_presets.find('halloween')
        self.assertEqual(row['start'], 'balmora')
        self.assertEqual(row['boot_commands'], ['dbg halloween'])
        self.assertIs(row['halloween'], True)
        self.assertNotIn('halloween', miniwind_presets.find('anim-stage'))     # only its own preset has the field

    def test_catalogue_lines_fit_the_engine_reader(self):
        # gate 4049: a 524-byte catalogue line broke every dbg command (aw_console.c DEBUG_LINE); the page tool
        # (pregate) now refuses it first
        import console_commands_doc as doc
        doc.entries((ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8'))
        with self.assertRaisesRegex(ValueError, 'the engine reads at most'):
            doc.entries('AWDC1\nPLAYTESTING|x|aw_x|' + 'y' * 400 + '\n')

    def test_build_options(self):
        import build
        args = build.parser().parse_args(['--miniwind-halloween'])
        self.assertEqual(args.miniwind_preset, 'halloween')
        args = build.parser().parse_args(['--miniwind', '--halloween', '--halloween-soundtrack', 'x.mp4'])
        self.assertTrue(args.halloween)
        self.assertEqual(args.custom_ost, 'x.mp4')          # the old name is an alias of the custom OST slot
        self.assertEqual(hc.image_args(args), ['--halloween', '--custom-ost', 'x.mp4'])
        args = build.parser().parse_args(['--custom-ost', 'y.mp3'])
        self.assertEqual(hc.custom_ost(args), 'y.mp3')
        text = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        self.assertIn('halloween_cast.check(args, p)', text)       # before any stage runs

        class Exit(Exception):
            pass

        class P:
            def exit(self, code, text):
                raise Exit(text)
        for argv, said in ((['--custom-ost', '/no/such/file'], 'no such file'),):
            with self.assertRaisesRegex(Exit, said):
                hc.check(build.parser().parse_args(argv), P())
        hc.check(build.parser().parse_args(['--miniwind', '--halloween']), P())
        # the image step builds the cast in a --halloween image: every full-world build and the MiniWind preset
        aga = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("if getattr(args,'halloween',False):", aga)
        self.assertIn('halloween_report=halloween_cast.prepare(args.data_files,boot/\'id1\',jobs=jobs)', aga)

    def test_a_full_build_plans_the_cast_and_the_flag_leaves_it_out(self):
        # HALLOWEEN-SCENE-53 / BENCH-NO-STANDARD-DEMO-48 (v0.0.54): the cast is in every full-world image, so
        # aw bench halloween works in release images; --halloween-cast off leaves it out. Imperative 19: the option
        # reaches the image step alone, so no other stage's command (and key) changes.
        from test_actor_library import steps
        default = dict(steps())
        self.assertEqual(default, dict(steps('--halloween-cast', 'on')))
        left_out = dict(steps('--halloween-cast', 'off'))
        self.assertEqual(default['image'].count('--halloween'), 1)
        self.assertNotIn('--halloween', left_out['image'])
        self.assertEqual(sorted(default), sorted(left_out))
        changed = sorted(n for n in default if [str(x) for x in default[n]] != [str(x) for x in left_out[n]])
        self.assertEqual(changed, ['image'])
        # no song by default: the custom OST slot stays empty
        self.assertNotIn('--custom-ost', default['image'])
        import build
        self.assertEqual(hc.full_image_args(build.parser().parse_args([])), ['--halloween'])
        self.assertEqual(hc.full_image_args(build.parser().parse_args(['--halloween-cast', 'off'])), [])

    def test_miniwind_keeps_its_own_choice(self):
        # a MiniWind build takes the cast only with --halloween (its preset): never twice, never by default
        from test_actor_library import steps
        plain = dict(steps('--miniwind', '--miniwind-scope', 'exterior'))
        cast = dict(steps('--miniwind', '--miniwind-scope', 'exterior', '--halloween'))
        self.assertNotIn('--halloween', plain['image'])
        self.assertEqual(cast['image'].count('--halloween'), 1)

    def test_dancers_have_the_casts_own_names_and_shared_files_are_kept(self):
        # a full image holds Desele's dancers as Suran residents (progs/a_<hash>.mdl, installed after the cast):
        # the cast's dancers take names of their own; a shared file the image holds is kept, the cast's own replaced
        import hashlib
        name = hc.dancer_model('breton dancer girl')
        self.assertEqual(name, 'progs/hw_' + hashlib.sha256(b'breton dancer girl').hexdigest()[:12] + '.mdl')
        self.assertLess(len(name), 64)
        with tempfile.TemporaryDirectory() as tmp:
            stage, id1 = Path(tmp) / 'stage', Path(tmp) / 'id1'
            for root, files in ((stage, {'progs/humanoid.awsk': b'new', name: b'cast', hc.CAST_FILE: b'AWHW1',
                                         'sound/aw/cast/bolt.wav': b'w', 'progs/items/x.mdl': b'item2'}),
                                (id1, {'progs/humanoid.awsk': b'old', name: b'stale', 'progs/items/x.mdl': b'item'})):
                for path, raw in files.items():
                    (root / path).parent.mkdir(parents=True, exist_ok=True)
                    (root / path).write_bytes(raw)
            written, kept = hc.install(stage, id1)
            self.assertEqual(sorted(kept), ['progs/humanoid.awsk', 'progs/items/x.mdl'])
            self.assertEqual(sorted(written), sorted([name, hc.CAST_FILE, 'sound/aw/cast/bolt.wav']))
            self.assertEqual((id1 / 'progs/humanoid.awsk').read_bytes(), b'old')
            self.assertEqual((id1 / name).read_bytes(), b'cast')

    def test_members_are_made_side_by_side(self):
        # basic 6: the v0.0.53 Halloween builds made the cast on one core for about 2 minutes; the members now go to
        # the builder's worker pool, and a member other than the skeletons is left out with its reason
        text = (ROOT / 'tools/halloween_cast.py').read_text(encoding='utf-8')
        self.assertIn('in_order_map(member, items,', text)
        kind, identifier, error = hc.member(('dancer', (None, None, {'id': 'x'}, None, 'ffmpeg', {})))
        self.assertEqual((kind, identifier), ('dancer', 'x'))
        self.assertTrue(error)

    def test_custom_ost_slot_empty_without_setting_and_only_the_image_step_takes_it(self):
        # CUSTOM-OST-SLOT-53: without the option or the machine setting the slot stays empty; the setting reaches the
        # image step only (it keys no other stage: a VERSION-only change rebuilds nothing new because of it)
        import os
        import build
        old = os.environ.pop(hc.CUSTOM_OST_SETTING, None)
        try:
            self.assertIsNone(hc.custom_ost(build.parser().parse_args([])))
            os.environ[hc.CUSTOM_OST_SETTING] = 'z.flac'
            self.assertEqual(hc.custom_ost(build.parser().parse_args([])), 'z.flac')
        finally:
            os.environ.pop(hc.CUSTOM_OST_SETTING, None)
            if old is not None:
                os.environ[hc.CUSTOM_OST_SETTING] = old
        from test_actor_library import steps
        plain = dict(steps('--miniwind', '--miniwind-scope', 'exterior'))
        slot = dict(steps('--miniwind', '--miniwind-scope', 'exterior', '--custom-ost', __file__))
        changed = sorted(name for name in plain if [str(x) for x in plain[name]] != [str(x) for x in slot.get(name, [])])
        self.assertEqual(changed, ['image'])
        # the image step packs it in the music block, after every earlier stage
        aga = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn('track,bpm=halloween_cast.soundtrack(halloween_cast.custom_ost(args),target)', aga)


if __name__ == '__main__':
    unittest.main()
