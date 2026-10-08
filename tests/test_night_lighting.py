# SPDX-License-Identifier: GPL-3.0-only
"""The image builder writes the night lamp, night window and fog tables."""
import hashlib, json, struct, sys, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import night_lighting as NL
from test_light_sources import ligh, cell
from test_night_windows import bsp, INDEX, PALETTE


def master():
    return (ligh(b'light_de_streetlight_01', b'l\\s.nif', 223, (245, 140, 40), 1)
            + ligh(b'light_de_lantern_10', b'l\\l.nif', 128, (0, 166, 255), 1)
            + cell(b'Balmora', 0, -3, -2, [(b'light_de_streetlight_01', (1, 2, 3)), (b'light_de_lantern_10', (4, 5, 6))])
            + cell(b'Seyda Neen', 0, -2, -9, [(b'light_de_streetlight_01', (7, 8, 9))]))


class Stage:
    """A synthetic image stage: final maps, palette and scenery sources."""
    def __init__(self, root):
        self.root = root; self.id1 = root / 'boot/id1'
        (self.id1 / 'maps').mkdir(parents=True); (self.id1 / 'gfx').mkdir()
        (self.id1 / 'gfx/palette.lmp').write_bytes(bytes(c for rgb in PALETTE for c in rgb))
        maps = {'bm019': bsp([('surface7', 1)], [[0]], [(13, 1)]),          # window glass
                'balmora': bsp([('surface3', 3)], [[0]], [(12, 1)]),        # bottle: dark
                'sn012': bsp([('surface9', 1)], [[0]], [(14, 1)]),                # paper window
                'vf0000': bsp([('surface1', 1)], [[0]], [(13, 1)])}        # world terrain
        for name, raw in maps.items():
            (self.id1 / 'maps' / (name + '.bsp')).write_bytes(raw)
        self.master = root / 'Morrowind.esm'; self.master.write_bytes(master())
        seyda = json.loads(json.dumps(INDEX))
        seyda['models'][4]['materials'][0]['texture_source'] = 'Tx_window_paper_01.tga'
        for name, index in (('balmora-scenery', INDEX), ('town-scenery', seyda)):
            (root / name).mkdir()
            (root / name / 'scenery-index.json').write_text(json.dumps(index), encoding='utf-8')
        (root / 'scene').mkdir()

    def stage(self, **sources):
        return NL.stage(self.id1, master=self.master, maps=['balmora', 'bm019', 'sn012', 'vf0000'],
                        sources=NL.scenery_sources(**sources), palette=self.id1 / 'gfx/palette.lmp',
                        work_dir=self.root / 'out/night-lighting')


class FormatTests(unittest.TestCase):
    def test_project_fog_table_is_valid(self):
        raw, places = NL.fog_table((ROOT / 'config/fog-locations.txt').read_bytes())
        self.assertGreaterEqual(places, 1)
        self.assertEqual(raw, (ROOT / 'config/fog-locations.txt').read_bytes())

    def test_fog_table_rejects_what_the_engine_would_misread(self):
        self.assertEqual(NL.fog_table(b'# c\nbalmora 300 250\n\nseyda 1500 100\n')[1], 2)
        for raw in (b'', b'balmora 300 250', b'balmora 300 250\r\n', b'balmora 300 250\nbalmora 300 250\n',
                    b'balmora 300\n', b'balmora 300 250 1\n', b'balmora 99 250\n', b'balmora 300 1501\n',
                    b'bal mora 300 250\n', 'balmorä 300 250\n'.encode('utf-8'), b'balmora\t300 250\n',
                    b'#' + b'x' * 200 + b'\n'):
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                NL.fog_table(raw)

    def test_lamp_table_check_follows_the_engine(self):
        from light_sources import lamp_table
        raw = lamp_table(master())
        self.assertEqual(NL.check_lamp_table(raw), 3)
        rows = [raw[8 + k * 20:28 + k * 20] for k in range(3)]
        for bad in (b'AWL2' + raw[4:], raw[:-1], raw[:4] + struct.pack('<I', 4) + raw[8:],
                    raw[:8] + rows[2] + rows[0] + rows[1]):
            with self.assertRaises(ValueError):
                NL.check_lamp_table(bad)

    def test_lamp_table_check_refuses_more_lamps_than_the_engine_cache(self):
        def table(cells):
            rows = b''.join(struct.pack('<hh3fHBB', x, y, 0.0, 0.0, 0.0, 223, 1, 1) for x, y in sorted(cells))
            return b'AWL1' + struct.pack('<I', len(cells)) + rows
        full = [(0, 0)] * 128 + [(1, 1)] * 128
        self.assertEqual(NL.check_lamp_table(table(full)), 256)
        self.assertEqual(NL.check_lamp_table(table(full + [(3, 3)])), 257)
        with self.assertRaisesRegex(ValueError, 'LAMPS-CACHE-31'):
            NL.check_lamp_table(table(full + [(1, 0)]))

    def test_window_table_check(self):
        self.assertEqual(NL.check_window_table(b''), 0)
        self.assertEqual(NL.check_window_table(b'bm019 surface7\nsn012 surface9\n'), 2)
        for bad in (b'bm019\n', b'bm019 surface7', b'sn012 a\nbm019 b\n', b'bm019 a\r\n', b'bm019  a\n'):
            with self.assertRaises(ValueError):
                NL.check_window_table(bad)

    def test_sky_palette_overlay_treats_the_lamp_table_as_opaque(self):
        import sky_palette_overlay
        self.assertIn('.awl', sky_palette_overlay.OPAQUE)


class StageTests(unittest.TestCase):
    def test_builder_writes_all_three_tables_with_receipt_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = Stage(Path(tmp))
            receipt = s.stage(balmora_scenery=s.root / 'balmora-scenery', town_scenery=s.root / 'town-scenery',
                              scene=s.root / 'scene')
            world = s.id1 / 'world'
            self.assertEqual(sorted(p.name for p in world.iterdir()), ['fog-locations.txt', 'lamps.awl', 'night-windows.txt'])
            lamps = (world / 'lamps.awl').read_bytes()
            self.assertEqual(lamps[:8], b'AWL1' + struct.pack('<I', 3))
            self.assertEqual(len(lamps), 8 + 3 * 20)
            self.assertEqual((world / 'night-windows.txt').read_bytes(), b'bm019 surface7\nsn012 surface9\n')
            self.assertEqual((world / 'fog-locations.txt').read_bytes(), (ROOT / 'config/fog-locations.txt').read_bytes())
            for name in NL.TABLES:
                raw = (s.id1 / name).read_bytes()
                self.assertEqual(receipt['tables'][name], {**receipt['tables'][name], 'bytes': len(raw),
                                                           'sha256': hashlib.sha256(raw).hexdigest()})
                self.assertNotIn(b'\r', raw)
            self.assertEqual(receipt['tables']['world/lamps.awl']['lamps'], 3)
            self.assertEqual(receipt['tables']['world/night-windows.txt']['maps'], 2)
            summary = receipt['night_windows']
            self.assertEqual(summary['maps_classified'], 3)
            self.assertEqual(summary['other_maps_not_classified'], 1)
            self.assertEqual(summary['town_maps_skipped'], {})
            self.assertEqual([u['name'] for u in summary['sources_used']], ['balmora', 'seyda'])
            # Optional overlays the build was not given are reported, not fatal.
            self.assertEqual({k['name']: k['reason'][:20] for k in summary['sources_skipped']},
                             {'opening-barrel': 'no scenery-index.jso', 'world-flora': 'not supplied'})
            self.assertEqual(receipt['status'], 'partial')
            work = s.root / 'out/night-lighting'
            self.assertEqual(json.loads((work / 'night-lighting.json').read_text(encoding='utf-8')), receipt)
            self.assertEqual(summary['report_sha256'],
                             hashlib.sha256((work / summary['report']).read_bytes()).hexdigest())
            self.assertEqual(sorted(json.loads((work / summary['report']).read_text(encoding='utf-8'))),
                             ['balmora', 'bm019', 'sn012'])

    def test_every_source_present_is_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = Stage(Path(tmp))
            for name in ('scene/opening-barrel-source', 'flora/source'):
                (s.root / name).mkdir(parents=True)
                (s.root / name / 'scenery-index.json').write_text(
                    json.dumps({'textures': [], 'models': [], 'references': []}), encoding='utf-8')
            receipt = s.stage(balmora_scenery=s.root / 'balmora-scenery', town_scenery=s.root / 'town-scenery',
                              scene=s.root / 'scene', world_flora=s.root / 'flora')
            self.assertEqual(receipt['status'], 'complete')
            self.assertEqual(receipt['night_windows']['sources_skipped'], [])
            self.assertEqual(len(receipt['night_windows']['sources_used']), 4)

    def test_missing_town_scenery_skips_that_town_and_never_guesses(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = Stage(Path(tmp))
            (s.root / 'flora/source').mkdir(parents=True)
            (s.root / 'flora/source/scenery-index.json').write_text(json.dumps(INDEX), encoding='utf-8')
            receipt = s.stage(town_scenery=s.root / 'town-scenery', world_flora=s.root / 'flora')
            # The flora overlay alone would light Balmora's glass from the wrong
            # source; the town without its own scenery gets no line instead.
            self.assertEqual((s.id1 / 'world/night-windows.txt').read_bytes(), b'sn012 surface9\n')
            self.assertEqual(receipt['night_windows']['town_maps_skipped'],
                             {'balmora': 'balmora scenery not supplied', 'bm019': 'balmora scenery not supplied'})
            self.assertEqual(receipt['status'], 'partial')
            self.assertTrue((s.id1 / 'world/lamps.awl').is_file())
            self.assertTrue((s.id1 / 'world/fog-locations.txt').is_file())

    def test_no_scenery_at_all_still_writes_valid_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = Stage(Path(tmp))
            receipt = s.stage()
            self.assertEqual((s.id1 / 'world/night-windows.txt').read_bytes(), b'')
            self.assertEqual(receipt['tables']['world/night-windows.txt']['maps'], 0)
            self.assertEqual(len(receipt['night_windows']['sources_skipped']), 4)

    def test_invalid_fog_source_stops_the_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = Stage(Path(tmp)); bad = s.root / 'fog.txt'; bad.write_bytes(b'balmora 300 250\r\n')
            with self.assertRaises(ValueError):
                NL.stage(s.id1, master=s.master, maps=[], sources=NL.scenery_sources(), fog_source=bad)
            self.assertEqual(list((s.id1 / 'world').iterdir()), [])  # nothing half-written

    def test_image_options_and_their_defaults(self):
        args = SimpleNamespace(scene=Path('/r/intro-scene'), balmora_cache=Path('/r/balmora-work'),
                               town_flora_source_index=Path('/r/scenery/scenery-index.json'),
                               world_flora=Path('/r/world-flora'))
        sources = {s['name']: s['directory'] for s in NL.image_sources(args)}
        self.assertEqual(sources, {'balmora': Path('/r/balmora-work/scenery'), 'seyda': Path('/r/scenery'),
                                   'opening-barrel': Path('/r/intro-scene/opening-barrel-source'),
                                   'world-flora': Path('/r/world-flora/source')})
        args.balmora_scenery, args.town_scenery = Path('/b'), Path('/t')
        sources = {s['name']: s['directory'] for s in NL.image_sources(args)}
        self.assertEqual((sources['balmora'], sources['seyda']), (Path('/b'), Path('/t')))
        bare = {s['name']: s['directory'] for s in NL.image_sources(SimpleNamespace(scene=Path('/s')))}
        self.assertEqual(bare['balmora'], None); self.assertEqual(bare['world-flora'], None)


class BuilderWiringTests(unittest.TestCase):
    def test_finalize_writes_tables_from_final_maps_before_the_save_fingerprint(self):
        import build_aga
        source = Path(build_aga.__file__).read_text(encoding='utf-8')
        finalize = source[source.index('def finalize_image(args):'):source.index('\ndef main():')]
        tables = finalize.index('stage_night_lighting(boot/')
        self.assertLess(finalize.rindex('verify_optimized_maps(boot/', 0, tables), tables)
        self.assertLess(finalize.index('optimize_maps(boot/'), tables)
        self.assertLess(tables, finalize.index('write_content_fingerprint(boot/'))
        self.assertLess(tables, finalize.index('pack_world_volumes(boot'))
        self.assertIn("'night_lighting':night_lighting,", finalize)

    def test_guided_build_passes_the_town_scenery(self):
        import build
        args = build.parser().parse_args([])
        args.data_files = Path('/owned/Data Files'); args.sdk = Path('/sdk')
        tools = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
        steps = dict(build.commands(args, tools, Path('/private/run')))
        image = steps['image']
        self.assertEqual(Path(image[image.index('--town-scenery') + 1]), Path('/private/run/scenery'))
        self.assertEqual(Path(image[image.index('--balmora-scenery') + 1]), Path('/private/run/balmora-work/scenery'))
        self.assertEqual(Path(steps['scenery'][steps['scenery'].index('--out') + 1]), Path('/private/run/scenery'))
        self.assertEqual(Path(steps['balmora'][steps['balmora'].index('--out') + 1]), Path('/private/run/balmora-work'))

    def test_image_cli_accepts_the_scenery_options(self):
        import build_aga
        argv = ['build_aga.py', 'image', '--sdk', '/sdk', '--data-files', '/owned', '--no-npc-gallery',
                '--world-scenery', '/w', *[part for name in ('scene', 'music', 'media', 'engine', 'out', 'qcc', 'qbsp',
                                                             'vis', 'light', 'xdftool', 'rdbtool') for part in ('--' + name, '/' + name)]]
        for extra, expected in (([], (None, None)), (['--town-scenery', '/t', '--balmora-scenery', '/b'], (Path('/t'), Path('/b')))):
            with self.subTest(extra=extra), patch.object(sys, 'argv', argv + extra), patch.object(build_aga, 'image') as image:
                build_aga.main()
                args = image.call_args[0][0]
                self.assertEqual((args.town_scenery, args.balmora_scenery), expected)

    def test_save_fingerprint_binds_the_tables_when_present(self):
        from build_aga import write_content_fingerprint
        names = ['maps/intro_docks.bsp', 'maps/sncourt.bsp', 'seyda-regions.txt', 'balmora-regions.txt',
                 'progs.dat', 'character/catalog.awc', 'world/map.awm', 'world/journal.awj',
                 'world/entries.dat', 'world/quests.awq', 'world/region-names.awn']
        def fingerprint(root):
            with patch('area_config.SCENES', []), patch('build_aga.town_region_map_names', return_value=[]):
                write_content_fingerprint(root)
            return (root / 'save-content.bin').read_bytes()
        def expected(root, extra):
            h = hashlib.sha256()
            for name in names + extra:
                h.update(name.encode() + b'\0' + hashlib.sha256((root / name).read_bytes()).digest())
            return h.digest()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in names:
                (root / name).parent.mkdir(parents=True, exist_ok=True); (root / name).write_bytes(name.encode())
            self.assertEqual(fingerprint(root), expected(root, []))  # stages without the tables
            for name in NL.TABLES:
                (root / name).write_bytes(b'table ' + name.encode())
            with_tables = fingerprint(root)
            self.assertEqual(with_tables, expected(root, list(NL.TABLES)))
            (root / 'world/lamps.awl').write_bytes(b'changed')
            self.assertNotEqual(fingerprint(root), with_tables)


if __name__ == '__main__':
    unittest.main()
