# SPDX-License-Identifier: GPL-3.0-only
"""The index of every item the player can hold in the hands (DBG-CYCLEITEMS-67; docs/INVENTORY.md "Every item the
hands can hold").

Made in the image step from the game's own records (Morrowind, Tribunal and Bloodmoon, through the item catalogue's
reader tools/prepare_inventory.py source_items), never by hand. The item tests (the item tester and its test field,
the look book's held-item page) go through it.

  id1/inventory/holdable.txt    (cp1252 text, one item per line, fields separated by tabs)
    AWHI1
    <game name> <id> <kind> <hands> <action> <equips>

  kind     the weapon type (short blade, long blade, long blade two-handed, blunt, blunt two-handed, blunt two-handed
           wide, spear, axe, axe two-handed, bow, crossbow, thrown), shield, light, lockpick or probe
  hands    right, left, or both (a two-handed weapon, a bow, a crossbow)
  action   the original's animation group of its use (OpenMW 0.51 mwmechanics/weapontype.cpp, read not copied):
           shortbladeonehand, weapononehand, weapontwohand, bluntonehand, blunttwohand, weapontwowide, bowandarrow,
           crossbow, throwweapon; shield = block (the original's "shield" group); light = none (it is carried: the left
           arm takes the "torch" group); lockpick and probe = pickprobe
  equips   1 when the catalogue equips it today (its row's equip flag), else 0 (a lockpick or probe until they are held,
           or a piece the catalogue refuses with its named reason)

Rules (the original's, as OpenMW 0.51 reads them): a weapon is held in the right hand, both hands for a two-handed one
and the marksman's bow and crossbow (mwworld/inventorystore.cpp, weapontype.cpp TwoHanded); arrows and bolts are
ammunition, not held. A shield (ARMO type 8) and a carried light (LIGH flag "can carry") take the left hand; a lockpick
(LOCK) and a probe (PROB) the right. Other tools (repair hammers, apparatus) are used from the inventory, not held."""

FORMAT = 'AWHI1'
PATH = 'inventory/holdable.txt'
# WPDT type -> (kind, hands, action)
WEAPONS = {
    0: ('short blade', 'right', 'shortbladeonehand'),
    1: ('long blade', 'right', 'weapononehand'),
    2: ('long blade two-handed', 'both', 'weapontwohand'),
    3: ('blunt', 'right', 'bluntonehand'),
    4: ('blunt two-handed', 'both', 'blunttwohand'),
    5: ('blunt two-handed wide', 'both', 'weapontwowide'),
    6: ('spear', 'both', 'weapontwowide'),
    7: ('axe', 'right', 'bluntonehand'),
    8: ('axe two-handed', 'both', 'blunttwohand'),
    9: ('bow', 'both', 'bowandarrow'),
    10: ('crossbow', 'both', 'crossbow'),
    11: ('thrown', 'right', 'throwweapon'),
}
SHIELD = 8
KIND_ORDER = [v[0] for _, v in sorted(WEAPONS.items())] + ['shield', 'light', 'lockpick', 'probe']


def holdable(item):
    """(kind, hands, action) of a catalogue source item (prepare_inventory.source_items' dict), or None."""
    if item['kind'] == 'WEAP':
        return WEAPONS.get(item['subtype'])
    if item['kind'] == 'ARMO' and item['subtype'] == SHIELD:
        return ('shield', 'left', 'block')
    if item.get('light'):
        return ('light', 'left', 'none')
    if item['kind'] == 'LOCK':
        return ('lockpick', 'right', 'pickprobe')
    if item['kind'] == 'PROB':
        return ('probe', 'right', 'pickprobe')
    return None


def rows(items, row_flags):
    """[(name, id, kind, hands, action, equips)] of every holdable item, in kind order, then by id. ROW_FLAGS {id:
    the catalogue row's flags} (bit 1 equippable, bit 4 equipped by the inventory's E today)."""
    out = []
    for identifier, item in items.items():
        held = holdable(item)
        if held is None:
            continue
        flags = row_flags.get(identifier, 0)
        name = ' '.join(str(item['name']).split()) or identifier
        out.append((name, identifier) + held + (1 if flags & 1 and flags & 4 else 0,))
    out.sort(key=lambda r: (KIND_ORDER.index(r[2]), r[1]))
    return out


def text(index_rows):
    """The index file's bytes (cp1252, as the catalogue's names)."""
    lines = [FORMAT]
    for row in index_rows:
        if any('\t' in str(v) or '\n' in str(v) for v in row):
            raise ValueError('A tab or line break in a holdable item field: %r' % (row,))
        lines.append('\t'.join(str(v) for v in row))
    return ('\n'.join(lines) + '\n').encode('cp1252')


def read(raw):
    """text()'s rows back (the tests, the look book and the receipt check)."""
    lines = raw.decode('cp1252').rstrip('\n').split('\n')
    if lines[0] != FORMAT:
        raise ValueError('Not a holdable item index')
    out = []
    for line in lines[1:]:
        f = line.split('\t')
        if len(f) != 6 or f[2] not in KIND_ORDER or f[3] not in ('right', 'left', 'both') or f[5] not in ('0', '1'):
            raise ValueError('Damaged holdable item row: %r' % line)
        out.append((f[0], f[1], f[2], f[3], f[4], int(f[5])))
    return out


def write_index(id1, items, row_flags):
    """Write id1/inventory/holdable.txt; the report (counts per kind, how many equip today)."""
    from pathlib import Path
    index_rows = rows(items, row_flags)
    out = Path(id1) / PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(text(index_rows))
    kinds = {}
    for r in index_rows:
        k = kinds.setdefault(r[2], [0, 0])
        k[0] += 1
        k[1] += r[5]
    print('Holdable item index: %d items (%d equip today) in %s' % (len(index_rows), sum(r[5] for r in index_rows),
                                                                    PATH), flush=True)
    return {'path': PATH, 'items': len(index_rows), 'equip': sum(r[5] for r in index_rows),
            'kinds': {k: {'items': v[0], 'equip': v[1]} for k, v in kinds.items()}}
