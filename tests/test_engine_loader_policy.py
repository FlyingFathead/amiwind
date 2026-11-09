# SPDX-License-Identifier: GPL-3.0-only
"""The CHIM stages key engine/aga/src/model.c by the loader policy the heap audits read (BUILD-CHIM-HEAP-KEY-LOADER-63).

The shared actor shapes edited model.c's alias reader and re-keyed the whole CHIM world, because the heap audits read
model.c and a stage key counted it whole. tools/engine_loader_policy.py now gives model.c's key value: the sprite,
BSP slice, alias and packed-edge policies the audits extract, and the digest of the brush and edge-cache loaders the
packed-edge pin covers. This test fails when an edit outside those loaders changes the value, when a limit edit does
not, when the heap audits' policies refuse this tree, or when the CHIM world stage keys model.c whole again."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import engine_loader_policy as P  # noqa: E402


def tree(edit=None):
    """A temporary checkout copy of engine/aga/src (model.c changed by EDIT(text))."""
    temp = Path(tempfile.mkdtemp(prefix='aw-loader-policy-'))
    shutil.copytree(ROOT / 'engine/aga/src', temp / 'engine/aga/src')
    if edit:
        path = temp / P.MODEL_C
        path.write_text(edit(path.read_text(encoding='utf-8')), encoding='utf-8', newline='\n')
    return temp


class LoaderPolicyKey(unittest.TestCase):
    def setUp(self):
        self.temps = []

    def tearDown(self):
        for temp in self.temps:
            shutil.rmtree(temp, ignore_errors=True)

    def value(self, edit=None):
        temp = tree(edit)
        self.temps.append(temp)
        return P.key_value(temp)

    def test_every_policy_accepts_this_tree(self):
        found = P.policy(ROOT / 'engine/aga/src')
        refused = {name: value for name, value in found.items() if str(value).startswith('refused')}
        self.assertEqual(refused, {}, 'a heap audit policy refuses the engine source: re-pin it after review')

    def test_edit_outside_the_loaders_keeps_the_key(self):
        def edit(text):
            self.assertIn('Con_Printf ("Cached models:\\n");', text)
            return text.replace('Con_Printf ("Cached models:\\n");', 'Con_Printf ("Cached models, all:\\n");')
        self.assertEqual(self.value(), self.value(edit))

    def test_a_loader_limit_changes_the_key(self):
        def edit(text):
            changed = text.replace('#define AW_BSP_SLICE_BYTES 16384', '#define AW_BSP_SLICE_BYTES 32768')
            self.assertNotEqual(changed, text)
            return changed
        self.assertNotEqual(self.value(), self.value(edit))

    def test_a_brush_loader_edit_changes_the_key(self):
        def edit(text):
            head = 'void Mod_LoadEdges (lump_t *l)\n{'
            self.assertIn(head, text)
            return text.replace(head, head + '\n    int aw_scratch_unused = 0; (void)aw_scratch_unused;', 1)
        self.assertNotEqual(self.value(), self.value(edit))

    def test_an_alias_reader_define_keeps_the_key(self):
        def edit(text):
            changed = text.replace('#define AW_TILE_RUN 64', '#define AW_TILE_RUN 65')
            self.assertNotEqual(changed, text)
            return changed
        self.assertEqual(self.value(), self.value(edit))

    def test_an_unused_new_define_keeps_the_key(self):
        def edit(text):
            return '#define AW_CK_NOBODY_READS_THIS 3\n' + text
        self.assertEqual(self.value(), self.value(edit))

    def loader_reads(self, prelude, use):
        """An edit that puts PRELUDE at the top of model.c and USE into Mod_LoadEdges."""
        head = 'void Mod_LoadEdges (lump_t *l)\n{'

        def edit(text):
            self.assertIn(head, text)
            return prelude + '\n' + text.replace(head, head + '\n    ' + use, 1)
        return edit

    def test_a_define_a_loader_uses_changes_the_key(self):
        use = 'int aw_ck = AW_CK_LIMIT; (void)aw_ck;'
        self.assertNotEqual(self.value(self.loader_reads('#define AW_CK_LIMIT 3', use)),
                            self.value(self.loader_reads('#define AW_CK_LIMIT 4', use)))

    def test_a_define_reached_through_a_macro_changes_the_key(self):
        use = 'int aw_ck = AW_CK_OUTER; (void)aw_ck;'
        self.assertNotEqual(self.value(self.loader_reads('#define AW_CK_INNER 3\n#define AW_CK_OUTER (AW_CK_INNER*2)', use)),
                            self.value(self.loader_reads('#define AW_CK_INNER 4\n#define AW_CK_OUTER (AW_CK_INNER*2)', use)))

    def test_a_static_table_a_loader_indexes_changes_the_key(self):
        use = 'int aw_ck = aw_ck_table[1]; (void)aw_ck;'
        self.assertNotEqual(self.value(self.loader_reads('static const int aw_ck_table[2] = {1, 2};', use)),
                            self.value(self.loader_reads('static const int aw_ck_table[2] = {1, 3};', use)))

    def test_chim_world_stage_keys_model_c_by_policy(self):
        import build_cache
        index = build_cache.SourceIndex(ROOT, top_format=build_cache.STAGE_TOP_FORMAT)
        selected = index.selection(ROOT / 'tools/chim_build.py')[0]
        self.assertTrue(str(selected.get(P.MODEL_C, '')).startswith(P.PREFIX), selected.get(P.MODEL_C))


if __name__ == '__main__':
    unittest.main()
