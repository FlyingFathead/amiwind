# SPDX-License-Identifier: GPL-3.0-only
"""tools/perf_db.py: schema, append-only rows, idempotent and refused re-reads, ledgers read in segments, every run
file kind, retired-run archives, deterministic rebuild from the content store, queries and dumps."""
import contextlib
import gzip
import io
import json
import os
import sqlite3
import tarfile
import tempfile
import time
import unittest
from pathlib import Path

import perf_db

RUN_A = '2026_10_10_v0.0.36-dev3_full-test_aaaaaaa'
RUN_B = '2026_10_11_v0.0.36-dev4_full-test_bbbbbbb'
BALMORA, SEYDA = 'frames/x-03/y-02', 'frames/x-02/y-09'


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1), encoding='utf-8', newline='\n')


def heap_frame(frame, peak, budget=6242304, breakdown=None):
    row = {'frame': frame + '/frame.ccf', 'peak_bytes': peak, 'budget_bytes': budget, 'headroom_bytes': budget - peak,
           'median_bytes': peak // 3, 'positions': 9216, 'positions_over_budget': 0 if peak <= budget else 3,
           'ring_models': 96, 'ring_chunks': 31, 'ring_textures': 88, 'zone_bytes': 7028736, 'streamed_bytes': 0,
           'largest_block_bytes': 464336, 'ok': peak <= budget,
           'load_ring': {'peak_bytes': peak + 1000, 'headroom_bytes': budget - peak - 1000, 'positions_over_budget': 5}}
    if breakdown:
        row['peak_breakdown'] = breakdown
    return row


def make_run(root, name, balmora_peak=6226544, status='passed', started='2026-10-10T16:53:34+00:00'):
    """A synthetic run folder with one file of every kind perf_db reads."""
    run = Path(root) / name
    steps = [{'name': 'setup', 'status': 'passed', 'jobs': 1, 'started_seconds': 0.1, 'elapsed_seconds': 0.3,
              'returncode': 0, 'reused': 'reused (fingerprint f1) from /vol/ws8/build/x',
              'profile': {'cpu_seconds': 0.2, 'cores_avg': 0.9, 'peak_process_rss_bytes': 64352256}},
             {'name': 'chim', 'status': status, 'jobs': 12, 'started_seconds': 9.3, 'elapsed_seconds': 2335.2,
              'returncode': 0 if status == 'passed' else 1,
              'profile': {'cpu_seconds': 6580.1, 'cores_avg': 2.8, 'peak_process_rss_bytes': 3333922816}}]
    write_json(run / 'build-state.json', {
        'runtime_version': '0.0.36-dev3', 'builder': 'chim', 'chim_version': '0.1.0', 'recipe': 'r1',
        'builder_options': {'builder': 'chim', 'chim_areas': ['balmora', 'seyda']},
        'source_sha256': {'VERSION': 'aa' * 32, 'tools/build.py': 'bb' * 32},
        'run_name': {'name': name, 'commit': name[-7:], 'purpose': 'full-test'},
        'stage_cache': {'reuse_from': '/vol/ws8/build/x', 'fingerprints': {'setup': 'f1', 'chim': 'f2'}},
        'build_started_at': started, 'status': status, 'elapsed_seconds': 2400.5, 'steps': steps})
    write_json(run / 'build-profile.json', {
        'version': '0.0.36-dev3', 'status': status, 'started_at': started, 'wall_seconds': 2400.6,
        'overhead': {'wrapper_cpu_seconds': 1.1},
        'stages': [{'name': 'chim', 'status': status, 'wall': 2335.3, 'cpu': 6580.2, 'cores_avg': 2.82, 'jobs': 12,
                    'jobs_mean': 11.5, 'start': 9.3, 'peak_process_rss_bytes': 3333922816,
                    'peak_tree_rss_bytes': 47095316480, 'read_bytes': 10, 'write_bytes': 20, 'reused': None,
                    'host': {'cpus': 24, 'busy_percent': 64.2, 'other_percent': 15.4, 'samples': 10,
                             'host_busy': False}}]})
    write_json(run / 'build-progress.json', {
        'status': status, 'started_at': started, 'elapsed_seconds': 2400.7,
        'host': {'cpus': 24, 'busy_percent': 4.9},
        'stages': [{'name': 'chim', 'status': status, 'expected_seconds': 2000.0, 'expected_source': 'history',
                    'elapsed_seconds': 2335.2, 'jobs': 12}]})
    write_json(run / 'build-summary.json', {
        'version': '0.0.36-dev3', 'status': status, 'started_at': started, 'finished_at': '2026-10-10T17:33:34+00:00',
        'elapsed_seconds': 2400.0, 'compiler_warnings': {'count': 0},
        'output': {'path': f'/vol/ws8/build/{name}/image/AmiWind.hdf', 'bytes': 4026564608, 'sha256': 'cc' * 32},
        'profile': {'wall_seconds': 2400.0, 'cpu_seconds': 7000.0},
        'reuse': {'reuse_from': '/vol/ws8/build/x', 'stages': 2, 'reused': 1, 'rebuilt': 1, 'unexpected': 0,
                  'rows': [{'stage': 'chim', 'class': 'EXPECTED', 'cause': 'input change'}], 'saved_seconds': 5.0}})
    write_json(run / 'chim-world' / 'chim-heap.json', {
        'zone_kib': 6864, 'status': 'passed' if balmora_peak <= 6242304 else 'failed',
        'frames': [heap_frame(BALMORA, balmora_peak, breakdown={'terrain_drawn': 100, 'models_drawn': 200}),
                   heap_frame(SEYDA, 5670768)]})
    write_json(run / 'chim-world' / 'chim-stairs.json', {
        'status': 'passed', 'tested': 12, 'frames': 2, 'tasks': 4,
        'summary': {BALMORA + '/frame.ccf': {'step': {'covered': 3, 'failed': 2, 'untestable': 1},
                                             'ramp': {'covered': 1}},
                    SEYDA + '/frame.ccf': {'step': {'untestable': 5}}},
        'failures': [], 'advisory_failures': [{'map': BALMORA + '/frame.ccf', 'result': 'failed'}],
        'pass_cache': {'mode': 'cached', 'reused': 1, 'walked': 1, 'sampled': [SEYDA + '/frame.ccf']}})
    write_json(run / 'chim-world' / 'chim-timing.json', {
        'jobs': 12, 'wall_seconds': 2345.9, 'timing': {'seconds': 2335.2, 'cpu_seconds': 6580.2, 'sections': [
            {'section': 'meshes', 'seconds': 1.5, 'cpu_seconds': 2.0}, {'section': 'meshes', 'seconds': 0.5}]},
        'units': {'terrain': {'built': 10, 'reused': 20}}})
    write_json(run / 'chim-world' / 'chim-validate.json', {
        'failure_count': 0, 'measured': {'bytes_total': 323356128, 'bytes_by_kind': {'FRAM': 10, 'SECT': 20},
                                         'chunks': 62667, 'visibility': {'world_face_share': 0.4,
                                                                         'placements_sent_per_view': {'max': 7}}}})
    write_json(run / 'chim-world' / 'chim-receipt.json', {
        'chunks': 62667, 'models': 2768,
        'files': [{'path': 'chim/frames/x-03/y-02/frame.ccf', 'bytes': 100, 'kind': 'FRAM'},
                  {'path': 'chim/frames/x-03/y-02/s00.ccs', 'bytes': 300, 'kind': 'SECT'},
                  {'path': 'chim/world.cwi', 'bytes': 50, 'kind': 'INDX'}],
        'far_terrain': [{'file': 'far/-3_-2.far', 'bytes': 23476}]})
    write_json(run / 'image' / 'chim-frame-heap.json', {
        'maps': {'balmora-chim': dict(heap_frame(BALMORA, balmora_peak), map='balmora-chim.bsp')}})
    write_json(run / 'image' / 'stair-walk.json', {
        'status': 'passed', 'maps': 2596, 'summary': {'interiors and other maps': {'flight step': {'passed': 420}}},
        'failures': [], 'advisory_failures': [], 'pass_cache': {'hits': 39, 'misses': 2557}})
    write_json(run / 'image' / 'world-partitions.json', {
        'partitions': [{'volume': 'AW_WORLD0', 'bytes': 2013265920, 'sha256': 'dd' * 32, 'files': [{}, {}]}]})
    write_json(run / 'image' / 'heap-watcher.json', {'status': 'estimate_passed', 'heap_budget_bytes': 11534336})
    return run


def aw_gate_result(folder, gate, status='passed', failures=0, started='2026-10-10 20:11:56 +0300'):
    name = f'2026_10_10_v0.0.36-dev3_gate-{gate}-test_abcdef{gate % 10}'
    write_json(Path(folder) / f'{name}.json', {
        'schema': 'aw-result-1', 'kind': 'gate', 'status': status, 'run_name': name, 'gate': gate,
        'commit': 'abcdef1', 'version': 'v0.0.36-dev3', 'started': started, 'finished': started, 'seconds': 106.1,
        'numbers': {'tests_run': 3354, 'failures': failures, 'errors': 0, 'skipped': 3, 'unexpected_skips': 0,
                    'engine_warnings': 0},
        'steps': {'suite': {'exit': 0 if not failures else 1, 'ok': not failures}},
        'timings': {'suite_s': 82.2, 'queue_wait_s': 1, 'queued_at': 1791652316}})
    return name


def quiet(function, *args, **kwargs):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = function(*args, **kwargs)
    return code, out.getvalue(), err.getvalue()


class PerfDbTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.runs = self.root / 'build'
        self.store = self.root / 'store'
        self.db_path = self.root / 'perf.db'

    def tearDown(self):
        self.tmp.cleanup()

    def open(self, store=True):
        return perf_db.PerfDb(self.db_path, store=perf_db.Store(self.store) if store else None)

    def count(self, db, table):
        return db.db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]

    def test_schema_tables_views_and_append_only(self):
        db = self.open()
        names = {r[0] for r in db.db.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")}
        for name in ('runs', 'stages', 'gates', 'heap', 'stair', 'sizes', 'cpu_samples', 'source_files', 'run_view',
                     'stage_view', 'heap_view', 'gate_view'):
            self.assertIn(name, names)
        db.ingest_path(make_run(self.runs, RUN_A))
        with self.assertRaises(sqlite3.DatabaseError):
            db.db.execute('UPDATE heap SET peak_bytes = 0')
        with self.assertRaises(sqlite3.DatabaseError):
            db.db.execute('DELETE FROM source_files')
        db.close()

    def test_every_run_file_kind_lands_in_its_table(self):
        db = self.open()
        results = db.ingest_path(make_run(self.runs, RUN_A))
        self.assertEqual(sorted(p.split('/', 2)[2] for p, o in results if o == 'new'), sorted(perf_db.RUN_FILES))
        for table in ('runs', 'stages', 'heap', 'stair', 'sizes', 'metrics', 'reuse'):
            self.assertGreater(self.count(db, table), 0, table)
        q = db.db.execute
        self.assertEqual(q('SELECT peak_bytes, breakdown FROM heap_view WHERE run=? AND frame=?',
                           (RUN_A, BALMORA)).fetchone(), (6226544, '{"models_drawn":200,"terrain_drawn":100}'))
        self.assertEqual(q('SELECT origin FROM heap_view WHERE run=? AND frame=?', (RUN_A, BALMORA)).fetchone()[0],
                         'chim-heap')
        self.assertEqual(q("SELECT failed, covered, untestable, advisory_failures, sampled FROM stair "
                           "WHERE origin='chim-stairs' AND frame=?", (BALMORA,)).fetchone(), (2, 4, 1, 1, 0))
        self.assertEqual(q("SELECT walked, reused, sampled FROM stair WHERE origin='chim-stairs' AND frame='*'")
                         .fetchone(), (1, 1, 1))
        self.assertEqual(q("SELECT walked, reused FROM stair WHERE origin='image-stairs' AND frame='*'").fetchone(),
                         (2557, 39))
        stage = q("SELECT wall_s, cpu_s, cores, peak_rss_bytes, expected_s, expected_basis, fingerprint, origin "
                  "FROM stage_view WHERE run=? AND stage='chim'", (RUN_A,)).fetchone()
        self.assertEqual(stage, (2335.2, 6580.1, 2.8, 3333922816, 2000.0, 'history', 'f2', 'build-state'))
        run = q('SELECT kind, version, commit_hash, result, started_utc, finished_utc, stages_reused, host_load '
                'FROM run_view WHERE run=?', (RUN_A,)).fetchone()
        self.assertEqual(run[:7], ('build', '0.0.36-dev3', 'aaaaaaa', 'passed', '2026-10-10T16:53:34Z',
                                   '2026-10-10T17:33:34Z', 1))
        self.assertIn('busy_percent', run[7])
        sizes = dict(q('SELECT item, bytes FROM size_view WHERE run=?', (RUN_A,)).fetchall())
        self.assertEqual(sizes['image/AmiWind.hdf'], 4026564608)
        self.assertEqual(sizes['partition/AW_WORLD0'], 2013265920)
        self.assertEqual(sizes['chim/frame/frames/x-03/y-02'], 400)
        self.assertEqual(sizes['chim/class/far'], 23476)
        self.assertEqual(sizes['chim/total'], 323356128)
        metrics = dict(q("SELECT scope || ':' || name, value FROM metrics WHERE run=?", (RUN_A,)).fetchall())
        self.assertEqual(metrics['chim-section:meshes.seconds'], 2.0)
        self.assertEqual(metrics['chim-units:terrain.built'], 10)
        self.assertEqual(metrics['chim-visibility:placements_sent_per_view.max'], 7)
        db.close()

    def test_reingest_is_idempotent_and_changed_bytes_are_refused(self):
        run = make_run(self.runs, RUN_A)
        db = self.open()
        db.ingest_path(run)
        before = perf_db.canonical_sha(db.db)
        self.assertTrue(all(o == 'same' for _, o in db.ingest_path(run)))
        self.assertEqual(perf_db.canonical_sha(db.db), before)
        write_json(run / 'chim-world' / 'chim-heap.json', {'frames': [heap_frame(BALMORA, 1)]})
        with self.assertRaises(perf_db.Conflict):
            db.ingest_path(run)
        self.assertEqual(perf_db.canonical_sha(db.db), before)
        db.close()

    def test_ledgers_are_read_in_appended_segments_and_rewrites_are_refused(self):
        ledger = self.root / 'samples.jsonl'
        lines = [json.dumps({'t': f'2026-10-10T22:3{i}:00', 'name': 'HOST', 'cpu_pct': 50.0 + i}) for i in range(3)]
        ledger.write_text('\n'.join(lines[:2]) + '\n' + lines[2][:10], encoding='utf-8', newline='\n')
        db = self.open()
        db.ingest_path(ledger)
        self.assertEqual(self.count(db, 'cpu_samples'), 2)              # the half-written last line waits
        ledger.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
        self.assertEqual(db.ingest_path(ledger), [('ledgers/samples.jsonl', 'new')])
        self.assertEqual(db.ingest_path(ledger), [('ledgers/samples.jsonl', 'same')])
        self.assertEqual([r[0] for r in db.db.execute('SELECT line FROM cpu_samples ORDER BY line')], [1, 2, 3])
        segments = db.db.execute('SELECT byte_offset, first_line, lines FROM source_files ORDER BY id').fetchall()
        self.assertEqual([(s[1], s[2]) for s in segments], [(1, 2), (3, 1)])
        ledger.write_text('\n'.join(lines[1:]) + '\n', encoding='utf-8', newline='\n')
        with self.assertRaises(perf_db.Conflict):
            db.ingest_path(ledger)
        db.close()

    def test_compare_orders_runs_by_start_and_reports_deltas(self):
        make_run(self.runs, RUN_A, balmora_peak=6226544, started='2026-10-10T10:00:00+00:00')
        make_run(self.runs, RUN_B, balmora_peak=6348016, status='failed', started='2026-10-10T12:00:00+00:00')
        db = self.open()
        db.ingest_path(self.runs)
        headers, rows = perf_db.compare(db.db, 'heap.peak', BALMORA + '/frame.ccf')
        self.assertEqual([(r[0], r[4], r[5]) for r in rows], [(RUN_A, 6226544, 0), (RUN_B, 6348016, 121472)])
        headers, rows = perf_db.compare(db.db, 'heap.peak', SEYDA, runs=[RUN_B, RUN_A, 'missing-run'])
        self.assertEqual([r[0] for r in rows], [RUN_B, RUN_A, 'missing-run'])
        self.assertEqual(rows[-1][-1], 'not in the database')
        text = perf_db.table_text(headers, rows)
        self.assertIn('5,670,768', text)
        headers, rows = perf_db.stage_history(db.db, 'chim')
        self.assertEqual([r[0] for r in rows], [RUN_A, RUN_B])
        with self.assertRaises(perf_db.PerfDbError):
            perf_db.compare(db.db, 'heap.nonsense', BALMORA)
        db.close()

    def test_retired_run_archive_matches_its_folder_and_adds_new_runs(self):
        run = make_run(self.runs, RUN_A)
        archive = self.root / 'trials' / f'{RUN_A}.tar.gz'
        archive.parent.mkdir()
        with tarfile.open(archive, 'w:gz') as tar:
            for name in ('build-state.json', 'build-summary.json', 'build-profile.json'):
                tar.add(run / name, arcname=name)
            info = tarfile.TarInfo('logs/01-setup.log')
            info.size = 3
            tar.addfile(info, io.BytesIO(b'log'))
        db = self.open()
        db.ingest_path(run)
        rows_before = self.count(db, 'stages')
        results = db.ingest_path(archive)
        self.assertEqual([o for p, o in results if p.startswith('runs/')], ['same'] * 3)
        self.assertEqual(self.count(db, 'stages'), rows_before)
        self.assertEqual(db.db.execute("SELECT kind, stored FROM source_files WHERE path=?",
                                       (f'archives/{RUN_A}.tar.gz',)).fetchone(), ('archive', 0))
        other = self.root / 'trials' / 'rc1c-a266a40.tar.gz'
        with tarfile.open(other, 'w:gz') as tar:
            tar.add(run / 'build-state.json', arcname='./build-state.json')
        db.ingest_path(other)
        self.assertEqual(db.db.execute("SELECT via FROM source_files WHERE path='runs/rc1c-a266a40/build-state.json'")
                         .fetchone()[0], 'archives/rc1c-a266a40.tar.gz')
        self.assertIsNotNone(db.db.execute("SELECT 1 FROM stage_view WHERE run='rc1c-a266a40'").fetchone())
        db.close()

    def test_rebuild_from_the_store_is_deterministic(self):
        make_run(self.runs, RUN_A)
        make_run(self.runs, RUN_B, balmora_peak=6348016)
        results = self.root / 'results'
        aw_gate_result(results, 1613)
        ledger = self.root / 'gate-ledger.jsonl'
        ledger.write_text(json.dumps({'gate': 815, 'ok': True, 'complete': True, 'tests_run': 1649,
                                      'start': '2026-10-09T05:45:51+03:00', 'wall_seconds': 260.9}) + '\n',
                          encoding='utf-8', newline='\n')
        db = self.open()
        for path in (self.runs, results, ledger):
            db.ingest_path(path)
        live = perf_db.canonical_sha(db.db)
        db.close()
        shas = []
        for name in ('re1.db', 're2.db'):
            code, out, _ = quiet(perf_db.main, ['--store', str(self.store), 'rebuild', '--out', str(self.root / name)])
            self.assertEqual(code, 0)
            again = perf_db.PerfDb(self.root / name, create=False)
            shas.append(perf_db.canonical_sha(again.db))
            again.close()
        self.assertEqual(shas[0], shas[1])
        self.assertEqual(shas[0], live)
        code, _, err = quiet(perf_db.main, ['--store', str(self.store), 'rebuild', '--out', str(self.root / 're1.db')])
        self.assertEqual(code, 2)
        self.assertIn('never overwrites', err)

    def test_gate_results_and_summary(self):
        results = self.root / 'results'
        aw_gate_result(results, 1613)
        aw_gate_result(results, 1771, status='failed', failures=1)
        write_json(results / 'not-a-result.json', {'schema': 'something-else'})
        db = self.open()
        db.ingest_path(results)
        counts, headers, rows = perf_db.gate_summary(db.db, '2026-10-10')
        self.assertEqual(counts, {'failed': 1, 'passed': 1})
        self.assertEqual(sorted(r[1] for r in rows), [1613, 1771])
        self.assertEqual(db.db.execute('SELECT suite_s, engine_warnings FROM gate_view WHERE gate=1613').fetchone(),
                         (82.2, 0))
        with self.assertRaises(perf_db.PerfDbError):
            db.ingest_path(results / 'not-a-result.json')
        db.close()

    def test_running_runs_wait_and_stale_running_states_are_read(self):
        run = make_run(self.runs, RUN_A, status='running')
        db = self.open()
        self.assertEqual(db.ingest_path(run), [(f'runs/{RUN_A}', 'running')])
        old = time.time() - 8 * 3600
        for name in ('build-state.json', 'build-progress.json'):
            os.utime(run / name, (old, old))
        self.assertTrue(any(o == 'new' for _, o in db.ingest_path(run)))
        db.close()

    def test_strict_ingest_refuses_running_runs(self):
        make_run(self.runs, RUN_A, status='running')
        code, _, err = quiet(perf_db.main, ['--db', str(self.db_path), '--store', str(self.store), 'ingest', '--strict',
                                            str(self.runs / RUN_A)])
        self.assertEqual(code, 1)
        self.assertIn('still running', err)

    def test_dump_is_reproducible_and_never_overwritten(self):
        db = self.open()
        db.ingest_path(make_run(self.runs, RUN_A))
        first = perf_db.sql_dump(db.db, self.root / 'a.sql.gz')
        second = perf_db.sql_dump(db.db, self.root / 'b.sql.gz')
        self.assertEqual(first[0], second[0])
        self.assertEqual((self.root / 'a.sql.gz.sha256').read_text(encoding='utf-8'), f'{first[0]}  a.sql.gz\n')
        with gzip.open(self.root / 'a.sql.gz', 'rt', encoding='utf-8') as handle:
            self.assertIn('CREATE TABLE heap', handle.read())
        with self.assertRaises(perf_db.PerfDbError):
            perf_db.sql_dump(db.db, self.root / 'a.sql.gz')
        db.close()

    def test_queries_open_read_only_and_export_csv(self):
        db = self.open()
        db.ingest_path(make_run(self.runs, RUN_A))
        db.close()
        reader = perf_db.PerfDb(self.db_path, create=False)
        with self.assertRaises(sqlite3.OperationalError):
            reader.db.execute("INSERT INTO meta (key, value) VALUES ('x', 'y')")
        reader.close()
        out = self.root / 'csv'
        code, _, _ = quiet(perf_db.main, ['--db', str(self.db_path), 'export', '--csv', str(out)])
        self.assertEqual(code, 0)
        heap = (out / 'heap_view.csv').read_text(encoding='utf-8').splitlines()
        self.assertTrue(heap[0].startswith('run,frame,'))
        self.assertEqual(len(heap), 3)
        code, text, _ = quiet(perf_db.main, ['--db', str(self.db_path), 'run', RUN_A])
        self.assertEqual(code, 0)
        self.assertIn('runs/' + RUN_A + '/build-state.json', text)

    def test_helpers(self):
        self.assertEqual(perf_db.to_utc('2026-10-10 19:52:55 +0300'), '2026-10-10T16:52:55Z')
        self.assertEqual(perf_db.to_utc('2026-10-10T16:53:57+0000'), '2026-10-10T16:53:57Z')
        self.assertEqual(perf_db.to_utc('2026-10-10 03:12 +0300'), '2026-10-10T00:12:00Z')
        self.assertIsNone(perf_db.to_utc('2026-10-08T19:34:49'))
        self.assertEqual(perf_db.frame_key('chim/frames/x-03/y-02/frame.ccf'), BALMORA)
        self.assertEqual(perf_db.frame_key('frames/x-03/y-02/frame.bsp'), BALMORA)
        self.assertEqual(perf_db.run_name('/vol/ws8/build/rc1c-a266a40'), 'rc1c-a266a40')
        self.assertEqual(perf_db.run_name('final34b-3707069 (release, quiet host)'), 'final34b-3707069')
        self.assertEqual(perf_db.run_kind('2026_10_10_v0.0.36-dev3_gate-1613-x_7255e43'), 'gate')
        self.assertEqual(perf_db.run_kind('mw2-033b'), 'miniwind')
        self.assertEqual(perf_db.run_kind(RUN_A), 'build')



class AwPostStepTests(unittest.TestCase):
    """tools/aw.py runs the configured perf database command once per written result and never hides a failure."""

    def run_post(self, config, document, path='result.json'):
        import aw
        return quiet(aw.perf_db_post, config, document, path)

    def test_post_step_fills_the_template_logs_and_reports_failures(self):
        import sys
        with tempfile.TemporaryDirectory() as folder:
            script = ('import sys; print("ingest", " ".join(sys.argv[1:])); '
                      'sys.exit(3 if sys.argv[1] == "build" else 0)')
            config = {'state_dir': folder, 'perf_db': {'command': [sys.executable, '-c', script, '{kind}',
                                                                   '{run_name}', '{run_dir}', '{result}']}}
            gate = {'kind': 'gate', 'run_name': 'g1', 'artifacts': ['C:/x/result.json']}
            code, out, err = self.run_post(config, gate, 'r1.json')
            self.assertEqual(code, 0)
            self.assertIn('aw perf-db: ingest gate g1  r1.json', out)
            build = {'kind': 'build', 'run_name': 'b1', 'artifacts': ['/vol/ws8/build/b1', 'C:/x/b1.json']}
            code, out, err = self.run_post(config, build, 'b1.json')
            self.assertEqual(code, 3)
            self.assertIn('/vol/ws8/build/b1', out)
            self.assertIn('aw perf-db: FAILED (exit 3) for b1', err)
            log = [json.loads(line) for line in (Path(folder) / 'aw-trials.jsonl').read_text().splitlines()]
            self.assertEqual([(r['event'], r['run_name'], r['exit']) for r in log],
                             [('perf-db', 'g1', 0), ('perf-db', 'b1', 3)])
            self.assertIsNone(self.run_post(config, dict(build, dry_run=True))[0])
            self.assertIsNone(self.run_post({'state_dir': folder}, build)[0])
            off = {'state_dir': folder, 'perf_db': dict(config['perf_db'], enabled=False)}
            self.assertIsNone(self.run_post(off, build)[0])


if __name__ == '__main__':
    unittest.main()
