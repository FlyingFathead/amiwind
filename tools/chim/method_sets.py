# SPDX-License-Identifier: GPL-3.0-only
"""Named mesh method sets: the methods a listed mesh of Solstheim's stages is made with (config/mesh-method-sets.json;
SOL-GLACIER-METHODS-AB-COMPARE-68).

A set is chosen per build or CHIMport run by name and only reaches the runners of Solstheim's stages and CHIMport
(tools/bloodmoon_solstheim.py, tools/solstheim_test_world.py, tools/chimport.py: their own option --mesh-method-set
NAME, never an option of tools/chim_build.py, whose code keys the base world's stage). A runner installs the set for
its own process before the converter runs and restores everything after it, as it installs the shared unit pool: the
converter's code, the base world's stage and every existing unit kind's code key are unchanged, and a mesh the set
does not name is made as today. The set 'baseline' is today's methods for every mesh.

The methods (METHODS), each a row under the mesh in a set:
- 'C' (chim.collision_exact): the placed collision with exact footing: the walkable pieces kept, the other faces as
  convex proxies tested against today's top on the walkable surface. The converter's variant and tile units of a
  listed mesh run as this method's own unit kinds ('variant-c', 'variant-bsp2-c', 'tiles-budget-c',
  'tiles-budget-union-c'), registered here for the process; the mesh units stay today's units. A mesh the BSP2 union
  list stores tile by tile (config/collision-union-bsp2.json "tiles": the icebergs) goes to its tiles at once: its
  whole variant is not made.
- 'D': the drawn mesh by method 2 (tools/model_method2.py, its unit kind 'mesh-method2'), its row given here and added
  to the method-2 table for the process (model_method2.load_table); the collision stays the source mesh's.

The converter prepares its areas in worker processes when it has more than one (build_parallel spawns them): the
Solstheim runners' unit cache pickles as an installing cache (cache_reduce), so each such worker installs the same set
before it prepares an area. Every unit of method C reports its figures into REPORT_LINES in the converter's output
folder (the report given to install), summed up as REPORT at the end.
"""
import json
from pathlib import Path

from chim.units import PooledUnitCache

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / 'config' / 'mesh-method-sets.json'
FORMAT = 'aw-mesh-method-sets-1'
OPTION = '--mesh-method-set'
BASELINE = 'baseline'
METHODS = ('C', 'D')       # the methods this tree builds
REPORT = 'mesh-method-set.json'
REPORT_LINES = 'mesh-method-set.jsonl'
D_KEYS = ('kind', 'source_sha256', 'recipe', 'source', 'counts', 'ab')
_ACTIVE = None             # (name, table path, report folder) of the set installed in this process


def mesh_path(stem):
    """The model path of a listed mesh (method 2's table key)."""
    return 'meshes/%s.nif' % stem


def load(path=None):
    """The sets file, checked: its format, every set's meshes listed under a layer, every method one this tree has,
    each method's row."""
    from chim.collision_exact import settings as c_settings
    data = json.loads(Path(path or TABLE).read_text(encoding='utf-8'))
    where = path or TABLE
    if data.get('format') != FORMAT:
        raise ValueError('%s: unknown format %r' % (where, data.get('format')))
    listed = {mesh for meshes in (data.get('layers') or {}).values() for mesh in meshes}
    sets = data.get('sets') or {}
    if BASELINE not in sets or sets[BASELINE].get('meshes'):
        raise ValueError('%s: the set %r is today\'s methods and names no mesh' % (where, BASELINE))
    for name, row in sets.items():
        for mesh, methods in (row.get('meshes') or {}).items():
            if mesh not in listed:
                raise ValueError('%s: set %r names %s, which no layer lists' % (where, name, mesh))
            unknown = sorted(set(methods) - set(METHODS))
            if unknown:
                raise ValueError('%s: set %r: method(s) %s of %s are not built by this tree'
                                 % (where, name, ', '.join(unknown), mesh))
            if 'C' in methods:
                c_settings(methods['C'])
            if 'D' in methods:
                d = methods['D']
                missing = [k for k in D_KEYS if k not in d]
                if missing or len(str(d.get('source_sha256', ''))) != 64:
                    raise ValueError('%s: set %r: the D row of %s needs %s (source_sha256: the NIF file\'s SHA-256)'
                                     % (where, name, mesh, ', '.join(D_KEYS)))
    return data


def take(argv):
    """(the set's name or None, ARGV without the option): the runner's own option, never the converter's."""
    argv = list(argv)
    if OPTION not in argv:
        return None, argv
    at = argv.index(OPTION)
    if at + 1 >= len(argv) or argv[at + 1].startswith('--'):
        raise SystemExit('%s needs a set name (config/mesh-method-sets.json)' % OPTION)
    name = argv[at + 1]
    del argv[at:at + 2]
    return name, argv


def out_folder(argv):
    """The converter's --out folder in its arguments ARGV, or None: where a runner's set report goes."""
    for i, part in enumerate(argv):
        if part == '--out' and i + 1 < len(argv):
            return Path(argv[i + 1])
        if part.startswith('--out='):
            return Path(part.split('=', 1)[1])
    return None


def rows(name, path=None):
    """(record, {mesh: C row}, {mesh: D row}) of the set NAME; an unknown set is refused."""
    data = load(path)
    if name not in data['sets']:
        raise SystemExit('%s %s: no such set in %s (sets: %s)' % (OPTION, name, path or TABLE,
                                                                  ', '.join(sorted(data['sets']))))
    meshes = data['sets'][name].get('meshes') or {}
    record = {'set': name, 'meshes': sorted(meshes), 'methods': {mesh: sorted(m) for mesh, m in meshes.items()}}
    c_rows = {mesh: m['C'] for mesh, m in meshes.items() if 'C' in m}
    d_rows = {mesh: m['D'] for mesh, m in meshes.items() if 'D' in m}
    return record, c_rows, d_rows


def install(name, path=None, report=None):
    """Install the set NAME for this process: (record, restore). The record says which set and which meshes it
    makes otherwise; restore puts back everything the set replaced and writes the report (REPORT in the folder
    REPORT, when given). An unknown set is refused."""
    global _ACTIVE
    record, c_rows, d_rows = rows(name, path)
    undo = []
    report = report if c_rows else None      # a set without method C has no figures to report
    if report is not None:
        Path(report).mkdir(parents=True, exist_ok=True)
        (Path(report) / REPORT_LINES).write_text('', encoding='utf-8', newline='\n')
    if c_rows:
        undo.append(_install_c(c_rows, report))
    if d_rows:
        undo.append(_install_d(d_rows))
    before = _ACTIVE
    _ACTIVE = (name, str(path) if path else None, str(report) if report is not None else None)

    def restore():
        global _ACTIVE
        while undo:
            undo.pop()()
        _ACTIVE = before
        if report is not None:
            write_report(record, report)
    return record, restore


def _install_c(c_rows, report):
    """Method C for the meshes of C_ROWS: its unit kinds registered and chim.build.run_units dispatching the listed
    meshes' variant and tile units to them; returns the undo."""
    import chim.build
    from chim import collision_exact as CE
    from chim import units as U
    added = []
    for base, (kind, worker) in CE.KINDS.items():
        if kind not in U.CODE_ENTRIES:
            U.CODE_ENTRIES[kind] = [('tools/chim/collision_exact.py', worker)]
            U.TOOLS[kind] = list(U.TOOLS[base]) + ['tools/chim/collision_exact.py']
            added.append(kind)
    original = chim.build.run_units
    chim.build.run_units = dispatcher(original, c_rows, report)

    def undo():
        chim.build.run_units = original
        for kind in added:
            U.CODE_ENTRIES.pop(kind, None)
            U.TOOLS.pop(kind, None)
    return undo


# kinds whose units are a listed mesh's placed variant made another way (format 0.8, edge bevels, the large-model cut):
# method C does not make them, so a listed mesh on one of them is refused instead of left as today
REFUSED_KINDS = ('variant-bevels', 'variant-placed', 'tiles', 'tiles-bevels', 'tiles-placed', 'tiles-budget-placed',
                 'cut')


def dispatcher(original, c_rows, report=None):
    """chim.build.run_units with the units of the meshes in C_ROWS on method C's kinds (chim.collision_exact.KINDS):
    each such unit keyed by its own key, the method's form and row; every other unit as before. Each C unit's figures
    are taken out of its result and reported."""
    from chim import collision_exact as CE
    from chim.units import fingerprint
    from routed_hull import mesh_stem

    def listed(task):
        model = task.get('model') if isinstance(task, dict) else None
        return mesh_stem(model['source']) if isinstance(model, dict) and model.get('source') else None

    def run_units(kind, items, worker, jobs, cache, soft=None):
        at = [i for i, (_, task) in enumerate(items) if listed(task) in c_rows] if items else []
        if not at:
            return original(kind, items, worker, jobs, cache, soft)
        if kind in REFUSED_KINDS:
            raise ValueError('mesh method C does not make %s units: %s' % (
                kind, ', '.join(sorted({items[i][1]['model']['source'] for i in at}))))
        if kind not in CE.KINDS:
            return original(kind, items, worker, jobs, cache, soft)
        out = [None] * len(items)
        chosen = set(at)
        rest = [i for i in range(len(items)) if i not in chosen]
        for i, result in zip(rest, original(kind, [items[i] for i in rest], worker, jobs, cache, soft) if rest else ()):
            out[i] = result
        c_kind, c_worker = CE.KINDS[kind]
        run = []
        for i in at:
            fp, task = items[i]
            stem = listed(task)
            if kind == 'variant' and task.get('qbsp'):
                from chim.union_bsp2 import tiles_listed
                if tiles_listed(task['model']['source']):
                    # stored as tiles of its own frame, as today (the union list's "tiles"): its whole variant is not
                    # made under method C (chim.build frame_input takes over_budget to the tile kinds)
                    out[i] = {'over_budget': 'mesh method C: stored as tiles of its own frame '
                                             '(config/collision-union-bsp2.json lists it for tiles)'}
                    continue
            row = CE.settings(c_rows[stem])
            run.append((i, (fingerprint(c_kind, fp, CE.FORM, row), dict(task, collision_exact_row=row))))
        if run:
            for (i, (_, task)), result in zip(run, original(c_kind, [item for _, item in run], getattr(CE, c_worker),
                                                            jobs, cache, soft)):
                result, figures = CE.take_figures(result)
                out[i] = result
                if figures is not None:
                    note(report, kind, task, figures)
        return out
    run_units.dispatching = c_rows
    return run_units


def note(report, kind, task, figures):
    """One C unit's figures: printed, and a line in REPORT_LINES of the report folder."""
    from chim.build import variant_key, variant_name
    try:
        name = variant_name(task['model'], variant_key(task['ref']))
    except (KeyError, TypeError, ValueError):       # a placement record without the fields a name reads
        name = '%s@%s' % (task['model']['source'], task['ref'].get('number'))
    row = {'kind': kind, 'mesh': task['model']['source'], 'variant': name, 'figures': figures}
    print('[method C] %s: %d pieces of %d (kept %d, proxies %d, back %d); walkable cells %d, over 8 game units %d, '
          'lost %d, largest move %.1f' % (name, figures.get('pieces', 0), figures.get('pieces_today', 0),
                                          figures.get('kept', 0), figures.get('proxies', 0), figures.get('back', 0),
                                          figures.get('walkable_cells', 0), figures.get('over_8_cells', 0),
                                          figures.get('lost_cells', 0), figures.get('largest_move', 0.0)), flush=True)
    if report is not None:
        line = json.dumps(row, sort_keys=True) + '\n'
        with open(Path(report) / REPORT_LINES, 'a', encoding='utf-8', newline='\n') as stream:
            stream.write(line)


def write_report(record, report):
    """REPORT in the folder REPORT: the set and every C unit's figures (the last line per variant and kind), with the
    walkable surface summed up per mesh."""
    path = Path(report) / REPORT_LINES
    units = {}
    if path.is_file():
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.strip():
                row = json.loads(line)
                units[(row['kind'], row['mesh'], row['variant'])] = row
    by_mesh = {}
    for row in units.values():
        f = row['figures']
        m = by_mesh.setdefault(row['mesh'], {'units': 0, 'walkable_cells': 0, 'over_8_cells': 0, 'lost_cells': 0,
                                             'pieces_today': 0, 'pieces': 0, 'largest_move': 0.0, 'largest_at': None})
        m['units'] += 1
        for k in ('walkable_cells', 'over_8_cells', 'lost_cells', 'pieces_today', 'pieces'):
            m[k] += int(f.get(k) or 0)
        if float(f.get('largest_move') or 0) >= m['largest_move']:
            m['largest_move'] = float(f.get('largest_move') or 0)
            m['largest_at'] = {'variant': row['variant'], 'local_game_units': f.get('largest_at')}
    for m in by_mesh.values():
        m['within_8_share'] = round(1 - m['over_8_cells'] / m['walkable_cells'], 6) if m['walkable_cells'] else None
    out = {'format': 'aw-mesh-method-set-report-1', 'set': record, 'meshes': by_mesh,
           'units': sorted(units.values(), key=lambda r: (r['mesh'], r['variant'], r['kind']))}
    (Path(report) / REPORT).write_text(json.dumps(out, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    return out


def _install_d(d_rows):
    """Method D for the meshes of D_ROWS: their rows added to method 2's table for this process; returns the undo."""
    import model_method2
    original = model_method2.load_table
    added = {mesh_path(stem): dict(row, method=row.get('method', 2)) for stem, row in d_rows.items()}

    def load_table(path=None):
        data = original(path)
        clash = sorted(set(added) & set(data['models']))
        if clash:
            raise ValueError('mesh method D: config/model-method-2.json already has a row for %s' % ', '.join(clash))
        for source, row in added.items():
            if row.get('kind') not in model_method2.KINDS or row.get('panels', 'baked') not in ('baked', 'frosted'):
                raise ValueError('mesh method D %s: kind and panels as config/model-method-2.json takes them' % source)
        return dict(data, models=dict(data['models'], **added))
    model_method2.load_table = load_table

    def undo():
        model_method2.load_table = original
    return undo


class SetPooledUnitCache(PooledUnitCache):
    """The Solstheim runners' pooled unit cache while a set is installed: pickled into a worker process (the
    converter's area workers), it installs the same set there first (cache_reduce)."""

    def __reduce__(self):
        return cache_reduce(PooledUnitCache, (self.folder, self.pool), self.__dict__)


def cache_reduce(cls, args, state):
    """How the runners' pooled unit cache pickles (bloodmoon_solstheim.pooled_units): as CLS(*ARGS) with STATE when
    no set is installed in this process (the form before), else as an installing cache (worker_cache)."""
    if _ACTIVE is None or cls is not PooledUnitCache:
        return cls, args, state
    return worker_cache, (tuple(args), *_ACTIVE), state


def worker_cache(args, name, path, report):
    """The pooled cache in a worker process, with the set NAME installed there first (for the process's lifetime:
    a converter worker belongs to the stage that started it)."""
    if _ACTIVE is None:
        install_here(name, path, report)
    elif _ACTIVE[0] != name:
        raise ValueError('mesh method set %s handed to a process that holds %s' % (name, _ACTIVE[0]))
    return SetPooledUnitCache(*args)


def install_here(name, path=None, report=None):
    """install for a worker process: no restore, no report file of its own (its units' lines go to the folder's
    REPORT_LINES, which the installing runner sums up)."""
    global _ACTIVE
    record, c_rows, d_rows = rows(name, path)
    if c_rows:
        _install_c(c_rows, report)
    if d_rows:
        _install_d(d_rows)
    _ACTIVE = (name, path, report)
    print('mesh method set %s installed in worker process' % name, flush=True)
    return record


def line(record):
    """The runner's line on the set it built with."""
    if not record['meshes']:
        return 'mesh method set %s: today\'s methods for every mesh' % record['set']
    return 'mesh method set %s: %s' % (record['set'], '; '.join(
        '%s %s' % (mesh, ', '.join(record['methods'][mesh])) for mesh in record['meshes']))
