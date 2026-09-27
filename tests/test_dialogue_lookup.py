import struct,unittest
from mwad.dialogue_lookup import build_lookup

def info(identifier,extra=()):
    return [('INAM',identifier.encode()),('DATA',struct.pack('<iibbbb',1,50,-1,0,-1,0)),
            ('RNAM',b'Test Race'),('SNAM',b'Voice\\test.mp3'),*extra]
class DialogueLookupTests(unittest.TestCase):
    def test_order_conditions_and_scripts_are_preserved_not_approved(self):
        a={'id':'person','race':'test race','female':False,'class':'watch','faction':''}
        fields=info('second',[('PNAM',b'first'),('SCVR',b'unknown'),('INTV',struct.pack('<i',42)),
                   ('SCVR',b'next'),('FLTV',struct.pack('<f',.5)),('BNAM',b';comment\nchangequest 1')])
        table=build_lookup({'hello':[info('first'),fields,info('wrong',[('ONAM',b'other')])]},[a])
        self.assertEqual(table['actors']['person']['topics']['hello'],[0,1])
        item=table['responses'][1]
        self.assertEqual(item['previous'],'first');self.assertEqual(item['sound'],'voice/test.mp3')
        self.assertEqual([c['operand']['value'] for c in item['conditions']],[42,.5])
        self.assertTrue(item['has_executable_result'])
        self.assertEqual(item['raw_subrecords'],[[k,v.hex()] for k,v in fields])
    def test_bad_conditions_rejected(self):
        for extra in [[('SCVR',b'no_operand')],[('INTV',b'1234')],[('SCVR',b'x'),('INTV',b'12')]]:
            with self.assertRaises(ValueError):build_lookup({'hello':[info('a',extra)]},[])
    def test_comment_only_result_and_duplicate_ids(self):
        t=build_lookup({'idle':[info('x',[('BNAM',b' ; note\n; another')])]},[])
        self.assertFalse(t['responses'][0]['has_executable_result'])
        with self.assertRaises(ValueError):build_lookup({'hello':[info('x'),info('x')]},[])
