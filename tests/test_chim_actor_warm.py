# SPDX-License-Identifier: GPL-3.0-only
"""The type 1 actor queue's warm step (EXPERIMENTAL, "chim actors warm 1", engine aw_actors.c): a queued actor's
first-time loads (model, then voice) and the client's new sounds each take a tick of their own before or after its
spawn. Source checks: off by default; the warm-off path is the one the measurements compared against (every
pending actor spawned with its client lists in its own tick); a tick that only loaded runs no client list pass and
prints its trace line only after it is timed; the client lists keep mover models lazy as the level start does.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'engine/aga/src/aw_actors.c').read_text(encoding='utf-8')


class ActorWarmSourceTests(unittest.TestCase):
    def test_off_by_default(self):
        self.assertRegex(SRC, r'\nstatic int\s+warm_on;')
        self.assertIn('warm_on = atoi (Cmd_Argv (3)) != 0;', SRC)

    def test_warm_steps_only_when_on(self):
        self.assertIn('if (warm_on && limit > 0 && WarmStep (&pending[best]))', SRC)
        self.assertIn('if (warm_on && limit > 0 && ClientSoundStep ())', SRC)
        # warm off: client lists with sounds after every tick, as before
        self.assertIn('if (spawned || !(warm_on && limit > 0))', SRC)
        self.assertIn('ClientLists (!(warm_on && budget_n > 0));', SRC)

    def test_trace_printed_after_the_tick_is_timed(self):
        body = SRC[SRC.index('static int WarmStep'):SRC.index('static void SpawnQueued')]
        self.assertNotIn('Con_Printf ("actors: tick warmed %s', body)
        queued = SRC[SRC.index('static void SpawnQueued'):]
        self.assertLess(queued.index('t0 = Sys_FloatTime () - t0;'), queued.index('Con_Printf ("%s", warm_note);'))

    def test_client_lists_keep_movers_lazy(self):
        lists = SRC[SRC.index('static void ClientLists'):SRC.index('static int ClientSoundStep')]
        self.assertIn('AW_AnimLazy (sv.model_precache[i]) ? Mod_FindName (sv.model_precache[i])', lists)

    def test_every_queue_entry_starts_cold(self):
        self.assertEqual(len(re.findall(r'q->warmed = 0;', SRC)), 2)   # the frame map rows and the actor table


if __name__ == '__main__':
    unittest.main()
