# SPDX-License-Identifier: GPL-3.0-only
"""CHIM-FRAME-EDGE-EFRAG-CRASH-36 and ENGINE-CRASH-EXIT-KEYBOARD-36: source checks on the engine.

- A leaf link to an entity without a valid model (the crash read model_t.type at address 0x44: a NULL model) no
  longer ends the game: R_StoreEfrags leaves the entity out, counts it and names it (labelled safety net), and cuts a
  leaf chain that loops (a hang with looping audio) instead of spinning.
- The CHIM paths that clear a placement's or static's model remove that entity's links first, whatever its counters say.
- Every exit route removes the engine's input.device handler first (else AmigaDOS keeps a handler in freed memory:
  latched shift/caps, M and N eaten).
"""
import re
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / 'engine' / 'aga' / 'src'


def text(name):
    return (SRC / name).read_text(encoding='utf-8')


def body(source, signature):
    start = source.index(signature)
    open_at = source.index('{', start)
    depth = 0
    for i in range(open_at, len(source)):
        depth += {'{': 1, '}': -1}.get(source[i], 0)
        if depth == 0:
            return source[open_at:i + 1]
    raise AssertionError('unbalanced ' + signature)


class EfragSafetyNetTests(unittest.TestCase):
    def test_store_efrags_never_ends_the_game(self):
        store = body(text('r_efrag.c'), 'void R_StoreEfrags (efrag_t **ppefrag)')
        self.assertNotIn('Sys_Error', store)
        self.assertNotIn('Host_Error', store)
        # a NULL model is checked before its type is read
        self.assertLess(store.index('if (!clmodel)'), store.index('switch (clmodel->type)'))
        self.assertIn('BadEfrag (pent, "a bad model type; left out")', store)
        # a looping chain is cut at the pool's size
        self.assertIn('++walked > aw_efrags_capacity', store)
        self.assertIn('*ppefrag = NULL', store)

    def test_remove_efrags_never_walks_a_missing_leaf_or_a_loop(self):
        remove = body(text('r_efrag.c'), 'void R_RemoveEfrags (entity_t *ent)')
        self.assertIn('prev = ef->leaf ? &ef->leaf->efrags : NULL', remove)
        self.assertIn('++steps > aw_efrags_capacity', remove)
        # a reset pool's link is already free: the chain is dropped, never pushed on the free list again
        leafless = remove[remove.index('if (!prev)'):remove.index('steps = 0;')]
        self.assertIn('break;', leafless)

    def test_safety_net_is_labelled_and_counted(self):
        source = text('r_efrag.c')
        self.assertIn('SAFETY NET (CHIM-FRAME-EDGE-EFRAG-CRASH-36)', source)
        self.assertIn('aw_efrags_bad++', body(source, 'static void BadEfrag ('))
        self.assertIn('aw_efrag_describe = ChimChunks_Describe', text('chim/chim_chunks.c'))


class LinksBeforeModelTests(unittest.TestCase):
    def test_deactivate_drops_links_before_clearing_the_model(self):
        deactivate = body(text('chim/chim_chunks.c'), 'static void Deactivate (int index)')
        self.assertLess(deactivate.index('DropEfrags (&c->places[i].ent)'), deactivate.index('ent.model = NULL'))

    def test_release_takes_every_linked_placement(self):
        release = body(text('chim/chim_chunks.c'), 'void ChimChunks_ReleaseEfrags (void)')
        self.assertIn('c->places[j].leaves || c->places[j].ent.efrag', release)

    def test_unplace_removes_links_whatever_the_leaf_count(self):
        unplace = body(text('chim/chim_statics.c'), 'static void Unplace (chim_statics_t *L, chim_static_t *s)')
        remove = unplace.index('ChimGraft_RemoveEfrags (&s->ent)')
        leaves_block = body(unplace[unplace.index('if (s->leaves)'):], 'if (s->leaves)')
        self.assertNotIn('ChimGraft_RemoveEfrags', leaves_block)
        self.assertLess(remove, unplace.index('s->ent.model = NULL'))


class ExitRemovesInputHandlerTests(unittest.TestCase):
    def test_every_exit_route_removes_the_handler_first(self):
        source = text('sys_amiga.c')
        error = body(source, 'void Sys_Error (char *error, ...)')
        self.assertLess(error.index('AW_InputGuardShutdown()'), error.index('Host_Shutdown'))
        quit_ = body(source, 'void Sys_Quit(void)')
        self.assertLess(quit_.index('AW_InputGuardShutdown()'), quit_.index('Host_Shutdown'))
        init = body(source, 'void AW_InputGuardInit(void)')
        self.assertIn('atexit(AW_InputGuardShutdown)', init)

    def test_removal_can_run_twice(self):
        shutdown = body(text('sys_amiga.c'), 'void AW_InputGuardShutdown(void)')
        for flag in ('guard_added', 'guard_open', 'guard_io', 'guard_port'):
            self.assertRegex(shutdown, r'if\(' + flag + r'\)')


if __name__ == '__main__':
    unittest.main()


class SafetyNetIsNoticedTests(unittest.TestCase):
    """The game keeps running, but a smoke that saw the safety net used fails (so it is never hidden)."""

    def test_state_file_reports_the_count(self):
        self.assertIn(r'fprintf(f,"efrags_bad %d\n",aw_efrags_bad)', text('aw_remote.c'))

    def test_engine_smoke_fails_when_the_net_was_used(self):
        import sys
        sys.path.insert(0, str(SRC.parents[2] / 'tools'))
        import engine_smoke
        self.assertIn('b=$(st efrags_bad)', engine_smoke.PROBE)
        self.assertIn('FAIL efrag safety net used', engine_smoke.PROBE)


class RelinkLoopPointerTests(unittest.TestCase):
    """The root cause: the third-person hook assigned the player body to CL_RelinkEntities' loop pointer, so the
    rest of that frame's entities were walked in the memory after aw_view.c's static body."""

    def test_loop_pointer_is_never_reassigned(self):
        relink = body(text('cl_main.c'), 'void CL_RelinkEntities (void)')
        self.assertNotIn('ent = aw_view_body', relink)
        self.assertIn('draw = aw_view_body (ent)', relink)
        self.assertIn('cl_visedicts[cl_numvisedicts] = draw', relink)
