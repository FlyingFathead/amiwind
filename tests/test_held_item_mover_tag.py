# SPDX-License-Identifier: GPL-3.0-only
"""GUARD-WEAPON-INVISIBLE-65: an actor whose layout names a skeletal mover draws its weapon when it fights.

The opening's people (the boat guard and the dock guard of Seyda Neen among them) are baked models; the layout of each
names an actor-library model as its mover, the skeletal full kit worn to walk and fight. At spawn the mover is
registered by name only (engine/aga/src/aw_anim.c lazy_index: nothing loaded; the slot holds 0 or the count of the
model it held before) and aw_items.c AW_ItemsPrep read the mover's tag against that count. The skeletal tag form
(AWTS1) demands the table's count, so every such tag was refused at the level load and the actor fought with nothing
drawn in its hands; the row form (AWTG1) has read a mover's tag with its own count since ANIMKIT-ITEM-TAG-FRAMES-35.
Now both forms read a count not known at spawn from the tag itself (AW_ItemsTagFrames), the mover branch never passes
the mover's slot count, and frames_match still checks the model's frames once it is loaded and worn."""
import os
import re
import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(1, str(ROOT / 'tools'))

import test_aga_native_source as native  # noqa: E402

UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


def body(text, head):
    start = text.index(head)
    return text[start:text.index('\n}\n', start)]


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class MoverTagNativeTests(unittest.TestCase):
    def test_the_guards_mover_tags_read_with_their_own_count(self):
        # the two guards' own tags: refused against every count a mover's slot can hold at spawn (the old route),
        # read with their 2932 frames now; a known count is still checked; the row form and bad tags
        native.NativeSourceTests().compile_run('aga_items_mover_tag_test.c', [SRC / 'aw_items.c'],
                                               defines=('AW_ITEMS_HOST_TEST',), cflags=UBSAN)


class MoverTagWiringTests(unittest.TestCase):
    def setUp(self):
        self.items = code('aw_items.c')

    def test_the_mover_branch_never_passes_the_movers_slot_count(self):
        prep = body(self.items, 'void AW_ItemsPrep(edict_t *actor) {')
        self.assertIn('prep(sv.models[i],a->mover,0);', prep)
        self.assertNotIn('sv.models[i]->numframes', prep)
        # a model known by name only (another layout's mover) spawned as an actor's own model: its tag's count too
        self.assertIn('if(m->numframes<0 || m->numframes>AW_ITEMS_MAX_SKEL_FRAMES)return;', prep)
        self.assertIn('prep(m,m->name,m->numframes);', prep)

    def test_both_tag_forms_take_the_count_rule_before_parsing(self):
        prep = body(self.items, 'static void prep(model_t *m,const char *name,int numframes) {')
        rule = prep.index('numframes=AW_ItemsTagFrames((const char *)text,numframes);')
        self.assertLess(rule, prep.index('if(!strncmp((const char *)text,"AWTS1 ",6)){'))
        self.assertIn('AW_ItemsParseSkel((const char *)text,numframes,', prep[rule:])
        self.assertLess(rule, prep.index('frames=AW_ItemsParse((const char *)text,numframes,rows,numframes,items);'))
        # the row form's own numframes-0 parse is the shared rule now
        self.assertIn('if(!numframes){refused(path,given,declared);', prep)
        self.assertNotIn('number(&p,&declared)', prep)
        # the rule lives in the host-testable half the fixture compiles
        host = self.items[:self.items.index('#ifndef AW_ITEMS_HOST_TEST')]
        self.assertIn('int AW_ItemsTagFrames(const char *text,int numframes) {', host)

    def test_a_refusal_says_both_counts(self):
        prep = body(self.items, 'static void prep(model_t *m,const char *name,int numframes) {')
        self.assertNotIn('invalid, items not drawn', prep)
        self.assertEqual(prep.count('refused(path,given,declared);'), 3)
        self.assertIn('"Item tags %s: invalid against %d model frames (the tag has %d), items not drawn\\n"',
                      body(self.items, 'static void refused(const char *path,int model_frames,int tag_frames) {'))

    def test_the_worn_model_is_still_checked_and_a_mismatch_said(self):
        self.assertIn('static int frames_match(model_t *m,int t) {return t>=0 && m && m->numframes==table[t].frames;}',
                      self.items)
        show = body(self.items, 'int AW_ItemsShow(edict_t *actor,edict_t *out[AW_ITEMS_KINDS]) {')
        self.assertIn('turned(actor) || !frames_match(model_of(actor),t=entry_of(model_of(actor)))){', show)
        self.assertIn('mismatch_told(t);return 0;', show)
        self.assertIn('int t=-1,', show)       # not set when a turned or freed actor stops the test first
        self.assertIn('frames_match(model_of(actor),t=entry_of(model_of(actor)))',
                      body(self.items, 'void AW_ItemsUpdate(edict_t *actor,edict_t *items[AW_ITEMS_KINDS]) {'))

    def test_the_level_counts_start_clean(self):
        # New Game and every new server start with no table and no count (the reset rule); a new world too
        self.assertIn('by_own_count=full_spawns=0;', body(self.items, 'void AW_ItemsSceneReset(void) {'))
        self.assertIn('by_own_count=full_spawns=0;', body(self.items, 'static void level_check(void) {'))
        prep = body(self.items, 'static void prep(model_t *m,const char *name,int numframes) {')
        self.assertLess(prep.index('declared=AW_ItemsTagFrames((const char *)text,0);'), prep.index('if(used>=TABLE){'))
        self.assertIn('if(declared && !full_spawns++)', prep)

    def test_the_pick_status_shows_the_tables(self):
        kit = code('aw_animkit.c')
        self.assertIn('AW_ItemsTables(e,counts,&model,info);', kit)
        self.assertIn('int AW_ItemsTables(edict_t *actor,int counts[4],const char **model,int info[3]) {', self.items)


if __name__ == '__main__':
    unittest.main()
