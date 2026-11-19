#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The creature moves table (CREATURE-NIXHOUND-HUMAN-MOVES-67, docs/CREATURES.md "How each creature moves and
fights"): every creature record of the
masters against what a build gave its model, and what the engine does with it in a fight.

Per creature: the record's flags (two-legged, walks, swims, flies, weapon and shield), the model's method, where
each animation group the engine plays comes from (the creature's own table; 'base': the shared humanoid table's;
'walk': its walk played when it runs; 'idle': its idle standing in, or missing), its attack style (a four-legged
creature strikes with its record's own attacks 1-3, which OpenMW mwclass/creature.cpp hit takes as the chop, slash and
thrust types; a two-legged one fights hand to hand: aw_combat_rules.c AW_CombatCreatureSheet) and whether it side-steps
a miss (NPCs and two-legged creatures only: OpenMW mwmechanics/aicombat.cpp AiCombatStorage::updateCombatMove;
aw_combat.c npc_react_miss). A row is a MISMATCH when it differs from the original's rules:
  human-groups      a group of the shared humanoid table on a creature not flagged two-legged (OpenMW gives the
                    human xbase_anim.kf only to two-legged creatures: mwrender/creatureanimation.cpp);
  run-on-idle       a living creature's run standing on idle although it has a walk (OpenMW plays the walk:
                    mwmechanics/character.cpp refreshMovementAnims).
A group the creature's own files lack (a kwama queen's walk) stays on idle, as in the original: noted, no mismatch. A
mesh the creature library does not hold (Dagoth Ur's own path, the werewolf) is noted; whether a creature is built at
all is the creature census's question (tools/creature_census.py).

  creature_moves.py table --data DATA_FILES --library RUN/actor-library/creature-library.json --out FILE.json [--md FILE.md]
  creature_moves.py check ...   the same, and exit 1 when a row has a mismatch
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

FORMAT = 'AmiWind creature moves 1'
FLAGS = (('two-legged', 0x01), ('weapon and shield', 0x04), ('swims', 0x10), ('flies', 0x20), ('walks', 0x40))
GROUPS = ('idle', 'walk', 'run', 'attack', 'hit', 'death')
MOVING = ('walk', 'run')


def row_of(ident, record, model):
    """One creature's row: RECORD {mesh, name, flags, dead}, MODEL its creature-library model row or None."""
    flags = [name for name, bit in FLAGS if record.get('flags', 0) & bit]
    biped = 'two-legged' in flags
    row = {'id': ident, 'name': record.get('name', ''), 'mesh': record.get('mesh', ''), 'flags': flags,
           'dead': bool(record.get('dead')), 'attack_style': 'hand to hand' if biped else 'own attacks 1-3',
           'side_steps': biped, 'method': None, 'groups': {}, 'triangles': None, 'mismatches': [], 'notes': []}
    if not row['mesh']:
        row['notes'].append('no mesh')
        return row
    if model is None:
        row['notes'].append('not in the creature library')
        return row
    kit = model.get('kit') or {}
    row['method'] = model.get('method')
    row['triangles'] = model.get('triangles')
    row['groups'] = {g: kit.get(g, 'idle') for g in GROUPS}
    base = sorted(g for g, s in row['groups'].items() if s == 'base')
    if base and not biped:
        row['mismatches'].append('human-groups: %s' % ', '.join(base))
    if any('xbase_anim' in str(s).casefold() for s in model.get('sources', [])) and not biped:
        row['mismatches'].append('human-groups: the shared xbase_anim.kf')
    if row['groups'].get('run') == 'idle' and row['groups'].get('walk') not in (None, 'idle') and not row['dead']:
        row['mismatches'].append('run-on-idle')
    idle = [g for g in ('walk', 'run', 'attack', 'hit', 'death') if row['groups'].get(g) == 'idle']
    if idle:
        row['notes'].append('its own files lack %s (idle stands in, as in the original)' % ', '.join(idle))
    return row


def table(records, library):
    """{'format', 'rows', 'counts'}: RECORDS {id: {mesh, name, flags, dead}} (creature_library.plan's bases over the
    masters in load order), LIBRARY the build's creature-library.json."""
    models = {str(k).casefold().replace('\\', '/'): v for k, v in (library.get('models') or {}).items()}
    rows = []
    for ident in sorted(records):
        r = records[ident]
        mesh = str(r.get('mesh') or '').casefold().replace('\\', '/')
        rows.append(row_of(ident, dict(r, mesh=mesh), models.get(mesh) if mesh else None))
    counts = {'creatures': len(rows), 'two-legged': sum('two-legged' in r['flags'] for r in rows),
              'mismatches': sum(bool(r['mismatches']) for r in rows),
              'groups from the humanoid table': sum(s == 'base' for r in rows for s in r['groups'].values()),
              'groups standing on idle': sum(s == 'idle' for r in rows for s in r['groups'].values())}
    return {'format': FORMAT, 'rows': rows, 'counts': counts}


def markdown(result):
    lines = ['# Creature moves', '', 'Generated by tools/creature_moves.py (%s).' % FORMAT, '',
             ' '.join('%s: %s.' % (k, v) for k, v in result['counts'].items()), '',
             '| Creature | Mesh | Flags | Attack | Side step | ' + ' | '.join(GROUPS) + ' | Mismatch |',
             '|' + '---|' * (6 + len(GROUPS))]
    for r in result['rows']:
        lines.append('| %s | %s | %s | %s | %s | %s | %s |' % (
            r['id'], r['mesh'], ', '.join(r['flags']) or '-', r['attack_style'], 'yes' if r['side_steps'] else 'no',
            ' | '.join(r['groups'].get(g, '-') for g in GROUPS), '; '.join(r['mismatches']) or '-'))
    return '\n'.join(lines) + '\n'


def read_records(data):
    """The creature records of the three masters present in DATA, in load order (a later master's record replaces an
    earlier), as tools/creature_tables.py reads them."""
    import creature_library
    from creature_tables import MASTERS
    from mwad.paths import child_ci
    out = {}
    for name in MASTERS:
        path = child_ci(Path(data), name, required=False)
        if path:
            out.update(creature_library.plan(path.read_bytes())['bases'])
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('command', choices=('table', 'check'))
    p.add_argument('--data', required=True)
    p.add_argument('--library', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--md')
    a = p.parse_args(argv)
    result = table(read_records(a.data), json.loads(Path(a.library).read_text(encoding='utf-8')))
    Path(a.out).write_text(json.dumps(result, indent=1) + '\n', encoding='utf-8', newline='\n')
    if a.md:
        Path(a.md).write_text(markdown(result), encoding='utf-8', newline='\n')
    print('creature moves: %s' % ', '.join('%s %s' % (k, v) for k, v in result['counts'].items()))
    for r in result['rows']:
        if r['mismatches']:
            print('  MISMATCH %s (%s): %s' % (r['id'], r['mesh'], '; '.join(r['mismatches'])))
    return 1 if a.command == 'check' and result['counts']['mismatches'] else 0


if __name__ == '__main__':
    sys.exit(main())
