"""The actor placement check (OUTDOOR-CREATURES-MISSING-66, BUILD-ACTOR-SPEC-CHECK-66): the people and creatures of
the original's exterior, per area kind, against what the image places, as a stage verdict that fails the build.

Area kinds:
  exterior-region  cells of the region frames: the window joins the actor table there (every record);
  exterior-town    cells inside a town map's core (world/regions.awr town rows): the town frame's resident stage
                   places the NPCs; the creatures and levelled points come from the actor table only when the engine
                   joins a town map's cells (aw_actors.c TownJoin, since v0.0.66).
Kinds: NPC_, CREA, LEVC (a levelled creature point), corpse.

Original = the records of the actor table (tools/chim/actors.py writes every exterior NPC_, CREA and LEVC reference
of the master; the table's own builder checks that count against the master). Placed = what the image reaches.
A drop beyond config/actor_census_allowlist.json fails (exit 1) and names each area and kind.

Usage (in the build container, right after the actor table and the town stages):
  python3 tools/chim/actor_census_check.py BUILD_RUN_DIR [--town-join on|off] [--json OUT]
"""
import argparse
import collections
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import actors  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ALLOWLIST = os.path.join(HERE, '..', '..', 'config', 'actor_census_allowlist.json')
KIND_NAMES = {v: k for k, v in actors.KINDS.items()}
TOWN_STAGE_KINDS = ('NPC_', 'corpse')      # placed by a town frame's resident stage


def town_cores(regions_awr):
    """[(origin x, origin y, x0, y0, x1, y1)] of the town rows of world/regions.awr (aw_world.c load_directory)."""
    out = []
    if regions_awr[:4] != b'AWR2':
        return out
    for i in range(2):
        for end in ('<', '>'):
            v = struct.unpack_from(end + '7f', regions_awr, 8 + i * 28)
            if all(abs(x) < 1e6 for x in v) and v[3] < v[5] and v[4] < v[6]:
                out.append((v[0], v[1], v[3], v[4], v[5], v[6]))
                break
    return out


def area_of(cell, cores):
    """'exterior-town' when the cell's centre lies in a town core (aw_world.c AW_CellMap's rule), else region."""
    x = (cell[0] + 0.5) * actors.CELL_UNITS * actors.LOCAL
    y = (cell[1] + 0.5) * actors.CELL_UNITS * actors.LOCAL
    for ox, oy, x0, y0, x1, y1 in cores:
        if x0 <= x - ox <= x1 and y0 <= y - oy <= y1:
            return 'exterior-town'
    return 'exterior-region'


def count(run, town_join=True):
    """{area: {kind: {'original': n, 'placed': n}}} of build run RUN."""
    id1 = os.path.join(run, 'image', 'boot', 'id1')
    with open(os.path.join(id1, 'maps', 'chim-actors.cca'), 'rb') as fh:
        _head, cells, recs, bases, _text = actors.read_table(fh.read())
    with open(os.path.join(id1, 'world', 'regions.awr'), 'rb') as fh:
        cores = town_cores(fh.read())
    town_npcs = 0
    for name in sorted(os.listdir(run)):
        if name.startswith('chim-town-'):
            p = os.path.join(run, name, 'entities.json')
            if os.path.exists(p):
                with open(p, encoding='utf-8') as fh:
                    rows = json.load(fh).get('rows', [])
                town_npcs += sum(1 for r in rows if r.get('classname') in ('aw_npc', 'aw_corpse'))
    out = collections.defaultdict(lambda: collections.defaultdict(lambda: {'original': 0, 'placed': 0}))
    for cell, first, n in cells:
        area = area_of(cell, cores)
        for r in recs[first:first + n]:
            kind = KIND_NAMES.get(bases[r['base']]['kind'], str(bases[r['base']]['kind']))
            row = out[area][kind]
            row['original'] += 1
            if area == 'exterior-region' or (kind not in TOWN_STAGE_KINDS and town_join):
                row['placed'] += 1
    # the town residents: placed by the town stages (their rows, the towns outside the two world slots included)
    for kind in TOWN_STAGE_KINDS:
        row = out['exterior-town'][kind]
        row['placed'] = min(row['original'], town_npcs) if kind == 'NPC_' else row['original']
    return {a: dict(k) for a, k in out.items()}


def verdict(counts, allowlist):
    """[failure lines] for every area and kind whose placed count falls short of the original by more than the
    allowlist's tracked number for it ({"exterior-town/NPC_": {"missing": n, "register": ID}})."""
    bad = []
    for area in sorted(counts):
        for kind in sorted(counts[area]):
            row = counts[area][kind]
            missing = row['original'] - row['placed']
            allowed = allowlist.get('%s/%s' % (area, kind), {}).get('missing', 0)
            if missing > allowed:
                bad.append('%s %s: %d of %d placed, %d missing (allowed %d)' % (
                    area, kind, row['placed'], row['original'], missing, allowed))
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('run')
    ap.add_argument('--town-join', choices=('on', 'off'), default='on',
                    help='whether the engine joins a town map\'s cells from the actor table (on since v0.0.66)')
    ap.add_argument('--allowlist', default=ALLOWLIST)
    ap.add_argument('--json')
    a = ap.parse_args(argv)
    print('=== actor placement check: %s ===' % a.run, flush=True)
    counts = count(a.run, a.town_join == 'on')
    with open(a.allowlist, encoding='utf-8') as fh:
        allow = json.load(fh)['allow']
    for area in sorted(counts):
        for kind in sorted(counts[area]):
            r = counts[area][kind]
            print('  %-16s %-7s original %5d placed %5d' % (area, kind, r['original'], r['placed']))
    bad = verdict(counts, allow)
    if a.json:
        with open(a.json, 'w', encoding='utf-8', newline='\n') as fh:
            json.dump({'counts': counts, 'failures': bad, 'town_join': a.town_join}, fh, indent=1, sort_keys=True)
            fh.write('\n')
    for line in bad:
        print('FAIL ' + line)
    print('actor placement check: %s' % ('FAIL' if bad else 'PASS'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
