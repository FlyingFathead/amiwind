# SPDX-License-Identifier: GPL-3.0-only
"""The expansions' first-minute checks (tools/build_preflight.py EARLY_CHECKS, phase 'inputs').

What can only fail on an expansion's data fails here, before any stage, with every problem collected:

- presented_exteriors: the interior cells that behave like an exterior (Mournhold's districts) can be presented as
  exterior cell blocks from the SELECTED game files (tools/presented_exterior.py): no block touches a cell of the
  game's own grid, no cell is larger than the largest block, and the cells that config/visual-recipes.json gives the
  districts' recipe to are exactly the presented blocks' cells (a district cell without the recipe would meet the
  collision surface gate without its rows, a recipe cell that is no district would get rows it was not measured
  for).

Each function takes an EarlyContext and returns a list of problems; it never exits. With the base game alone there is
nothing to check.
"""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DISTRICT_RECIPE = 'mournhold-v1'


def recipe_cells(recipe=DISTRICT_RECIPE, path=None):
    """The cells config/visual-recipes.json gives RECIPE to, as (x, y)."""
    doc = json.loads(Path(path or ROOT / 'config' / 'visual-recipes.json').read_text(encoding='utf-8'))
    return {tuple(int(v) for v in key.split(',')) for key, row in (doc.get('cell_settings') or {}).items()
            if isinstance(row, dict) and row.get('visual_recipe') == recipe}


NO_LAND = 'no_land'


def no_land_cells(path=None):
    """The cells config/visual-recipes.json marks as having no LAND record by design (cell_settings "no_land": the
    regions preflight and the CHIM stage admit such a cell without terrain, tools/chim/regions.py), as (x, y)."""
    doc = json.loads(Path(path or ROOT / 'config' / 'visual-recipes.json').read_text(encoding='utf-8'))
    return {tuple(int(v) for v in key.split(',')) for key, row in (doc.get('cell_settings') or {}).items()
            if isinstance(row, dict) and row.get(NO_LAND)}


def block_cells(receipt):
    """The exterior cells of a presentation receipt's blocks, as (x, y)."""
    return {(row['block'][0] + dx, row['block'][1] + dy) for row in receipt.get('cells', ())
            for dx in range(row['size'][0]) for dy in range(row['size'][1])}


def presented_problems(merged, tribunal, recipes=None, config=None):
    """[problem] of presenting the merged master MERGED (bytes); TRIBUNAL: whether Tribunal is selected (the districts'
    recipe cells are held against the blocks only then)."""
    import presented_exterior
    try:
        _, receipt = presented_exterior.present(merged, config or presented_exterior.load_config())
    except ValueError as exc:
        return ['the selected game files cannot be presented (tools/presented_exterior.py, '
                'config/presented-exteriors.json): %s' % exc]
    problems = []
    if tribunal:
        blocks, listed = block_cells(receipt), recipe_cells(path=recipes)
        missing, extra = sorted(blocks - listed), sorted(listed - blocks)
        if missing:
            problems.append('presented cells without the districts\' recipe %s in config/visual-recipes.json '
                            'cell_settings: %s' % (DISTRICT_RECIPE, ', '.join('%d,%d' % c for c in missing)))
        if extra:
            problems.append('cells with the districts\' recipe %s that are no presented cell: %s'
                            % (DISTRICT_RECIPE, ', '.join('%d,%d' % c for c in extra)))
        # a presented cell has no LAND record (its ground is placed models): exactly these cells are admitted
        # without terrain; a cell of the game's own grid marked so would be converted without its land
        bare = no_land_cells(recipes)
        unmarked, wrong = sorted(blocks - bare), sorted(bare - blocks)
        if unmarked:
            problems.append('presented cells without "%s" in config/visual-recipes.json cell_settings (the CHIM '
                            'stage would refuse them: no LAND record): %s'
                            % (NO_LAND, ', '.join('%d,%d' % c for c in unmarked)))
        if wrong:
            problems.append('cells marked "%s" that are no presented cell (they would be converted without their '
                            'terrain): %s' % (NO_LAND, ', '.join('%d,%d' % c for c in wrong)))
    return problems


# A selected master's named set of cells (tools/chim/regions.py layer_sets) -> the build module that builds its
# finished cells and the option value that holds the module's cells (tools/build.py "THE EXPANSIONS AS BUILD
# MODULES"). A master with a named set and no module here is reported, never failed: its module is not built yet.
SET_MODULES = {'Tribunal.esm': ('tribunal-mournhold', 'tribunal_mournhold_cells'),
               'Bloodmoon.esm': ('bloodmoon-solstheim', 'bloodmoon_solstheim_cells')}
# Where each module's cells are resolved, for the problem text
MODULE_RESOLVERS = {'tribunal-mournhold': 'tools/build.py resolve_tribunal_mournhold',
                    'bloodmoon-solstheim': 'tools/bloodmoon_solstheim_module.py resolve'}


def set_plan(name, status_path):
    """The regions preflight's table of the named set NAME against the tracker file STATUS_PATH, by its module's own
    rule: Solstheim's module also takes its open-sea cells with a record from its explicit list
    (tools/bloodmoon_solstheim_module.py module_plan, CHIM-SEA-BETWEEN-ISLANDS-64)."""
    from chim import regions as chim_regions
    if name == chim_regions.layer_sets().get('Bloodmoon.esm'):
        import bloodmoon_solstheim_module
        return bloodmoon_solstheim_module.module_plan(status_path)[0]
    return chim_regions.plan([name], status_path, towns=())[0]


def finished_set_cells(name, status_path):
    """The cells of the named set NAME that the tracker file STATUS_PATH calls finished (the cells a build takes), as
    (x, y), sorted, with the open-sea cells its module names explicitly (set_plan); the set's own preflight problems
    are not this check's."""
    from chim import regions as chim_regions
    return sorted(chim_regions.table_kinds(set_plan(name, status_path)))


def left_out_text(name, status_path, limit=6):
    """One line on the cells of the named set NAME that a build leaves out, grouped by reason (the regions preflight's
    dropped list: not finished, open sea not listed), so the log names every space of the set it does not build (the
    project's full-parity rule: every space of a shipped master is built); '' when none, or when the tracker file
    cannot be read here."""
    try:
        dropped = set_plan(name, status_path)['dropped']
    except (OSError, ValueError, KeyError):
        return ''
    if not dropped:
        return ''
    groups = {}
    for row in dropped:
        reason = str(row.get('reason') or '')
        reason = reason.split(': ', 1)[1] if ': CHIMport' in reason else reason    # the region name in front
        groups.setdefault(reason.split(' (')[0][:90], []).append('%d,%d' % tuple(row['cell']))
    return '; %d left out: %s' % (len(dropped), '; '.join(
        '%d %s (%s%s)' % (len(cells), reason, ' '.join(cells[:limit]), ' ...' if len(cells) > limit else '')
        for reason, cells in sorted(groups.items())))


PRIVATE_TEST_VERSION = re.compile(r'[0-9]+\.[0-9]+\.[0-9]+-dev[0-9]+')   # project_version's private-test rule


def sol_test_reason(args, version=None):
    """The stated reason a Solstheim test image (--chim-sol-test) takes none of Solstheim's finished cells: the
    module's own NOT BUILT record (tools/bloodmoon_solstheim_module.py resolve, args.bloodmoon_solstheim_record), on
    a development version only (VERSION, default project_version.run_version). None otherwise: without the option or
    the record, or on a release candidate or final, the refusal stands (CHIM-SOL-TEST-TWO-CHIMSOL-STORES-68)."""
    record = getattr(args, 'bloodmoon_solstheim_record', None)
    if not getattr(args, 'chim_sol_test', None) or not isinstance(record, dict) or record.get('built') is not False:
        return None
    if version is None:
        import project_version
        version = project_version.run_version()
    if not PRIVATE_TEST_VERSION.fullmatch(str(version)):
        return None
    return ('--chim-sol-test: a test image of named Solstheim cells, the module left out; a development build only, '
            'refused for release candidates and finals')


def module_set_problems(masters, args, status_path, log=print, version=None):
    """[problem]: a selected master whose named set has finished cells and whose module takes none of them, without
    a stated reason (the module switched off, a cell list of the caller's own, a MiniWind sandbox, a Solstheim test
    image on a development version: sol_test_reason). One line per selected master with a named set, so the build
    log always says what happens to an expansion's cells. VERSION: for sol_test_reason."""
    from chim import regions as chim_regions
    problems = []
    sets = chim_regions.layer_sets()
    for master in masters:
        if master not in sets:
            continue
        cells = finished_set_cells(sets[master], status_path)
        if master not in SET_MODULES:
            log('Expansion cells: %s, named set %s: %d finished cell(s), NOT built: no build module takes them yet'
                % (master, sets[master], len(cells)))
            continue
        module, attribute = SET_MODULES[master]
        taken = getattr(args, attribute, None)
        if taken:
            from chim.regions import decode_cells
            count = len(decode_cells(taken))
            log('Expansion cells: %s, named set %s: %d finished cell(s), %d built by the module %s%s'
                % (master, sets[master], len(cells), count, module, left_out_text(sets[master], status_path)))
            if count != len(cells):
                problems.append('%s: the module %s takes %d cell(s) of the named set %s, the tracker file calls %d '
                                'finished' % (master, module, count, sets[master], len(cells)))
            continue
        # --presented-exteriors off switches off only the module of the presented districts (Mournhold's)
        reason = ('--presented-exteriors off' if module == 'tribunal-mournhold'
                  and (getattr(args, 'presented_exteriors', None) or 'on') == 'off'
                  else '--chim-regions names the cells of this build' if getattr(args, 'chim_regions', None)
                  else 'a MiniWind sandbox' if getattr(args, 'miniwind', False)
                  else sol_test_reason(args, version) if module == 'bloodmoon-solstheim' else None)
        if not cells or reason:
            log('Expansion cells: %s, named set %s: %d finished cell(s), none built (%s)'
                % (master, sets[master], len(cells), reason or 'none finished'))
            continue
        problems.append('%s is selected and its named set %s has %d finished cell(s), but the module %s takes none '
                        'of them: this build would hold no %s cell (%s)'
                        % (master, sets[master], len(cells), module, sets[master], MODULE_RESOLVERS[module]))
    return problems


def module_sets(context):
    """EARLY_CHECKS entry: every selected master's named set is built by its module, or the log says why not
    (module_set_problems). Only a full CHIM build has region cells."""
    from mwad.masters import is_base_only, selected_masters
    masters = selected_masters(context.masters or None)
    args = context.args
    if is_base_only(masters) or args is None or getattr(args, 'chim_regions_cells', None) is None:
        return []
    status = getattr(args, 'chim_regions_status', None) or ROOT / 'docs' / 'chim' / 'cell-progress-reference.json'
    return module_set_problems(masters, args, status, context.log)


# The modules whose world the image installs as a store of its own with its own frame maps: the option value that
# holds the module's cells -> its store (tools/chim/layer_stores.py MODULE_STAGES, tools/chim/sol_test.py LANDS).
MODULE_STORES = {'tribunal_mournhold_cells': 'chimmh', 'bloodmoon_solstheim_cells': 'chimsol',
                 # the recordless open sea of the area Bloodmoon adds to the map's box (SOL-SEA-CROSSING-68)
                 'bloodmoon_solstheim_sea_cells': 'chimsea'}


def module_map_names(cells_text, store, offset=0):
    """The frame map names the image gives a module's cells (CELLS_TEXT: "x,y:k ..."), in its world table's order:
    the names tools/chim/layer_stores.py install and frame_holders use (mh0000, mh0001, ...). OFFSET: the frame maps
    of the land whose numbering this one continues (tools/chim/sol_test.py LANDS 'after': the sea after Solstheim)."""
    from chim import regions
    from chim.sol_test import LANDS, map_name
    land = LANDS[store]
    # the recordless open sea after every other cell (the "|" part), as the module's world table orders it
    table = regions.ownership(regions.decode_cells(cells_text), {'values': ['module']},
                              after=regions.decode_after(cells_text))
    return [map_name(offset + index, land['prefix'], land['limit']) for index, _frame in enumerate(table['frames'])]


def finalize_table_problems(names, store):
    """[problem]: a table the image's LAST steps build that does not know a module's frame map NAMES, found from
    the names alone, in seconds. The image step meets these tables only after every stage has run: an image stopped
    there 1 h 34 min into a build, in the door check's job table, on the first frame map of Mournhold's districts
    (DOOR-CHECK-MODULE-FRAME-MAPS-67). Checked here with the image step's own code:
    - the engine's map names (aw_maps.h through tools/door_audit.py): every name is a map the engine can load;
    - the door check's job table (tools/door_engine_check.py job_lines): a door in such a frame gets a row with
      its reason, and the table is built without an error;
    - the disk layout (tools/layout_plan.py): the module's store moves as one folder."""
    import door_audit
    import door_engine_check
    import layout_plan
    problems = []
    source = ROOT / 'engine' / 'aga' / 'src'
    try:
        engine = door_audit.engine_map_names((source / 'aw_maps.h').read_text(encoding='utf-8', errors='replace'),
                                             (source / 'aw_town_table.h').read_text(encoding='utf-8',
                                                                                    errors='replace'))
        unknown = [n for n in names if door_audit.terrain_id(n) < 0 or not door_audit.map_valid(n, engine)]
    except (OSError, ValueError, KeyError) as exc:
        unknown, problems = [], ['the engine\'s map names cannot be read for the module\'s frame maps: %r' % exc]
    if unknown:
        problems.append('frame maps of the store %s the engine does not know as maps (aw_maps.h AW_TerrainId): %s'
                        % (store, ', '.join(unknown)))
    # one door in each of the module's frames, against an open-world directory that holds none of them (as the
    # image's is when the door check runs)
    rows = [{'reference': index + 1, 'holder': name, 'holder_kind': 'region',
             'bank': {'box': [[0.0, 0.0, 0.0], [8.0, 8.0, 64.0]], 'target': '-', 'arrival': [0.0, 0.0, 0.0]}}
            for index, name in enumerate(names)]
    directory = [('vf0000', [0.0, 0.0, 0.0], [-1024.0, -1024.0, 1024.0, 1024.0])]
    try:
        planned = door_engine_check.job_lines(rows, lambda name: None, directory)
        silent = [row['holder'] for row, line, why in planned if line is None and not why]
        if len(planned) != len(rows) or silent:
            problems.append('the door check\'s job table gives no row or no reason for the frame maps %s'
                            % ', '.join(silent or names))
    except Exception as exc:        # any error here is the late failure this check exists to find early
        problems.append('the door check\'s job table (tools/door_engine_check.py job_lines) stops on a frame map of '
                        'the store %s: %s: %s' % (store, type(exc).__name__, exc))
    folder = 'id1/%s/' % store
    if layout_plan.movable_unit(folder + 'world.cwi') != folder:
        problems.append('the disk layout does not move the store folder %s as one unit (tools/layout_plan.py '
                        'STORE_UNITS)' % folder)
    return problems


def module_frame_maps(context):
    """EARLY_CHECKS entry: every table the image's last steps build knows the frame maps of the modules this build
    installs as stores of their own (finalize_table_problems). Nothing to check without such a module."""
    args = context.args
    problems = []
    from chim.regions import decode_cells
    from chim.sol_test import LANDS
    for attribute, store in MODULE_STORES.items():
        cells = getattr(args, attribute, None) if args is not None else None
        if not cells:
            continue
        # a land that continues another's numbering (LANDS 'after'): its names start after the other's frames
        after = LANDS[store].get('after')
        before = next((getattr(args, a, None) for a, s in MODULE_STORES.items() if s == after), None) if after else None
        names = module_map_names(cells, store, len(decode_cells(before)) if before else 0)
        context.log('Early check module-frame-maps: store %s, %d frame maps (%s .. %s) against the engine\'s map '
                    'names, the door check\'s job table and the disk layout' % (store, len(names), names[0], names[-1]))
        problems += finalize_table_problems(names, store)
    return problems


# A module's world stage -> its store: right after the stage has passed, its maps are tried against the image's
# last per-map checks (module_store_after).
MODULE_WORLD_STAGES = {'tribunal-mournhold': 'chimmh', 'bloodmoon-solstheim': 'chimsol',
                       'bloodmoon-solstheim-sea': 'chimsea'}


def store_unit_problem(store, sizes, headroom_mib=None, limit=None):
    """None, or the problem of a module's store whose files (SIZES, bytes each) do not fit ONE partition below LIMIT
    with HEADROOM_MIB free: the disk layout moves a store as one unit (tools/layout_plan.py movable_unit) and never
    splits it, so such a store stops the image step in its last minutes. Counted as the planner counts: classic FFS
    blocks per file, the default headroom and the 2 GiB limit unless given."""
    import layout_plan
    headroom_mib = layout_plan.DEFAULT_HEADROOM_MIB if headroom_mib is None else int(headroom_mib)
    limit = layout_plan.PARTITION_LIMIT if limit is None else int(limit)
    blocks = sum(layout_plan.file_blocks(size) for size in sizes)
    mib = layout_plan.size_mib(blocks, headroom_mib * layout_plan.MIB)
    if mib * layout_plan.MIB < limit:
        return None
    return ('the store %s is %d bytes in %d files: with %d MiB headroom it needs a %d MiB partition, and a store '
            'moves as one unit that must stay below %d bytes (2 GiB): split the store or reduce its frames before '
            'the image step' % (store, sum(sizes), len(sizes), headroom_mib, mib, limit))


def store_map_problems(world, store, scratch, jobs=1, log=print):
    """[problem] of the image's last per-map checks on a module's REAL frame maps, minutes after its stage has passed
    instead of in the image step an hour later (DOOR-CHECK-MODULE-FRAME-MAPS-67). WORLD: the stage's output folder;
    SCRATCH: an empty folder. The store is installed into SCRATCH/id1 with the image's own code
    (tools/chim/layer_stores.py install: the store, its frame maps, its rows file, the 32 MB marks, the flames), then,
    each on its own and every failure collected:
    - the engine's per-map tables (tools/map_engine_limits.py check_maps);
    - the shared exterior sky in every frame map (tools/frame_sky_check.py);
    - the engine's map names for the files written, and the rows file's form;
    - the door check's job table for a door in each of the frames (tools/door_engine_check.py job_lines);
    - the disk layout: the store moves as one folder (tools/layout_plan.py);
    - the effect links' reader of frame maps (tools/effect_links.py frame_maps).
    Proven on a build's real districts before it was registered (8 probes, about 5 s in all)."""
    from pathlib import Path as _Path
    world, id1 = _Path(world), _Path(scratch) / 'id1'
    problems = []

    def tried(name, function):
        try:
            said = function()
            log('  %s: %s' % (name, said))
        except Exception as exc:        # each check's failure is one problem; the next check still runs
            problems.append('%s on the frame maps of the store %s: %s: %s' % (name, store, type(exc).__name__, exc))

    from chim import layer_stores
    value = '%s=%s' % (store, world)
    try:
        records = layer_stores.install([value], id1, {})
        holders = layer_stores.frame_holders([value])
    except Exception as exc:
        return ['the image\'s install of the store %s from %s stops: %s: %s' % (store, world, type(exc).__name__, exc)]
    maps = id1 / 'maps'
    log('  store %s installed: %d files, %d frame maps' % (store, records[0]['files'], len(records[0]['maps'])))

    def limits():
        from map_engine_limits import check_maps
        return '%d maps fit the engine\'s tables' % check_maps(maps, None, jobs=jobs)['maps']

    def sky():
        import frame_sky_check
        missing = frame_sky_check.frame_maps_without_sky(maps)
        if missing:
            raise ValueError(frame_sky_check.problem_text(missing, 'the store\'s maps'))
        return 'every frame map names the shared exterior sky'

    def names():
        import door_audit
        source = ROOT / 'engine' / 'aga' / 'src'
        engine = door_audit.engine_map_names((source / 'aw_maps.h').read_text(encoding='utf-8', errors='replace'),
                                             (source / 'aw_town_table.h').read_text(encoding='utf-8',
                                                                                    errors='replace'))
        unknown = sorted(p.stem for p in maps.iterdir() if not door_audit.map_valid(p.stem, engine))
        if unknown:
            raise ValueError('maps the engine does not know: %s' % ', '.join(unknown))
        from chim.sol_test import LANDS
        raw = (id1 / LANDS[store]['directory']).read_bytes()
        count = int.from_bytes(raw[4:8], 'little')
        if raw[:4] != b'AWS1' or len(raw) != 8 + 52 * count or count != len(holders):
            raise ValueError('the rows file does not hold one 52-byte row per frame (%d rows, %d bytes, %d frames)'
                             % (count, len(raw), len(holders)))
        return 'the engine knows every map name; the rows file holds %d rows' % count

    def doors():
        frames = sorted(name for name, _origin in holders.values())
        left = finalize_table_problems(frames, store)
        if left:
            raise ValueError('; '.join(left))
        return 'the door check\'s job table lists a door in each of the %d frames' % len(frames)

    def effects():
        import effect_links
        return '%d frame maps read for the effect links' % len(effect_links.frame_maps(id1))

    def one_partition():
        # the store moves as ONE unit (layout_plan.movable_unit): with the default headroom it has to fit one
        # partition below 2 GiB, or the image step refuses it at the very end ("does not fit one partition")
        problem = store_unit_problem(store, [size for _path, size in layout_plan_walk(id1 / store)])
        if problem:
            raise ValueError(problem)
        return 'the store fits one partition below 2 GiB with its headroom (%d bytes)' % records[0]['bytes']

    def layout_plan_walk(folder):
        import layout_plan
        return layout_plan.walk(folder)

    for name, function in (('the disk layout\'s one-partition limit', one_partition),
                           ('the engine\'s per-map tables', limits), ('the frame map sky check', sky),
                           ('the engine\'s map names and the rows file', names), ('the door check\'s job table', doors),
                           ('the effect links\' frame map reader', effects)):
        tried(name, function)
    return problems


def module_store_after(context):
    """EARLY_CHECKS entry, phase after:<a module's world stage>: store_map_problems on the stage's output in this
    run, in a scratch folder that is removed afterwards. Nothing to check without the stage's output."""
    problems = []
    from build_scratch import scratch_dir
    for stage, store in MODULE_WORLD_STAGES.items():
        world = Path(context.run) / stage if context.run is not None else None
        if world is None or not (world / 'chim' / 'world.cwi').is_file():
            continue
        with scratch_dir(prefix='module-store-check-', keep_on_failure=False) as scratch:
            problems += store_map_problems(world, store, scratch, log=context.log)
    return problems


CHECK_FORMAT = 'aw-presented-exteriors-check-2'      # 2: the no-LAND mark is held against the blocks too
CACHE_FOLDER = 'cache/expansion-preflight'


def check_key(data_files, masters, config=None, recipes=None):
    """What decides the check's answer: the selected masters' SHA-256 in load order, the presentation's format and
    block config, the districts' recipe cells and this check's own format."""
    import hashlib
    import presented_exterior
    from mwad.paths import child_ci
    inputs = [[name, hashlib.sha256(child_ci(Path(data_files), name).read_bytes()).hexdigest()] for name in masters]
    value = [CHECK_FORMAT, presented_exterior.FORMAT, config or presented_exterior.load_config(), inputs,
             sorted(recipe_cells(path=recipes)), sorted(no_land_cells(recipes))]
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def presented_exteriors(context):
    """EARLY_CHECKS entry: the presentation of the selected game files (see the module text). A pass is recorded in
    the workspace by check_key, so a build whose game files, block config and recipe cells are the ones already
    checked does not present them again (the check takes about 11 s on the three game files, the key under 1 s). A
    problem is never recorded: it is found again until it is fixed."""
    from mwad.masters import is_base_only, master_bytes, selected_masters
    masters = selected_masters(context.masters or None)
    if is_base_only(masters) or not context.data_files:
        return []
    record = None
    if context.workspace is not None:
        record = Path(context.workspace) / CACHE_FOLDER / (check_key(context.data_files, masters) + '.json')
        if record.is_file():
            context.log('Early check presented-exteriors: passed before on these game files (%s)' % record.name)
            return []
    tribunal = any(name.casefold() == 'tribunal.esm' for name in masters)
    problems = presented_problems(master_bytes(context.data_files, masters), tribunal)
    if not problems and record is not None:
        try:
            record.parent.mkdir(parents=True, exist_ok=True)
            record.write_text(json.dumps({'format': CHECK_FORMAT, 'masters': list(masters), 'result': 'passed'},
                                         indent=1) + '\n', encoding='utf-8', newline='\n')
        except OSError:
            pass                        # a workspace that cannot be written: the check runs again next time
    return problems


def module_places(module_master, cells_text, config=None):
    """The presented cells a module's build converts whole, as the stages read them from the data stage's receipt
    (presented_exterior.build_places), made here from the module's own merged master MODULE_MASTER (bytes) before
    any stage has run: the blocks are plan()'s, by the cells' sorted names."""
    import presented_exterior as pe
    found = pe.flagged_cells(module_master)
    plan = pe.plan(found, config or pe.load_config())
    receipt = {'cells': [dict(plan[key], cell=found[key]['name']) for key in sorted(plan)]}
    return pe.build_places(receipt, pe.cells_of_text(cells_text))[0]


def district_table_problems(merged, places, log=print):
    """[problem] of keying the placed things of the presented districts PLACES outdoors (tools/prepare_focus.py
    cells_presented), held against the districts' own cells of the merged master MERGED (bytes), per district:
    - every reference of the cell is in exactly one cell of its block (none lost, none twice);
    - the focus rows under the block's keys are the rows the cell gives as a room, by count and by kind, and none
      is left under a room number;
    - a block cell's rows, the 3 x 3 window around it and its placed items fit the engine's tables.
    One log line per district with its counts."""
    import prepare_focus as pf
    problems = []
    numbers = {key: index + 1 for index, key in enumerate(sorted(places))}
    try:
        objects = pf.objects_of(merged, pf.item_lists(merged))
        as_rooms = pf.placements(merged, objects, numbers)
        outdoors = pf.placements(merged, objects, numbers, presented=places)
    except (SystemExit, ValueError) as exc:
        return ['the districts\' placed things cannot be keyed outdoors (tools/prepare_focus.py): %s' % exc]
    own = {cell.casefold(): len(refs) for cell, interior, _g, _r, refs in pf.cells_of(merged)
           if interior and cell.casefold() in places}
    moved = {}
    for cell, interior, _grid, _region, refs in pf.cells_presented(merged, places):
        if not interior and cell.casefold() in places:
            moved[cell.casefold()] = moved.get(cell.casefold(), 0) + len(refs)
    counts = pf.presented_counts(outdoors, numbers, places)
    sizes = {key: len(rows) for key, rows in outdoors.items()}
    items = {key: sum(1 for row in rows if row[0] == 'I') for key, rows in outdoors.items()}
    for key, place in sorted(places.items()):
        name, row = place['cell'], counts[place['cell']]
        before = as_rooms.get(numbers[key], [])
        kinds = {}
        for r in before:
            kinds[r[0]] = kinds.get(r[0], 0) + 1
        log('District tables: %s: %d references, %d placed things outdoors %s in cells %s'
            % (name, own.get(key, 0), row['rows'], row['kinds'], row['cells']))
        if key not in own:
            problems.append('%s: the selected game files hold no such interior cell' % name)
            continue
        if moved.get(key, 0) != own[key]:
            problems.append('%s: %d references in its cell, %d in the cells of its block'
                            % (name, own[key], moved.get(key, 0)))
        if row['rows'] != len(before) or row['kinds'] != dict(sorted(kinds.items())):
            problems.append('%s: %d placed things %s as a room, %d %s under its block\'s keys'
                            % (name, len(before), dict(sorted(kinds.items())), row['rows'], row['kinds']))
        if row['left_in_room']:
            problems.append('%s: %d rows left under its room number' % (name, row['left_in_room']))
        for dx in range(place['size'][0]):
            for dy in range(place['size'][1]):
                gx, gy = place['block'][0] + dx, place['block'][1] + dy
                cell_key = pf.exterior_key(gx, gy)
                near = [pf.exterior_key(gx + ax, gy + ay) for ax in (-1, 0, 1) for ay in (-1, 0, 1)]
                window, placed = sum(sizes.get(k, 0) for k in near), sum(items.get(k, 0) for k in near)
                if sizes.get(cell_key, 0) > pf.MAX_ROWS:
                    problems.append('%s: cell %d,%d holds %d rows, over the table\'s %d a key'
                                    % (name, gx, gy, sizes[cell_key], pf.MAX_ROWS))
                if window > pf.WINDOW_ROWS:
                    problems.append('%s: %d rows in the 3 x 3 cells around %d,%d, over the engine\'s %d'
                                    % (name, window, gx, gy, pf.WINDOW_ROWS))
                if placed > pf.PLACED_ITEMS:
                    problems.append('%s: %d placed items in the 3 x 3 cells around %d,%d, over the engine\'s %d'
                                    % (name, placed, gx, gy, pf.PLACED_ITEMS))
    return problems


def district_tables(context):
    """EARLY_CHECKS entry: the placed things of the districts the module tribunal-mournhold builds, keyed outdoors
    (district_table_problems), from the selected game files alone, before any stage. Nothing to check without the
    module's cells."""
    args = context.args
    cells = getattr(args, 'tribunal_mournhold_cells', None) if args is not None else None
    if not cells or not context.data_files:
        return []
    from mwad.masters import master_bytes, selected_masters
    masters = selected_masters(context.masters or None)
    module = ('Morrowind.esm', 'Tribunal.esm')          # tools/build.py TRIBUNAL_MOURNHOLD_MASTERS
    module_master = master_bytes(context.data_files, module)
    merged = module_master if tuple(masters) == module else master_bytes(context.data_files, masters)
    try:
        places = module_places(module_master, cells)
    except ValueError as exc:
        return ['the module\'s districts cannot be planned (tools/presented_exterior.py): %s' % exc]
    if not places:
        context.log('District tables: the module converts no district whole: nothing keyed outdoors')
        return []
    return district_table_problems(merged, places, context.log)
