import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from music_catalogue import build_catalogue, write_catalogue


def fixture(names):
    return {'tracks': [{'source': name, 'file': f'track{i:02d}.mws',
                        'sha256': hashlib.sha256(audio.encode()).hexdigest()}
                       for i, (name, audio) in enumerate(names)]}


def parse(raw):
    # Independent format reader: exercise what the bounded native line scanner
    # will receive, without importing generator normalization helpers.
    lines=raw.decode('ascii').splitlines()
    assert lines.pop(0)=='AWOST1'
    result={}
    for line in lines:
        number,group,alias=line.split(' ')
        assert 0<=int(number)<=98 and group in ('0','1','2')
        assert 1<=len(alias)<=95 and len(line)<159
        assert all(c.isascii() and (c.isalnum() or c in '_.+-') for c in alias)
        assert alias not in result
        result[alias]=(int(number),int(group))
    return result


class MusicCatalogueTests(unittest.TestCase):
    def test_original_ids_aliases_specials_and_duplicate_title(self):
        data=fixture([('Music/Special/morrowind title.mp3','title'),
                      ('Music/Explore/Morrowind Title.mp3','title'),
                      ('Music\\Explore\\mx_explore_1.mp3','explore'),
                      ('Music/Battle/MW battle 4.mp3','battle'),
                      ('Music/Special/MW_Death.mp3','death')])
        raw,report=build_catalogue(data);aliases=parse(raw)
        self.assertNotIn(b'\r',raw)
        self.assertEqual(aliases['mx_explore_1'],(2,0))
        self.assertEqual(aliases['mx_explore_1.mp3'],(2,0))
        self.assertEqual(aliases['mw_battle_4'],(3,1))
        self.assertEqual(aliases['mw_death'],(4,2))
        self.assertEqual(aliases['morrowind_title'],(0,2))
        self.assertEqual(aliases['01'],(1,2))
        self.assertEqual(aliases['track01.mws'],(1,2))
        self.assertEqual(report['numeric_ids'],list(range(5)))
        self.assertEqual(build_catalogue(data),(raw,report))

    def test_different_audio_collision_omitted_but_paths_and_ids_retained(self):
        raw,report=build_catalogue(fixture([('Music/Explore/a.mp3','a'),('Music/Battle/a.mp3','b')]))
        aliases=parse(raw)
        self.assertNotIn('a',aliases)
        self.assertNotIn('a.mp3',aliases)
        self.assertEqual(aliases['music_explore_a'],(0,0))
        self.assertEqual(aliases['music_battle_a.mp3'],(1,1))
        self.assertTrue(any(r['reason']=='ambiguous different audio' for r in report['omitted_aliases']))

    def test_unsupported_or_long_names_keep_numeric_recall(self):
        raw,report=build_catalogue(fixture([('Music/Explore/'+('x'*100)+'.mp3','long'),
                                         ('Music/Special/musique-é.mp3','unicode')]))
        aliases=parse(raw)
        self.assertEqual(aliases['00'],(0,0));self.assertEqual(aliases['01'],(1,2))
        self.assertTrue(report['omitted_aliases'])

    def test_reserved_numeric_alias_never_redirects_numeric_track(self):
        raw,_=build_catalogue(fixture([('Music/Explore/01.mp3','zero'),('Music/Special/other.mp3','one')]))
        self.assertEqual(parse(raw)['01'],(1,2))

    def test_invalid_manifest_does_not_replace_existing_catalogue(self):
        invalid=[{'tracks':[]},fixture([('Music/../escape.mp3','x')]),fixture([('Music/Explore/a.mp3','x')])]
        invalid[-1]['tracks'][0]['file']='track04.mws'
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);out=root/'catalogue.txt';out.write_bytes(b'keep')
            for data in invalid:
                source=root/'soundtrack.json';source.write_text(json.dumps(data))
                with self.assertRaises(ValueError):write_catalogue(source,out)
                self.assertEqual(out.read_bytes(),b'keep')

    def test_highest_supported_id_and_writer_hash(self):
        data=fixture([(f'Music/Explore/{i}.mp3',str(i)) for i in range(99)])
        raw,_=build_catalogue(data);self.assertEqual(parse(raw)['98'],(98,0))
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);source=root/'soundtrack.json';source.write_text(json.dumps(data))
            report=write_catalogue(source,root/'catalogue.txt')
            self.assertEqual((root/'catalogue.txt').read_bytes(),raw)
            self.assertEqual(report['catalogue_sha256'],hashlib.sha256(raw).hexdigest())


if __name__=='__main__':unittest.main()
