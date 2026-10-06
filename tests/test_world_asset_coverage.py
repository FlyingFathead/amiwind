# SPDX-License-Identifier: GPL-3.0-only
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import os
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import world_asset_coverage as w


def file(path,number=1):return dict(path=path,bytes=number,sha256=f'{number:064x}')


def fixture():
    source=dict(categories=[dict(id='flora',scope='Synthetic complete base-master population',
                                 assets_complete=True,exterior_complete=True,interior_complete=True)],
                pins=[dict(label='base master',sha256='a'*64)],
                assets=[dict(id='mesh',category='flora',available=True,sha256='b'*64)],
                placements=[dict(id='p1',asset='mesh',space='exterior',admission='eligible'),
                            dict(id='p2',asset='mesh',space='interior',admission='eligible')])
    digest=w.digest(source)
    common=dict(status='verified',source_catalogue_sha256=digest,categories=['flora'])
    model=file('id1/progs/plant.mdl')
    bsp=file('id1/maps/m1.bsp',2);cat=file('id1/harvest-m1.txt',3)
    return dict(schema=w.SCHEMA,build=dict(id='candidate-one'),source=source,source_catalogue_sha256=digest,
        conversion=dict(**common,records=[dict(asset='mesh',category='flora',source_sha256='b'*64,outputs=[model])]),
        maps=dict(**common,build_id='candidate-one',records=[dict(id='m1',space='exterior',binding='verified',admission='passed',representation='external_catalogue',
                                       bsp=bsp,catalogue=cat,placements=['p1'])]),
        installed=dict(**common,build_id='candidate-one',files=copy.deepcopy([model,bsp,cat])))


def repin(e):
    sha=w.digest(e['source']);e['source_catalogue_sha256']=sha
    for key in ('conversion','maps','installed','routing'):
        if key in e:e[key]['source_catalogue_sha256']=sha


class CoverageTests(unittest.TestCase):
    def test_engine_only_is_unknown_not_zero_and_width_is_dynamic(self):
        r=w.report(build={'id':'engine-only'})
        self.assertEqual(r['status'],'unknown');self.assertEqual(r['rows'],[])
        with patch.object(w.shutil,'get_terminal_size',return_value=os.terminal_size((53,24))):
            text=w.terminal(r)
        self.assertEqual(text.splitlines()[0],'-'*53)
        self.assertTrue(all(len(line)<=53 for line in text.splitlines()))
        self.assertIn('unknown',text)

    def test_exact_image_closure_and_unmapped_interior_split(self):
        r=w.report(fixture())['rows'][0]
        self.assertEqual(r['assets']['converted'],1)
        a,b=r['placements']['exterior'],r['placements']['interior']
        self.assertEqual((a['source_total'],a['can_be_placed'],a['installed_unique'],a['installed_map_copies']),(1,1,1,1))
        self.assertEqual((b['source_total'],b['can_be_placed'],b['still_missing_from_admitted_maps']),(1,0,1))
        self.assertIsNone(a['reachable_verified'])
        self.assertEqual(b['reasons'],{'missing_map_binding':1})

    def test_overlap_duplicates_do_not_inflate_unique_originals(self):
        e=fixture();row=copy.deepcopy(e['maps']['records'][0]);row['id']='m2'
        row['bsp']=file('id1/maps/m2.bsp',4);row['catalogue']=file('id1/harvest-m2.txt',5)
        e['maps']['records'].append(row);e['installed']['files'] += [row['bsp'],row['catalogue']]
        result=w.report(e)['rows'][0]['placements']['exterior']
        self.assertEqual((result['installed_unique'],result['installed_map_copies']),(1,2))

    def test_partial_scope_and_unprovided_category_stay_unknown(self):
        e=fixture();e['source']['categories'][0]['interior_complete']=False
        e['source']['categories'].append(dict(id='buildings',scope='Partial source survey',
            assets_complete=False,exterior_complete=False,interior_complete=False));repin(e)
        rows=w.report(e)['rows']
        self.assertIsNone(rows[0]['placements']['interior']['source_total'])
        self.assertIsNone(rows[0]['placements']['interior']['still_missing_from_admitted_maps'])
        self.assertIsNone(rows[1]['assets']['converted'])
        self.assertIsNone(rows[1]['placements']['exterior']['can_be_placed'])

    def test_missing_source_unsupported_and_unconverted_reasons_are_distinct(self):
        for case in ('missing_source','unsupported','not_converted_for_build'):
            e=fixture()
            if case=='missing_source':
                e['source']['assets'][0]['available']=False;e['conversion']['records']=[]
            elif case=='unsupported':
                e['source']['placements'][0].update(admission='unsupported',reason='owner theft rules pending')
            else:e['conversion']['records']=[]
            repin(e)
            r=w.report(e)['rows'][0]['placements']['exterior']
            self.assertEqual(r['reasons'],{case:1});self.assertEqual(r['can_be_placed'],0)

    def test_stale_model_or_catalogue_never_counts_as_installed(self):
        for index in (0,1,2):
            e=fixture();e['installed']['files'][index]['sha256']='f'*64
            p=w.report(e)['rows'][0]['placements']['exterior']
            self.assertEqual(p['can_be_placed'],1);self.assertEqual(p['installed_unique'],0)
            self.assertEqual(p['reasons'],{'missing_or_different_packaged_files':1})

    def test_failed_map_admission_cannot_become_placeable(self):
        e=fixture();e['maps']['records'][0]['admission']='failed'
        p=w.report(e)['rows'][0]['placements']['exterior']
        self.assertEqual((p['can_be_placed'],p['installed_unique']),(0,0))
        self.assertEqual(p['reasons'],{'map_not_admitted':1})

    def test_reachability_requires_current_map_and_build_binding(self):
        e=fixture();e['routing']=dict(status='verified',categories=['flora'],
            source_catalogue_sha256=e['source_catalogue_sha256'],build_id='candidate-one',
            records=[dict(map='m1',bsp_sha256=e['maps']['records'][0]['bsp']['sha256'])])
        p=w.report(e)['rows'][0]['placements']['exterior'];self.assertEqual(p['reachable_verified'],1)
        for change in ('build','map'):
            x=copy.deepcopy(e)
            if change=='build':x['routing']['build_id']='other'
            else:x['routing']['records'][0]['bsp_sha256']='f'*64
            with self.assertRaises(ValueError):w.report(x)

    def test_duplicate_identity_wrong_category_and_tampered_source_rejected(self):
        e=fixture()
        mutators=[lambda x:x['source']['placements'].append(x['source']['placements'][0]),
                  lambda x:x['conversion']['records'][0].update(category='other'),
                  lambda x:x['conversion']['records'][0].update(source_sha256='e'*64),
                  lambda x:x['maps']['records'][0]['placements'].append('p1'),
                  lambda x:x['maps']['records'][0].update(space='interior'),
                  lambda x:x['installed'].update(build_id='old')]
        for mutate in mutators:
            x=copy.deepcopy(e);mutate(x)
            with self.assertRaises(ValueError):w.report(x)
        with self.assertRaises(ValueError):w.report(e,build={'id':'other'})

    def test_external_catalogue_cannot_be_omitted_from_installed_closure(self):
        e=fixture();e['maps']['records'][0].pop('catalogue')
        e['installed']['files']=[f for f in e['installed']['files'] if not f['path'].endswith('.txt')]
        with self.assertRaisesRegex(ValueError,'runtime catalogue'):w.report(e)

    def test_wrong_bsp_filename_is_not_a_placeable_runtime_map(self):
        e=fixture();e['maps']['records'][0]['bsp']['path']='id1/maps/unrelated.bsp'
        e['installed']['files'][1]['path']='id1/maps/unrelated.bsp'
        with self.assertRaisesRegex(ValueError,'filename'):w.report(e)

    def test_stale_map_admission_requires_current_build_binding(self):
        e=fixture();e['maps']['build_id']='old-build'
        with self.assertRaisesRegex(ValueError,'another build'):w.report(e)

    def test_missing_stage_is_unknown_even_with_assets(self):
        e=fixture();e.pop('installed');p=w.report(e)['rows'][0]['placements']['exterior']
        self.assertEqual(p['can_be_placed'],1);self.assertIsNone(p['installed_unique'])
        e.pop('maps');p=w.report(e)['rows'][0]['placements']['exterior']
        self.assertIsNone(p['can_be_placed']);self.assertIsNone(p['still_missing_from_admitted_maps'])


if __name__=='__main__':unittest.main()
