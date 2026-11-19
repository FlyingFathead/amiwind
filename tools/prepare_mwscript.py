#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Builder stage mwscript: every script of the game data compiled into one file, id1/mwscript.awm.

Inputs: the masters (Morrowind, Tribunal, Bloodmoon), the media stage's catalogue (media-coverage.json: which
converted file each sound and voice became) and the soundtrack (music/soundtrack.json: each track's number),
and config/mwscript.json. Sounds, voices and music are referred to by index into the media catalogue's files
(sound/pool/a<hash>.wav, music/trackNN.mws): no audio is copied. One unit, keyed by the SHA-256 of all of
those and of the compiler's source (tools/mwscript/ident.py): an unchanged key reuses the file from the pool (tools/file_cache.py).

  prepare_mwscript.py --data-files DIR --media RUN/media --music RUN/music --out RUN/mwscript
                      [--cache POOL --cache-report FILE]

Writes OUT/id1/mwscript.awm and OUT/mwscript-report.json (counts, sizes, every script sound that does not map
and why). The design and the format: docs/MWSCRIPT_BYTECODE.md.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))

from mwscript.gamedata import GameData, MASTERS  # noqa: E402
from mwscript.compiler import compile_program, bindings  # noqa: E402
from mwscript.media import MediaMap  # noqa: E402
from mwscript import awms  # noqa: E402
from mwscript import newgame  # noqa: E402
from mwscript import events  # noqa: E402

CONFIG = ROOT / 'config' / 'mwscript.json'
NAME = 'mwscript.awm'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


# The compiler's identity (its files hashed whole), the '=' trace lines that key them whole in the stage's record, and
# the image step's check: tools/mwscript/ident.py (BUILD-MWSCRIPT-STAGE-REUSED-COMPILER-CHANGED-59)
from mwscript.ident import compiler_files, compiler_identity, check as check_compiler  # noqa: E402,F401
from mwscript.ident import note_read as note_compiler_read  # noqa: E402


def bound_addons(masters=None):
    """The expansion masters whose OWN placements this image binds (EXPANSION-SCRIPTS-NOT-ATTACHED-66): the build's
    selection after the base game (mwad.masters.selected_masters: MASTERS, else the environment variable
    AMIWIND_MASTERS, which tools/build.py sets from --dlc / --no-dlc), in load order. () with the base game alone, so
    a base-only build binds, writes and keys exactly what it did before. Until v0.0.67 the stage bound none, so every
    scripted person, creature and object an expansion places ran without its script, also in the expansion rooms the
    image holds (0 of the v0.0.66 release build's 9,095 bindings)."""
    from mwad.masters import selected_masters
    return tuple(m for m in selected_masters(masters) if m.casefold() != MASTERS[0].casefold())


def presented_places(receipt, cells):
    """MOURNHOLD-EXTERIOR-CELLS-66: the districts this build presents as exterior cells and converts whole, from the
    presented-data stage's receipt RECEIPT (a path) and the build's CHIM cells CELLS ("x,y:k ..."), as the image step
    reads them (tools/presented_exterior.py build_places); {} without a receipt."""
    if not receipt:
        return {}
    import presented_exterior
    return presented_exterior.build_places(json.loads(Path(receipt).read_text(encoding='utf-8')),
                                           presented_exterior.cells_of_text(cells or ''))[0]


def unit_inputs(data_files, media, music, config, rooms=None, addons=None, presented=None):
    from mwad.paths import child_ci
    from mwscript.rooms import room_table, table_digest
    # the room maps the player's PositionCell loads (the repo's room lists): keyed by what the table holds
    from mwscript.aftercensus import CONFIG as AFTER_CENSUS
    inputs = {'compiler': compiler_identity(), 'config': sha(config),
              'rooms': table_digest(room_table() if rooms is None else rooms),
              # DBG-HORS-AFTER-CENSUS-67: the path out of the census office the script AW_AfterCensus is read from
              'after-census.json': sha(AFTER_CENSUS)}
    for name in MASTERS:
        path = child_ci(Path(data_files), name, required=False)
        inputs[name] = sha(path) if path else None
    inputs['media-coverage.json'] = sha(Path(media) / 'media-coverage.json')
    track = Path(music) / 'soundtrack.json' if music else None
    inputs['soundtrack.json'] = sha(track) if track and track.is_file() else None
    # the expansions whose own placements are bound: only when there are any, so the base game's unit key stays
    addons = bound_addons() if addons is None else tuple(addons)
    if addons:
        inputs['bound_addons'] = list(addons)
    # the presented districts' moves: only when there are any, so every other build's unit key stays
    if presented:
        inputs['presented'] = {key: {'block': place['block'], 'size': place['size'], 'offset': place['offset']}
                               for key, place in sorted(presented.items())}
    return inputs


def build(data_files, media, music, out, config=CONFIG, addons=None, presented=None):
    """ADDONS: the expansion masters whose own placements are bound (None: bound_addons(), the build's selection).
    PRESENTED: the presented districts this build converts (presented_places; a PositionCell into one goes outdoors)."""
    addons = bound_addons() if addons is None else tuple(addons)
    config_data = json.loads(Path(config).read_text(encoding='utf-8'))
    data = GameData().load(data_files)
    # DBG-HORS-AFTER-CENSUS-67: the bare 'dbg aw hors' starts AW_AfterCensus once: the state of a player who has walked
    # out of the census office, read from the game's own scripts (tools/mwscript/aftercensus.py), compiled with them
    from mwscript.aftercensus import inject as after_census
    after = after_census(data)
    soundtrack = Path(music) / 'soundtrack.json' if music else None
    mapper = MediaMap.from_files(data, Path(media) / 'media-coverage.json',
                                 soundtrack if soundtrack and soundtrack.is_file() else None)
    program, compiled = compile_program(data, mapper, handwritten=config_data['handwritten']['patterns'],
                                        presented=presented)
    moves = {'rows': len(program.moves), 'rooms_known': len(program.rooms or {})}
    if presented:
        moves['presented_districts'] = sorted(place['cell'] for place in presented.values())
    binds = bindings(program, compiled, addons=addons)
    # the build check (NPC-STORY-DISABLED-AT-START-42): a new game starts Main's run-once scripts and each of their
    # disables reaches its placed reference; a failure stops the stage here
    new_game = newgame.check(program, compiled)
    # SCRIPTED-EVENT-FALLING-MAGE-61: the actors standing on an object some script disables (the HELD section), and
    # the census of distance-triggered world events for the script tracker
    held = events.check(data)
    program.held = held['rows']
    program.far = events.far_triggers(data, held['rows'])
    census = events.census(data)
    conf = {'range_units': int(config_data['activation']['range_units']),
            'ops_per_frame': int(config_data['budget']['ops_per_frame']),
            'ops_per_run': int(config_data['budget']['ops_per_run'])}
    # EXPANSION-SCRIPT-LIMITS-66: the script engine's table sizes counted from the whole game (every master's
    # placements, whether or not this image binds the add-on worlds): the engine allocates exactly these at load
    from mwscript.plan import plan as table_plan
    sizes_plan = table_plan(program, compiled, bindings(program, compiled, addons=tuple(MASTERS[1:])), data)
    conf.update({k: sizes_plan[k] for k in ('instances', 'cells', 'parked', 'park_cells')})
    raw, sizes = awms.write(program, compiled, binds, conf)
    awms.read(raw)   # the output schema: the file reads back
    for row in awms.scripts(awms.read(raw)):
        awms.decode(row['code'])
    target = Path(out) / 'id1' / NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)

    def media_rows(table):
        return {'names': len(table), 'mapped': sum(1 for r in table.rows if r.get('resolved')),
                'unmapped': [{'name': r.get('id') or r.get('path'), 'reason': r.get('reason')}
                             for r in table.rows if not r.get('resolved')],
                'repaired': [{'name': r.get('id') or r.get('path'), 'note': r['note']}
                             for r in table.rows if r.get('resolved') and r.get('note')]}
    report = {'format': 'AWMS1', 'file': 'id1/' + NAME, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
              'sections': sizes, 'scripts': len(compiled),
              'not_compiled': [c.name for c in compiled if c.error],
              'bindings': len(binds), 'globals': len(program.globals), 'journal_topics': len(program.journal),
              # EXPANSION-SCRIPT-LIMITS-66: the script engine's tables as the file plans them, and how they were counted
              'tables': {k: sizes_plan[k] for k in ('instances', 'cells', 'parked', 'park_cells')},
              'tables_counted': sizes_plan['report'],
              # SAVE-SCRIPT-ROW-HINT-ONLY-65: the scripts' variables by name (LOCN) and any names that share a key
              'local_names': getattr(program, 'local_names_report', None),
              'player_moves': moves,
              'after_census': after,
              'new_game': {'scripts': new_game['scripts'], 'counts': new_game['counts'],
                           'controls': new_game['controls'],
                           'actors': sorted(d['id'] for d in new_game['disabled'] if d['type'] in newgame.ACTOR_TYPES)},
              'held_actors': {'rows': [dict(r, cell=str(r['cell']), position=[round(v, 1) for v in r['position']])
                                       for r in held['rows']],
                              'near_not_held': len(held['near'])},
              'distance_events': {'scripts': len({r['script'] for r in census}), 'placements': len(census),
                                  'rows': [dict(r, cell=str(r['cell'])) for r in census]},
              'actors': dict(program.actors.report, items=len(program.actors.items),
                             spells=len(program.actors.spells), inventory_entries=len(program.actors.inventory),
                             spell_entries=len(program.actors.spell_list)),
              'media': {'sounds': media_rows(program.sounds), 'voices': media_rows(program.voices),
                        'music': media_rows(program.music)},
              'unmapped_uses': [{'script': s, 'kind': k, 'name': n, 'reason': why}
                                for s, k, n, why in program.unresolved]}
    if addons:
        # EXPANSION-SCRIPTS-NOT-ATTACHED-66: the bindings of the selected expansions' own placements, per master (only
        # with an expansion selected, so the base game's report is as before)
        from mwscript.gamedata import ADDON_KEY_STRIDE
        from mwscript.compiler import BIND_HELD

        def owned(r, m):
            return (r['reference'] & 0xFFFFFF) // ADDON_KEY_STRIDE == MASTERS.index(m)
        per = {m: sum(1 for r in binds if owned(r, m)) for m in addons}
        # EXPANSION-HELD-ITEMS-66: of those, the items their own holders carry (BIND_HELD rows)
        held = {m: sum(1 for r in binds if r['flags'] & BIND_HELD and owned(r, m)) for m in addons}
        report['bound_addons'] = {'masters': list(addons), 'rows': per, 'held': held}
    (Path(out) / 'mwscript-report.json').write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8',
                                                   newline='\n')
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--media', type=Path, required=True, help='the media stage output (media-coverage.json)')
    p.add_argument('--music', type=Path, help='the music stage output (soundtrack.json)')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--config', type=Path, default=CONFIG)
    p.add_argument('--cache', type=Path, help='the shared pool (tools/file_cache.py): reuse an unchanged unit')
    p.add_argument('--cache-report', type=Path)
    p.add_argument('--presented-receipt', type=Path,
                   help='the presented-data stage\'s receipt (tools/build.py gives it only when that stage runs; '
                        'MOURNHOLD-EXTERIOR-CELLS-66): a PositionCell into a district the build converts goes outdoors')
    p.add_argument('--presented-cells', default='', help='the CHIM cells the build converts, with --presented-receipt')
    args = p.parse_args(argv)
    presented = presented_places(args.presented_receipt, args.presented_cells)
    started = time.time()
    print('[mwscript] start: one unit (the whole program), 1 worker: the compiler reads every script once; '
          'serial by design (member access needs every script), measured in seconds', flush=True)
    addons = bound_addons()
    print('[mwscript] bound placements: Morrowind.esm%s' % (
        ''.join(', ' + m + "'s own" for m in addons) or ' only (the base game alone)'), flush=True)
    inputs = unit_inputs(args.data_files, args.media, args.music, args.config, addons=addons, presented=presented)
    if args.presented_receipt:
        print('[mwscript] presented districts: %s (a PositionCell into one goes outdoors to its moved place)'
              % (', '.join(sorted(p['cell'] for p in presented.values())) or 'none converted whole by this build'),
              flush=True)
    note_compiler_read()
    key =hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    target = args.out / 'id1' / NAME
    result = 'off'
    cache = None
    if args.cache:
        from file_cache import FileCache
        cache = FileCache(args.cache, 'mwscript', {'inputs': inputs})
        target.parent.mkdir(parents=True, exist_ok=True)
        facts = cache.fetch(cache.key(key, {}), target)
        result = 'hit' if facts and facts.get('report') else 'miss'
    if result == 'hit':
        report = facts['report']
        (args.out / 'mwscript-report.json').write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8',
                                                       newline='\n')
    else:
        report = build(args.data_files, args.media, args.music, args.out, args.config, addons=addons,
                       presented=presented)
        if cache:
            cache.store(cache.key(key, {}), target, {'report': report})
    receipt = {'unit_key': key, 'inputs': inputs, 'cache': result, 'sha256': sha(target), 'bytes': target.stat().st_size}
    (args.out / 'mwscript-receipt.json').write_text(json.dumps(receipt, indent=1) + '\n', encoding='utf-8',
                                                    newline='\n')
    if args.cache_report:
        from file_cache import write_report
        write_report(args.cache_report, 'mwscript', {'units': {'hit': int(result == 'hit'), 'miss': int(result == 'miss'),
                                                               'enabled': bool(cache)}})
    m = report['media']
    print('[mwscript] %d scripts (%d not compiled), %d bytes (%s), %d placed scripted objects; sounds %d/%d mapped, '
          'voices %d/%d, music %d/%d; unit %s' % (
              report['scripts'], len(report['not_compiled']), report['bytes'], report['sha256'][:12],
              report['bindings'], m['sounds']['mapped'], m['sounds']['names'], m['voices']['mapped'],
              m['voices']['names'], m['music']['mapped'], m['music']['names'], result), flush=True)
    ba = report.get('bound_addons')
    if ba:   # EXPANSION-SCRIPTS-NOT-ATTACHED-66
        print("[mwscript] the expansions' own scripted placements bound: %s (of them items their holders carry: %s)" % (
            ', '.join('%s %d' % kv for kv in ba['rows'].items()),
            ', '.join('%s %d' % kv for kv in (ba.get('held') or {}).items())), flush=True)
    t = report.get('tables')
    if t:   # EXPANSION-SCRIPT-LIMITS-66: what the engine allocates for the scripts, counted from every master
        c = report.get('tables_counted') or {}
        print('[mwscript] script engine tables planned from the game: %d attached instances, %d local values, %d parked '
              'objects, %d parked values (busiest map %s: %d placed, %d held; %d global scripts; %d bound objects with '
              'values)' % (t['instances'], t['cells'], t['parked'], t['park_cells'],
                           (c.get('busiest_map') or {}).get('map'), (c.get('busiest_map') or {}).get('placed', 0),
                           (c.get('busiest_map') or {}).get('held', 0), (c.get('global_scripts') or {}).get('distinct', 0),
                           (c.get('bound') or {}).get('with_values', 0)), flush=True)
    ng = report.get('new_game')
    if ng:
        c = ng['counts']
        print('[mwscript] new game: %d scripts start once (%s); they disable %d references (%d actors), %d placed '
              'once and bound, %d placed more than once, %d not placed in the world' % (
                  c['scripts'], ', '.join(s['name'] for s in ng['scripts']), c['disabled'], c['actors'],
                  c['resolved'], c['placed_more_than_once'], c['not_placed']), flush=True)
        k = ng.get('controls') or {}
        if k.get('enabled_by'):   # OPENING-FIGHTING-ON-BEFORE-PAPERS-66: the carried CharGen's switches (NGCS)
            print('[mwscript] new game: the carried scripts switch off %s; switched on again by %s' % (
                ', '.join(k['enabled_by']), '; '.join('%s: %s' % (n, ', '.join(s[:4]) + (' ...' if len(s) > 4 else ''))
                                                     for n, s in k['enabled_by'].items())), flush=True)
    held = report.get('held_actors')
    if held:
        print('[mwscript] held actors: %d stand on an object a script disables (%s); %d others near such an object '
              'are not on it' % (len(held['rows']), ', '.join('%s on %s' % (r['actor_id'], r['support_id'])
                                                             for r in held['rows'][:6]), held['near_not_held']), flush=True)
    ev = report.get('distance_events')
    if ev:
        print('[mwscript] distance-triggered world events: %d scripts, %d placements' % (ev['scripts'],
                                                                                        ev['placements']), flush=True)
    for kind in ('sounds', 'voices', 'music'):
        for row in m[kind]['unmapped']:
            print('[mwscript] [warning: unmapped %s] %s: %s' % (kind[:-1] if kind != 'music' else kind,
                                                                row['name'], row['reason']), flush=True)
    print('[mwscript] end: took %.1f s, 1 worker' % (time.time() - started), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
