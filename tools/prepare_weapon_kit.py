#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The weapon kit of `dbg give weapons` (DBG-GIVE-WEAPONS-59): one of the game's own weapons of every weapon type, and
a light and a heavy shield, chosen from the records at build time into inventory/weapon-kit.txt (the engine reads it
only when the command runs; nothing of it is resident).

The choice is a rule, never a hand list: per type, the plain items (no enchantment, no script, a name, a world model
and an icon in the catalogue), those of iron, steel or chitin first, then the one the game's records name most often
(references placed in cells, NPC, creature and container inventories, levelled item lists), then the cheaper, then
the id. Melee weapons that can be equipped come before those that cannot. Each row carries the record's own numbers:
chop, slash and thrust (for bows, crossbows, thrown weapons and ammunition the chop is their damage), speed, reach,
weight, value, health, enchantment points and, for shields, armour; "-" where a number does not apply to the kind.

Table (ASCII, one row per line, after the line AWKIT1; aw_inventory.c AW_WeaponKitParse):
  id|count|kind|type|name|chop|slash|thrust|speed|reach|weight|value|health|enchant|armour
kind: W melee, R bow or crossbow, T thrown, A arrows or bolts, S shield.
"""
import hashlib, struct
from collections import Counter
from mwad.esm import records, subrecords, text

KIT_PATH = 'inventory/weapon-kit.txt'
MATERIALS = ('iron', 'steel', 'chitin')
# Original weapon type (WPDT type) -> the console's type label, the kind and how many are given.
TYPES = {0: ('short blade', 'W', 1), 1: ('long blade, 1H', 'W', 1), 2: ('long blade, 2H', 'W', 1),
         3: ('blunt, 1H', 'W', 1), 4: ('blunt, 2H', 'W', 1), 5: ('staff, 2H', 'W', 1), 6: ('spear, 2H', 'W', 1),
         7: ('axe, 1H', 'W', 1), 8: ('axe, 2H', 'W', 1), 9: ('bow', 'R', 1), 10: ('crossbow', 'R', 1),
         11: ('thrown', 'T', 20), 12: ('arrows', 'A', 50), 13: ('bolts', 'A', 50)}
# Shield armour class (0 light, 1 medium, 2 heavy, by weight as prepare_inventory classes it) -> label.
SHIELDS = ((0, 'light shield'), (2, 'heavy shield'))
SHIELD_TYPE = 8
FLAG_EQUIP_SUPPORTED = 4
NAME_BYTES, TYPE_BYTES, STAT_BYTES = 48, 24, 12


def record_uses(esm):
    """How often the game's records name each id (casefolded): references placed in cells, NPC, creature and
    container inventories (NPCO) and levelled item lists (INAM)."""
    uses = Counter()
    for kind, _, raw in records(esm):
        if kind not in ('CELL', 'NPC_', 'CREA', 'CONT', 'LEVI'):
            continue
        fields = list(subrecords(raw))
        if kind == 'CELL':
            names = [value for tag, value in fields if tag == 'NAME'][1:]   # the first NAME is the cell's own
        elif kind == 'LEVI':
            names = [value for tag, value in fields if tag == 'INAM']
        else:
            names = [value[4:] for tag, value in fields if tag == 'NPCO' and len(value) > 4]
        for value in names:
            uses[value.split(b'\0')[0].decode('cp1252', 'replace').casefold()] += 1
    return uses


def number(value):
    """A record's number as the original's tooltips show it: up to two decimals, trailing zeros dropped (OpenMW
    mwgui/tooltips.cpp toString; aw_inventory.c weight_text)."""
    if isinstance(value, int):
        return str(value)
    out = '%.2f' % value
    return out.rstrip('0').rstrip('.') if '.' in out else out


def span(low, high):
    return '%d-%d' % (low, high)


def _fits(item):
    name = item['name']
    return (all(32 <= ord(c) < 127 and c not in '|"' for c in name + item['id']) and
            len(name.encode('cp1252')) < NAME_BYTES and len(item['id']) < 64)


def _plain(item, flags):
    """No enchantment, no script, an own name, a world model in the catalogue (flag 2) and an icon."""
    return (not item['enchantment'] and not item['script'] and item['name'] != item['id'] and
            bool(item['source_icon']) and bool(flags.get(item['id'], 0) & 2) and _fits(item))


def _rank(item, uses, prefer_equip, flags):
    material = item['name'].split()[0].casefold() if item['name'].split() else ''
    return (material not in MATERIALS, prefer_equip and not flags.get(item['id'], 0) & FLAG_EQUIP_SUPPORTED,
            -uses[item['id']], item['value'], item['id'])


def weapon_row(item, label, kind, count):
    raw = item['raw']
    weight, value, _, health, speed, reach, enchant = struct.unpack_from('<fihhffH', raw)
    chop, slash, thrust = raw[22:24], raw[24:26], raw[26:28]
    dash = '-'
    if kind == 'W':
        stats = [span(*chop), span(*slash), span(*thrust), number(speed), number(reach)]
    elif kind == 'R':
        stats = [span(*chop), dash, dash, number(speed), dash]
    else:   # thrown weapons and ammunition: their damage; no condition (OpenMW hasItemHealth)
        stats = [span(*chop), dash, dash, number(speed) if kind == 'T' else dash, dash]
    stats += [number(weight), number(value), number(int(health)) if kind in 'WR' else dash, number(int(enchant)), dash]
    return [item['id'], str(count), kind, label, item['name'], *stats]


def shield_row(item, label):
    _, weight, value, health, enchant, armour = struct.unpack_from('<ifiiii', item['raw'])
    return [item['id'], '1', 'S', label, item['name'], '-', '-', '-', '-', '-', number(weight), number(value),
            number(health), number(enchant), number(armour)]


def shield_class(item, settings):
    """Light 0, medium 1, heavy 2 by weight (OpenMW mwclass/armor.cpp getEquipmentSkill; prepare_inventory)."""
    limit = settings.get('ishieldweight')
    if limit is None:
        return None
    if item['weight'] <= limit * settings.get('flightmaxmod', .6) + .0005:
        return 0
    return 1 if item['weight'] <= limit * settings.get('fmedmaxmod', .9) + .0005 else 2


def choose(items, settings, flags, uses):
    """The kit's rows in order (weapon types 0..13, then the shields) and the types the records have no plain
    item for."""
    rows, chosen, missing = [], [], []
    by_type = {}
    for item in items.values():
        if item['kind'] == 'WEAP' and len(item.get('raw', b'')) == 32 and _plain(item, flags):
            by_type.setdefault(struct.unpack_from('<h', item['raw'], 8)[0], []).append(item)
    for weapon_type, (label, kind, count) in sorted(TYPES.items()):
        candidates = sorted(by_type.get(weapon_type, ()), key=lambda i: _rank(i, uses, kind == 'W', flags))
        if not candidates:
            missing.append(label)
            continue
        best = candidates[0]
        rows.append(weapon_row(best, label, kind, count))
        chosen.append({'id': best['id'], 'type': label, 'name': best['name'], 'uses': uses[best['id']]})
    shields = [i for i in items.values() if i['kind'] == 'ARMO' and i['subtype'] == SHIELD_TYPE and
               len(i.get('raw', b'')) >= 24 and _plain(i, flags)]
    for wanted, label in SHIELDS:
        candidates = sorted((i for i in shields if shield_class(i, settings) == wanted),
                            key=lambda i: _rank(i, uses, True, flags))
        if not candidates:
            missing.append(label)
            continue
        best = candidates[0]
        rows.append(shield_row(best, label))
        chosen.append({'id': best['id'], 'type': label, 'name': best['name'], 'uses': uses[best['id']]})
    for row in rows:
        if len(row[3]) >= TYPE_BYTES or any(len(stat) >= STAT_BYTES or ' ' in stat for stat in row[5:]):
            raise ValueError('Weapon kit field exceeds its limit: ' + row[0])
    return rows, chosen, missing


def write_kit(id1, items, settings, flags, esm):
    """Write inventory/weapon-kit.txt under ID1 from the catalogue's ITEMS (prepare_inventory.source_items), the
    game SETTINGS, each catalogue row's FLAGS and the master's bytes ESM; the report for the build receipt. No row:
    no file (an engine without the file says so on the command)."""
    rows, chosen, missing = choose(items, settings, flags, record_uses(esm))
    report = {'path': KIT_PATH, 'rows': chosen, 'missing': missing}
    out = id1 / KIT_PATH
    if not rows:
        report['path'] = None
        return report
    body = 'AWKIT1\n# id|count|kind|type|name|chop|slash|thrust|speed|reach|weight|value|health|enchant|armour\n'
    body += ''.join('|'.join(row) + '\n' for row in rows)
    raw = body.encode('ascii')
    if len(raw) > 8192:
        raise ValueError('Weapon kit table larger than the engine reads (8192 bytes)')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)
    report['sha256'] = hashlib.sha256(raw).hexdigest()
    print('[weapon kit] %d items, %s%s' % (len(rows), ', '.join(r['id'] for r in chosen),
                                           ('; none for ' + '; '.join(missing)) if missing else ''), flush=True)
    return report
