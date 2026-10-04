# SPDX-License-Identifier: GPL-3.0-only
import struct,unittest,subprocess,sys,tempfile
from pathlib import Path
from player_hull import lumps,pack_lumps
from dedup_bsp_planes import dedup_bsp


def fixture():
    d=[bytearray() for _ in range(15)]
    d[0]=bytearray(b'{"classname" "worldspawn" "aw_render_pool" "*1"}\0')
    a=struct.pack('<4fi',1,0,0,2,0);b=struct.pack('<4fi',0,1,0,3,1)
    d[1]=bytearray(a+b+a+b)
    d[5]=bytearray(struct.pack('<i2h6h2H',3,-1,-1,0,0,0,1,1,1,0,1))
    d[7]=bytearray(struct.pack('<Hhihh4Bi',2,0,0,3,0,255,255,255,255,-1))
    d[9]=bytearray(struct.pack('<iHH',3,65535,65534))
    d[4]=bytearray(b'PVS exact');d[8]=bytearray(b'Light exact');d[14]=bytearray(bytes(64))
    return pack_lumps(d)

class PlaneDedupTests(unittest.TestCase):
    def test_all_reference_types_remapped_with_other_fields_exact(self):
        raw=fixture();out,receipt=dedup_bsp(raw);a,b=lumps(raw),lumps(out)
        self.assertEqual(receipt['duplicates_removed'],2);self.assertEqual(len(b[1]),40)
        self.assertEqual(struct.unpack_from('<H',b[7])[0],0)
        self.assertEqual(struct.unpack_from('<i',b[5])[0],1);self.assertEqual(struct.unpack_from('<i',b[9])[0],1)
        for i in (0,2,3,4,6,8,10,11,12,13,14):self.assertEqual(a[i],b[i])
        self.assertEqual(a[5][4:],b[5][4:]);self.assertEqual(a[7][2:],b[7][2:]);self.assertEqual(a[9][4:],b[9][4:])
        self.assertEqual(b[1],a[1][:40]);self.assertEqual(receipt['file_bytes_saved'],40)
        twice,r2=dedup_bsp(out);self.assertEqual(twice,out);self.assertTrue(r2['byte_identical'])
    def test_signed_zero_and_plane_type_are_not_approximately_merged(self):
        d=lumps(fixture());d[1]=bytearray(struct.pack('<4fi',1,0.,0,2,0)+struct.pack('<4fi',1,-0.,0,2,0)+struct.pack('<4fi',1,0.,0,2,3))
        struct.pack_into('<H',d[7],0,0);struct.pack_into('<i',d[5],0,1);struct.pack_into('<i',d[9],0,2)
        raw=pack_lumps(d);out,r=dedup_bsp(raw);self.assertEqual(out,raw);self.assertEqual(r['duplicates_removed'],0)
    def test_invalid_reference_rejected_for_each_consumer(self):
        for lump,fmt,value in ((7,'<H',4),(5,'<i',-1),(9,'<i',4)):
            d=lumps(fixture());struct.pack_into(fmt,d[lump],0,value)
            with self.assertRaises(ValueError):dedup_bsp(pack_lumps(d))
    def test_malformed_record_and_nonfinite_plane_rejected(self):
        d=lumps(fixture());d[1].pop()
        with self.assertRaises(ValueError):dedup_bsp(pack_lumps(d))
        d=lumps(fixture());struct.pack_into('<f',d[1],0,float('nan'))
        with self.assertRaises(ValueError):dedup_bsp(pack_lumps(d))
    def test_overlapping_lump_headers_rejected(self):
        raw=bytearray(fixture());offset=struct.unpack_from('<i',raw,4+1*8)[0]
        struct.pack_into('<i',raw,4+5*8,offset)
        with self.assertRaises(ValueError):dedup_bsp(raw)
class PlaneDedupCliTests(unittest.TestCase):
    def invoke(self, source, output):
        import dedup_bsp_planes
        return subprocess.run([sys.executable, dedup_bsp_planes.__file__, str(source), '--out', str(output)],
                              capture_output=True, text=True)

    def test_preexisting_receipt_preserved_and_no_bsp_written(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source.bsp'
            source.write_bytes(fixture())
            output = root / 'new.bsp'
            receipt = output.with_suffix('.plane-dedup.json')
            receipt.write_bytes(b'KEEP ORIGINAL RECEIPT')
            result = self.invoke(source, output)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())
            self.assertEqual(receipt.read_bytes(), b'KEEP ORIGINAL RECEIPT')
            self.assertEqual(source.read_bytes(), fixture())

    def test_source_output_and_sidecar_aliases_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source.bsp'
            source.write_bytes(fixture())
            result = self.invoke(source, source)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('aliases source', result.stderr)
            self.assertEqual(source.read_bytes(), fixture())
            # A BSP input can have an arbitrary extension; its receipt alias
            # must be protected just as strictly as the BSP output alias.
            source = root / 'new.plane-dedup.json'
            source.write_bytes(fixture())
            result = self.invoke(source, root / 'new.bsp')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('aliases source', result.stderr)
            self.assertFalse((root / 'new.bsp').exists())
            self.assertEqual(source.read_bytes(), fixture())

    def test_preexisting_bsp_preserved_and_receipt_not_created(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source.bsp'
            source.write_bytes(fixture())
            output = root / 'new.bsp'
            output.write_bytes(b'KEEP ORIGINAL BSP')
            result = self.invoke(source, output)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_bytes(), b'KEEP ORIGINAL BSP')
            self.assertFalse(output.with_suffix('.plane-dedup.json').exists())

    def test_fresh_cli_outputs_both_payloads(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source.bsp'
            source.write_bytes(fixture())
            output = root / 'new.bsp'
            result = self.invoke(source, output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), dedup_bsp(fixture())[0])
            self.assertTrue(output.with_suffix('.plane-dedup.json').is_file())
            self.assertEqual(source.read_bytes(), fixture())


if __name__ == '__main__':
    unittest.main()
