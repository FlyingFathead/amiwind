# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-TESTER-32GB-OOM-67: the room stages store each resident the moment its worker hands it back.

prepare_area.populate baked the residents through build_parallel.ordered_map, which hands results back in input order:
a resident finished behind a slower one waited for it, unstored, and a build that stopped then (out of memory, a lost
worker) made it again on the next run (the room batches' residents: 2,280 of them, 528 min from scratch). The bakes now
go through unit_store.completed_units: each resident is published and stored as it comes back, then all of them are
installed in identifier order as before, so the stage's output does not change. Synthetic residents, no game data;
the bake is replaced by a module-level stand-in (the real pool's workers import it)."""
import contextlib
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import prepare_area as area  # noqa: E402

SLOW, FAST = 'aaa_slow', 'bbb_fast'      # in identifier order the slow one comes first
LOSE_ENV, SLOW_ENV = 'OOMPLAN_TEST_LOSE', 'OOMPLAN_TEST_SLOW_SECONDS'


def fake_bake(task):
    """build_resident_reads' stand-in: the resident named in LOSE_ENV loses its worker after SLOW_ENV seconds (the
    build stopped while it baked; '*': every one); every other one is back at once."""
    ident = task[2]['id']
    if os.environ.get(LOSE_ENV) in (ident, '*'):
        time.sleep(float(os.environ.get(SLOW_ENV) or 0))
        raise RuntimeError('the worker baking %s was lost' % ident)
    raw = b'fictional model of ' + ident.encode()
    return ident, raw, b'', {'appearance': task[2], 'step': .25, 'greeting': {'text': ''},
                             'sha256': hashlib.sha256(raw).hexdigest()}


def reversed_completion(function, items, jobs=None, cost=None):
    """build_parallel.completed_map as a pool hands results back when the first unit is the slowest: the last first."""
    for item in reversed(list(items)):
        yield function(item)


def tree(folder):
    folder = Path(folder)
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob('*')) if p.is_file()}


class ResidentsStoredAsTheyFinish(unittest.TestCase):
    def setUp(self):
        import known_inputs
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        lock = self.root / 'inputs.json'
        lock.write_text('{"schema": "%s", "files": {"Morrowind.esm": {"sha256": "%s"}}}' % (known_inputs.LOCK_SCHEMA,
                                                                                         '2' * 64))
        self.ffmpeg = self.root / 'ffmpeg'
        self.ffmpeg.write_bytes(b'not a real program')
        self.cache = self.root / 'cache'
        self.env = {'AMIWIND_PASS_CACHE': str(self.cache), known_inputs.LOCK_ENV: str(lock), LOSE_ENV: '',
                    SLOW_ENV: '0'}

    def scene(self, name):
        from player_hull import pack_lumps
        from chim.frame_map import empty_world
        import seyda_entities
        data = self.root / name
        (data / 'scene/id1/maps').mkdir(parents=True)
        (data / 'Morrowind.esm').write_bytes(b'fictional master fixture')
        scene = data / 'scene'
        (scene / 'id1/progs').mkdir()
        (scene / 'id1/gfx').mkdir()
        (scene / 'id1/gfx/palette.lmp').write_bytes(bytes(768))
        chunks = empty_world([-32., -32., -32.], [32., 32., 32.])
        chunks[0] = b'{"classname" "worldspawn"}' + bytes([0])
        (scene / 'id1/maps/seyda.bsp').write_bytes(pack_lumps(chunks))
        seyda_entities.publish(scene, pack_lumps(chunks))
        return data, scene

    def populate(self, data, scene, jobs=1):
        refs = [{'id': ident, 'number': number, 'scale': 1., 'position': [-11264., -71680., 64.],
                 'rotation_radians': [0., 0., 0.]} for number, ident in ((17, SLOW), (18, FAST))]
        with contextlib.ExitStack() as stack:
            for name, value in {'load_master': ({'NPC_': {SLOW: [], FAST: []}}, [{'refs': refs}], {}),
                                'first': b'', 'foot_class': 'bare', 'voices_of': {}, 'greeting_fixture': {},
                                'behavior_record': {},
                                'greeting_settings': {'distance': 10, 'reset_distance': 20, 'duration': 1}}.items():
                stack.enter_context(patch.object(area, name, return_value=value))
            stack.enter_context(patch.object(area, 'outfit', side_effect=lambda kinds, ident: {
                'id': ident, 'name': ident, 'female': False, 'skeleton': 'fixture'}))
            stack.enter_context(patch.object(area, 'build_resident_reads', fake_bake))
            import actor_grounding           # the synthetic ids have no grounding class: on the floor
            stack.enter_context(patch.object(actor_grounding, 'fields', lambda ident, reference=None: {
                'aw_source_id': ident, 'aw_ground_mode': 0}))
            stack.enter_context(patch.object(area.npc_items, 'attach_items', side_effect=lambda k, i, a: a))
            stack.enter_context(patch.object(area.npc_lod, 'publish', return_value={'mode': 'off'}))
            return area.populate(data, scene, rooms={}, reports=[], ffmpeg=str(self.ffmpeg), jobs=jobs, doors=False)

    def stored(self):
        import pass_cache
        return sorted(label for unit, label, *_ in pass_cache.list_units(self.cache, area.RESIDENT_UNIT))

    def test_a_resident_finished_behind_a_lost_one_is_stored(self):
        data, scene = self.scene('lost')
        import build_parallel
        with patch.dict(os.environ, dict(self.env, **{LOSE_ENV: SLOW})), \
                patch.object(build_parallel, 'completed_map', reversed_completion), \
                self.assertRaisesRegex(RuntimeError, 'the worker baking aaa_slow was lost'):
            self.populate(data, scene)
        self.assertEqual(self.stored(), [FAST])

    def test_on_a_real_pool_the_fast_resident_is_stored_before_the_slow_one_fails(self):
        data, scene = self.scene('pool')
        with patch.dict(os.environ, dict(self.env, **{LOSE_ENV: SLOW, SLOW_ENV: '3'})), \
                self.assertRaisesRegex(RuntimeError, 'the worker baking aaa_slow was lost'):
            self.populate(data, scene, jobs=2)
        self.assertEqual(self.stored(), [FAST])

    def test_the_order_they_finish_in_changes_nothing_installed(self):
        import build_parallel
        results = []
        for name, order in (('in-order', None), ('reversed', reversed_completion)):
            data, scene = self.scene(name)
            with patch.dict(os.environ, dict(self.env, AMIWIND_PASS_CACHE='off')), \
                    (patch.object(build_parallel, 'completed_map', order) if order else contextlib.nullcontext()):
                report = self.populate(data, scene)
            results.append((tree(scene), report))
        self.assertEqual(results[0], results[1])
        self.assertTrue(any(path.endswith('.mdl') for path in results[0][0]))

    def test_a_second_run_restores_both_and_bakes_nothing(self):
        data, scene = self.scene('first')
        with patch.dict(os.environ, self.env):
            self.populate(data, scene)
        self.assertEqual(self.stored(), [SLOW, FAST])
        data, scene = self.scene('second')
        with patch.dict(os.environ, dict(self.env, **{LOSE_ENV: '*'})):      # any bake now fails the test
            self.populate(data, scene)
        self.assertTrue(any(path.endswith('.mdl') for path in tree(scene)))


if __name__ == '__main__':
    unittest.main()
