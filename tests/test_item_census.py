"""The item census (tools/item_census.py, DROP-ALL-TEST-58) without game data: it fails when a kind of item has
no catalogue row, no icon or no world model."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import item_census as ic  # noqa: E402


def rec(ident, kind, model='m/a.nif', icon='a.dds'):
    return {'id': ident, 'kind': kind, 'model': model, 'icon': icon}


def every_kind(**override):
    """One complete record per kind (model m/<kind>.nif, icon <kind>.dds), some entries replaced."""
    out = {}
    for kind in ic.KIND_LABELS:
        tag = kind.replace(':', '_').lower()
        out[kind] = rec('item_' + tag, kind, 'm/%s.nif' % tag, '%s.dds' % tag)
    out.update(override)
    return list(out.values())


def table_of(records):
    return {ic.mesh_key(r['model']) for r in records if r['model']}


def ids_of(records):
    return {r['id'].casefold() for r in records}


class ItemCensusTests(unittest.TestCase):
    def test_complete_builder_passes(self):
        records = every_kind()
        result = ic.census(records, ids_of(records), table_of(records))
        self.assertEqual(ic.check(result), [])
        self.assertEqual(result['all']['records'], len(ic.KIND_LABELS))
        self.assertIsNone(result['all']['icon_built'])

    def test_a_kind_missing_from_the_catalogue_fails(self):
        records = every_kind()
        catalogued = ids_of(records) - {'item_misc_key'}
        failures = ic.check(ic.census(records, catalogued, table_of(records)))
        self.assertEqual(failures, ['MISC:key: 1 of 1 items are not in the inventory catalogue'])

    def test_a_model_the_stage_held_back_fails(self):
        records = every_kind()
        held = {ic.mesh_key('m/appa.nif')}
        failures = ic.check(ic.census(records, ids_of(records), table_of(records), held))
        self.assertIn('APPA: 1 of 1 items name a world model that is not in the item model table', failures)

    def test_a_mesh_missing_from_the_table_fails_and_case_does_not_matter(self):
        records = every_kind(ALCH=rec('item_alch', 'ALCH', 'M\\Potion.NIF', 'p.dds'))
        table = table_of(records) - {'m/potion.nif'}
        self.assertEqual(len(ic.check(ic.census(records, ids_of(records), table))), 1)
        self.assertEqual(ic.check(ic.census(records, ids_of(records), table | {'m/potion.nif'})), [])

    def test_a_kind_without_any_model_or_icon_fails(self):
        records = every_kind(LOCK=rec('item_lock', 'LOCK', '', ''))
        failures = ic.check(ic.census(records, ids_of(records), table_of(records)))
        self.assertIn('LOCK: no item of the kind names a world model', failures)
        self.assertIn('LOCK: no item of the kind names an inventory picture', failures)

    def test_one_record_without_a_picture_is_counted_not_failed(self):
        records = every_kind() + [rec('item_weap_plain', 'WEAP', 'm/weap.nif', '')]
        result = ic.census(records, ids_of(records), table_of(records))
        self.assertEqual(ic.check(result), [])
        self.assertEqual(result['no_field']['WEAP']['icon'], ['item_weap_plain'])
        self.assertEqual(result['by_kind']['WEAP']['records'], 2)
        self.assertEqual(result['by_kind']['WEAP']['icon_field'], 1)

    def test_a_kind_with_no_records_fails(self):
        records = [r for r in every_kind() if r['kind'] != 'REPA']
        failures = ic.check(ic.census(records, ids_of(records), table_of(records)))
        self.assertEqual(failures, ['REPA: no item records at all (the kind is missing from the census)'])

    def test_image_columns(self):
        records = every_kind()
        result = ic.census(records, ids_of(records), table_of(records), icon_ids=ids_of(records) - {'item_clot'},
                           drawn_ids=ids_of(records) - {'item_ingr'})
        self.assertEqual(sorted(ic.check(result)),
                         sorted(['CLOT: 1 of 1 items name an inventory picture that the image does not carry',
                                 'INGR: 1 of 1 items have a catalogue row without a drawable world model']))
        self.assertEqual(result['all']['icon_built'], len(ic.KIND_LABELS) - 1)
        self.assertEqual(result['by_kind']['INGR']['model_drawn'], 0)

    def test_effect_records_are_not_items(self):
        items = {'WEAP': {'vfx_x': {'id': 'vfx_x', 'model': 'e/x.nif', 'icon': '', 'type': 0, 'carry': True},
                          'magic_bolt': {'id': 'magic_bolt', 'model': 'w/b.nif', 'icon': '', 'type': 0, 'carry': True},
                          'dagger': {'id': 'dagger', 'model': 'w/d.nif', 'icon': 'd.dds', 'type': 0, 'carry': True}},
                 'LIGH': {'lamp': {'id': 'lamp', 'model': 'l/l.nif', 'icon': 'l.dds', 'type': -1, 'carry': True},
                          'wall': {'id': 'wall', 'model': 'l/w.nif', 'icon': '', 'type': -1, 'carry': False}},
                 'MISC': {'gold_001': {'id': 'Gold_001', 'model': 'm/g.nif', 'icon': 'g.dds', 'type': 0, 'carry': True},
                          'key1': {'id': 'key1', 'model': 'm/k.nif', 'icon': 'k.dds', 'type': 1, 'carry': True},
                          'cup': {'id': 'cup', 'model': 'm/c.nif', 'icon': 'c.dds', 'type': 0, 'carry': True}}}
        got = {(r['id'], r['kind']) for r in ic.census_records(items)}
        self.assertEqual(got, {('dagger', 'WEAP'), ('lamp', 'LIGH'), ('Gold_001', 'MISC:gold'), ('key1', 'MISC:key'),
                               ('cup', 'MISC')})

    def test_image_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp)
            (id1 / 'gfx').mkdir()
            (id1 / 'inventory').mkdir()
            (id1 / 'progs').mkdir()
            (id1 / 'progs' / 'm.mdl').write_bytes(b'x')
            icon_row = b'inv:Ring_A'.ljust(160, b'\0')
            (id1 / 'gfx' / 'icons.awl').write_bytes(b'AWL2' + struct.pack('<I', 2) + icon_row +
                                                    b'item:other'.ljust(160, b'\0'))

            def row(ident, model):
                return ident.encode().ljust(64, b'\0') + b'\0' * 120 + model.encode().ljust(64, b'\0') + \
                    b'\0' * (512 - 248)
            (id1 / 'inventory' / 'items.awi').write_bytes(b'AWI2' + struct.pack('<I', 2) + row('Ring_A', 'progs/m.mdl') +
                                                          row('ring_b', 'progs/gone.mdl'))
            icons, drawn = ic.read_image(id1)
            self.assertEqual(icons, {'ring_a'})
            self.assertEqual(drawn, {'ring_a'})

    def test_every_item_type_of_the_coverage_tool_is_catalogued(self):
        """A record type the coverage tool counts as an item but the inventory builder does not catalogue could
        be neither owned nor dropped."""
        import item_coverage
        import prepare_inventory
        self.assertEqual(set(item_coverage.TYPES) - set(prepare_inventory.KINDS), set())
        self.assertEqual({k.split(':')[0] for k in ic.KIND_LABELS}, set(item_coverage.TYPES))


if __name__ == '__main__':
    unittest.main()
