# SPDX-License-Identifier: GPL-3.0-only
"""Every name the image step functions read is defined (no NameError at the end of a build).

finalize_image wrote build.json with torchtest_report, a local of image(): every
image build that passed all gates stopped with a NameError after packing.
"""
import builtins
from pathlib import Path
import symtable
import unittest

ROOT = Path(__file__).resolve().parents[1]


def undefined_names(path, function):
    source = path.read_text(encoding='utf-8')
    table = symtable.symtable(source, str(path), 'exec')
    module_names = {symbol.get_name() for symbol in table.get_symbols()}
    child = next(t for t in table.get_children() if t.get_name() == function)
    missing = []
    for symbol in child.get_symbols():
        name = symbol.get_name()
        if symbol.is_referenced() and not (symbol.is_assigned() or symbol.is_parameter() or symbol.is_imported()
                                           or name in module_names or hasattr(builtins, name)):
            missing.append(name)
    return sorted(missing)


class ImageStepNameTests(unittest.TestCase):
    def test_image_functions_read_only_defined_names(self):
        path = ROOT / 'tools/build_aga.py'
        for function in ('image', 'finalize_image', 'engine', 'install_world_scenery', 'write_content_fingerprint'):
            with self.subTest(function=function):
                self.assertEqual(undefined_names(path, function), [])


if __name__ == '__main__':
    unittest.main()
