# SPDX-License-Identifier: GPL-3.0-only
"""Routing-priority removal must preserve partial cores and direct dependencies."""
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from world_payload import prune, shadowed, subtract


def fixture(root):
    (root / 'world').mkdir()
    (root / 'maps').mkdir()
    # Town covers map zero; map one crosses its right boundary; map two
    # repeats map one and is shadowed by that earlier region.
    raw = b'AWR2' + struct.pack('<I', 3)
    raw += struct.pack('<7f', 0, 0, 0, 0, 0, 10, 10) * 2
    for i, core in enumerate(((0, 0, 10, 10), (5, 0, 15, 10), (5, 0, 15, 10))):
        raw += struct.pack('<8s11f', ('vf%04d' % i).encode(), 0, 0, 0, *core, -1000, -1000, 1000, 1000)
        data = struct.pack('<iii', 29, 124, 3) + bytes(112) + b'{}\0'
        (root / 'maps' / ('vf%04d.bsp' % i)).write_bytes(data)
    (root / 'world/regions.awr').write_bytes(raw)
    return [{'world_slot': 0}]


class PayloadTests(unittest.TestCase):
    def test_never_compiled_map_handoff_to_real_fingerprint(self):
        from build_aga import never_built_maps, write_content_fingerprint
        import build_aga
        import exterior_plan as E
        from test_harvest_fingerprint import HarvestFingerprintTests
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            id1, terrain = root / 'boot/id1', root / 'world-terrain'
            terrain.mkdir()
            HarvestFingerprintTests().seed(id1)
            towns = [{'owner': 'town', 'core': [0, 0, 2048, 2048]}]
            plan = E.make([(0, 0), (1, 0)], [], towns, 'master')
            rows = [dict(name='vf%04d' % i, cell=[i, 0], origin=[i*2048+1024, 1024, 0],
                         core=[[-1024]*2, [1024]*2], coverage=[[-1920]*2, [1920]*2]) for i in range(2)]
            rows[0]['routing_only'] = True
            packet = b'AWR2' + struct.pack('<I', 2) + bytes(56)
            for row in rows:
                packet += struct.pack('<8s11f', row['name'].encode(), *row['origin'],
                                      *row['core'][0], *row['core'][1], *row['coverage'][0], *row['coverage'][1])
            (id1 / 'world/regions.awr').write_bytes(packet)
            receipt = {'master_sha256': 'master', 'exterior_checklist': plan, 'regions': rows}
            (terrain / 'world-regions.json').write_text(json.dumps(receipt))
            entity = b'{"classname" "worldspawn" "_chim_frame" "0 0"}\0'
            owner = id1 / 'maps/town-chim.chim'
            owner.write_bytes(struct.pack('<iii', 29, 124, len(entity)) + bytes(112) + entity)
            (id1 / 'maps/vf0001.bsp').write_bytes(b'required-map')
            with patch.object(E, 'town_cores', return_value=towns), \
                 patch('town_config.runtime_towns', return_value=[{'id': 'town', 'name': 'town', 'regions': 'town/regions.awr', 'prefix': 'tt'}]), \
                 patch('area_config.SCENES', []), patch('build_aga.town_region_map_names', return_value=[]):
                omitted = never_built_maps(id1, [], terrain)
                self.assertEqual(omitted, ['maps/vf0000.bsp'])
                # Early layout runs before owner frame generation. It must
                # follow the same checklist, using validated CHIM town areas.
                import payload_preflight
                owner_bytes = owner.read_bytes()
                owner.unlink()
                before = {p: p.read_bytes() for p in id1.rglob('*') if p.is_file()}
                with patch.object(payload_preflight, 'planned_maps', return_value=([], set(), [])), \
                     patch.object(build_aga, 'chim_world_receipt', return_value=({}, ['town'])), \
                     patch('chim.frame_map.region_map_names', return_value=set()), \
                     patch.object(payload_preflight, 'check_disk_layout', wraps=payload_preflight.check_disk_layout) as layout:
                    args = SimpleNamespace(exterior_terrain=terrain, chim_world=root/'chim',
                                           payload_preflight_only=True)
                    # Invoke the real image wrapper; unrelated payload checks
                    # can fail on this small fixture, but the layout must pass.
                    with patch.object(payload_preflight, 'check_engine_map_limits', return_value=0):
                        try:
                            build_aga.payload_preflight(args, root, [], 1)
                        except ValueError as exc:
                            self.assertNotIn('disk-layout:', str(exc))
                    layout.assert_called_once()
                    self.assertIn('maps/vf0000.bsp', layout.call_args.args[1])
                # The real sky/cull/hand/night classifier also runs before
                # CHIM frame generation. Only validated omissions disappear.
                with patch.object(build_aga, 'chim_world_receipt', return_value=({}, ['town'])), \
                     patch('chim.frame_map.region_map_names', return_value=set()):
                    classified = build_aga.staged_exterior_map_names(id1, root/'chim', terrain)
                    self.assertEqual(classified, {'vf0001', 'intro_docks', 'sncourt'})
                    required = id1 / 'maps/vf0001.bsp'
                    required_bytes = required.read_bytes()
                    required.unlink()
                    self.assertEqual(build_aga.staged_exterior_map_names(id1, root/'chim', terrain), classified)
                    from exterior_sky_build import configure_staged_maps
                    with self.assertRaisesRegex(ValueError, 'Missing staged maps'):
                        configure_staged_maps(id1, exterior_maps=classified, work_dir=root/'sky')
                    required.write_bytes(required_bytes)
                with patch.object(build_aga, 'chim_world_receipt', return_value=({}, [])), \
                     patch('chim.frame_map.region_map_names', return_value=set()):
                    with self.assertRaisesRegex(ValueError, 'no planned CHIM town owner'):
                        build_aga.staged_exterior_map_names(id1, root/'chim', terrain)
                planned = E.omitted_paths(terrain, id1, planned_towns={'town'})
                self.assertEqual(planned, omitted)
                payload_preflight.check_disk_layout(id1.parent, set(planned), [], None)
                with self.assertRaises(FileNotFoundError):
                    payload_preflight.check_disk_layout(id1.parent, set(), [], None)
                with self.assertRaisesRegex(ValueError, 'no planned CHIM town owner'):
                    E.omitted_paths(terrain, id1, planned_towns=set())
                self.assertEqual({p: p.read_bytes() for p in before}, before)
                owner.write_bytes(owner_bytes)
                # Real prebuild command binding -> actual image CLI parser ->
                # the same final fingerprint entry called by finalize_image.
                argv = ['image', '--no-npc-gallery']
                for option in ('sdk', 'data-files', 'scene', 'media', 'engine', 'out',
                               'qcc', 'qbsp', 'vis', 'light', 'xdftool', 'rdbtool'):
                    argv += ['--' + option, str(root / option)]
                command = dict(E.bind_steps([('image', argv)], root / 'exterior-checklist.json'))['image']
                def assemble(args):
                    self.assertEqual(args.exterior_terrain, terrain)
                    handed = build_aga.image_content_fingerprint(args, id1, 1, [], [])
                    self.assertEqual(handed, omitted)
                    import world_volumes
                    def split(paths, boot_bytes):
                        self.assertEqual([p.name for p in paths], ['vf0001.bsp'])
                        return paths, []
                    with patch.object(world_volumes, 'partition_batches', side_effect=split), \
                         patch.object(world_volumes, 'write_partitions', return_value=[]):
                        world_volumes.pack(id1, root, '0.0.39-dev1', 'unused', omitted=handed)
                with patch.object(build_aga, 'image', side_effect=assemble), \
                     patch('build_profile.instrument'), patch.object(sys, 'argv', ['build_aga.py', *command]):
                    build_aga.main()
                before = (id1 / 'save-content.bin').read_bytes()
                owner.write_bytes(owner.read_bytes() + b'changed')
                write_content_fingerprint(id1, removed=omitted)
                self.assertNotEqual(before, (id1 / 'save-content.bin').read_bytes())
                self.assertFalse((terrain / 'vf0000').exists())
                self.assertFalse((id1 / 'maps/vf0000.bsp').exists())
                with self.assertRaises(FileNotFoundError):
                    write_content_fingerprint(id1)
                catalogue = id1 / 'harvest-vf0000.txt'
                catalogue.write_bytes(b'unused')
                with self.assertRaisesRegex(ValueError, 'unused harvest'):
                    never_built_maps(id1, [], terrain)
                catalogue.unlink()
                duplicate = id1 / 'maps/vf0000.bsp'
                duplicate.write_bytes(b'must never be compiled')
                with self.assertRaisesRegex(ValueError, 'compiled or staged'):
                    never_built_maps(id1, [], terrain)
                duplicate.unlink()
                owner.unlink()
                with self.assertRaisesRegex(ValueError, 'no active CHIM town owner'):
                    never_built_maps(id1, [], terrain)

    def test_volume_packer_requires_declared_omissions(self):
        import world_volumes
        with tempfile.TemporaryDirectory() as td:
            # pack() sizes everything under id1's parent: keep that parent private to this test
            root = Path(td) / 'id1'
            root.mkdir()
            towns = fixture(root)
            rows = prune(root, root / 'receipt.json', towns)
            omitted = [r['file'] for r in rows]
            with patch.object(world_volumes, 'write_partitions', return_value=[]) as writer:
                with self.assertRaises(FileNotFoundError):
                    world_volumes.pack(root, root, 'test', 'unused')
                writer.assert_not_called()
                # Only the required map reaches the real partition planner.
                world_volumes.pack(root, root, 'test', 'unused', omitted=omitted)
                self.assertEqual([[p.name for p in batch] for batch in writer.call_args.args[0]],
                                 [['vf0001.bsp']])

    def test_volume_packer_rejects_unexpected_absence_and_present_omission(self):
        import world_volumes
        with tempfile.TemporaryDirectory() as td:
            # pack() sizes everything under id1's parent: keep that parent private to this test
            root = Path(td) / 'id1'
            root.mkdir()
            fixture(root)
            with patch.object(world_volumes, 'write_partitions') as writer:
                with self.assertRaisesRegex(ValueError, 'remains at packing'):
                    world_volumes.pack(root, root, 'test', 'unused', omitted=['maps/vf0000.bsp'])
                (root / 'maps/vf0000.bsp').unlink()
                (root / 'maps/vf0001.bsp').unlink()
                with self.assertRaises(FileNotFoundError):
                    world_volumes.pack(root, root, 'test', 'unused', omitted=['maps/vf0000.bsp'])
                writer.assert_not_called()

    def test_pruned_world_fingerprint_binds_retained_maps_and_rejects_missing(self):
        from build_aga import write_content_fingerprint
        from test_harvest_fingerprint import HarvestFingerprintTests
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            towns = fixture(root)
            rows = prune(root, root / 'receipt.json', towns)
            removed = [row['file'] for row in rows]
            HarvestFingerprintTests().seed(root)
            with patch('area_config.SCENES', []), patch('build_aga.town_region_map_names', return_value=[]):
                write_content_fingerprint(root, removed=removed)
                before = (root / 'save-content.bin').read_bytes()
                kept = root / 'maps/vf0001.bsp'
                kept.write_bytes(kept.read_bytes() + b'changed')
                write_content_fingerprint(root, removed=removed)
                self.assertNotEqual(before, (root / 'save-content.bin').read_bytes())
                with self.assertRaises(FileNotFoundError):
                    write_content_fingerprint(root)
                kept.unlink()
                with self.assertRaises(FileNotFoundError):
                    write_content_fingerprint(root, removed=removed)

    def test_retired_catalogues_leave_and_retained_catalogues_validate(self):
        from build_aga import harvest_fingerprint_entries
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            towns = fixture(root)
            for name in ('vf0000', 'vf0001', 'vf0002'):
                (root / ('harvest-' + name + '.txt')).write_bytes(b'AWH1 0 0 0\n')
            # A town's catalogue-following table is a real dependency even
            # when routing otherwise shadows that map's core.
            (root / 'town-regions.txt').write_bytes(b'vf0002\n')
            rows = prune(root, root / 'receipt.json', towns)
            self.assertEqual([r['file'] for r in rows],
                             ['maps/vf0000.bsp', 'harvest-vf0000.txt'])
            self.assertFalse((root / 'harvest-vf0000.txt').exists())
            self.assertTrue((root / 'harvest-vf0001.txt').exists())
            self.assertTrue((root / 'harvest-vf0002.txt').exists())
            entries = harvest_fingerprint_entries(root, plant_capacity=256)
            self.assertEqual({name for name, _ in entries},
                             {'harvest-vf0001.txt', 'harvest-vf0002.txt'})

    def test_half_open_boundary_and_partial_core(self):
        self.assertEqual(subtract((0, 0, 10, 10), (10, 0, 20, 10)), [(0, 0, 10, 10)])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            towns = fixture(root)
            self.assertEqual(shadowed(root, towns), ['vf0000', 'vf0002'])
            rows = prune(root, root / 'receipt.json', towns)
            self.assertEqual([r['file'] for r in rows], ['maps/vf0000.bsp', 'maps/vf0002.bsp'])
            self.assertTrue((root / 'maps/vf0001.bsp').exists())
            self.assertEqual(len((root / 'world/regions.awr').read_bytes()), 220)

    def test_direct_door_dependency_retained(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            towns = fixture(root)
            (root / 'scene-doors.txt').write_bytes(b'destination vf0000\n')
            prune(root, root / 'receipt.json', towns)
            self.assertTrue((root / 'maps/vf0000.bsp').exists())
            report = json.loads((root / 'receipt.json').read_text())
            self.assertEqual(report['retained_dependencies'][0]['references'], ['scene-doors.txt'])

    def test_invalid_map_fails_before_removal(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            towns = fixture(root)
            (root / 'maps/broken.bsp').write_bytes(b'bad')
            with self.assertRaises(ValueError):
                prune(root, root / 'receipt.json', towns)
            self.assertTrue((root / 'maps/vf0000.bsp').exists())

    def test_entity_reference_and_chim_in_bsp_extension_survive(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            towns = fixture(root)
            for name, entity in [('vf0000', b'{"classname" "worldspawn" "_chim_frame" "0 0"}\0'),
                                 ('vf0001', b'{"classname" "trigger_changelevel" "map" "vf0002"}\0')]:
                (root / 'maps' / (name + '.bsp')).write_bytes(
                    struct.pack('<iii', 29, 124, len(entity)) + bytes(112) + entity)
            self.assertEqual(prune(root, root / 'receipt.json', towns), [])
            self.assertTrue((root / 'maps/vf0000.bsp').exists())
            self.assertTrue((root / 'maps/vf0002.bsp').exists())




class OceanChecklistTests(unittest.TestCase):
    def fixture(self):
        import exterior_plan as E
        plan = E.make([(0, 0)], [(1, 0)], master_sha256='master', ocean_cells=[(1, 0)])
        rows = [dict(name='vf%04d' % i, cell=[i, 0], origin=[i*2048+1024, 1024, 0],
                     core=[[-1024]*2, [1024]*2]) for i in range(2)]
        return E, plan, rows

    def test_explicit_ocean_is_separate_from_the_source_inventory(self):
        E, plan, rows = self.fixture()
        self.assertEqual(plan['ocean_cells'], [[1, 0]])
        self.assertEqual(E.validate(plan), plan)
        self.assertEqual(E.classify_regions(plan, rows[:1], 'master', {(1, 0)},
                                           before_ocean_routing=True), {'vf0000': 'bsp'})
        self.assertEqual(E.classify_regions(plan, rows, 'master', {(1, 0)}),
                         {'vf0000': 'bsp', 'vf0001': 'chim-region'})

    def test_missing_final_ocean_and_undeclared_cells_are_rejected(self):
        E, plan, rows = self.fixture()
        with self.assertRaisesRegex(ValueError, 'survey cells'):
            E.classify_regions(plan, rows[:1], 'master', {(1, 0)})
        with self.assertRaisesRegex(ValueError, 'absent'):
            E.make([(0, 0)], [(1, 0)], master_sha256='master')
        with self.assertRaisesRegex(ValueError, 'explicitly selected'):
            E.make([(0, 0)], [], master_sha256='master', ocean_cells=[(1, 0)])
        with self.assertRaisesRegex(ValueError, 'selection differs'):
            E.classify_regions(plan, rows, 'master', set())

    def test_completed_stage_requires_ocean_routing_and_no_bsp(self):
        E, plan, rows = self.fixture()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); path = root/'checklist.json'
            path.write_text(json.dumps(plan))
            def write(selected):
                (root/'world-regions.json').write_text(json.dumps(
                    dict(master_sha256='master', regions=selected)))
            write(rows[:1])
            with self.assertRaisesRegex(ValueError, 'survey cells'):
                E.verify_stage(path, root)
            write(rows)
            with self.assertRaisesRegex(ValueError, 'ownership changed'):
                E.verify_stage(path, root)
            rows[1]['chim_region'] = True; write(rows)
            E.verify_stage(path, root)


if __name__ == '__main__':
    unittest.main()
