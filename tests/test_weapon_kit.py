# SPDX-License-Identifier: GPL-3.0-only
"""dbg give weapons (DBG-GIVE-WEAPONS-59): the builder's weapon kit table from synthetic original records (the rule:
plain items, iron/steel/chitin first, the most often named, then the cheaper; the records' own numbers), the engine's
rules on that same table (tests/aga_weapon_kit_test.c: parse, all-or-nothing grant, console lines), the catalogue
route and the docs."""
import os
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import prepare_inventory as inv
import prepare_weapon_kit as kit

SRC = ROOT / 'engine/aga/src'
MESH = 'w\\w_test.nif'


def field(kind, data):
    return kind.encode() + struct.pack('<I', len(data)) + data


def record(kind, fields):
    data = b''.join(field(k, v) for k, v in fields)
    return kind.encode() + struct.pack('<III', len(data), 0, 0) + data


def text(value):
    return value.encode() + b'\0'


def weapon(ident, name, weapon_type, value, chop, *, thrust=None, weight=3., health=400, speed=2.5, reach=1.,
           enchant=20, extra=()):
    wpdt = struct.pack('<fihhffH6Bi', weight, value, weapon_type, health, speed, reach, enchant, *chop, *chop,
                       *(thrust or chop), 0)
    fields = [('NAME', text(ident))] + ([('FNAM', text(name))] if name else [])
    return record('WEAP', fields + [('MODL', text(MESH)), ('ITEX', text('w\\tx.tga')), ('WPDT', wpdt), *extra])


def shield(ident, name, weight, value, health=200, enchant=250, armour=10):
    aodt = struct.pack('<ifiiii', 8, weight, value, health, enchant, armour)
    return record('ARMO', [('NAME', text(ident)), ('FNAM', text(name)), ('MODL', text(MESH)),
                           ('ITEX', text('a\\tx.tga')), ('AODT', aodt)])


def gmst(name, value):
    return record('GMST', [('NAME', text(name)), ('FLTV' if name[0] == 'f' else 'INTV',
                                                  struct.pack('<f' if name[0] == 'f' else '<i', value))])


def npco(ident, count=1):
    return ('NPCO', struct.pack('<i', count) + ident.encode().ljust(32, b'\0'))


def master():
    raw = b''.join(gmst(*g) for g in (('iShieldWeight', 9), ('fLightMaxMod', .6), ('fMedMaxMod', .9),
                                       ('iBaseArmorSkill', 30)))
    raw += weapon('iron dagger', 'Iron Dagger', 0, 10, (4, 5), thrust=(5, 5))
    raw += weapon('iron fork', 'Iron Fork', 0, 1, (3, 5))                 # cheapest iron, named by nothing
    raw += weapon('chitin dagger', 'Chitin Dagger', 0, 6, (3, 3))         # named less often than the iron dagger
    raw += weapon('glass dagger', 'Glass Dagger', 0, 900, (6, 9))         # named most often, not iron/steel/chitin
    raw += weapon('firebite dagger', 'Firebite Dagger', 0, 10, (3, 3), extra=[('ENAM', text('firebite'))])
    raw += weapon('chargen dagger', 'Iron Dagger', 0, 1, (4, 5), extra=[('SCRI', text('chargendagger'))])
    raw += weapon('vfx_bolt', '', 12, 0, (0, 0))                          # no name of its own: a spell effect
    raw += weapon('chitin short bow', 'Chitin Short Bow', 9, 20, (1, 10), weight=2., health=500, speed=1.,
                  enchant=10)
    raw += weapon('iron arrow', 'Iron Arrow', 12, 1, (2, 3), weight=.1, health=10, speed=1.)
    raw += shield('chitin_shield', 'Chitin Shield', 4., 22)
    raw += record('CELL', [('NAME', text('Seyda Neen')), ('NAME', text('iron dagger')), ('NAME', text('iron dagger')),
                           ('NAME', text('glass dagger')), ('NAME', text('glass dagger')), ('NAME', text('glass dagger')),
                           ('NAME', text('firebite dagger')), ('NAME', text('firebite dagger'))])
    raw += record('NPC_', [('NAME', text('guard')), npco('iron dagger'), npco('chitin dagger'),
                           npco('firebite dagger'), npco('glass dagger')])
    raw += record('LEVI', [('NAME', text('random_dagger')), ('INAM', text('chitin dagger'))])
    return raw


def build(tmp):
    base = Path(tmp)
    (base / 'Morrowind.esm').write_bytes(master())
    table = {inv.mesh_key(MESH): 'progs/items/m0000000000000001.mdl'}
    with patch.object(inv, 'resolve_data_files', return_value=base):
        report = inv.prepare(base, base / 'id1', palette=b'\0' * 768, models=False, model_table=table)
    return base / 'id1' / kit.KIT_PATH, report


class WeaponKitBuilderTests(unittest.TestCase):
    def test_kit_rule_and_record_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, report = build(tmp)
            lines = path.read_text(encoding='ascii').splitlines()
        self.assertEqual(lines[0], 'AWKIT1')
        self.assertEqual(lines[2:], [
            'iron dagger|1|W|short blade|Iron Dagger|4-5|4-5|5-5|2.5|1|3|10|400|20|-',
            'chitin short bow|1|R|bow|Chitin Short Bow|1-10|-|-|1|-|2|20|500|10|-',
            'iron arrow|50|A|arrows|Iron Arrow|2-3|-|-|-|-|0.1|1|-|20|-',
            'chitin_shield|1|S|light shield|Chitin Shield|-|-|-|-|-|4|22|200|250|10'])
        kit_report = report['weapon_kit']
        self.assertEqual([r['id'] for r in kit_report['rows']],
                         ['iron dagger', 'chitin short bow', 'iron arrow', 'chitin_shield'])
        self.assertEqual(kit_report['rows'][0]['uses'], 3)
        self.assertIn('heavy shield', kit_report['missing'])
        self.assertIn('crossbow', kit_report['missing'])
        self.assertEqual(len(kit_report['sha256']), 64)

    def test_every_kit_item_is_a_catalogue_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, _ = build(tmp)
            items = (path.parent / 'items.awi').read_bytes()
            ids = {items[8 + i * 512:8 + i * 512 + 64].split(b'\0')[0].decode() for i in range(struct.unpack_from('<I', items, 4)[0])}
            for line in path.read_text(encoding='ascii').splitlines()[2:]:
                self.assertIn(line.split('|')[0], ids)

    def test_no_plain_item_no_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'Morrowind.esm').write_bytes(weapon('firebite dagger', 'Firebite Dagger', 0, 10, (3, 3),
                                                        extra=[('ENAM', text('firebite'))]))
            with patch.object(inv, 'resolve_data_files', return_value=base):
                report = inv.prepare(base, base / 'id1', palette=b'\0' * 768, models=False,
                                     model_table={inv.mesh_key(MESH): 'progs/items/m1.mdl'})
            self.assertFalse((base / 'id1' / kit.KIT_PATH).exists())
        self.assertIsNone(report['weapon_kit']['path'])

    def test_every_weapon_type_has_a_label_and_kind(self):
        self.assertEqual(sorted(kit.TYPES), list(range(14)))
        self.assertEqual({v[1] for v in kit.TYPES.values()}, {'W', 'R', 'T', 'A'})
        self.assertEqual(kit.number(1.350000023841858), '1.35')
        self.assertEqual(kit.number(3.0), '3')
        self.assertEqual(kit.number(40), '40')

    @unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
    @unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
    def test_engine_rules_on_the_builders_table(self):
        from test_aga_native_source import NativeSourceTests
        with tempfile.TemporaryDirectory(prefix='amiwind-weapon-kit-') as tmp:
            path, _ = build(tmp)
            NativeSourceTests.compile_run(self, 'aga_weapon_kit_test.c', [SRC / 'aw_inventory.c', SRC / 'aw_state.c'],
                                          defines=['AW_INVENTORY_RULES_ONLY'],
                                          cflags=['-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                                                  '-Wno-unused-parameter', '-fsanitize=address,undefined',
                                                  '-fno-sanitize-recover=all'],
                                          arguments=[str(path)])


class WeaponKitWiringTests(unittest.TestCase):
    def test_catalogue_route_and_command(self):
        catalogue = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8')
        self.assertIn('PLAYTESTING|give weapons|aw_inventory|[stats] ', catalogue)
        console = (SRC / 'aw_console.c').read_text(encoding='utf-8')
        self.assertIn('strcpy(out+used," give weapons");', console)
        inventory = (SRC / 'aw_inventory.c').read_text(encoding='utf-8')
        self.assertIn('#define WEAPON_KIT_FILE "inventory/weapon-kit.txt"', inventory)
        self.assertEqual(kit.KIT_PATH, 'inventory/weapon-kit.txt')
        # read on the command and freed after it: nothing resident
        body = inventory[inventory.index('static void weapon_kit(int give)'):inventory.index('void AW_InventoryGrantCommand')]
        self.assertEqual(body.count('AW_TryMalloc('), 2)
        # a line exactly the console's width is followed by an empty one (seen in game, 78 columns): one less
        self.assertIn('width=AW_ConsoleWidth()-1', body)
        self.assertGreaterEqual(body.count('free(rows)'), 5)

    def test_docs(self):
        page = (ROOT / 'docs/INVENTORY.md').read_text(encoding='utf-8')
        self.assertIn('dbg give weapons', page)
        commands = (ROOT / 'docs/AMIWIND_CONSOLE_COMMANDS.md').read_text(encoding='utf-8')
        self.assertIn('`dbg give weapons`', commands)


if __name__ == '__main__':
    unittest.main()
