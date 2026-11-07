# SPDX-License-Identifier: GPL-3.0-only
"""Scripted world events: the actors that stand on an object a script removes, and the census of distance-triggered
events (SCRIPTED-EVENT-FALLING-MAGE-61, v0.0.62).

The original's falling mage north of Seyda Neen is not scripted to fall: he stands on an invisible platform, a
script disables the platform, and the game's physics drops him (OpenMW 0.51: World::disable removes the platform's
collision; the actor then falls under gravity and the fall damage on landing kills him, mwmechanics/character.cpp).
So the general rule, for every actor of the game data, not one name:

  an actor HELD by an object = an NPC or creature placed in the same cell as a placed object (activator, static,
  container or door) that some script disables, standing on it: its feet at most HELD_REACH game units sideways
  from the object's origin and from 0 to HELD_RISE units above it.

The builder writes each such pair as a row of the HELD section of id1/mwscript.awm (awms.py): the actor's reference,
the object's reference and the actor's placed position. The engine keeps a held actor at that position (no ground
snap) while the object is there and lets it fall once a script disables the object (aw_fall.c).

Measured on the game data, 7 November 2026: 1 actor of Morrowind.esm (the falling mage on his platform); the other
candidates near a disabled object stand beside it (more than 32 units sideways) or below it, listed in the report
with the reason.

census() lists every placed script that waits for the player's distance (GetDistance) and then changes the world
(Enable, Disable, StartCombat, a Place call, PositionCell, a Fall): the scripted world events of this kind, for the
script tracker (docs/MWSCRIPT_FEATURES.md)."""
import re

ACTOR_TYPES = ('NPC_', 'CREA')
SUPPORT_TYPES = ('ACTI', 'STAT', 'CONT', 'DOOR')
HELD_REACH = 32.0     # game units sideways from the object's origin
HELD_RISE = 128.0     # game units above the object's origin at most
NEAR = 160.0          # the report's look-around for candidates (sideways)

_TARGET = r'(?:"([^"]+)"|([^\s",;()]+))'
_DISABLE_REF = re.compile(_TARGET + r'\s*->\s*disable\b', re.I)
_DISABLE_SELF = re.compile(r'(?:^|[\s,])disable\b', re.I)
# what a distance-triggered event does, by the call (case folded)
EVENT_CALLS = (('enable', 'enables'), ('disable', 'disables'), ('startcombat', 'attacks'),
               ('placeatpc', 'places'), ('placeatme', 'places'), ('placeitem', 'places'),
               ('positioncell', 'moves'), ('position', 'moves'), ('fall', 'falls'), ('forcegreeting', 'greets'),
               ('aitravel', 'walks'), ('aifollow', 'follows'), ('say', 'says'), ('playsound', 'plays a sound'))


def _code(text):
    """The script's lines without comments."""
    return '\n'.join(line.split(';', 1)[0] for line in (text or '').splitlines())


def disable_targets(data):
    """The folded ids a script disables: `ID->Disable` in any script or dialogue result, and every record whose own
    script calls Disable without a reference (it disables itself)."""
    targets = set()
    texts = [s.text for s in data.scripts.values()] + [text for (_, text) in getattr(data, 'results', {})]
    for text in texts:
        for m in _DISABLE_REF.finditer(_code(text)):
            targets.add((m.group(1) or m.group(2)).strip().casefold())
    for ident, (_, script) in data.bases.items():
        s = data.scripts.get(script) if script else None
        if s is None:
            continue
        for line in _code(s.text).splitlines():
            m = _DISABLE_SELF.search(line)
            if m and '->' not in line[:m.start() + 1]:
                targets.add(ident)
                break
    return targets


def held_actors(data):
    """{'rows': [{actor, actor_id, support, support_id, cell, position, rise, reach}], 'near': [...]} : the held
    pairs by the rule above (rows, sorted by actor reference) and the other actors within NEAR of a disabled object
    with why they are not held (near)."""
    targets = disable_targets(data)
    placed = getattr(data, 'placements', {})
    by_cell = {}
    for number, (kind, ident, cell, x, y, z) in placed.items():
        by_cell.setdefault(cell, ([], []))
        if kind in ACTOR_TYPES:
            by_cell[cell][0].append((number, ident, x, y, z))
        elif kind in SUPPORT_TYPES and ident in targets and len(data.object_refs.get(ident, ())) == 1:
            by_cell[cell][1].append((number, ident, x, y, z))
    rows, near = [], []
    for cell, (actors, supports) in by_cell.items():
        for a in actors:
            best = None
            for s in supports:
                reach = ((a[2] - s[2]) ** 2 + (a[3] - s[3]) ** 2) ** 0.5
                rise = a[4] - s[4]
                if reach > NEAR:
                    continue
                if reach <= HELD_REACH and 0.0 < rise <= HELD_RISE:
                    if best is None or rise < best[1]:
                        best = (s, rise, reach)
                else:
                    near.append({'actor': a[0], 'actor_id': a[1], 'support': s[0], 'support_id': s[1],
                                 'why': ('%.0f units sideways' % reach) if reach > HELD_REACH else
                                        ('%.0f units %s it' % (abs(rise), 'below' if rise <= 0 else 'above'))})
            if best:
                s, rise, reach = best
                rows.append({'actor': a[0], 'actor_id': a[1], 'support': s[0], 'support_id': s[1], 'cell': cell,
                             'position': (a[2], a[3], a[4]), 'rise': round(rise, 1), 'reach': round(reach, 1)})
    rows.sort(key=lambda r: r['actor'])
    near.sort(key=lambda r: (r['actor'], r['support']))
    return {'rows': rows, 'near': near}


def check(data):
    """The held report; raises ValueError when a held pair cannot work in the engine (a reference out of the
    24-bit range the object state keys by, or an actor held twice)."""
    r = held_actors(data)
    seen, problems = set(), []
    for row in r['rows']:
        if not (0 < row['actor'] <= 0xFFFFFF and 0 < row['support'] <= 0xFFFFFF):
            problems.append('%s on %s: reference out of range' % (row['actor_id'], row['support_id']))
        if row['actor'] in seen:
            problems.append('%s held twice' % row['actor_id'])
        seen.add(row['actor'])
    if problems:
        raise ValueError('Held actors check (SCRIPTED-EVENT-FALLING-MAGE-61): ' + '; '.join(problems))
    return r


def census(data):
    """Every placed scripted object whose script tests the player's distance and changes the world: [{script, id,
    type, cell, reference, does: [verbs]}], sorted by script and cell; one row per script and placement (Morrowind.esm
    placements; scripts of the add-ons are listed with no placement when the image does not place them)."""
    events = {}
    for name, s in data.scripts.items():
        code = _code(s.text).lower()
        if 'getdistance' not in code:
            continue
        does = []
        for call, verb in EVENT_CALLS:
            if re.search(r'(?:^|[\s>,"(])' + call + r'\b', code) and verb not in does:
                does.append(verb)
        if not any(v in does for v in ('enables', 'disables', 'attacks', 'places', 'moves', 'falls')):
            continue
        events[name] = does
    rows = []
    for ref in data.references:
        if ref['script'] in events:
            rows.append({'script': ref['script'], 'id': ref['id'].casefold(), 'type': ref['type'],
                         'cell': ref['cell'], 'reference': ref['reference'], 'does': events[ref['script']]})
    placed = {r['script'] for r in rows}
    for name, does in events.items():
        if name not in placed:
            rows.append({'script': name, 'id': '', 'type': '', 'cell': '', 'reference': 0, 'does': does})
    rows.sort(key=lambda r: (r['script'], str(r['cell']), r['reference']))
    return rows
