"""Recorded-stage exception (BUILD-SEYDA-REGEN-30) is honoured byte for byte.

BUILD-SEYDA-RECORDED-REWRITTEN-32: v0.0.32-dev1 installed the recorded v0.0.31
Seyda Neen maps, then the actor ground bake rewrote one placement in 64 of them
and the town flora step copied sn029 over seyda.bsp. These tests keep a map
under the exception unchanged through the image passes that touch maps; the one
named difference (owner option A) is seyda.bsp as the fallback region alias.
"""
import ast
import contextlib
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
import recorded_stage  # noqa: E402  (tools/ is on the suite path)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def recorded_tree(root, maps=('sn000.bsp', 'sn001.bsp', 'intro_docks.bsp', 'sncourt.bsp', 'seyda.bsp'), alias=True):
    """A small recorded folder and a pin that matches it (seyda.bsp shipped as the sn000 alias)."""
    id1 = root / 'recorded/id1'
    (id1 / 'maps').mkdir(parents=True)
    files = {}
    for name in maps:
        files['maps/' + name] = ('recorded ' + name).encode()
    files['seyda-regions.txt'] = b'AWBR1 0\n'
    files['seyda-regions.json'] = json.dumps({'fallback_alias': 'sn000', 'regions': []}).encode()
    for name, raw in files.items():
        (id1 / name).write_bytes(raw)
    pin = root / 'pin.json'
    record = {'format': 'AmiWind recorded stage pin 1', 'exception': 'BUILD-SEYDA-REGEN-30', 'decision': 'test',
              'files': [dict(file=n, bytes=len(r), sha256=sha(r)) for n, r in sorted(files.items())]}
    if alias:
        record['aliases'] = {'maps/seyda.bsp': {'source': 'maps/sn000.bsp', 'reason': 'test: fallback region alias'}}
    pin.write_text(json.dumps(record), encoding='utf-8')
    return root / 'recorded', pin, files


class PinTests(unittest.TestCase):
    def test_shipped_pin_is_the_v031_seyda_set_with_the_owner_alias(self):
        record, files, aliases = recorded_stage.load_pin()
        maps = sorted(name[5:] for name in files if name.startswith('maps/'))
        self.assertEqual(maps, sorted([f'sn{i:03d}.bsp' for i in range(64)] +
                                      ['intro_docks.bsp', 'sncourt.bsp', 'seyda.bsp']))
        self.assertEqual(set(files) - {'maps/' + m for m in maps}, {'seyda-regions.txt', 'seyda-regions.json'})
        # v0.0.31's seyda.bsp is the complete town; option A (owner, 8 October 2026)
        # ships the fallback region alias instead, the one named difference.
        self.assertEqual(files['maps/seyda.bsp'][0], 4411968)
        self.assertEqual(aliases, {'maps/seyda.bsp': 'maps/sn029.bsp'})
        self.assertIn('Owner decision', record['aliases']['maps/seyda.bsp']['reason'])
        ship = recorded_stage.shipped(files, aliases)
        self.assertEqual(len(ship), 69)
        self.assertEqual([n for n, s in ship.items() if n != s], ['maps/seyda.bsp'])
        self.assertEqual(record['exception'], 'BUILD-SEYDA-REGEN-30')

    def test_source_must_match_the_pin_exactly(self):
        with tempfile.TemporaryDirectory() as temp:
            recorded, pin, _ = recorded_tree(Path(temp))
            recorded_stage.check_source(recorded, pin)
            (recorded / 'id1/maps/sn001.bsp').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'differ'):
                recorded_stage.check_source(recorded, pin)
            (recorded / 'id1/maps/sn001.bsp').unlink()
            with self.assertRaisesRegex(ValueError, 'missing maps/sn001.bsp'):
                recorded_stage.check_source(recorded, pin)
            (recorded / 'id1/maps/sn001.bsp').write_bytes(b'recorded sn001.bsp')
            (recorded / 'id1/maps/sn002.bsp').write_bytes(b'extra')
            with self.assertRaisesRegex(ValueError, 'unexpected maps/sn002.bsp'):
                recorded_stage.check_source(recorded, pin)
            (recorded / 'id1/maps/sn002.bsp').unlink()
            # The aliased recorded file is optional, but if present it must be the pinned one.
            (recorded / 'id1/maps/seyda.bsp').write_bytes(b'other town')
            with self.assertRaisesRegex(ValueError, 'differ.*maps/seyda.bsp'):
                recorded_stage.check_source(recorded, pin)
            (recorded / 'id1/maps/seyda.bsp').unlink()
            recorded_stage.check_source(recorded, pin)

    def test_alias_must_be_the_recorded_fallback_region(self):
        with tempfile.TemporaryDirectory() as temp:
            recorded, pin, _ = recorded_tree(Path(temp))
            record = json.loads(pin.read_text(encoding='utf-8'))
            record['aliases']['maps/seyda.bsp']['source'] = 'maps/sn001.bsp'
            pin.write_text(json.dumps(record), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'fallback region sn000'):
                recorded_stage.install(recorded, Path(temp) / 'id1/maps', work_dir=Path(temp) / 'w', pin=pin)
            del record['aliases']['maps/seyda.bsp']['reason']
            pin.write_text(json.dumps(record), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Invalid recorded-stage alias'):
                recorded_stage.load_pin(pin)


class InstallAndCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.recorded, self.pin, self.files = recorded_tree(root)
        self.id1 = root / 'image/boot/id1'
        (self.id1 / 'maps').mkdir(parents=True)
        (self.id1 / 'maps/seyda.bsp').write_bytes(b'complete converted town')
        (self.id1 / 'maps/bm000.bsp').write_bytes(b'balmora')
        self.work = root / 'image/bounded-seyda'
        with contextlib.redirect_stdout(io.StringIO()):
            self.report = recorded_stage.install(self.recorded, self.id1 / 'maps', work_dir=self.work, pin=self.pin)

    def test_install_replaces_the_region_conversion_outputs(self):
        self.assertEqual(self.report['fallback_alias'], 'sn000')
        for name, raw in self.files.items():
            expected = self.files['maps/sn000.bsp'] if name == 'maps/seyda.bsp' else raw
            self.assertEqual((self.id1 / name).read_bytes(), expected, name)
        receipt = recorded_stage.load_receipt(self.work)
        row = next(r for r in receipt['files'] if r['file'] == 'maps/seyda.bsp')
        self.assertEqual(row['replaced_sha256'], sha(b'complete converted town'))
        self.assertEqual((row['source'], row['sha256']), ('maps/sn000.bsp', sha(self.files['maps/sn000.bsp'])))
        self.assertEqual(recorded_stage.frozen_maps(self.work),
                         {'sn000.bsp', 'sn001.bsp', 'intro_docks.bsp', 'sncourt.bsp', 'seyda.bsp'})

    def test_every_pass_check_stops_on_any_rewrite(self):
        (self.id1 / 'maps/bm000.bsp').write_bytes(b'balmora rewritten')  # not recorded: allowed
        recorded_stage.check(self.id1, self.work, 'first pass')
        # dev1: a later pass rewrote one placement in the recorded region maps.
        (self.id1 / 'maps/sn001.bsp').write_bytes(b'recorded sn001.bsp, rebaked')
        with self.assertRaisesRegex(ValueError, 'broken by actor bake: 1 .*maps/sn001.bsp'):
            recorded_stage.check(self.id1, self.work, 'actor bake')
        (self.id1 / 'maps/sn001.bsp').write_bytes(self.files['maps/sn001.bsp'])
        # The alias stays the fallback region: the complete town back in its place is a change too.
        (self.id1 / 'maps/seyda.bsp').write_bytes(self.files['maps/seyda.bsp'])
        with self.assertRaisesRegex(ValueError, 'broken by town copy: 1 .*maps/seyda.bsp'):
            recorded_stage.check(self.id1, self.work, 'town copy')
        (self.id1 / 'maps/seyda.bsp').unlink()
        with self.assertRaisesRegex(ValueError, 'broken by removal'):
            recorded_stage.check(self.id1, self.work, 'removal')
        checks = recorded_stage.load_receipt(self.work)['checks']
        self.assertEqual(checks, [dict(stage='first pass', files=7, status='byte-identical')])

    def test_check_without_a_recorded_stage_is_a_no_op(self):
        self.assertIsNone(recorded_stage.check(self.id1, Path(self.temp.name) / 'none', 'pass'))
        self.assertEqual(recorded_stage.frozen_maps(Path(self.temp.name) / 'none'), frozenset())

    def test_recorded_town_flora_is_kept_and_its_sprites_installed(self):
        sprite = 'progs/aw_flora/f_0123456789abcdef.spr'
        raw = b'map with "model" "' + sprite.encode() + b'"'
        files = dict(self.files, **{'maps/sn000.bsp': raw})
        (self.recorded / 'id1/maps/sn000.bsp').write_bytes(raw)
        (self.id1 / 'maps/sn000.bsp').write_bytes(raw)
        flora = Path(self.temp.name) / 'flora'
        (flora / 'progs/aw_flora').mkdir(parents=True)
        (flora / sprite).write_bytes(b'sprite')
        with contextlib.redirect_stdout(io.StringIO()):
            result = recorded_stage.keep_town_flora(self.id1.parent, flora, ['sn000.bsp', 'sn001.bsp'])
        self.assertEqual((result['recorded_maps'], result['recorded_maps_with_flora']), (2, 1))
        self.assertEqual((self.id1 / sprite).read_bytes(), b'sprite')
        for name, value in files.items():
            if name.startswith('maps/') and name != 'maps/seyda.bsp':
                self.assertEqual((self.id1 / name).read_bytes(), value)


class ActorPassTests(unittest.TestCase):
    """The real annotate/bake passes leave excluded (recorded) maps untouched."""

    def test_ground_bake_skips_recorded_maps(self):
        from actor_grounding import annotate, bake_ground
        from test_actor_ground import actor, alias, bsp
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()), \
                patch('actor_grounding.records', return_value=[('CELL', 0, b'')]), \
                patch('actor_grounding.subrecords', return_value=[]), \
                patch('actor_grounding.cell_data', return_value={'refs': [
                    {'number': 1, 'id': 'heddvild'}, {'number': 2, 'id': 'heddvild'}]}):
            id1 = Path(temp); maps = id1 / 'maps'; maps.mkdir()
            (id1 / 'progs').mkdir(); (id1 / 'progs/test.mdl').write_bytes(alias(4))
            (id1 / 'master.esm').write_bytes(b'')
            (maps / 'room.bsp').write_bytes(bsp(actor(ref='1')))
            (maps / 'kept.bsp').write_bytes(bsp(actor(ref='2')))
            before = {p.name: p.read_bytes() for p in maps.glob('*.bsp')}
            annotate(maps, id1 / 'master.esm', jobs=2, exclude={'kept.bsp'})
            report = bake_ground(maps, jobs=2, exclude={'kept.bsp'})
            self.assertEqual([row['reference'] for row in report], ['1'])
            self.assertEqual((maps / 'kept.bsp').read_bytes(), before['kept.bsp'])
            self.assertNotEqual((maps / 'room.bsp').read_bytes(), before['room.bsp'])


class ImageWiringTests(unittest.TestCase):
    """Static order of build_aga.py: every map-writing pass is followed by a check."""

    def calls(self, function):
        tree = ast.parse((ROOT / 'tools/build_aga.py').read_text(encoding='utf-8'))
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function)
        calls = [c for c in ast.walk(node) if isinstance(c, ast.Call)]
        name = lambda c: c.func.id if isinstance(c.func, ast.Name) else c.func.attr if isinstance(c.func, ast.Attribute) else ''
        return sorted(((c.lineno, c.col_offset, name(c), c) for c in calls), key=lambda row: row[:2])

    def test_recorded_maps_go_through_every_pass_unchanged(self):
        image = self.calls('image')
        names = [row[2] for row in image]
        convert = next(row[3] for row in image if row[2] == 'convert_builder_scene')
        self.assertIn('recorded', {k.arg for k in convert.keywords})
        for name in ('annotate', 'bake_ground'):
            call = next(row[3] for row in image if row[2] == name)
            self.assertIn('exclude', {k.arg for k in call.keywords}, name)
        last_writer = max(i for i, n in enumerate(names) if n in ('bake_ground', 'clear_baked', 'install_town_flora',
                                                                 'keep_town_flora', 'repair_balmora_maps'))
        self.assertIn('check', names[last_writer:names.index('finalize_image')])
        final = [row[2] for row in self.calls('finalize_image')]
        checks = [i for i, n in enumerate(final) if n == 'check_recorded']
        for writer in ('prepare_staged_sky', 'configure_staged_maps', 'cull_staged_maps', 'stamp_staged_hands',
                       'optimize_maps'):
            at = final.index(writer)
            self.assertTrue(any(c > at for c in checks), writer)
        self.assertLess(max(checks), final.index('write_content_fingerprint'))
        self.assertGreater(max(checks), final.index('stage_night_lighting'))

    def test_fallback_alias_copy_is_not_applied_to_recorded_maps(self):
        source = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        alias = re.search(r"\n( +)shutil\.copyfile\(boot/'id1/maps'/\(actual\['fallback_alias'\]", source)
        guard = source.rfind('if frozen:', 0, alias.start())
        self.assertNotEqual(guard, -1)
        self.assertGreater(len(alias.group(1)), len(source[source.rfind('\n', 0, guard) + 1:guard]))


class GuidedBuildTests(unittest.TestCase):
    def test_option_reaches_actor_contact_and_image_only_when_given(self):
        import build
        tools = {n: '/opt/' + n for n in ('qbsp', 'vis', 'light', 'qcc', 'xdftool', 'rdbtool', 'ffmpeg')}
        base = ['--data-files', '/data', '--workspace', '/ws', '--name', 'r', '--sdk', '/sdk', '--jobs', '2']
        plain = dict(build.commands(build.parser().parse_args(base), tools, Path('/run')))
        given = dict(build.commands(build.parser().parse_args(base + ['--seyda-recorded', '/rec']), tools, Path('/run')))
        for step in ('actor-contact', 'image'):
            self.assertNotIn('--seyda-recorded', plain[step])
            at = given[step].index('--seyda-recorded')
            self.assertEqual(str(given[step][at + 1]), str(Path('/rec')))
        self.assertEqual({k: v for k, v in plain.items() if k not in ('actor-contact', 'image')},
                         {k: v for k, v in given.items() if k not in ('actor-contact', 'image')})


if __name__ == '__main__':
    unittest.main()
