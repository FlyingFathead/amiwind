# SPDX-License-Identifier: GPL-3.0-only
"""The table readers' first-minute check (tools/build_preflight.py EARLY_CHECKS, phase 'inputs').

Every table the image carries is made by a stage that first READS the game's records and then bakes. A reader that
cannot read an expansion's records (a record kind it does not expect, a second record of an id, a cell outside the
base game's grid) used to stop its stage wherever that stage ran in the build. Here the reader half of every table
builder runs on the SELECTED game files before the first stage, without baking and without writing a table, and
every reader that fails is reported together.

READERS lists them: (name, function). A function takes a Selection (the data folder, the masters in load order, the
merged master as bytes and as a file, each master's own bytes) and returns {what it read: how many}; a count named in
its MUST tuple may not be zero (a reader that returns nothing where the game holds rows has stopped reading). A
reader that raises is a problem of that reader; the others still run.

The selection is given to every reader explicitly. A reader that still takes it from the environment
(mwad.masters.MASTERS_ENV) is run with that variable set to the selection and put back afterwards: the 'inputs' phase
runs before the build sets it, and without this such a reader would read the base game alone and pass.

With the base game alone there is nothing to check: the base game's readers are held by the stages' own tests.
A pass is recorded in the workspace by check_key (the selected files' SHA-256 and the readers' own source), so a
build whose game files and readers are the ones already checked does not read them again.
"""
import hashlib
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK_FORMAT = 'aw-table-readers-check-1'
CACHE_FOLDER = 'cache/table-reader-check'
MERGED_FOLDER = 'cache/table-reader-check/merged-masters'


class Selection:
    """The selected game files as the readers take them. DATA: the data folder; MASTERS: the names in load order;
    path: the merged master as a file in MERGED_DIR (mwad.masters.master_path: written once per set of game files
    and found again; the check gives a folder of the build workspace, never the source tree, which may be read-only:
    BUILD-MERGED-MASTER-IN-CHECKOUT-66); raw: its bytes; layers: [(name, bytes)] of each selected master by itself."""

    def __init__(self, data_files, masters, merged_dir):
        from mwad.masters import master_path
        from mwad.paths import child_ci
        self.data = Path(data_files)
        self.masters = tuple(masters)
        self.merged_dir = Path(merged_dir)
        self.path = Path(master_path(self.data, self.masters, self.merged_dir))
        self.raw = self.path.read_bytes()
        self.layers = [(name, child_ci(self.data, name).read_bytes()) for name in self.masters]


# ---------------------------------------------------------------- the readers

def _sizes(got, label):
    """{name: count} of a reader's result for its log line: a dict's sized values by key, a tuple's or list's sized
    parts by position."""
    if isinstance(got, dict):
        parts = [(str(key), value) for key, value in got.items()]
    elif isinstance(got, (tuple, list)):
        parts = [('part %d' % index, value) for index, value in enumerate(got)]
    else:
        parts = [('result', got)]
    return {'%s %s' % (label, name): len(value) for name, value in parts if hasattr(value, '__len__')}


def read_cells(sel):
    """The exterior checklist's cells (tools/exterior_plan.py) and the cells only an expansion adds."""
    import exterior_plan
    cells, _digest = exterior_plan.selected_cells(sel.data, sel.masters, sel.merged_dir)
    return {'exterior cells on the base grid': len(cells)}


read_cells.MUST = ('exterior cells on the base grid',)


def read_survey(sel):
    """The world survey's read of the merged master (tools/survey_vvardenfell.py run: mwad.audit.load_esm)."""
    from mwad.audit import load_esm
    return _sizes(load_esm(sel.path), 'survey')


read_survey.MUST = ()


def read_doors(sel):
    """The load doors as authored (mwad.interior.original_doors: the world door table's and the door check's read)."""
    from mwad.interior import original_doors
    return {'load doors': len(original_doors(sel.raw))}


read_doors.MUST = ('load doors',)


def read_travel(sel):
    """The travel table's read (tools/prepare_travel.py read_masters)."""
    import prepare_travel
    providers, _settings, cells, regions, found = prepare_travel.read_masters(sel.data, sel.masters)
    missing = [name for name in sel.masters if name not in found]
    if missing:
        raise ValueError('selected masters not read: ' + ', '.join(missing))
    return {'travel providers': len(providers), 'cells': len(cells), 'regions': len(regions)}


read_travel.MUST = ('travel providers', 'cells', 'regions')


def read_magic(sel):
    """The magic tables' read (tools/prepare_magic.py read_records; the selection from the environment)."""
    import prepare_magic
    mgef, models, sounds, gmst = prepare_magic.read_records(sel.data)
    return {'magic effects': len(mgef), 'effect models': len(models), 'effect sounds': len(sounds),
            'settings': len(gmst)}


read_magic.MUST = ('magic effects', 'effect models', 'effect sounds', 'settings')


def read_containers(sel):
    """The container census's read (tools/container_census.py census), which is also the focus tables' read of items,
    levelled lists and cells (tools/prepare_focus.py item_lists, objects_of, cells_of)."""
    import container_census
    _masters, records, places = container_census.census(sel.data, sel.masters)
    return {'container records': len(records), 'placed containers': len(places)}


read_containers.MUST = ('container records', 'placed containers')


def read_creatures(sel):
    """The creature census's read of each selected master (tools/creature_census.py uses)."""
    import creature_census
    got = creature_census.uses(sel.layers)
    return {'creature records': len(got['records'])}


read_creatures.MUST = ('creature records',)


def read_journal(sel):
    """The journal's and the region names' read (tools/prepare_world_ui.py journal_assets, region_names)."""
    import prepare_world_ui
    journal = prepare_world_ui.journal_assets(sel.raw)
    regions = prepare_world_ui.region_names(sel.raw)
    return {'journal parts': len(journal) if hasattr(journal, '__len__') else 1,
            'region name bytes': len(regions) if hasattr(regions, '__len__') else 1}


read_journal.MUST = ('journal parts', 'region name bytes')


def read_harvest(sel):
    """The harvest catalogue's read (tools/prepare_harvest.py source_records: plants, their contents, their
    placements)."""
    import prepare_harvest
    return _sizes(prepare_harvest.source_records(sel.raw), 'harvest')


read_harvest.MUST = ()


def read_dialogue(sel):
    """The dialogue tables' read (mwad.npc.load_master; tools/dialogue_lut.py dial_names)."""
    import dialogue_lut
    from mwad.npc import load_master
    kinds, _other, topics = load_master(sel.path)
    return {'record kinds': len(kinds), 'topics': len(topics), 'topic names': len(dialogue_lut.dial_names(sel.path))}


read_dialogue.MUST = ('record kinds', 'topics', 'topic names')


def read_scripts(sel):
    """The script plan's read (tools/mwscript/gamedata.py GameData.load: scripts, records, placements, per master)."""
    from mwscript.gamedata import GameData
    data = GameData()
    data.load(sel.data, sel.masters)
    missing = [name for name in sel.masters if name not in data.master_sha256]
    if missing:
        raise ValueError('selected masters not read: ' + ', '.join(missing))
    return {'scripts': len(data.scripts), 'scripted placements': len(data.references),
            'scripted add-on placements': len(data.addon_references)}


read_scripts.MUST = ('scripts', 'scripted placements', 'scripted add-on placements')


# (name, function): in the order they run, cheapest first
READERS = [
    ('exterior-cells', read_cells),
    ('load-doors', read_doors),
    ('travel', read_travel),
    ('magic', read_magic),
    ('creature-census', read_creatures),
    ('container-census-and-focus', read_containers),
    ('journal-and-regions', read_journal),
    ('harvest', read_harvest),
    ('world-survey', read_survey),
    ('dialogue', read_dialogue),
    ('script-plan', read_scripts),
]


# ---------------------------------------------------------------- the check

class _Environment:
    """MASTERS_ENV set to the selection while the readers run, and put back as it was."""

    def __init__(self, masters):
        from mwad.masters import MASTERS_ENV
        self.name, self.value = MASTERS_ENV, ','.join(masters)

    def __enter__(self):
        self.before = os.environ.get(self.name)
        os.environ[self.name] = self.value
        return self

    def __exit__(self, *exc):
        if self.before is None:
            os.environ.pop(self.name, None)
        else:
            os.environ[self.name] = self.before
        return False


def reader_problems(selection, readers=None, log=print):
    """[problem] of running every reader of READERS on SELECTION; one log line per reader with its counts and time.
    SELECTION: a Selection, or a function that makes it (a failure to make it is the one problem)."""
    problems = []
    try:
        sel = selection() if callable(selection) else selection
    except Exception as exc:                                  # the merge itself is the first reader
        return ['the selected game files cannot be merged and read (mwad.masters): %s: %s'
                % (type(exc).__name__, exc)]
    with _Environment(sel.masters):
        for name, function in (READERS if readers is None else readers):
            started = time.time()
            try:
                counts = function(sel) or {}
            except BaseException as exc:                      # SystemExit too: a reader never ends the build's checks
                if isinstance(exc, KeyboardInterrupt):
                    raise
                problems.append('reader %s (%s.%s) fails on the selected game files %s: %s: %s'
                                % (name, function.__module__, function.__name__, ', '.join(sel.masters),
                                   type(exc).__name__, exc))
                continue
            empty = [key for key in getattr(function, 'MUST', ()) if not counts.get(key)]
            if empty:
                problems.append('reader %s (%s.%s) reads nothing where the game holds rows: %s (selected: %s)'
                                % (name, function.__module__, function.__name__, ', '.join(empty),
                                   ', '.join(sel.masters)))
            log('  table reader %s: %s (%.1f s)' % (name, ', '.join('%d %s' % (n, key) for key, n in counts.items())
                                                    or 'read', time.time() - started))
    return problems


# the readers' own source files (the pass record's key holds their SHA-256: a changed reader is checked again)
SOURCES = (
    'tools/table_reader_check.py', 'tools/exterior_plan.py', 'tools/prepare_travel.py', 'tools/prepare_magic.py',
    'tools/container_census.py', 'tools/creature_census.py', 'tools/prepare_focus.py', 'tools/prepare_world_ui.py',
    'tools/prepare_harvest.py', 'tools/dialogue_lut.py', 'tools/cell_numbers.py', 'tools/mwscript/gamedata.py',
    'src/mwad/masters.py', 'src/mwad/esm.py', 'src/mwad/audit.py', 'src/mwad/interior.py', 'src/mwad/npc.py',
)


def check_key(data_files, masters, root=None):
    """What decides the check's answer: the selected masters' SHA-256 in load order, the readers' source files and
    this check's own format."""
    from mwad.paths import child_ci
    root = Path(root or ROOT)
    inputs = [[name, hashlib.sha256(child_ci(Path(data_files), name).read_bytes()).hexdigest()] for name in masters]
    sources = [[rel, hashlib.sha256((root / rel).read_bytes()).hexdigest()] for rel in sorted(SOURCES)]
    return hashlib.sha256(json.dumps([CHECK_FORMAT, inputs, sources], sort_keys=True).encode()).hexdigest()


def table_readers(context):
    """EARLY_CHECKS entry: every table builder's reader on the selected game files (see the module text). Nothing with
    the base game alone. A problem is never recorded: it is found again until it is fixed."""
    from mwad.masters import is_base_only, selected_masters
    masters = selected_masters(context.masters or None)
    if is_base_only(masters) or not context.data_files:
        return []
    record = None
    if context.workspace is not None:
        record = Path(context.workspace) / CACHE_FOLDER / (check_key(context.data_files, masters) + '.json')
        if record.is_file():
            context.log('Early check table-readers: passed before on these game files and readers (%s)' % record.name)
            return []
    if context.workspace is not None:
        problems = reader_problems(
            lambda: Selection(context.data_files, masters, Path(context.workspace) / MERGED_FOLDER), log=context.log)
    else:                               # no workspace: the merged file lives only as long as the check, in the
        import build_scratch            # builder's scratch folder (never the system temp directory)
        with build_scratch.scratch_dir(prefix='table-readers-', keep_on_failure=False) as scratch:
            problems = reader_problems(lambda: Selection(context.data_files, masters, scratch), log=context.log)
    if not problems and record is not None:
        try:
            record.parent.mkdir(parents=True, exist_ok=True)
            record.write_text(json.dumps({'format': CHECK_FORMAT, 'masters': list(masters), 'result': 'passed',
                                          'readers': [name for name, _ in READERS]}, indent=1) + '\n',
                              encoding='utf-8', newline='\n')
        except OSError:
            pass                        # a workspace that cannot be written: the check runs again next time
    return problems
