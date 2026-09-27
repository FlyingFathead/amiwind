"""Assembly fixtures are fictional; no game assets or extracted records."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from scenery_selection import select_source_refs, select_runtime_refs, validate_groups


def ref(number, name, kind, x, bounds=None):
    return {'number': number, 'id': name, 'type': kind, 'model': name+'.nif',
            'position': [x, 0, 0], 'bounds': bounds or [[x-1,-1,-1],[x+1,1,1]]}


class ScenerySelectionTests(unittest.TestCase):
    def setUp(self):
        self.groups = {'vessel': {'members': {'hull': 'ACTI', 'hatch': 'DOOR'},
                                  'presentation': 'fictional static preview'}}

    def test_source_closure_keeps_attachment_beyond_radius_not_other_activators(self):
        refs=[ref(1,'hull','ACTI',2),ref(2,'hatch','DOOR',20),
              ref(3,'editor_box','ACTI',0),ref(4,'rock','STAT',3)]
        selected,groups=select_source_refs(refs,[0,0],10,self.groups)
        self.assertEqual([r['number'] for r in selected],[1,2,4])
        validate_groups(selected,groups)
        with self.assertRaisesRegex(ValueError,'incomplete'):
            validate_groups(selected[1:],groups)

    def test_missing_deleted_and_ambiguous_members_fail(self):
        hull=ref(1,'hull','ACTI',2);hatch=ref(2,'hatch','DOOR',20)
        for refs in ([hull],[hull,{**hatch,'deleted':True}],
                     [hull,hatch,{**hatch,'number':3}]):
            with self.assertRaises(ValueError):
                select_source_refs(refs,[0,0],10,self.groups)

    def test_runtime_intersects_group_bounds_not_outside_origins(self):
        refs=[ref(1,'hull','ACTI',12,[[8,-2,-1],[18,2,1]]),
              ref(2,'hatch','DOOR',17),ref(3,'rock','STAT',3)]
        refs,groups=select_source_refs(refs,[0,0],30,self.groups)
        chosen,report=select_runtime_refs({'references':refs,'groups':groups},[0,0],1,10)
        self.assertEqual([r['number'] for r in chosen],[1,2,3])
        self.assertEqual(report['selected_groups'],['vessel'])
        chosen,report=select_runtime_refs({'references':refs,'groups':groups},[-20,0],1,10)
        self.assertEqual(chosen,[])

    def test_old_index_retains_unrelated_selection(self):
        chosen,report=select_runtime_refs({'references':[ref(1,'rock','STAT',3),
                                            ref(2,'tree','STAT',30)]},[0,0],1,10)
        self.assertEqual([r['number'] for r in chosen],[1])
        self.assertEqual(len(report['omitted']),1)
