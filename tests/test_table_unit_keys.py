"""The voice table, the dialogue table and the actor ground fit take their units from the unit cache when what they
bake from is unchanged (BUILD-TABLE-UNITS-REBAKE-63: the v0.0.63 dev builds baked both tables again in every build
and the ground fit had no cache at all, and the build's minute-one check could not read the dialogue table's key).

Each key covers exactly the code its bake reaches (pass_cache.source_digest of (module, function) entries): a real
input of the bake is in the key's reach, a file the bake never runs (the script compiler's game data and function
table, the stage's scheduling code) is not."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))

VOICE = (('tools/greeting_lut.py', 'build_master'), ('tools/greeting_lut.py', 'sound_resolver'))
DIALOGUE = (('tools/dialogue_lut.py', 'build_master'),)
GROUND = (('tools/actor_grounding.py', '_fit_head'), ('tools/actor_grounding.py', '_fit_search'),
          ('tools/actor_grounding.py', 'finish'))


def key_reach(entries):
    """{repository path: reached units or 'WHOLE'} as the cache key (form pass_cache.PASS_KEY_FORM) counts them."""
    import pass_cache
    from build_cache import SourceIndex
    index = SourceIndex(ROOT, top_format=pass_cache.PASS_KEY_FORM)
    out = {}
    for module, function in entries:
        python, data, uncertain, units = index.entry_units((ROOT / module).resolve(), function)
        assert not uncertain, (module, function)
        for path in python | data:
            if path in pass_cache.PASS_KEY_NEUTRAL:
                continue
            reached = units.get(path) if path.endswith('.py') and path not in data else None
            out.setdefault(path, set()).update(reached or {'WHOLE'})
    return out


class TableKeys(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.voice, cls.dialogue, cls.ground = key_reach(VOICE), key_reach(DIALOGUE), key_reach(GROUND)

    def test_the_voice_table_keys_on_what_its_bake_reads(self):
        reach = self.voice
        self.assertIn('build_master', reach['tools/greeting_lut.py'])
        self.assertIn('sound_resolver', reach['tools/greeting_lut.py'])
        self.assertIn('sound_range', reach['tools/mwscript/hearing.py'])     # the SOUN rows' hearing distances
        self.assertIn('tools/mwscript/media.py', reach)                      # the converted sounds' lengths
        self.assertIn('tools/text_defines.py', reach)
        self.assertIn('tools/prepare_media_assets.py', reach)
        # the script compiler's game data and function table are not read by the bake
        for path in ('tools/mwscript/gamedata.py', 'tools/mwscript/functions.py', 'tools/mwscript/parser.py'):
            self.assertNotIn(path, reach)
        self.assertNotIn('image_step', reach['tools/greeting_lut.py'])      # the cache lookup and checks around it

    def test_the_dialogue_table_keys_on_what_its_bake_reads(self):
        reach = self.dialogue
        self.assertIn('build_master', reach['tools/dialogue_lut.py'])
        self.assertIn('script_slots', reach['tools/dialogue_lut.py'])
        self.assertIn('declarations', reach['tools/mwscript/lexer.py'])      # the speaker's local slots
        self.assertIn('src/mwad/dialogue.py', reach)
        self.assertIn('tools/greeting_lut.py', reach)                        # the voice table's NPC order
        for path in ('tools/mwscript/gamedata.py', 'tools/mwscript/functions.py', 'tools/mwscript/parser.py'):
            self.assertNotIn(path, reach)
        self.assertNotIn('image_step', reach['tools/dialogue_lut.py'])

    def test_the_ground_fit_keys_on_what_its_fit_reads(self):
        reach = self.ground
        for unit in ('_fit_head', '_fit_search', 'finish', 'centre_support', 'search_offsets'):
            self.assertIn(unit, reach['tools/actor_grounding.py'])
        self.assertIn('owner', reach['tools/check_actor_ground.py'])         # which core map holds each spot
        self.assertIn('contact_samples', reach['tools/check_actor_ground.py'])
        self.assertIn('config/towns.json', reach)
        self.assertIn('tools/audit_walkability.py', reach)                   # the collision scene
        for unit in ('bake_ground', '_fit_all', '_bake_map', 'placement_inputs', 'ground_cache'):
            self.assertNotIn(unit, reach['tools/actor_grounding.py'])

    def test_a_reached_function_changes_the_key_and_an_unreached_one_keeps_it(self):
        """The digest itself: a different digest for a reached function's code, the same for an unreached one."""
        import pass_cache
        from build_cache import SourceIndex
        real = SourceIndex.unit_digest

        def edited(name):
            file, unit = name.split(':')

            def unit_digest(self, path, units):
                value = real(self, path, units)
                return value + '+edit' if unit in units and path.endswith(file) else value
            return unit_digest
        scripts = [(str(ROOT / m), f) for m, f in VOICE]
        base = pass_cache._source_digest(scripts)
        with mock.patch.object(SourceIndex, 'unit_digest', edited('hearing.py:sound_range')):
            self.assertNotEqual(pass_cache._source_digest(scripts), base)
        with mock.patch.object(SourceIndex, 'unit_digest', edited('greeting_lut.py:image_step')):
            self.assertEqual(pass_cache._source_digest(scripts), base)

    def test_the_minute_one_check_reads_every_table_key(self):
        """reuse_all.unit_cache_openers reads the code each key hashes (the dialogue table's named
        mwad.dialogue.__file__, a dotted module the check could not resolve: 'key cannot be read')."""
        import reuse_all
        openers = {o['name']: o for o in reuse_all.unit_cache_openers(ROOT)}
        for name, entries in (('npc-voice-table', VOICE), ('dialogue-table', DIALOGUE), ('actor-ground', GROUND)):
            self.assertIsNotNone(openers[name]['scripts'], name)
            self.assertEqual([(str(Path(p).relative_to(ROOT).as_posix()), f) for p, f in openers[name]['scripts']],
                             list(entries))

    def test_the_ground_bake_is_no_uncached_bake(self):
        import reuse_all
        self.assertNotIn(('tools/actor_grounding.py', 'bake_ground'), reuse_all.uncached_bakes(ROOT))

    def test_the_dev_builds_units_are_found_again(self):
        """The whole-file digests the v0.0.62 and v0.0.63 dev builds stored their table units under are looked up
        while the bake reach is the one measured on those trees (same reach apart from the moved, unchanged code)."""
        import unit_store
        self.assertIn('ca0e34d0e6789ffbc9022a46df1c32d937f80b9d41a16e36363855d8cb24cfae', unit_store.legacy_sources(
            'npc-voice-table', '60f51a53b786fbf51e951a08225b0b4076b0316eb1874a8c048ac0010c20fb20'))
        self.assertIn('004a9ca21f8a211f5e514ed00c236ab97f722d3c35d49d32a8a9addc3fdf07cc', unit_store.legacy_sources(
            'dialogue-table', 'e189af83bf90d3879a820f1837ca40cef7a911c2f79830ec5b0402f63f095b27'))

    def test_the_moved_rules_give_the_same_answers(self):
        from mwscript import gamedata, hearing, lexer, parser
        data = gamedata.GameData()
        data.gmst = {'faudiomindistancemult': 10.0}
        for soun in (None, {'min': 0, 'max': 0}, {'min': 3, 'max': 7}, {'min': 9, 'max': 2}):
            self.assertEqual(data.sound_range(soun), hearing.sound_range(data.gmst, soun))
        tokens = lexer.tokenize('begin x\nshort a\n float b\nlong a\nend\n', [])
        self.assertEqual(parser.declarations(tokens), {'a': ('s', 0), 'b': ('f', 1)})
        self.assertIs(parser.declarations, lexer.declarations)


def fake_head(task):
    token, maps, name, e, authored, angles = task
    result = {'map': name, 'reference': e.get('aw_ref'), 'status': 'supported', 'authored_origin': list(authored)}
    if e.get('aw_ref') == '2':
        return result, [authored[0], authored[1], authored[2] + .25]
    result.update(placed_origin=[authored[0], authored[1], authored[2] + .25], mesh_contact='unchanged', attempts=0)
    return result, None


def fake_search(task):
    token, maps, name, e, authored, angles, original, first, last = task
    return (first + 1, {'placed_origin': [authored[0] + 1.5, authored[1], original[2]], 'mesh_contact': 'fitted',
                        'attempts': first + 1}) if first >= 64 else None


class GroundUnits(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        (base / 'id1' / 'maps').mkdir(parents=True)
        (base / 'id1' / 'progs').mkdir()
        (base / 'id1' / 'progs' / 'npc.mdl').write_bytes(b'model')
        for name in ('alpha', 'beta'):
            (base / 'id1' / 'maps' / (name + '.bsp')).write_bytes(name.encode())
        self.maps = base / 'id1' / 'maps'
        self.entities = {
            'alpha': [{'classname': 'aw_npc', 'aw_ref': '1', 'origin': '10 20 30', 'model': 'progs/npc.mdl'},
                      {'classname': 'aw_npc', 'aw_ref': '2', 'origin': '40 50 60', 'model': 'progs/npc.mdl'}],
            'beta': [{'classname': 'aw_npc', 'aw_ref': '3', 'origin': '1 2 3', 'model': 'progs/npc.mdl'}]}

    def tearDown(self):
        self.tmp.cleanup()

    def bake(self, jobs=1):
        import io
        import contextlib
        import actor_grounding as AG
        calls = []

        def head(task):
            calls.append(task[2:4])
            return fake_head(task)
        serial = lambda function, items, jobs=1: [function(item) for item in items]  # noqa: E731
        output = io.StringIO()
        with mock.patch('build_parallel.ordered_map', serial), \
                mock.patch.object(AG, '_ground_entities', lambda path: self.entities[Path(path).stem]), \
                mock.patch.object(AG, '_fit_head', head if jobs <= 1 else fake_head), \
                mock.patch.object(AG, '_fit_search', fake_search), \
                mock.patch.object(AG, '_bake_map', lambda task: Path(task[0]).name), \
                mock.patch('map_files.is_chim_room', lambda path: False), \
                mock.patch('chim.interior.is_shell_map', lambda raw: False), \
                contextlib.redirect_stdout(output):
            report = AG.bake_ground(self.maps, jobs=jobs)
        return json.dumps(report, sort_keys=False), calls, output.getvalue()

    def test_a_second_bake_takes_every_placement_from_the_cache_with_the_same_report(self):
        import pass_cache
        off, _, _ = self.bake()
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, {pass_cache.ENV: folder}):
            first, calls, text = self.bake()
            self.assertEqual(len(calls), 3)
            self.assertIn('Actor support [0/3] cached, 3 to fit', text)
            self.assertRegex(text, r'Actor support \[3/3\] beta:3 \d+s')
            second, calls, text = self.bake()
            self.assertEqual(calls, [], 'a placement was fitted again although nothing it reads changed')
            self.assertIn('Actor support [3/3] cached, 0 to fit', text)
            with mock.patch.dict(os.environ, {pass_cache.REBUILD_ENV: 'actor-ground:alpha:2'}):
                _, calls, _ = self.bake()
            self.assertEqual([c[1]['aw_ref'] for c in calls], ['2'], '--rebuild-unit fits exactly the named one')
            self.assertEqual(first, off)
            self.assertEqual(second, off)
            # a real input changed: only the placements of that map fit again
            (self.maps / 'beta.bsp').write_bytes(b'beta, changed')
            third, calls, _ = self.bake()
            self.assertEqual([c[0] for c in calls], ['beta'])
            # the actor model changed: every placement that uses it fits again
            (self.maps.parent / 'progs' / 'npc.mdl').write_bytes(b'model 2')
            _, calls, _ = self.bake()
            self.assertEqual(len(calls), 3)

    def test_the_pool_reports_each_placement_once_with_the_serial_result(self):
        """The pooled fit hands every placement to the store exactly once, after its first hit is settled, with
        what bake_ground reports for it."""
        import actor_grounding as AG
        tasks = [('t', str(self.maps), 'alpha', e, [float(v) for v in e['origin'].split()], (0.0, 0.0, 0.0))
                 for e in self.entities['alpha']]
        for jobs in (1, 3):
            final = {}
            with mock.patch.object(AG, '_fit_head', fake_head), mock.patch.object(AG, '_fit_search', fake_search):
                heads, best = AG._fit_all(tasks, jobs, lambda index, result: final.setdefault(index, []).append(result))
            reported = [result if original is None else AG.finish(dict(result), best.get(index))
                        for index, (result, original) in enumerate(heads)]
            self.assertEqual({k: len(v) for k, v in final.items()}, {0: 1, 1: 1}, jobs)
            self.assertEqual([final[0][0], final[1][0]], reported, jobs)
            self.assertEqual(final[1][0]['attempts'], 65)

    def test_the_inputs_name_what_the_fit_reads(self):
        import actor_grounding as AG
        e = self.entities['alpha'][0]
        first = AG.placement_inputs(self.maps, 'alpha', e, [10.0, 20.0, 30.0], (0.0, 0.0, 0.0))
        (self.maps / 'beta.bsp').write_bytes(b'unrelated map changed')
        self.assertEqual(AG.placement_inputs(self.maps, 'alpha', e, [10.0, 20.0, 30.0], (0.0, 0.0, 0.0)), first)
        (self.maps.parent / 'progs' / 'npc.anm').write_text('idle 0 8\n', encoding='ascii')
        self.assertNotEqual(AG.placement_inputs(self.maps, 'alpha', e, [10.0, 20.0, 30.0], (0.0, 0.0, 0.0)), first)
        moved = dict(e, angles='0 90 0')
        self.assertNotEqual(AG.placement_inputs(self.maps, 'alpha', moved, [10.0, 20.0, 30.0], (0.0, 90.0, 0.0)),
                            first)


if __name__ == '__main__':
    unittest.main()
