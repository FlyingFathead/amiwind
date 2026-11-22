#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The expansions' actors, counted at every build (the actor spec check's part 3; docs/ACTOR_RECORDS.md "The
expansions' actors").

Each expansion is done in three stages, each a milestone with a measured count (config/expansion-stages.json): the
world (its places built), the actors (every person and creature it places, in its own places and in Vvardenfell,
placed and complete), the script logic. This module counts, per land (Mournhold for Tribunal, Solstheim for Bloodmoon,
and the actors the expansions insert into Vvardenfell), from a build's stored outputs only (no build, no emulator):

  stage 1  the expansion's rooms the image holds (image/cell-numbers.json maps, by each room's master) and its new
           exterior cells the image holds (image/entity-tracker.json converted_cells)
  stage 2  every actor placement the expansion adds and every base placement of an actor record it changes: placed
           (rooms: entity-tracker placed_refs; outdoors: maps/chim-actors.cca in a converted cell; either: the image's
           stores of frames, chim-layer-stores.json, the districts' and Solstheim's), and complete: a model the engine
           plays, every stat the record has (the actor record audit's fields), its inventory and equipment, its combat
           style (tools/combat_style_audit.py), every animation kind the original gives it, its own script attached
           (mwscript.awm BIND by the merged reference number; a script the compiler leaves out as inert, which only
           declares the locals the dialogue reads, needs none) with its variables
  stage 3  the scripts the expansion's master defines: compiled (in the build's script file, not broken), attached
           (a binding of the expansion's own placements), running (attached, a start script or started by a script)

A column that config/expansion-stages.json "tracked_gaps" names (a world-wide gap with its own register entry, such
as the levelled inventory picked once at build time) is counted and listed with its entry, never a stop. At milestone
1 an incomplete actor is a count; at milestone 2 or more each one is a failure line naming the actor, its reference,
its place and the columns it lacks, which stops the image step (actor_spec_check.stage) and the early checks
(build_preflight EARLY_CHECKS, early()). With the base game alone nothing here runs.

  python3 tools/expansion_actor_check.py RUN --data-files DIR [--json OUT]     (both expansions)
"""
import argparse
import collections
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools' / 'chim', ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

SETTING = ROOT / 'config' / 'expansion-stages.json'
STRIDE = 1 << 22                 # mwad.masters ADDON_KEY_STRIDE
MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')
VVARDENFELL = 'Vvardenfell (inserted)'
STAT_FIELDS = ('level', 'attributes', 'skills', 'health', 'magicka', 'fatigue', 'hello', 'fight', 'flee', 'alarm',
               'services', 'disposition', 'reputation', 'rank', 'gold', 'race', 'class', 'faction', 'creature type',
               'attacks', 'soul', 'flags', 'blood', 'spells', 'stats vocabulary')
GEAR_FIELDS = ('inventory', 'inventory levelled', 'weapon', 'ranged weapon', 'armour', 'weapon and shield flag')
SCRIPT_FIELDS = ('script locals',)
COLUMNS = ('placed', 'model', 'stats', 'inventory/equipment', 'combat style', 'animations', 'script attached',
           'script locals')


def load_setting(path=SETTING):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def bad_states(states, fields):
    return {f: states[f] for f in fields if states.get(f) not in (None, 'carried', 'absent')}


def failing(row, tracked):
    """The columns row ROW fails ([] = complete), the fields TRACKED (config tracked_gaps) set apart."""
    if row['tag'] == 'LEVC':
        return [] if row['placed'] else ['placed']
    bad = [] if row['placed'] else ['placed']
    if not row.get('model'):
        bad.append('model')
    if row.get('stats'):
        bad.append('stats')
    if [f for f in row.get('gear') or {} if f not in tracked]:
        bad.append('inventory/equipment')
    if row.get('combat') == 'different style':
        bad.append('combat style')
    if row.get('anim'):
        bad.append('animations')
    if row.get('script') and row.get('script_bound') is False:
        bad.append('script attached')
    if row.get('script_fields'):
        bad.append('script locals')
    return bad


def summary(rows, setting, stage1=None, stage3=None):
    """{land: counts} of the rows (each with its 'land'), with the tracked gaps listed by register entry."""
    tracked = setting.get('tracked_gaps') or {}
    out = {}
    for land in sorted({r['land'] for r in rows} | set(stage1 or {}) | set(stage3 or {})):
        rs = [r for r in rows if r['land'] == land and r['tag'] in ('NPC_', 'CREA')]
        cols = collections.Counter(c for r in rs for c in failing(r, tracked))
        gaps = {f: {'placements': sum(1 for r in rs if f in (r.get('gear') or {})), 'register': g.get('register')}
                for f, g in tracked.items()}
        levc = [r for r in rows if r['land'] == land and r['tag'] == 'LEVC']
        out[land] = {'stage 1 places built': (stage1 or {}).get(land),
                     'stage 2 actors placed': sum(1 for r in rs if r['placed']),
                     'stage 2 actors complete': sum(1 for r in rs if not failing(r, tracked)),
                     'stage 2 actor placements': len(rs),
                     'stage 2 failing columns': dict(sorted(cols.items())),
                     'stage 2 tracked gaps (not a stop)': gaps,
                     'levelled points placed': '%d of %d' % (sum(1 for r in levc if r['placed']), len(levc)),
                     'stage 3 scripts': (stage3 or {}).get(land)}
    return out


def verdict(rows, setting, limit=40):
    """[failure lines]: every incomplete actor of an expansion whose milestone is 2 or more (rows carry 'master', the
    expansion they belong to); [] at milestone 1."""
    tracked = setting.get('tracked_gaps') or {}
    stop = {m for m, e in (setting.get('expansions') or {}).items() if int(e.get('milestone', 1)) >= 2}
    lines = []
    for r in rows:
        if r.get('master') not in stop or r['tag'] not in ('NPC_', 'CREA'):
            continue
        bad = failing(r, tracked)
        if bad:
            lines.append('expansion actor %s (reference %s, %s, %s): lacks %s' % (
                r['id'], r['ref'], r['master'], r['cell'], ', '.join(bad)))
    if len(lines) > limit:
        lines = lines[:limit] + ['... and %d more incomplete expansion actors' % (len(lines) - limit)]
    return lines


def store_actor_refs(image):
    """{merged reference} of every person and creature the image's stores of frames place (image/
    chim-layer-stores.json, tools/chim/layer_stores.py: Mournhold's district frames and Solstheim's frames); an empty set
    for a build without them. EXPANSION-SCRIPTS-NOT-ATTACHED-66 (v0.0.68): the check read only the rooms' entity
    tracker and the open world's actor table, so the 57 district actors and the 201 Solstheim outdoor actors the stores
    place were counted as not placed."""
    out = set()
    for frame in store_frames(image):
        for r in (frame.get('actors') or {}).get('actors') or ():
            if r.get('reference') is not None:
                out.add(int(r['reference']))
    return out


def store_frames(image):
    """Every frame of the image's stores of frames (image/chim-layer-stores.json maps, each with its 'cell' x, y and
    its 'actors'); [] for a build without them."""
    path = Path(image) / 'chim-layer-stores.json'
    if not path.is_file():
        return []
    return [frame for store in json.loads(path.read_text(encoding='utf-8')) if isinstance(store, dict)
            for frame in store.get('maps') or ()]


def script_bound(script, number, bound, inert):
    """True or False: the actor's own script has a binding (mwscript.awm BIND) or not; None when it has no script or
    its script is one the compiler leaves out of the bindings as inert (INERT: their folded names), a script that only
    declares the locals the dialogue reads (nolore, nohello: the base game binds none of its 148 such placements
    either). EXPANSION-SCRIPTS-NOT-ATTACHED-66 (v0.0.68): those were counted as not attached (27 in Mournhold, 47 on
    Solstheim on 18 November 2026)."""
    if not script or script.casefold() in inert:
        return None
    return number in bound


def land_of(master, interior, xy, cell, cell_masters):
    """The land a placement belongs to: a cell an expansion first defines is its land; a base game cell is
    Vvardenfell."""
    owner = cell_masters.get(cell.casefold() if interior else tuple(xy), MASTERS[0])
    if owner == MASTERS[0]:
        return VVARDENFELL
    return {'Tribunal.esm': 'Mournhold', 'Bloodmoon.esm': 'Solstheim'}.get(owner, owner)


def first_definers(data_files, masters):
    """{room name casefold or (x, y): the first master that defines the cell}."""
    from mwad.esm import records, subrecords
    from mwad.paths import child_ci
    out = {}
    for name in masters:
        for tag, _flags, payload in records(child_ci(Path(data_files), name).read_bytes()):
            if tag != 'CELL':
                continue
            parts = list(subrecords(payload))
            data = next((d for t, d in parts if t == 'DATA'), b'')
            if len(data) >= 4 and struct.unpack_from('<I', data)[0] & 1:
                key = next((d for t, d in parts if t == 'NAME'), b'').split(b'\0', 1)[0].decode('cp1252').casefold()
            elif len(data) >= 12:
                key = struct.unpack_from('<ii', data, 4)
            else:
                continue
            out.setdefault(key, name)
    return out


def check(run, data_files, masters, audit, master_raw=None):
    """{'setting', 'lands', 'failures', 'rows'} of build run RUN for the selected MASTERS (the expansions after the base
    game); AUDIT: actor_record_audit.audit's report over the run (its 'rows')."""
    import actor_spec_check as asc
    import actors as chim_actors
    import combat_style_audit as csa
    import prepare_combat
    from mwscript import awms
    from mwscript.codegen import SCRIPT_BROKEN, SCRIPT_START, SCRIPT_GLOBAL, SCRIPT_INERT
    run = Path(run)
    image, id1 = run / 'image', run / 'image' / 'boot' / 'id1'
    setting = load_setting()
    addons = [m for m in masters if m != MASTERS[0]]
    if master_raw is None:
        from mwad.masters import master_bytes
        master_raw = master_bytes(data_files, masters)
    tags, _flags, _lists, refs = asc.read_original(master_raw, numbers=True)
    definers = first_definers(data_files, masters)
    tracker = json.loads((image / 'entity-tracker.json').read_text(encoding='utf-8'))
    placed_rooms = {k.casefold(): {n for v in kinds.values() for n in v} for k, kinds in tracker['placed_refs'].items()}
    converted = {c.casefold() for c in tracker['converted_cells']}
    cn = json.loads((image / 'cell-numbers.json').read_text(encoding='utf-8'))
    mapped = {r['number'] for r in cn['maps']}
    _h, cells, recs, bases, _t = chim_actors.read_table((id1 / 'maps' / chim_actors.FILE_NAME).read_bytes())
    table = {r['key']: bool(bases[r['base']]['text']) or bases[r['base']]['kind'] == 2
             for _cell, first, n in cells for r in recs[first:first + n]}
    f = awms.read((id1 / 'mwscript.awm').read_bytes())
    names = awms.strings(f)
    scrp = awms.scripts(f)
    bound = {struct.unpack_from('>I', f['BIND'], 24 * i)[0]: struct.unpack_from('>IHH', f['BIND'], 24 * i)
             for i in range(f['BIND_rows'])}
    inert = {names[s['name']].casefold() for s in scrp if s['flags'] & SCRIPT_INERT}
    in_stores = store_actor_refs(image)
    arow = {r['id']: r for r in audit['rows']}
    crecords, crefs = csa.read_masters(data_files)
    style = {r['id']: r['match'] for r in csa.audit(crecords, crefs, prepare_combat, prepare_combat)}
    from actor_record_audit import read_masters, first, text
    from mwad.esm import records as esm_records, subrecords
    from mwad.paths import child_ci
    records, _refcount = read_masters(data_files)
    script_of = {ident: (text(first(fields, 'SCRI')).casefold() or None)
                 for tag in ('NPC_', 'CREA') for ident, fields in records[tag].items()}

    def actor_payloads(name):
        out = {}
        for tag, _fl, payload in esm_records(child_ci(Path(data_files), name).read_bytes()):
            if tag in ('NPC_', 'CREA'):
                out[text(first(list(subrecords(payload)), 'NAME')).casefold()] = payload
        return out
    # the base game's actor records an expansion changes: their base game placements count as the expansion's too
    base_actors, changed = actor_payloads(MASTERS[0]), {}
    for name in addons:
        for ident, payload in actor_payloads(name).items():
            if ident in base_actors and base_actors[ident] != payload:
                changed[ident] = name
    rows = []
    for interior, xy, ident, number, cell in refs:
        tag = tags.get(ident)
        if tag not in ('NPC_', 'CREA', 'LEVC'):
            continue
        owner = MASTERS[number // STRIDE] if number // STRIDE < len(MASTERS) else None
        master = owner if owner in addons else changed.get(ident)
        if master not in addons:
            continue
        land = land_of(master, interior, xy, cell, definers)
        if interior:
            room = cell.casefold()
            placed = number in placed_rooms.get('interior:' + room, ()) or number in in_stores
        else:
            placed = ((number & 0xFFFFFF) in table and ('exterior:%d,%d' % tuple(xy)) in converted) or \
                number in in_stores
        row = {'ref': number, 'id': ident, 'tag': tag, 'master': master, 'land': land,
               'cell': cell if interior else '%d,%d' % tuple(xy), 'placed': placed}
        if tag != 'LEVC':
            a = arow.get(ident) or {'states': {}, 'anim_method': 'not in this build'}
            row['model'] = a.get('anim_method') not in (None, 'not in this build')
            row['stats'] = bad_states(a['states'], STAT_FIELDS)
            row['gear'] = bad_states(a['states'], GEAR_FIELDS)
            row['anim'] = {k: v for k, v in a['states'].items() if k.startswith('anim ') and v not in ('carried', 'absent')}
            row['combat'] = style.get(ident)
            row['script'] = script_of.get(ident)
            row['script_bound'] = script_bound(row['script'], number, bound, inert)
            if row['script'] and row['script_bound'] is None:
                row['script_inert'] = True
            row['script_fields'] = bad_states(a['states'], SCRIPT_FIELDS)
        rows.append(row)
    # stage 1: the rooms and the new exterior cells of each expansion the image holds
    land_name = {'Tribunal.esm': 'Mournhold', 'Bloodmoon.esm': 'Solstheim'}
    # v0.0.68 (EXPANSION-SCRIPTS-NOT-ATTACHED-66): the stores' frames are built exterior cells too (Solstheim's), and a
    # district the build presents on frames is a built place (its cell has no room map by design)
    framed = {tuple(fr['cell']) for fr in store_frames(image) if fr.get('cell') is not None}
    receipt = run / 'mwscript' / 'mwscript-receipt.json'
    presented = {k.casefold() for k in ((json.loads(receipt.read_text(encoding='utf-8')).get('inputs') or {})
                                        .get('presented') or {})} if receipt.is_file() else set()
    stage1 = {}
    for m in addons:
        rooms = [r for r in cn['table'] if r['master'] == m]
        cells_new = [k for k, v in definers.items() if v == m and isinstance(k, tuple)]
        stage1[land_name.get(m, m)] = {
            'rooms with a map': '%d of %d' % (sum(1 for r in rooms if r['number'] in mapped), len(rooms)),
            'new exterior cells built': '%d of %d' % (sum(1 for k in cells_new if 'exterior:%d,%d' % k in converted
                                                          or k in framed), len(cells_new))}
        districts = [r for r in rooms if r['cell'].casefold() in presented]
        if districts:
            stage1[land_name.get(m, m)]['districts on frames'] = '%d of %d rooms without a map' % (
                len(districts), sum(1 for r in rooms if r['number'] not in mapped))
    # stage 3: the scripts each expansion defines, compiled, attached by its own placements, running
    defined = {}
    for m in addons:
        for tag, _fl, payload in esm_records(child_ci(Path(data_files), m).read_bytes()):
            if tag == 'SCPT':
                head = dict(subrecords(payload)).get('SCHD', b'')
                defined.setdefault(head[:32].split(b'\0', 1)[0].decode('cp1252', 'replace').casefold(), m)
    index = {names[s['name']].casefold(): s for s in scrp}
    attached = collections.defaultdict(set)
    for ref, script, flags in bound.values():
        owner = MASTERS[(ref & 0xFFFFFF) // STRIDE] if (ref & 0xFFFFFF) // STRIDE < len(MASTERS) else None
        if owner in addons and script < len(scrp):
            attached[owner].add(names[scrp[script]['name']].casefold())
    stage3 = {}
    for m in addons:
        mine = [s for s, owner in defined.items() if owner == m]
        compiled = [s for s in mine if s in index and not index[s]['flags'] & SCRIPT_BROKEN]
        running = [s for s in compiled if s in attached[m] or index[s]['flags'] & (SCRIPT_START | SCRIPT_GLOBAL)]
        stage3[land_name.get(m, m)] = {'defined': len(mine), 'compiled': len(compiled),
                                       'attached': len([s for s in compiled if s in attached[m]]),
                                       'running (attached or started)': len(running)}
    lands = summary(rows, setting, stage1, stage3)
    return {'setting': {m: e.get('milestone', 1) for m, e in (setting.get('expansions') or {}).items() if m in addons},
            'lands': lands, 'failures': verdict(rows, setting), 'rows': rows}


def early(context):
    """EARLY_CHECKS (phase 'stored', build_preflight): with an expansion at milestone 2 or more, the check over the
    reuse source's stored outputs (the previous build of this line) in the build's first minutes; [] otherwise."""
    masters = [m for m in context.masters if m != MASTERS[0]]
    setting = load_setting()
    if not any(int((setting.get('expansions') or {}).get(m, {}).get('milestone', 1)) >= 2 for m in masters):
        return []
    source = getattr(context.args, 'reuse_from', None)
    if not source or not (Path(source) / 'image' / 'entity-tracker.json').is_file():
        return []
    import actor_record_audit as ara
    records, refs = ara.read_masters(context.data_files)
    build = ara.read_build(source)
    build['anim'] = ara.read_anim_build(source)
    audit = ara.audit(records, refs, build, original=ara.OriginalGroups(ara.game_reader(context.data_files)))
    return ['in the reuse source %s: %s' % (Path(source).name, line)
            for line in check(source, context.data_files, list(context.masters), audit)['failures']]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('run', type=Path)
    ap.add_argument('--data-files', type=Path, required=True)
    ap.add_argument('--json', type=Path)
    a = ap.parse_args(argv)
    import actor_record_audit as ara
    records, refs = ara.read_masters(a.data_files)
    build = ara.read_build(a.run)
    build['anim'] = ara.read_anim_build(a.run)
    audit = ara.audit(records, refs, build, original=ara.OriginalGroups(ara.game_reader(a.data_files)))
    report = check(a.run, a.data_files, list(MASTERS), audit)
    if a.json:
        a.json.write_text(json.dumps(report, indent=1, default=str) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'setting': report['setting'], 'lands': report['lands']}, indent=1))
    for line in report['failures']:
        print('FAIL ' + line)
    return 1 if report['failures'] else 0


if __name__ == '__main__':
    sys.exit(main())
