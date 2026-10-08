import struct
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import check_world_map_heap as heap


SIZES = {
    'pointer': 4, 'short': 2, 'int': 4, 'hunk': 16,
    'dvertex': 12, 'dedge': 4, 'dplane': 20, 'dnode': 24,
    'dclipnode': 8, 'dleaf': 28, 'texinfo': 40, 'dface': 20,
    'dmodel': 64, 'mvertex': 12, 'medge': 8, 'mplane': 20,
    'mtexinfo': 44, 'msurface': 64, 'mnode': 40, 'mleaf': 48,
    'clipnode': 8, 'texture': 60, 'hull': 40,
}


def make_bsp():
    lumps = [b''] * 15
    lumps[0] = b'e' * 5
    lumps[1] = b'p' * 20
    texture = bytearray(struct.pack('<ii', 1, 8))
    texture.extend(b'\0' * 16 + struct.pack('<II4I', 16, 16, 40, 104, 120, 124))
    texture.extend(b'x' * 340)
    lumps[2] = bytes(texture)
    lumps[3] = b'v' * 12
    lumps[4] = b'z' * 64000
    lumps[5] = b'n' * 24
    lumps[6] = b't' * 40
    lumps[7] = b'f' * 20
    lumps[8] = b'l' * 40000
    lumps[9] = b'c' * 8
    lumps[10] = b'a' * 28
    lumps[11] = b'm' * 2
    lumps[12] = b'd' * 4
    lumps[13] = b's' * 4
    lumps[14] = b'b' * 64
    offset = heap.HEADER_SIZE
    header = bytearray(struct.pack('<i', heap.BSP_VERSION))
    body = bytearray()
    for lump in lumps:
        if lump:
            header.extend(struct.pack('<ii', offset, len(lump)))
            body.extend(lump)
            offset += len(lump)
        else:
            header.extend(struct.pack('<ii', 0, 0))
    return bytes(header + body)


class WorldMapHeapEstimateTests(unittest.TestCase):
    def test_section_directory_static_cost_applies_without_a_section_catalogue(self):
        with tempfile.TemporaryDirectory() as temp:
            maps=Path(temp);(maps/'sn012.bsp').write_bytes(make_bsp())
            before=heap.inspect_maps(maps,SIZES)['maps'][0]
            after=heap.inspect_maps(maps,dict(SIZES,interior_section_static=728))['maps'][0]
        self.assertEqual(after['interior_section_static_allowance_bytes'],728)
        self.assertEqual(after['additional_static_allowance_bytes'],before['additional_static_allowance_bytes']+728)
        self.assertEqual(after['peak_loader_bytes'],before['peak_loader_bytes'])
        self.assertEqual(after['estimated_total_bytes'],before['estimated_total_bytes']+728)
        self.assertEqual(after['estimated_clearance_bytes'],before['estimated_clearance_bytes']-728)

    def test_static_link_pages_are_charged_after_model_loading(self):
        with tempfile.TemporaryDirectory() as temp:
            maps=Path(temp);(maps/'sn012.bsp').write_bytes(make_bsp())
            before=heap.inspect_maps(maps,SIZES)['maps'][0]
            # Isolate the final phase; sprite_heap tests real link traversal and
            # exact page payload/alignment/header accounting independently.
            with patch('sprite_heap.inspect_efrags',return_value={'resident_hunk_bytes':16416}):
                after=heap.inspect_maps(maps,SIZES)['maps'][0]
        self.assertEqual(after['resident_loader_bytes'],before['resident_loader_bytes']+16416)
        self.assertEqual(after['peak_loader_bytes'],max(before['peak_loader_bytes'],after['resident_loader_bytes']))
        self.assertEqual(after['estimated_total_bytes'],after['peak_loader_bytes']+after['baseline_reserve_bytes']+after['safety_headroom_bytes'])

    def test_estimates_decoded_target_allocations_and_direct_byte_loads(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'sn012.bsp'
            path.write_bytes(make_bsp())
            result = heap.estimate_bsp(path, SIZES)
        self.assertEqual(result['counts']['surfedges'], 1)
        self.assertEqual(result['counts']['marksurfaces'], 1)
        self.assertEqual(result['counts']['clipnodes'], 1)
        self.assertEqual(result['temporary_input_peak_lump'], 'textures')
        # The 388-byte texture lump fits one window; no prefix.
        self.assertEqual(result['temporary_input_peak_bytes'], 16 + 400)
        self.assertGreater(result['resident_loader_bytes'], 104000)
        self.assertGreaterEqual(result['peak_loader_bytes'], result['resident_loader_bytes'])
        self.assertEqual(result['resident_bytes_at_peak'] + result['temporary_input_bytes_at_peak'],
                         result['peak_loader_bytes'])
        labels = [row['allocation'] for row in result['resident_allocations']]
        self.assertIn('lighting (direct byte load)', labels)
        self.assertIn('visibility (direct byte load)', labels)
        self.assertIn('hull0 clipnodes', labels)

    def test_balmora_catalogue_adds_target_hunk_without_removing_bsp_payload(self):
        raw=make_bsp();table=heap.lump_table(raw,Path('synthetic'))
        table['entities']=b'{"classname" "func_wall"}\n'*3
        header=bytearray(struct.pack('<i',29));body=bytearray();offset=heap.HEADER_SIZE
        for name in heap.RECORDS:
            lump=table[name];header.extend(struct.pack('<ii',offset if lump else 0,len(lump)))
            body.extend(lump);offset+=len(lump)
        sizes={**SIZES,'scenery':64}
        with tempfile.TemporaryDirectory() as temp:
            maps=Path(temp);(maps/'bm019.bsp').write_bytes(header+body)
            (maps/'sn019.bsp').write_bytes(header+body)
            report=heap.inspect_maps(maps,sizes)
        a,b=report['maps']
        expected=heap.hunk_alloc_bytes(3*64,sizes['hunk'])
        self.assertEqual(a['scenery_catalogue']['placements'],3)
        self.assertEqual(a['scenery_catalogue']['hunk_bytes'],expected)
        self.assertEqual(a['peak_loader_bytes']-b['peak_loader_bytes'],expected)
        self.assertEqual(a['resident_loader_bytes']-b['resident_loader_bytes'],expected)
        self.assertEqual(b['scenery_catalogue']['placements'],0)

    def test_inspection_requires_positive_baseline_and_safety_headroom(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'maps'
            path.mkdir()
            (path / 'small.bsp').write_bytes(make_bsp())
            with self.assertRaisesRegex(ValueError, 'Baseline reserve must be positive'):
                heap.inspect_maps(path, SIZES, baseline_reserve_bytes=0)
            with self.assertRaisesRegex(ValueError, 'Safety headroom must be positive'):
                heap.inspect_maps(path, SIZES, safety_headroom_bytes=0)

    def test_inspection_reports_over_budget_maps_without_calling_them_validated(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'maps'
            path.mkdir()
            (path / 'sn012.bsp').write_bytes(make_bsp())
            result = heap.inspect_maps(path, SIZES, baseline_reserve_bytes=heap.HEAP_RESERVE_BYTES,
                                       safety_headroom_bytes=1)
        self.assertEqual(result['failing_maps'], ['sn012.bsp'])
        self.assertEqual(result['maps'][0]['gate'], 'fail')
        self.assertEqual(result['acceptance'], 'estimate-only; not target or gameplay validation')

    def test_sliced_sections_hold_one_slice_not_a_staged_lump(self):
        table = heap.lump_table(make_bsp(), Path('synthetic'))
        table['faces'] = b'f' * (20 * 5000)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'sn012.bsp'
            path.write_bytes(build_bsp(table))
            result = heap.estimate_bsp(path, SIZES)
        slice_temp = SIZES['hunk'] + heap.BSP_RECORD_PREFIX_BYTES + heap.BSP_SLICE_BYTES
        self.assertEqual((heap.BSP_SLICE_BYTES, heap.BSP_RECORD_PREFIX_BYTES, heap.BSP_DIRECTORY_BYTES),
                         (16384, 64, 2052))
        self.assertEqual(result['bsp_slice_bytes'], heap.BSP_SLICE_BYTES)
        self.assertEqual(result['temporary_input_peak_bytes'], slice_temp)
        self.assertEqual(result['temporary_input_peak_lump'], 'faces')
        faces = next(row for row in result['resident_allocations'] if row['allocation'] == 'faces')
        self.assertEqual(faces['hunk_bytes'], heap.hunk_alloc_bytes(5000 * SIZES['msurface'], SIZES['hunk']))
        # The staged loader also held all 100,000 input bytes beside the faces.
        self.assertLessEqual(result['peak_loader_bytes'], result['resident_loader_bytes'] + slice_temp)
        self.assertGreaterEqual(result['peak_loader_bytes'], faces['resident_after_bytes'] + slice_temp)
        self.assertLess(result['peak_loader_bytes'],
                        faces['resident_after_bytes'] + heap.hunk_temp_bytes(100001, SIZES['hunk']))

    def test_slice_accounting_for_short_and_empty_sections(self):
        self.assertEqual(heap.slice_temp_bytes(0, 16), 0)
        self.assertEqual(heap.slice_temp_bytes(20, 16, prefix_bytes=0), 48)
        self.assertEqual(heap.slice_temp_bytes(20, 16), 112)
        self.assertEqual(heap.slice_temp_bytes(16384, 16), 16464)
        self.assertEqual(heap.slice_temp_bytes(10 ** 6, 16), 16464)
        self.assertEqual(heap.slice_prefix_bytes('faces', 10 ** 6), 64)
        self.assertEqual(heap.slice_prefix_bytes('textures', 388), 0)
        self.assertEqual(heap.slice_prefix_bytes('faces', 16384), 0)
        self.assertEqual(heap.slice_prefix_bytes('textures', 16388), 2064)
        self.assertEqual(heap.slice_prefix_bytes('textures', 10 ** 6), 2064)
        with self.assertRaises(ValueError):
            heap.slice_temp_bytes(-1, 16)

    def test_failed_prefix_certification_attempt_is_charged_at_nodes(self):
        table = heap.lump_table(make_bsp(), Path('synthetic'))
        # Ten nodes: a forward world chain 0..8 and an inline root 9 that has
        # faces, so the predicted prefix (9 nodes) fails certification.
        nodes = [struct.pack('<i2h6h2H', 0, i + 1, -1, 0, 0, 0, 0, 0, 0, 0, 0) for i in range(8)]
        nodes.append(struct.pack('<i2h6h2H', 0, -1, -1, 0, 0, 0, 0, 0, 0, 0, 0))
        nodes.append(struct.pack('<i2h6h2H', 0, -1, -1, 0, 0, 0, 0, 0, 0, 0, 1))
        table['nodes'] = b''.join(nodes)
        table['models'] = (struct.pack('<9f7i', *([0.0] * 9), 0, 0, 0, 0, 1, 0, 1) +
                           struct.pack('<9f7i', *([0.0] * 9), 9, 0, 0, 0, 0, 0, 0))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'sn012.bsp'
            path.write_bytes(build_bsp(table))
            result = heap.estimate_bsp(path, SIZES)
        policy = result['node_residency']
        self.assertFalse(policy['direct_hull0'])
        self.assertEqual(policy['failed_prefix_attempt_nodes'], 9)
        rows = result['resident_allocations']
        index = next(i for i, row in enumerate(rows) if row['allocation'] == 'nodes')
        before = rows[index - 1]['resident_after_bytes']
        attempt = (heap.hunk_alloc_bytes(10 * SIZES['clipnode'], SIZES['hunk']) +
                   heap.hunk_alloc_bytes(9 * SIZES['mnode'], SIZES['hunk']))
        self.assertGreater(attempt, rows[index]['hunk_bytes'])
        self.assertEqual(result['peak_section'], 'nodes')
        self.assertEqual(result['peak_loader_bytes'], before + attempt + heap.slice_temp_bytes(240, SIZES['hunk'], prefix_bytes=0))
        self.assertEqual(heap.predicted_render_prefix(heap.lump_table(build_bsp(table), Path('x'))), 9)

    def test_slice_policy_is_bound_to_the_loader_source(self):
        source = (Path(heap.ROOT) / 'engine/aga/src/model.c').read_text(encoding='utf-8')
        self.assertEqual(heap.bsp_slice_policy(source),
                         {'mode': 'bounded_slices', 'slice_bytes': heap.BSP_SLICE_BYTES,
                          'record_prefix_bytes': heap.BSP_RECORD_PREFIX_BYTES,
                          'directory_bytes': heap.BSP_DIRECTORY_BYTES})
        staged = source + '\nvoid f(void){mod_base=Hunk_TempAlloc(l->filelen+1);}\n'
        with self.assertRaisesRegex(ValueError, 'Unrecognized BSP section loader'):
            heap.bsp_slice_policy(staged)
        with self.assertRaisesRegex(ValueError, 'Unrecognized BSP section loader'):
            heap.bsp_slice_policy(source.replace('#define AW_BSP_SLICE_BYTES', '#define AW_BSP_SLICE'))
        with self.assertRaisesRegex(ValueError, 'Unrecognized BSP section loader'):
            heap.bsp_slice_policy(source.replace('aw_bsp_slice_bytes+=aw_bsp_slice_prefix;', ''))


def build_bsp(table):
    header = bytearray(struct.pack('<i', heap.BSP_VERSION))
    body = bytearray()
    offset = heap.HEADER_SIZE
    for name in heap.RECORDS:
        lump = table[name]
        header.extend(struct.pack('<ii', offset if lump else 0, len(lump)))
        body.extend(lump)
        offset += len(lump)
    return bytes(header + body)


if __name__ == '__main__':
    unittest.main()
