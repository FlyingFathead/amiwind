# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-TESTER-32GB-OOM-67: a first build plans its memory from measured peaks.

A tester's 32 GB machine built for 32 hours and the build stopped for memory. On a first build the resource plan
(tools/resource_plan.py) had no measurement at all: every stage was "estimated, no data yet" (512 MiB a worker), so the
plan saw nothing wrong and the scheduler ran the CHIM world (its main process alone about 24 GiB) beside the room
batches (about 17 GiB): the v0.0.66 from-scratch build peaked at 43.7 GiB that way. Now:
  - the reference build's measured peaks (config/build-memory.json) are the last-resort measurement of a full build,
    labelled "measured in the reference build";
  - stages whose measured peaks do not fit side by side in the build's memory run one after another (the alone and
    memory-heavy lists the scheduler honours), each decision a WARN line in the log and in build-summary.md;
  - every reduction of workers for memory is a WARN line too;
  - swap counts when one stage's largest process is larger than the memory, and a full build below the need runs with
    a WARN line and the stop advice, never refused as WILL NOT FIT.
resource_plan is key-neutral (build_cache.INSTRUMENTATION_MODULES): nothing here moves a stage key."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import resource_plan as rp  # noqa: E402

GIB = 1 << 30

# the stages of a full build that matter here, in the order tools/build.py plans them (the v0.0.66 from-scratch
# build: the room batches before the CHIM world, the actor library after the CHIM tracker data; a pool stage has --jobs)
STEPS = [('census', ['python3', 'tools/prepare_census.py', '--jobs', '16']),
         ('chim-room-batches', ['python3', 'tools/chim_room_batches.py', '--jobs', '16']),
         ('chim', ['python3', 'tools/chim_build.py', '--jobs', '16']),
         ('cell-progress', ['python3', 'tools/cell_progress_chim.py']),
         ('actor-library', ['python3', 'tools/prepare_actor_library.py', '--jobs', '16']),
         ('music', ['python3', 'tools/prepare_music.py'])]
RUNNING = {'chim-room-batches', 'chim', 'actor-library', 'music'}


def got(memory_gb, threads=16, swap_gb=0.0, machine_gb=None):
    return {'memory_bytes': int(memory_gb * GIB), 'memory_source': 'test', 'used_bytes': 0, 'threads': threads,
            'threads_source': 'test', 'machine_bytes': int((machine_gb or memory_gb) * GIB), 'machine_threads': 16,
            'swap_bytes': int(swap_gb * GIB), 'swap_source': 'test'}


def first_build(memory_gb, swap_gb=0.0, steps=STEPS, running=RUNNING):
    """The plan of a first full build (no run, no history): the reference measurements only."""
    with tempfile.TemporaryDirectory() as workspace:
        gathered = rp.gather(None, workspace, scope='full', stair_walk='flights')
    return rp.plan(steps, running, 16, got(memory_gb, swap_gb=swap_gb), gathered)


class FirstBuildMemoryPlan(unittest.TestCase):
    def test_the_reference_build_is_the_last_resort_measurement(self):
        with tempfile.TemporaryDirectory() as workspace:
            gathered = rp.gather(None, workspace, scope='full', stair_walk='flights')
            mini = rp.gather(None, workspace, scope='miniwind', stair_walk='flights')
        chim = gathered['stages']['chim']
        self.assertEqual(len(chim), 1)
        self.assertTrue(chim[0]['reference'])
        self.assertGreater(chim[0]['largest_mib'], 20000)                 # the main process, about 24 GiB
        self.assertNotIn('chim', mini['stages'])                          # a MiniWind is not like for like
        doc = rp.plan(STEPS, RUNNING, 16, got(64), gathered)
        rows = {r['stage']: r for r in doc['stages']}
        self.assertTrue(rows['chim']['model'].startswith('measured in the reference build'))
        self.assertEqual(rows['music']['model'], 'estimated, no data yet')
        self.assertEqual(rp.validate(doc), [])

    def test_own_measurements_win_over_the_reference(self):
        own = {'jobs': 8, 'largest_mib': 900.0, 'total_mib': 1700.0, 'worker_mib': 100.0, 'wall': 60.0,
               'cores': 4.0, 'run': '/vol/ws8/build/r1', 'scope': 'full'}
        with tempfile.TemporaryDirectory() as workspace, \
                mock.patch.object(rp, 'chain', lambda run, hops=rp.CHAIN_RUNS: [Path(workspace)]), \
                mock.patch.object(rp, 'measure', lambda row, timeline=None: dict(own)):
            (Path(workspace) / 'build-profile.json').write_text(json.dumps({'stages': [{'name': 'chim'}]}))
            gathered = rp.gather(workspace, workspace, scope='full', stair_walk='flights')
        self.assertEqual([r.get('reference') for r in gathered['stages']['chim']], [None])
        self.assertTrue(gathered['stages']['chim-room-batches'][0]['reference'])

    def test_on_32_gib_chim_and_the_room_batches_do_not_run_side_by_side(self):
        doc = first_build(32)
        self.assertIn('chim', doc['alone'])
        self.assertIn('chim-room-batches', doc['memory_heavy'])
        held, _ = rp.alone_hold(['chim-room-batches'], ['chim'], doc['alone'], doc['memory_heavy'])
        self.assertEqual(held, {'chim-room-batches'})                     # it waits while chim runs
        held, order = rp.alone_hold(['chim', 'chim-room-batches'], [], doc['alone'], doc['memory_heavy'])
        self.assertIn('chim-room-batches', held)
        lines = rp.checklist(doc)
        warn = [line for line in lines if line.startswith('WARN memory plan:')]
        self.assertTrue(any('chim' in line and 'chim-room-batches' in line and 'side by side' in line for line in warn),
                        warn)
        self.assertTrue(any('measured in the reference build' in line for line in warn), warn)
        self.assertEqual(doc['refusals'], [])
        self.assertEqual(rp.validate(doc), [])

    def test_on_64_gib_they_still_run_side_by_side(self):
        doc = first_build(64)
        rows = {r['stage']: r for r in doc['stages']}
        self.assertNotIn('chim-room-batches', rows['chim'].get('not_beside') or [])
        self.assertFalse([w for w in doc.get('memory_warnings') or []
                          if set(w['stages']) == {'chim', 'chim-room-batches'}])
        # the actor library at 16 workers (about 2.6 GiB each, measured) beside the CHIM world is too much even here
        self.assertIn('actor-library', rows['chim'].get('not_beside') or [])

    def test_two_stages_whose_memory_is_in_their_workers_share_it(self):
        # the actor library (about 2.6 GiB a worker) and the room batches (about 0.8 GiB a worker): the running memory
        # guard gives each fewer workers while both run, so they are not made to wait for each other (48 GiB, as the
        # project's own full builds); the CHIM world's main process is the case it cannot help
        doc = first_build(48)
        rows = {r['stage']: r for r in doc['stages']}
        self.assertNotIn('chim-room-batches', rows['actor-library'].get('not_beside') or [])
        keys = {w['key'] for w in doc['memory_warnings']}
        self.assertTrue(any(k.startswith('shared:') and 'actor-library' in k and 'chim-room-batches' in k
                            for k in keys), keys)
        self.assertTrue(rp.one_process(rows['chim']))
        self.assertFalse(rp.one_process(rows['chim-room-batches']))

    def test_stages_that_wait_for_each_other_are_never_a_pair(self):
        import build_parallel
        with mock.patch.object(build_parallel, 'stage_dependencies',
                               lambda steps: {'census': [], 'chim': ['census'], 'chim-room-batches': ['chim'],
                                              'cell-progress': ['chim'], 'actor-library': ['chim-room-batches'],
                                              'music': []}):
            doc = first_build(32)
        self.assertFalse([w for w in doc.get('memory_warnings') or [] if w['key'].startswith('side-by-side:')])

    def test_every_reduction_of_workers_for_memory_is_a_warn_line(self):
        doc = first_build(32)
        rows = {r['stage']: r for r in doc['stages']}
        library = rows['actor-library']                    # about 2.6 GiB a worker in the reference build
        self.assertEqual(library['status'], 'WILL THROTTLE')
        self.assertLess(library['workers'], 16)
        keys = {w['key'] for w in doc['memory_warnings']}
        self.assertIn('workers:actor-library', keys)
        text = next(w['text'] for w in doc['memory_warnings'] if w['key'] == 'workers:actor-library')
        self.assertIn('%d of 16 workers' % library['workers'], text)

    def test_below_the_need_a_full_build_warns_and_runs_never_refused(self):
        doc = first_build(16)                              # chim's main process alone is about 24 GiB
        rows = {r['stage']: r for r in doc['stages']}
        self.assertEqual(rows['chim']['status'], 'WILL THROTTLE')
        self.assertEqual(rows['chim']['workers'], 1)
        self.assertEqual(doc['refusals'], [])
        self.assertNotEqual(doc['verdict'], 'refused')
        text = next(w['text'] for w in doc['memory_warnings'] if w['key'] == 'below-need:chim')
        self.assertIn('runs anyway', text)
        self.assertIn('same command', text)                # the stop advice: the same command, the same folder
        self.assertFalse(any(line.lstrip().startswith('WILL NOT FIT') for line in rp.checklist(doc)))

    def test_swap_counts_when_one_process_is_larger_than_the_memory(self):
        doc = first_build(24, swap_gb=16)                  # 19.2 GiB to plan with, 32 with the swap counted
        text = next(w['text'] for w in doc['memory_warnings'] if w['key'] == 'below-need:chim')
        self.assertIn('swap', text)
        self.assertIn('fits with', text)
        self.assertEqual(doc['got']['swap_mib'], 16 * 1024.0)

    def test_a_miniwind_unit_larger_than_memory_and_swap_is_still_refused(self):
        stages = {'chim': [{'jobs': 8, 'largest_mib': 1700.0, 'total_mib': 4000.0, 'worker_mib': 287.5,
                            'wall': 60.0, 'cores': 4.0, 'run': 'r', 'scope': 'miniwind'}]}
        gathered = {'stages': stages, 'stair': None, 'runs': ['r'], 'scope': 'miniwind', 'stair_walk': 'off'}
        doc = rp.plan(STEPS, {'chim'}, 8, got(1, swap_gb=0.5), gathered)
        self.assertEqual(doc['verdict'], 'refused')

    def test_the_limits_read_the_swap(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / 'memory.max').write_text('%d\n' % (32 * GIB))
            (Path(root) / 'memory.current').write_text('0\n')
            (Path(root) / 'memory.swap.max').write_text('%d\n' % (8 * GIB))
            with mock.patch.object(rp, 'machine_swap', lambda: (16 * GIB, 12 * GIB, 'test')):
                found = rp.limits(root=root)
                self.assertEqual(found['swap_bytes'], 8 * GIB)             # the container's own swap limit
                (Path(root) / 'memory.swap.max').write_text('max\n')
                self.assertEqual(rp.limits(root=root)['swap_bytes'], 12 * GIB)   # the machine's free swap
                (Path(root) / 'memory.swap.max').write_text('0\n')
                self.assertEqual(rp.limits(root=root)['swap_bytes'], 0)
                self.assertEqual(rp.limits(memory_gb=8, root=root)['swap_bytes'], 0)   # an asked lease: not counted

    def test_the_build_summary_shows_the_warn_lines(self):
        import build_digest
        doc = first_build(32)
        with tempfile.TemporaryDirectory() as run:
            (Path(run) / rp.FILE).write_text(rp.text(doc))
            (Path(run) / 'build-state.json').write_text(json.dumps({'status': 'running', 'steps': []}))
            record = build_digest.digest(run)
            page = build_digest.markdown(record)
        keys = [row['key'] for row in record['needs_attention']]
        self.assertTrue(any(key.startswith('memory-plan:side-by-side:') for key in keys), keys)
        self.assertIn('## Memory plan', page)
        self.assertIn('WARN memory plan:', page)

    def test_the_build_prints_the_warn_lines_and_hands_the_lists_to_the_scheduler(self):
        import build
        with tempfile.TemporaryDirectory() as workspace:
            args = types.SimpleNamespace(resource_check='fail', dry_run=False, reuse_from=None, workspace=Path(workspace),
                                         jobs=16, resource_memory_gb=32, resource_threads=16, miniwind=False,
                                         stair_walk='auto')
            metadata = {'stage_cache': {'reused': {}}}
            with mock.patch.object(rp, 'state_line', lambda *a, **k: ('Machine at start: test', {})), \
                    contextlib.redirect_stdout(io.StringIO()) as out:
                doc = build.resource_preflight(args, STEPS, metadata)
        self.assertIn('WARN memory plan:', out.getvalue())
        self.assertIn('chim', metadata['resource_plan_alone'])
        self.assertIn('chim-room-batches', metadata['resource_plan_heavy'])
        self.assertEqual(doc['refusals'], [])


if __name__ == '__main__':
    unittest.main()
