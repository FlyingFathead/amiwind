# SPDX-License-Identifier: GPL-3.0-only
"""What the hands hold carries through doors and cell changes (HANDS-STATE-LOST-THROUGH-DOORS-67): readied magic stays
readied. While a door, a teleport or a cell change loads, the server runs frames on the new map's player entity before
the client has spawned in it (Quake's SV_RunClients sets sv_player before it looks at the client's spawned flag), and
that entity's health is still 0. The casting frame took that for the player's death and lowered the magic (since
6a3b897f9, v0.0.61-dev2); since the magic and the weapon share the hands (1a0e3a3aa, v0.0.65) the hands, carried up
through the door by the hand snapshot, then showed the weapon stance, the fists. The drawn weapon, the fists, the held
light and its lit flag already cross by the snapshot (tests/aga_torch_qc_test.c transition_states). These checks fail
on the previous code."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
SRC = ROOT / 'engine/aga/src'


def code(name):
    text = (SRC / name).read_text(encoding='latin-1')
    return re.sub(r'/\*.*?\*/', '', text, flags=re.S)


def body(text, head):
    """The braces' body of the C function whose definition starts with HEAD."""
    start = text.index(head)
    at = text.index('{', start)
    depth = 0
    for i in range(at, len(text)):
        depth += {'{': 1, '}': -1}.get(text[i], 0)
        if not depth:
            return text[at:i + 1]
    raise ValueError('unbalanced ' + head)


class MagicThroughDoors(unittest.TestCase):
    def test_only_the_spawned_players_death_lowers_the_magic(self):
        cast = code('aw_cast.c')
        frame = body(cast, 'void AW_CastFrame(void)')
        self.assertIn('if(p->v.health<=0){if(player_spawned(p))ready=0;return;}', frame)
        self.assertNotIn('if(p->v.health<=0){ready=0;return;}', frame)
        spawned = body(cast, 'static int player_spawned(const edict_t *p)')
        for part in ('svs.clients[0].spawned', 'svs.clients[0].edict==p', 'svs.clients[0].active'):
            self.assertIn(part, spawned)

    def test_the_stance_is_read_back_in_play(self):
        hands = body(code('aw_debug.c'), 'static void hands(void)')
        self.assertIn('"hands stance: %s\\n"', hands)
        self.assertIn('aw_magic_readied?"magic ready"', hands)


if __name__ == '__main__':
    unittest.main()
