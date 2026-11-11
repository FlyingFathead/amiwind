"""Alternative models in one CHIM store (tools/chim/alt_models.py, aw_tree_crowns, TREES-DEPTH-56): the base store
stays byte for byte, only the other build's models that differ follow it (in compact sector files of model and
texture records only), with the textures they use that the base lacks; the texture ids in their images are renumbered
to the merged ids, and the map pairs exactly the carried models."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
from chim import alt_models as A  # noqa: E402
from chim import format as F  # noqa: E402

SETTINGS = {'draw_distance': 540.0, 'hysteresis': 96.0, 'collision_margin': 224.0, 'prefetch_margin': 256.0,
            'grain': 256, 'terrain_light': 12, 'placements': 2, 'models': 2, 'textures': 2, 'frames': 1,
            'sector_chunks': 3}
BASE_TEX = b'TEXA' * 4 + b'TEXB' * 4


def model_image(vertex_bytes, texture_ids):
    lumps = [b''] * 15
    lumps[2] = F.texture_refs(texture_ids)
    lumps[3] = vertex_bytes
    return F.brush_image(lumps)[0]


def store(root, tree_bytes, tree_textures, tex=BASE_TEX):
    """A one-frame store: frame file row 0, sector file row 1 holding the models rock and tree, two textures."""
    rock = model_image(struct.pack('<3f', 1, 2, 3), [0])
    tree = model_image(tree_bytes, tree_textures)
    sector = rock + tree + tex
    (root / 'frames/x-23/y+20').mkdir(parents=True)
    (root / 'frames/x-23/y+20/s00.ccs').write_bytes(sector)
    (root / 'frames/x-23/y+20/frame.ccf').write_bytes(b'FRAME')
    files = [{'kind': b'FRAM', 'sector': 0, 'cell': (-23, 20), 'bytes': 5, 'crc': F.crc32(b'FRAME'), 'entries': 0,
              'path': 'frames/x-23/y+20/frame.ccf'},
             {'kind': b'SECT', 'sector': 0, 'cell': (-23, 20), 'bytes': len(sector), 'crc': F.crc32(sector),
              'entries': 2, 'path': 'frames/x-23/y+20/s00.ccs'}]
    models = [('rock', 1, 0, len(rock), len(rock)), ('tree', 1, len(rock), len(tree), len(tree))]
    t0 = len(rock) + len(tree)
    textures = [('bark', 1, t0, 16, 2, 2), ('needles', 1, t0 + 16, 16, 2, 2)]
    (root / 'world.cwi').write_bytes(F.index_file(SETTINGS, files, models, textures))
    return root


def base_and_alt(d, alt_tex=BASE_TEX):
    base = store(d / 'base', struct.pack('<6f', 0, 0, 0, 0, 0, 100), [0, 1])
    alt = store(d / 'alt', struct.pack('<3f', 0, 0, 50), [1, 0], alt_tex)
    return base, alt


class AltModels(unittest.TestCase):
    def test_merge_carries_only_the_differing_model_and_shares_textures(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            base, alt = base_and_alt(d)
            base_index = (base / 'world.cwi').read_bytes()
            record = A.merge(base, alt, d / 'out', 1)
            out = d / 'out'
            self.assertEqual((out / 'frames/x-23/y+20/s00.ccs').read_bytes(),
                             (base / 'frames/x-23/y+20/s00.ccs').read_bytes())
            settings, files, models, textures = F.read_index((out / 'world.cwi').read_bytes())
            self.assertEqual(len(files), 3)
            self.assertEqual(files[2]['path'], 'frames/x+977/y+20/s00.ccs')
            self.assertEqual(files[2]['cell'], (977, 20))
            data = (out / files[2]['path']).read_bytes()
            self.assertEqual(F.crc32(data), files[2]['crc'])
            # the rock is the same in both builds and the textures have the same bytes: neither is carried
            self.assertEqual([m['name'] for m in models], ['rock', 'tree', 'tree#alt1'])
            self.assertEqual([t['name'] for t in textures], ['bark', 'needles'])
            self.assertEqual((settings['models'], settings['textures']), (3, 2))
            image = data[models[2]['offset']:models[2]['offset'] + models[2]['bytes']]
            self.assertEqual(F.read_texture_refs(F.read_brush_image(image)[2]), [1, 0])   # the base's own textures
            self.assertEqual(A.read_alt_map((out / A.ALT_FILE).read_bytes()), {1: [(1, 2)]})
            self.assertEqual((record['pairs'], record['models_added'], record['textures_added'],
                              record['textures_shared']), (1, 1, 0, 2))
            self.assertEqual(base_index, (base / 'world.cwi').read_bytes())

    def test_changed_textures_are_carried_and_renumbered(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            base, alt = base_and_alt(d, b'TEXC' * 4 + b'TEXD' * 4)
            A.merge(base, alt, d / 'out', 1)
            out = d / 'out'
            _, files, models, textures = F.read_index((out / 'world.cwi').read_bytes())
            self.assertEqual([t['name'] for t in textures], ['bark', 'needles', 'bark#alt1', 'needles#alt1'])
            data = (out / files[2]['path']).read_bytes()
            image = data[models[2]['offset']:models[2]['offset'] + models[2]['bytes']]
            self.assertEqual(F.read_texture_refs(F.read_brush_image(image)[2]), [3, 2])   # 1, 0 -> merged ids
            self.assertEqual(data[textures[2]['offset']:textures[2]['offset'] + 16], b'TEXC' * 4)

    def test_a_texture_in_a_sector_without_models_is_carried(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            tex = b'TEXC' * 4 + b'TEXD' * 4
            base, alt = base_and_alt(d, tex)
            # move the alternative's textures into a second sector file with no model
            raw = (alt / 'world.cwi').read_bytes()
            settings, files, models, textures = F.read_index(raw)
            (alt / 'frames/x-23/y+20/s01.ccs').write_bytes(tex)
            files.append({'kind': b'SECT', 'sector': 1, 'cell': (-23, 20), 'bytes': 32,
                          'crc': F.crc32(tex), 'entries': 0, 'path': 'frames/x-23/y+20/s01.ccs'})
            textures = [(t['name'], 2, 16 * i, 16, 2, 2) for i, t in enumerate(textures)]
            (alt / 'world.cwi').write_bytes(F.index_file(settings, files, [(m['name'], m['file'], m['offset'], m['bytes'],
                                                                        m['render']) for m in models], textures))
            A.merge(base, alt, d / 'out', 1)
            _, merged_files, _, merged_textures = F.read_index((d / 'out' / 'world.cwi').read_bytes())
            self.assertEqual(merged_files[merged_textures[2]['file']]['path'], 'frames/x+977/y+20/s01.ccs')

    def test_merged_store_carries_no_non_model_record(self):
        """The star build's sector file also holds chunk and terrain records and unchanged models: the merged store
        grows by exactly one compact file of the changed model and its new textures, nothing else."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            base, alt = base_and_alt(d, b'TEXC' * 4 + b'TEXD' * 4)
            settings, files, models, textures = F.read_index((alt / 'world.cwi').read_bytes())
            src = (alt / files[1]['path']).read_bytes()
            records = [(b'CHNK', 0, b'G' * 4000), (b'TERR', 7, b'T' * 3000)]
            records += [(b'MODL', i, src[m['offset']:m['offset'] + m['bytes']]) for i, m in enumerate(models)]
            records += [(b'TEXR', i, src[t['offset']:t['offset'] + t['bytes']]) for i, t in enumerate(textures)]
            sector = F.sector_file(records)
            at, _ = F.sector_layout(records)
            (alt / files[1]['path']).write_bytes(sector)
            files[1] = dict(files[1], bytes=len(sector), crc=F.crc32(sector), entries=len(records))
            (alt / 'world.cwi').write_bytes(F.index_file(
                settings, files,
                [(m['name'], 1, at[(b'MODL', i)], m['bytes'], m['render']) for i, m in enumerate(models)],
                [(t['name'], 1, at[(b'TEXR', i)], t['bytes'], 2, 2) for i, t in enumerate(textures)]))
            record = A.merge(base, alt, d / 'out', 1)
            out = d / 'out'
            _, mf, mm, mt = F.read_index((out / 'world.cwi').read_bytes())
            added = (out / mf[2]['path']).read_bytes()
            got = [(r['kind'], r['bytes']) for r in F.read_sector(added)]
            tree = models[1]
            self.assertEqual(got, [(b'MODL', tree['bytes']), (b'TEXR', 16), (b'TEXR', 16)])
            self.assertEqual(record['bytes_added'], len(added))
            img = added[mm[2]['offset']:mm[2]['offset'] + mm[2]['bytes']]
            self.assertEqual(img, A.patch_texture_ids(src[tree['offset']:tree['offset'] + tree['bytes']], 2))
            for k in (0, 1):
                e, t = mt[2 + k], textures[k]
                self.assertEqual(added[e['offset']:e['offset'] + e['bytes']], src[t['offset']:t['offset'] + t['bytes']])
            base_bytes = sum(p.stat().st_size for p in base.rglob('*') if p.is_file() and p.name != 'world.cwi')
            out_bytes = sum(p.stat().st_size for p in out.rglob('*')
                            if p.is_file() and p.name not in ('world.cwi', A.ALT_FILE))
            self.assertEqual(out_bytes, base_bytes + len(added))

    def test_patch_with_a_map(self):
        img = model_image(b'', [0, 1, -1])
        out = A.patch_texture_ids(img, {0: 5, 1: 2})
        self.assertEqual(F.read_texture_refs(F.read_brush_image(out)[2]), [5, 2, -1])

    def test_map_format(self):
        raw = A.alt_map_bytes({2: [(5, 9), (1, 7)], 1: [(1, 3)]})
        self.assertEqual(raw[:4], b'AWA1')
        self.assertEqual(A.read_alt_map(raw), {1: [(1, 3)], 2: [(1, 7), (5, 9)]})


if __name__ == '__main__':
    unittest.main()
