"""The input check requires the SELECTED expansions' files by size and SHA-256 (DLC-INPUT-CHECKSUMS-66): selected +
matching passes, selected + missing or different refuses, an expansion left out (--no-dlc) is not required, and the
base-only check is unchanged."""
import json
from pathlib import Path
import tempfile
import unittest

from mwad import input_check
from test_workflow import synthetic_install

FILES = ('Tribunal.esm', 'Tribunal.bsa', 'Bloodmoon.esm', 'Bloodmoon.bsa')


def add_expansions(data):
    for name in FILES:
        (data / name).write_bytes(('expansion ' + name).encode())


def reference_of(data, names):
    return {n.casefold(): {'bytes': (data / n).stat().st_size, 'sha256': input_check.digest(data / n)} for n in names}


class ExpansionInputCheck(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name) / 'Data Files'
        synthetic_install(self.data)
        self.base = reference_of(self.data, [p.name for p in self.data.iterdir()])

    def tearDown(self):
        self.temp.cleanup()

    def inspect(self, expansions, expansion_ref=None, **kw):
        return input_check.inspect(self.data, 'terrain', reference=self.base, expansions=expansions,
                                   expansion_ref=expansion_ref, **kw)

    def test_selected_and_matching_passes(self):
        add_expansions(self.data)
        report = self.inspect(['Tribunal', 'Bloodmoon'], reference_of(self.data, FILES))
        self.assertEqual(report['errors'], [])
        self.assertEqual(sum('match the reference' in c for c in report['checks']), 4)

    def test_selected_and_missing_refuses(self):
        add_expansions(self.data)
        ref = reference_of(self.data, FILES)
        (self.data / 'Bloodmoon.bsa').unlink()
        report = self.inspect(['Tribunal', 'Bloodmoon'], ref)
        self.assertEqual(len(report['errors']), 1)
        self.assertIn('Missing or empty required expansion input: Bloodmoon.bsa', report['errors'][0])
        self.assertIn(ref['bloodmoon.bsa']['sha256'], report['errors'][0])

    def test_selected_and_different_refuses(self):
        add_expansions(self.data)
        ref = reference_of(self.data, FILES)
        (self.data / 'Tribunal.esm').write_bytes(b'expansion Tribunal.esX')   # same size, other bytes
        report = self.inspect(['Tribunal'], ref)
        self.assertEqual(len(report['errors']), 1)
        self.assertIn('Tribunal.esm differs from the reference', report['errors'][0])
        self.assertIn(ref['tribunal.esm']['sha256'], report['errors'][0])
        allowed = self.inspect(['Tribunal'], ref, allow_differences=True)
        self.assertEqual(allowed['errors'], [])
        self.assertTrue(any('Tribunal.esm differs' in w for w in allowed['warnings']))

    def test_left_out_and_missing_passes(self):
        ref = {n.casefold(): {'bytes': 1, 'sha256': '0' * 64} for n in FILES}
        self.assertEqual(self.inspect([], ref)['errors'], [])
        only = self.inspect(['Tribunal'], {k: v for k, v in ref.items() if k.startswith('tribunal')})
        self.assertTrue(all('Tribunal' in e for e in only['errors']) and only['errors'])

    def test_base_only_unchanged(self):
        add_expansions(self.data)
        plain = input_check.inspect(self.data, 'terrain', reference=self.base)
        self.assertEqual(self.inspect(None), plain)
        self.assertEqual(self.inspect([]), plain)

    def test_reference_holds_the_known_inputs_values(self):
        repo = Path(__file__).resolve().parents[1]
        known = {e['name'].casefold(): e for e in json.loads((repo / 'config/known-inputs.json').read_text())['entries']}
        ref = input_check.expansion_reference()
        self.assertEqual(sorted(ref), sorted(n.casefold() for n in FILES))
        for name, entry in ref.items():
            self.assertEqual((entry['bytes'], entry['sha256']), (known[name]['bytes'], known[name]['sha256']))


if __name__ == '__main__':
    unittest.main()
