#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""World-wide check that every actor model plays the walk and attack groups its original animation has
(CREATURE-BIPED-ANIMS-62).

For one build (its id1 folder and actor library):
  * every creature mesh of the actor library whose original animation has a walk, run or attack group
    (creature-library.json "groups", read from the original keyframe files) must reach that group in the engine:
    in the layout of the model the world draws it with (<model>.anm) or in the layout of the mover that layout
    names (>PATH, worn while the actor walks or fights);
  * every actor base of the CHIM actor table (maps/chim-actors.cca) whose model names a mover must have that mover
    and its layout in the image;
  * the engine's per-level limits hold for the whole island, since a CHIM session is one level: the distinct
    mover names fit the mover name table (engine/aga/src/aw_anim.c LAZIES).

Prints one line per failure and the totals; exit 1 on any failure. Read only.

  python3 tools/actor_anim_reach.py --id1 <build>/image/boot/id1 --library <build>/actor-library/creature-library.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

MOVING = ('walk', 'run', 'attack')
SRC = Path(__file__).resolve().parents[1] / 'engine' / 'aga' / 'src' / 'aw_anim.c'


def engine_limit(name, source=SRC):
    """The value of #define NAME in aw_anim.c."""
    m = re.search(r'#define\s+%s\s+(\d+)' % name, Path(source).read_text(encoding='latin-1'))
    if not m:
        raise SystemExit('actor_anim_reach: %s not found in %s' % (name, source))
    return int(m.group(1))


def layout(id1, model):
    """(groups set, mover path or '') of a model's .anm; None when it has none."""
    p = Path(id1) / (model[:-4] + '.anm')
    if not p.is_file():
        return None
    groups, mover = set(), ''
    for word in p.read_text(encoding='latin-1').split():
        if word.startswith('>'):
            mover = word[1:]
        elif word[:1] not in '@~!' and ':' in word:
            groups.add(word.split(':', 1)[0])
    return groups, mover


def reach(id1, model):
    """Groups the engine can play for an actor drawn with MODEL: its layout's and its mover's."""
    own = layout(id1, model)
    if own is None:
        return set(), '', 'no layout %s' % (model[:-4] + '.anm')
    groups, mover = own
    if mover:
        worn = layout(id1, mover)
        if worn is None or not (Path(id1) / mover).is_file():
            return groups, mover, 'mover %s or its layout missing' % mover
        groups = groups | worn[0]
    return groups, mover, None


def table_models(id1):
    """{model: [record ids]} of the CHIM actor table's bases."""
    p = Path(id1) / 'maps' / 'chim-actors.cca'
    out = {}
    if not p.is_file():
        return out
    raw = p.read_bytes()
    for m in re.finditer(rb'"aw_source_id" "([^"]*)"[^{}]*?"model" "(progs/[^"]*\.mdl)"', raw):
        out.setdefault(m.group(2).decode('latin-1'), []).append(m.group(1).decode('latin-1'))
    return out


def check(id1, library, lazies=None):
    """(failures [str], facts {})."""
    lib = json.loads(Path(library).read_text(encoding='utf-8'))
    failures, movers, checked = [], set(), 0
    for mesh, info in sorted(lib.get('models', {}).items()):
        want = {g['name'] for g in info.get('groups', []) if g.get('name') in MOVING and g.get('source') != 'idle'}
        if not want or not info.get('model'):
            continue
        checked += 1
        got, mover, why = reach(id1, info['model'])
        if mover:
            movers.add(mover)
        if why:
            failures.append('%s (%s): %s' % (mesh, info['model'], why))
        missing = sorted(want - got)
        if missing:
            failures.append('%s (%s): original %s not played' % (mesh, info['model'], ', '.join(missing)))
    for model, ids in sorted(table_models(id1).items()):
        own = layout(id1, model)
        if own and own[1]:
            movers.add(own[1])
            if reach(id1, model)[2]:
                failures.append('%s (%s): %s' % (ids[0], model, reach(id1, model)[2]))
    if lazies is None:
        lazies = engine_limit('LAZIES')
    if len(movers) > lazies:
        failures.append('%d distinct movers over the engine mover name table (LAZIES %d)' % (len(movers), lazies))
    return failures, {'creature_meshes_checked': checked, 'movers': len(movers), 'lazies': lazies}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--id1', required=True)
    ap.add_argument('--library', required=True, help='actor-library/creature-library.json of the build')
    a = ap.parse_args(argv)
    failures, facts = check(a.id1, a.library)
    for line in failures:
        print('FAIL', line)
    print('actor_anim_reach: %d creature meshes with walk/run/attack checked, %d movers (table %d), %d failures'
          % (facts['creature_meshes_checked'], facts['movers'], facts['lazies'], len(failures)))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
