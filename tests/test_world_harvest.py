# SPDX-License-Identifier: GPL-3.0-only
"""Synthetic worldwide converter boundaries; contains no original game data."""
import copy
import hashlib
import io
import json
import struct
import tempfile
import unittest
from pathlib import Path

from mwad.audit import records
from prepare_harvest import (source_context, prepare_graph, placement_source_key,
                             identity_key, placement_index)
from prepare_harvest_alias import region_references, convert_plan, pin, catalogue
from test_prepare_harvest import source
from test_world_flora_integration import record, sub
from test_prepare_harvest_alias import sample, budget
from mwad.scene import pack_geometry


def cells(raw, specs):
    prefix = b''.join(record(tag, data) for tag, flags, data in records(raw) if tag != 'CELL')
    for name, count, owner in specs:
        head = sub('NAME', name.encode() + b'\0') if name else b''
        head += sub('DATA', struct.pack('<Iii', 1 if name else 0, -2, -10))
        for i in range(count):
            head += sub('FRMR', struct.pack('<I', 42 + i)) + sub('NAME', b'plant\0')
            head += sub('DATA', struct.pack('<6f', 1 + i, 2, 3, .1, .2, .3))
            if owner: head += sub('ANAM', b'owner\0')
        prefix += record('CELL', head)
    return prefix


def refs(context):
    result = []
    for ref in context['original'].values():
        r = copy.deepcopy(ref)
        r['source_key'] = placement_source_key(r, context['full']['master_sha256'])
        result.append(r)
    return result


def binding(ref):
    return dict(model='@0'), [v*.25 for v in ref['position']], [0, 0, 0]


def semantics(graph):
    nodes, edges, plants, _ = graph
    def expand(index):
        node = nodes[index]
        return (node['kind'], node['flags'], node['chance'], node['id'],
                tuple((expand(n), level, quantity) for n, level, quantity in
                      edges[node['first']:node['first'] + node['count']]))
    return {p['key']: tuple((expand(n), level, quantity) for n, level, quantity in
                           edges[p['first']:p['first']+p['count']]) for p in plants}


class WorldHarvestTests(unittest.TestCase):
    def test_interior_full_namespace_and_original_metadata(self):
        raw = cells(source(), [(None, 1, False), ('Cave A', 1, False), ('Cave B', 1, False)])
        context = source_context(raw)
        allrefs = refs(context)
        self.assertEqual(len(context['original']), 3)
        self.assertEqual(len(set(r['source_key'] for r in allrefs)), 3)
        self.assertEqual(len(prepare_graph(context, allrefs, binding)[2]), 3)
        self.assertEqual(context['catalogue'], placement_index(context['full'])[1])
        with self.assertRaises(ValueError): placement_source_key(allrefs[1], 'bad')
        allrefs[1]['container_state']['items'][0]['count'] += 1
        with self.assertRaisesRegex(ValueError, 'metadata mismatch'):
            prepare_graph(context, allrefs, binding)
        context = source_context(cells(source(), [('Cave A', 1, True)]))
        with self.assertRaisesRegex(ValueError, 'ownership'):
            prepare_graph(context, refs(context), binding)

    def test_root_span_sharing_keeps_order_quantities_and_nested_chance(self):
        raw = cells(source(), [(None, 10, False)])
        before = source_context(raw)
        after = source_context(raw, intern_root_spans=True)
        a = prepare_graph(before, refs(before), binding)
        b = prepare_graph(after, refs(after), binding)
        self.assertEqual(semantics(a), semantics(b))
        self.assertEqual(len(a[1]), 11)
        self.assertEqual(len(b[1]), 2)
        self.assertEqual(len({(p['first'], p['count']) for p in b[2]}), 1)
        # Change one synthetic original root legitimately in both proof contexts;
        # interning must distinguish order and quantity, never sort/merge roots.
        for context in (before, after):
            context['original'] = {key: copy.deepcopy(value) for key, value in context['original'].items()}
            values = list(context['original'].values())
            values[1]['container_state']['items'] = [{'id':'levelled','count':3}]
            values[2]['container_state']['items'] = [{'id':'levelled','count':2}, {'id':'ingredient','count':1}]
            values[3]['container_state']['items'] = list(reversed(values[2]['container_state']['items']))
        a = prepare_graph(before, refs(before), binding)
        b = prepare_graph(after, refs(after), binding)
        self.assertEqual(semantics(a), semantics(b))
        self.assertEqual(len({p['first'] for p in b[2][:4]}), 4)

    def test_capacity_is_explicit_and_no_truncation(self):
        for count in (24, 25, 77, 80, 81, 256, 257):
            raw = cells(source(), [('Dense cave', count, False)])
            old = source_context(raw)
            if count <= 24: self.assertEqual(len(prepare_graph(old, refs(old), binding)[2]), count)
            else:
                with self.assertRaisesRegex(ValueError, 'capacity'): prepare_graph(old, refs(old), binding)
            candidate = source_context(raw, max_plants=256, intern_root_spans=True)
            if count <= 256:
                graph = prepare_graph(candidate, refs(candidate), binding)
                self.assertEqual(len(graph[2]), count)
                self.assertEqual(len(graph[1]), 2)
            else:
                with self.assertRaisesRegex(ValueError, 'capacity'): prepare_graph(candidate, refs(candidate), binding)
        for maximum in (0, 257, True, 24.0):
            with self.assertRaises(ValueError): source_context(raw, max_plants=maximum)

    def test_interior_selection_cannot_bleed_between_cells_or_world(self):
        context = source_context(cells(source(), [(None,1,False),('Cave A',1,False),('Cave B',1,False)]))
        allrefs = refs(context)
        for ref in allrefs: ref['bounds'] = [[0,0,0],[5,5,5]]
        expected = next(r for r in allrefs if r['cell'] == 'Cave A')
        row = dict(origin=[0,0,0], coverage=[[-10,-10],[10,10]], source_kind='interior',
                   source_cell='Cave A', keys=[identity_key(expected['source_key'])])
        self.assertEqual(region_references(row, allrefs), [expected])
        row['source_cell'] = 'Cave B'
        with self.assertRaisesRegex(ValueError, 'coverage'): region_references(row, allrefs)
        row['source_cell'] = ''
        with self.assertRaisesRegex(ValueError, 'source cell'): region_references(row, allrefs)

    def test_interior_runs_actual_packet_converter_and_bsp_retention(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            # sample() obtains an exterior reference; adapt the real source/index
            # together, preserving geometry checks and the converter's own binding.
            args,bsp=sample(root/'in')
            raw=cells(source(), [('Cave A',1,False)])
            context=source_context(raw)
            ref=refs(context)[0]
            index=json.loads(args['index_raw'])
            from prepare_scenery import world_bounds
            ref.update(model_index=0,bounds=world_bounds(index['models'][0]['bounds'],ref))
            index['references']=[ref]; args['master']=raw;args['index_raw']=json.dumps(index).encode()
            args['plan']['inputs'].update(master=pin(raw),index=pin(args['index_raw']))
            args['plan'].update(global_slots=1,global_catalogue_sha256=context['catalogue'],
                                max_plants=256,intern_root_spans=True,compact_models=True)
            args['plan']['maps'][0].update(source_kind='interior',source_cell='Cave A',keys=[identity_key(ref['source_key'])])
            result=convert_plan(**args,output=root/'out',budget=budget(args))
            self.assertEqual(result['maps'][0]['source_cell'],'Cave A')
            self.assertEqual((root/'in/town.bsp').read_bytes(),bsp)
            self.assertIn(identity_key(ref['source_key']).encode(),(root/'out/harvest-town.txt').read_bytes())

    def test_per_map_model_registry_is_opt_in_and_default_stays_compatible(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); args,_=sample(root/'in')
            # The second original belongs to a distant region. The legacy plan
            # intentionally lists both models; compact mode admits only this map's.
            extra=record('CONT',sub('NAME',b'plant2\0')+sub('FNAM',b'Plant two\0')+
                sub('MODL',b'f/flora_bc_mushroom_02.nif\0')+sub('FLAG',struct.pack('<I',11))+
                sub('CNDT',struct.pack('<f',0))+sub('NPCO',struct.pack('<i32s',1,b'ingredient')))
            extra+=record('CELL',sub('DATA',struct.pack('<Iii',0,20,20))+sub('FRMR',struct.pack('<I',43))+
                sub('NAME',b'plant2\0')+sub('DATA',struct.pack('<6f',10000,10000,0,0,0,0)))
            raw=source(extra=extra);context=source_context(raw)
            index=json.loads(args['index_raw'])
            geometry=pack_geometry([[0,0,0,0,0,255,255,255,255],[8,0,1,1,0,255,255,255,255],
                                    [0,6,2,0,1,255,255,255,255]],[[0,1,2,0]],1)
            packet=args['archive_path'].read_bytes();offset=(len(packet)+511)&~511
            packet+=bytes(offset-len(packet))+geometry;args['archive_path'].write_bytes(packet)
            model=copy.deepcopy(index['models'][0]);model.update(source='meshes/f/flora_bc_mushroom_02.nif',
                source_sha256='b'*64,offset=offset,bounds=[[0,0,0],[8,6,2]],**pin(geometry))
            index['models'].append(model)
            from prepare_scenery import world_bounds
            allrefs=refs(context)
            for r in allrefs:
                r['model_index']=0 if r['id']=='plant' else 1
                r['bounds']=world_bounds(index['models'][r['model_index']]['bounds'],r)
            index['references']=allrefs;args['master']=raw;args['index_raw']=json.dumps(index).encode()
            args['plan']['inputs'].update(master=pin(raw),index=pin(args['index_raw']),packet=pin(packet))
            args['plan'].update(global_slots=2,global_catalogue_sha256=context['catalogue'])
            args['plan']['maps'][0]['keys']=[identity_key(next(r for r in allrefs if r['id']=='plant')['source_key'])]
            result=convert_plan(**args,output=root/'default')
            self.assertEqual(result['maps'][0]['models'],2)
            before=(root/'default/harvest-town.txt').read_bytes()
            # Captured from the old converter using this synthetic two-model
            # fixture. Keep compatibility independent of private source paths.
            self.assertEqual(len(before),566)
            self.assertEqual(hashlib.sha256(before).hexdigest(),
                '0ffe9b3d5242d074ad1892ef4f114f4e4feab22eec6ae95ff500c897123e3a38')
            args['plan']['compact_models']=True
            result=convert_plan(**args,output=root/'compact')
            self.assertEqual(result['maps'][0]['models'],1)
            compact=(root/'compact/harvest-town.txt').read_bytes()
            self.assertEqual(compact.splitlines()[0].split()[-1],b'1')
            self.assertEqual(result['maps'][0]['placements'][0]['key'],args['plan']['maps'][0]['keys'][0])
            args['plan']['compact_models']='yes'
            with self.assertRaisesRegex(ValueError,'boolean'):
                convert_plan(**args,output=root/'invalid')


if __name__ == '__main__': unittest.main()
