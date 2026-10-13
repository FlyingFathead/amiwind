# SPDX-License-Identifier: GPL-3.0-only
import math
import operator
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.script_visibility import classify_script, evaluate_visibility, audit_cell, BASE_TYPES
from mwad.esm import FormatError


def template(op='>', inverse=False):
    actions = ('disable', 0, 'enable', 1) if inverse else ('enable', 1, 'disable', 0)
    a, x, b, y = actions
    return f'begin sample\nif ( Stage {op} 2 )\nif ( GetDisabled == {x} )\n{a}\nendif\nelse\nif ( GetDisabled == {y} )\n{b}\nendif\nendif\nend sample'


def sub(tag, data):
    return struct.pack('<4sI', tag.encode(), len(data)) + data


def rec(tag, data):
    return struct.pack('<4sIII', tag.encode(), len(data), 0, 0) + data


def cell(refs):
    data = sub('NAME', b'') + sub('DATA', struct.pack('<Iii', 0, 10, 1))
    for number, name, deleted in refs:
        data += sub('FRMR', struct.pack('<I', number)) + sub('NAME', name.encode() + b'\0')
        data += sub('DATA', struct.pack('<6f', *([0]*6)))
        if deleted:
            data += sub('DELE', b'\0'*4)
    return rec('CELL', data)


class VisibilityTests(unittest.TestCase):
    def test_comparators_and_inverse(self):
        ops = {'==': operator.eq, '!=': operator.ne, '<': operator.lt, '>': operator.gt,
               '<=': operator.le, '>=': operator.ge}
        for op, fn in ops.items():
            for inverse in (False, True):
                rule = classify_script(template(op, inverse), {'stage'})
                self.assertEqual(rule['status'], 'conditional')
                for value in (1, 2, 3):
                    self.assertEqual(evaluate_visibility(rule, {'STAGE': value}), fn(value, 2) != inverse)

    def test_case_comments_and_missing_state(self):
        rule = classify_script(template().upper().replace('\n', '; comment\r\n'), {'Stage'})
        self.assertEqual(rule['status'], 'conditional')
        for value in (None, True, '3', math.nan, math.inf):
            self.assertIsNone(evaluate_visibility(rule, {'stage': value}))
        self.assertIsNone(evaluate_visibility(rule, {}))

    def test_unknown_is_not_hidden(self):
        source = template()
        cases = [source.replace('else', 'else\nset Other to 1'), source.replace('Stage', 'Local'),
                 source.replace('enable', 'activate'), source.replace('end sample', 'end wrong'),
                 source.replace('if ( Stage > 2 )', 'if ( CellChanged == 1 )'),
                 source.replace('begin sample', 'begin sample\nshort Stage')]
        for candidate in cases:
            rule = classify_script(candidate, {'stage'})
            self.assertEqual(rule['status'], 'unresolved_script')
            self.assertIsNone(evaluate_visibility(rule, {'stage': 3}))

    def test_reference_types_and_missing_data(self):
        raw = rec('GLOB', sub('NAME', b'Stage\0'))
        raw += rec('SCPT', sub('SCHD', b'sample\0'.ljust(52,b'\0')) + sub('SCTX', template().encode()))
        refs = []
        for n, kind in enumerate(sorted(BASE_TYPES), 1):
            name = 'object' + str(n)
            raw += rec(kind, sub('NAME', name.encode()) + sub('SCRI', b'sample'))
            refs.append((n, name, False))
        raw += rec('STAT', sub('NAME', b'plain'))
        raw += rec('STAT', sub('NAME', b'broken') + sub('SCRI', b'absent'))
        raw += rec('STAT', sub('NAME', b'dead') + sub('DELE', b'\0'*4))
        refs += [(100,'unknown',False),(101,'plain',False),(102,'broken',False),
                 (103,'dead',False),(104,'removed',True)]
        report = audit_cell(raw + cell(refs), (10,1), {'stage': 3})
        self.assertEqual(report['counts'], {'conditional':len(BASE_TYPES), 'missing_base':1,
                         'no_script':1, 'missing_script':1, 'deleted_base':1})
        self.assertTrue(all(r['enabled_at_requested_state'] for r in report['references'][:len(BASE_TYPES)]))
        self.assertTrue(all(r['enabled_at_requested_state'] is None for r in report['references'][len(BASE_TYPES):]))

    def test_fixed_snapshot_keeps_unknown_and_does_not_mutate_pool(self):
        from mwad.script_visibility import filter_references
        refs = [{'number': n, 'model_index': 0} for n in (1, 2, 3, 4)]
        report = {'references': [
            {'reference': 1, 'enabled_at_requested_state': False},
            {'reference': 2, 'enabled_at_requested_state': True},
            {'reference': 3, 'enabled_at_requested_state': None}]}
        selected = filter_references(refs, report)
        self.assertEqual([r['number'] for r in selected], [2, 3, 4])
        self.assertEqual(len(refs), 4)
        self.assertIs(selected[0], refs[1])
        # A later flora merge uses the same rule, even when the hidden reference
        # shares its pooled model with an enabled placement.
        self.assertEqual(filter_references(selected + [refs[0]], report), selected)

    def test_ambiguous_input_rejected(self):
        for raw in (cell([])*2, cell([(1,'x',False),(1,'x',False)]),
                    rec('STAT', sub('NAME', b'x'))*2 + cell([])):
            with self.assertRaises(FormatError):
                audit_cell(raw, (10,1))

    def test_cli_nonfinite_writes_nothing(self):
        tool = Path(__file__).resolve().parents[1]/'tools/audit_cell_visibility.py'
        with tempfile.TemporaryDirectory() as d:
            output = Path(d)/'out.json'
            result = subprocess.run([sys.executable, str(tool), str(Path(d)/'missing.esm'),
                                     '--cell','10','1','--state','Stage=nan','--out',str(output)], capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn(b'finite', result.stderr)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
