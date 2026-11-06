"""Synthetic original-record checks for inventory metadata and action admission."""
import struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import prepare_inventory as inv

def field(kind,data):
    return kind.encode()+struct.pack('<I',len(data))+data
def record(kind,fields):
    data=b''.join(field(k,v) for k,v in fields)
    return kind.encode()+struct.pack('<III',len(data),0,0)+data
def text(value):
    return value.encode()+b'\0'

class InventoryAssetsTests(unittest.TestCase):
    def test_binary_effects_are_not_enchantment_ids_and_original_initial_counts(self):
        raw=record('ALCH',[('NAME',text('potion')),('ALDT',struct.pack('<fii',.5,12,0)),('ENAM',b'\x00\x01\x02\x03'*6)])
        raw+=record('CLOT',[('NAME',text('shirt')),('FNAM',text('Shirt')),('CTDT',struct.pack('<ifHH',2,1.,3,0))])
        raw+=record('NPC_',[('NAME',text('player')),('NPCO',struct.pack('<i',1)+b'shirt'+b'\0'*27)])
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);(base/'Morrowind.esm').write_bytes(raw)
            with patch.object(inv,'resolve_data_files',return_value=base):
                report=inv.prepare(base,base/'id1',palette=b'\0'*768,models=False)
            items=base.joinpath('id1/inventory/items.awi').read_bytes()
            self.assertEqual(items[:4],b'AWI2');self.assertEqual(len(items),8+2*512)
            self.assertEqual(items[8+312:8+376],b'\0'*64)
            initial=base.joinpath('id1/inventory/initial.awi').read_bytes()
            self.assertEqual(initial[:8],b'AWST'+struct.pack('<I',1))
            self.assertEqual(initial[8:72].split(b'\0')[0],b'shirt')
            self.assertEqual(struct.unpack_from('<ii',initial,72),(1,8))
            self.assertEqual(report['initial_items'],[{'id':'shirt','count':1}])

    def test_debug_torch_row_from_the_original_torch_never_burns_out(self):
        # The debug torch (test only): one row made from LIGH "torch" (model, icon, weight, value, radius,
        # colour), burn time -1 (OpenMW: an infinite light), left hand, a carried light; the original
        # record keeps its own burn time in the receipt. Carried lights are catalogued too (ITEM-WORLD-MODELS-58);
        # a fixed light (LHDT flag 2 clear) is not.
        lhdt=struct.pack('<fiii4Bi',3.,5,210,256,245,140,40,0,115)
        fixed=struct.pack('<fiii4Bi',0.,0,-1,128,255,255,255,0,0)
        raw=record('LIGH',[('NAME',text('torch')),('MODL',text('l\\light_torch10.nif')),('FNAM',text('Torch')),
                           ('ITEX',text('l\\light_torch10.tga')),('LHDT',lhdt)])
        raw+=record('LIGH',[('NAME',text('light_com_candle_01')),('LHDT',lhdt)])
        raw+=record('LIGH',[('NAME',text('light_fixed')),('LHDT',fixed)])
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);(base/'Morrowind.esm').write_bytes(raw)
            with patch.object(inv,'resolve_data_files',return_value=base):
                report=inv.prepare(base,base/'id1',palette=b'\0'*768,models=False)
            items=base.joinpath('id1/inventory/items.awi').read_bytes()
        self.assertEqual(struct.unpack_from('<I',items,4)[0],3)
        rows={items[8+i*512:8+i*512+64].split(b'\0')[0]:items[8+i*512:8+(i+1)*512] for i in range(3)}
        self.assertEqual(set(rows),{b'aw_debug_torch',b'light_com_candle_01',b'torch'})
        self.assertEqual(struct.unpack_from('<iiifII',rows[b'torch'],160),(7,256,5,3.,1<<17,1|4|32))
        # its own burn time; byte 511 the record's flags (HELD-LIGHT-OWN-MODEL-61): 0x80 | flicker 1 | fire 2
        self.assertEqual(struct.unpack_from('<i3BB',rows[b'torch'],504),(210,245,140,40,0x80|1|2))
        row=items[8:8+512]
        self.assertEqual(row[:64].split(b'\0')[0],b'aw_debug_torch')
        self.assertEqual(row[64:160].split(b'\0')[0],b'Debug torch (test only)')
        category,subtype,value,weight,slots,flags=struct.unpack_from('<iiifII',row,160)
        self.assertEqual((category,subtype,value,weight,slots),(7,256,5,3.,1<<17))
        self.assertEqual(flags,1|4|32)
        self.assertEqual(struct.unpack_from('<i3BB',row,504),(-1,245,140,40,0x80|1|2))
        self.assertEqual(report['debug_torch'],{'id':'aw_debug_torch','name':'Debug torch (test only)','source':'torch',
            'time':-1,'source_time':210,'radius':256,'colour':[245,140,40],'flags':115})
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);(base/'Morrowind.esm').write_bytes(record('LIGH',[('NAME',text('light_com_candle_01')),('LHDT',lhdt)]))
            with patch.object(inv,'resolve_data_files',return_value=base):
                report=inv.prepare(base,base/'id1',palette=b'\0'*768,models=False)
            self.assertIsNone(report['debug_torch'])   # no original torch: no row, nothing invented

    def test_tools_are_catalogued_with_weight_value_and_kind(self):
        # APPA, LOCK, PROB, REPA (ITEM-WORLD-MODELS-58): weight and value from their own data layouts.
        raw=record('APPA',[('NAME',text('apparatus_a_mortar_01')),('MODL',text('m\\apparatus_a_mortar_01.nif')),
                           ('AADT',struct.pack('<iffi',0,.5,1.,10))])
        raw+=record('LOCK',[('NAME',text('pick_apprentice_01')),('LKDT',struct.pack('<fifi',.25,20,1.,25))])
        raw+=record('PROB',[('NAME',text('probe_bent')),('PBDT',struct.pack('<fifi',.5,6,.5,10))])
        raw+=record('REPA',[('NAME',text('hammer_repair')),('RIDT',struct.pack('<fiif',3.,10,20,1.))])
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);(base/'Morrowind.esm').write_bytes(raw)
            with patch.object(inv,'resolve_data_files',return_value=base):
                inv.prepare(base,base/'id1',palette=b'\0'*768,models=False)
            items=base.joinpath('id1/inventory/items.awi').read_bytes()
        rows={items[8+i*512:8+i*512+64].split(b'\0')[0]:struct.unpack_from('<iiif',items,8+i*512+160) for i in range(4)}
        self.assertEqual(rows,{b'apparatus_a_mortar_01':(7,0,10,1.),b'pick_apprentice_01':(7,-1,20,.25),
                               b'probe_bent':(7,-1,6,.5),b'hammer_repair':(7,-1,10,3.)})

    def test_model_table_names_each_item_model_by_mesh(self):
        # One model per mesh path, shared by every item that names it (ITEM-WORLD-MODELS-58).
        raw=record('MISC',[('NAME',text('key_a')),('MODL',text('m\\Key_Standard_01.nif')),('MCDT',struct.pack('<fii',.1,1,1))])
        raw+=record('MISC',[('NAME',text('key_b')),('MODL',text('M/key_standard_01.nif')),('MCDT',struct.pack('<fii',.1,1,1))])
        raw+=record('MISC',[('NAME',text('odd')),('MODL',text('m\\odd.nif')),('MCDT',struct.pack('<fii',.1,1,0))])
        table={inv.mesh_key('m\\key_standard_01.nif'):'progs/items/m0000000000000001.mdl'}
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);(base/'Morrowind.esm').write_bytes(raw)
            with patch.object(inv,'resolve_data_files',return_value=base):
                report=inv.prepare(base,base/'id1',palette=b'\0'*768,models=False,model_table=table)
            items=base.joinpath('id1/inventory/items.awi').read_bytes()
        models={items[8+i*512:8+i*512+64].split(b'\0')[0]:items[8+i*512+184:8+i*512+248].split(b'\0')[0] for i in range(3)}
        self.assertEqual(models,{b'key_a':b'progs/items/m0000000000000001.mdl',b'key_b':b'progs/items/m0000000000000001.mdl',b'odd':b''})
        self.assertEqual(report['held'],{'odd':{'model':'not in the item model table'}})

    def test_weapons_with_strike_or_use_enchantments_are_equipped(self):
        # EQUIP-SHARDAXE-REFUSED-61: a held weapon's Cast When Strikes or Cast When Used enchantment does nothing
        # while it is held (OpenMW mwmechanics/activespells.cpp: only a worn item's Constant Effect enchantment is an
        # active effect), so the weapon is equipped as any other (flag 4). v0.0.61 (PLAYER-CASTING-59): a Constant
        # Effect one too, its effects active while it is worn (aw_cast.c worn_frame); an unknown enchantment stays refused.
        wpdt=struct.pack('<fihhffhBBBBBBi',30.,100,8,800,1.,1.,0,1,20,1,30,1,5,0)
        raw=b''
        for ident,ench in (('plain axe',''),('strike axe','shard_en'),('use axe','use_en'),('constant axe','const_en'),
                           ('unknown axe','no_such_en')):
            fields=[('NAME',text(ident)),('MODL',text('w\\axe.nif')),('FNAM',text(ident)),('WPDT',wpdt)]
            if ench:fields.append(('ENAM',text(ench)))
            raw+=record('WEAP',fields)
        for ident,kind in (('shard_en',1),('use_en',2),('const_en',3)):
            raw+=record('ENCH',[('NAME',text(ident)),('ENDT',struct.pack('<4i',kind,10,100,0))])
        table={inv.mesh_key('w\\axe.nif'):'progs/items/m0000000000000002.mdl'}
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);(base/'Morrowind.esm').write_bytes(raw)
            with patch.object(inv,'resolve_data_files',return_value=base):
                inv.prepare(base,base/'id1',palette=b'\0'*768,models=False,model_table=table)
            items=base.joinpath('id1/inventory/items.awi').read_bytes()
        count=struct.unpack_from('<I',items,4)[0]
        flags={items[8+i*512:8+i*512+64].split(b'\0')[0]:struct.unpack_from('<I',items,8+i*512+180)[0] for i in range(count)}
        self.assertEqual(flags[b'plain axe']&5,5)
        self.assertEqual(flags[b'strike axe']&5,5)
        self.assertEqual(flags[b'use axe']&5,5)
        self.assertEqual(flags[b'constant axe']&5,5)
        self.assertEqual(flags[b'unknown axe']&5,1)

    def test_script_proof_requires_first_executable_registration_guard(self):
        source='Begin ring\nshort state\nshort OnPCAdd\nif ( CharGenState == -1 )\n return\nendif\nset state to 1\nEnd'
        self.assertTrue(inv.script_inert_after_registration(source))
        self.assertFalse(inv.script_inert_after_registration('Begin ring\nset state to 1\n'+source))
        self.assertFalse(inv.script_inert_after_registration('Begin ring\nif CharGenState == 1\nreturn\nendif'))
        with self.assertRaises(ValueError):inv.safe_text('binary\x01effect',64)
        with self.assertRaises(ValueError):inv.safe_text('a'*64,64)

if __name__=='__main__':unittest.main()
