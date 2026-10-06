import unittest
from asset_progress import category,checked_image,markdown,report

class AssetProgressTests(unittest.TestCase):
    def media(self):
        categories={n:{'missing_source':0,'missing_output':0} for n in ('voices','effects','music','videos')}
        categories['voices']['missing_source']=1
        return {'categories':categories,'entries':[{'category':'voices','source':'sound/vo/a.wav',
          'status':'included','path':'sound/pool/a.wav','bytes':4,'sha256':'abcd'}]}
    def test_unknown_geometry_and_versioned_image_match(self):
        source={'sound/vo/a.wav':4,'meshes/a.nif':20}
        image=checked_image([{'readback':'passed','files':[{'path':'id1/sound/pool/a.wav','bytes':4,'sha256':'abcd'}]}])
        rows={r['category']:r for r in report(source,self.media(),image)['rows']}
        self.assertEqual(rows['voices']['same_output_in_image'],1)
        self.assertEqual(rows['voices']['missing_referenced_sources'],1)
        self.assertIsNone(rows['meshes']['converted_sources'])
        self.assertIsNone(rows['voices']['runtime_accepted_sources'])
        image['id1/sound/pool/a.wav']['sha256']='different'
        self.assertEqual(report(source,self.media(),image)['rows'][0]['same_output_in_image'],0)
    def test_reject_double_counted_or_unavailable_conversion(self):
        media=self.media();media['entries']*=2
        with self.assertRaisesRegex(ValueError,'Duplicate'):report({'sound/vo/a.wav':4},media,{})
        with self.assertRaisesRegex(ValueError,'absent'):report({},self.media(),{})
    def test_reject_category_that_would_invent_coverage(self):
        media=self.media();media['entries'][0]['category']='effects'
        with self.assertRaisesRegex(ValueError,'category differs'):
            report({'sound/vo/a.wav':4},media,{})
        media=self.media();media['entries'][0]['source']='Sound\\Vo\\A.WAV'
        self.assertEqual(report({'sound/vo/a.wav':4},media,{})['rows'][0]['converted_sources'],1)
    def test_recorded_conversion_does_not_verify_changed_current_input(self):
        media=self.media();media['entries'][0]['source_sha256']='1'*64
        # An earlier digest cannot establish that the currently selected source
        # (including a new loose override) still has those bytes.
        for current_bytes in (4,999):
            result=report({'sound/vo/a.wav':current_bytes},media,{})
            row=result['rows'][0]
            self.assertEqual(row['converted_sources'],1)
            self.assertIsNone(row['current_input_verified_sources'])
            self.assertEqual(result['current_input_verification'],'not_checked')
            self.assertEqual(result['conversion_evidence_scope'],'supplied_media_report')
            self.assertIn('Recorded converted | Current input verified',markdown(result))
    def test_empty_batch_is_not_current_input_acceptance(self):
        media=self.media();media['entries']=[]
        result=report({'sound/vo/a.wav':4},media,{})
        self.assertEqual(result['rows'][0]['converted_sources'],0)
        self.assertIsNone(result['rows'][0]['current_input_verified_sources'])
        self.assertIn('zero means no such rows recorded', ' '.join(result['limits']))
    def test_image_requires_complete_readback_and_rejects_conflicts(self):
        with self.assertRaises(ValueError):checked_image([{'readback':'pending','files':[]}])
        a={'path':'id1/a.mdl','bytes':1,'sha256':'a'}
        with self.assertRaisesRegex(ValueError,'Conflicting'):
            checked_image([{'readback':'passed','files':[a,dict(a,sha256='b')]}])
        self.assertEqual(len(checked_image([{'readback':'passed','files':[a,a]}])),1)
    def test_source_types_keep_units_separate(self):
        self.assertEqual(category('Sound\\Vo\\A.WAV'),'voices')
        self.assertEqual(category('icons/a.dds'),'icons')
        self.assertEqual(category('textures/a.dds'),'textures')
        self.assertEqual(category('meshes/a.kf'),'animations')

if __name__=='__main__':unittest.main()
