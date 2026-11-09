# SPDX-License-Identifier: GPL-3.0-only
"""One follow implementation (v0.0.63, ESCORT-FOLLOW-63): the debug companion's follow think (aw_companion.c,
aw_follow.h) moves the companion and the script packages' followers and escorts (aw_ambient.c); the packages keep
their own rules. The companion's own behaviour is proven by tests/test_companion_native.py (unchanged); this test
keeps the two callers on the one think."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine/aga/src'


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


def body(text, head):
    start = text.index(head)
    depth, i = 0, text.index('{', start)
    while True:
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1


class FollowFold(unittest.TestCase):
    def test_the_companion_thinks_through_the_shared_think(self):
        c = code('aw_companion.c')
        self.assertIn('int AW_FollowThink(aw_follow_t *f,', c)
        self.assertIn('void AW_FollowStart(aw_follow_t *f,', c)
        think = body(c, 'static void think(edict_t *e,edict_t *p,float dt) {')
        self.assertIn('AW_FollowThink(&c.f,e,p,at,&r,dt);', think)
        self.assertIn('r.distance=AW_CompanionDistance();', think)        # its debug switches stay
        self.assertIn('r.mimic=AW_CompanionMimic();', think)
        self.assertIn('r.kind=companion_kind();', think)
        self.assertIn('r.place=1;', think)

    def test_the_packages_move_through_the_shared_think(self):
        a = code('aw_ambient.c')
        for head in ('static void follow_think(slot_t *s,float dt) {', 'static void escort_think(slot_t *s,float dt) {'):
            b = body(a, head)
            self.assertIn('follower_of(s)', b)
            self.assertIn('aw_ambient_follow_think(f,e,', b)
            self.assertIn('r.place=0;', b)                               # no placement inside a cell (OpenMW)
            self.assertIn('r.mimic=0;', b)
            # the slot's own walk stays only as the fallback when the pool is full or the hooks are not set
            self.assertLess(b.index('aw_ambient_follow_think'), b.rindex('walk(s,dt);'))
        self.assertIn('#define FOLLOWERS 8', a)
        self.assertIn('aw_ambient_follow_think=AW_FollowThink;', a)
        self.assertIn('aw_ambient_follow_start=AW_FollowStart;', a)
        # a new package starts a fresh follow state
        self.assertIn('s->follower=0;', body(a, 'int AW_AmbientFollow(edict_t *e,edict_t *target,float hours,'))
        self.assertIn('s->follower=0;', body(a, 'int AW_AmbientPackage(edict_t *e,edict_t *target,int kind,'))

    def test_one_follow_state_per_follower(self):
        h = (SRC / 'aw_follow.h').read_text(encoding='utf-8')
        self.assertIn('aw_path_t path;', h)
        c = code('aw_companion.c')
        self.assertIn('aw_follow_t f;', c)
        # the companion's state no longer carries its own path or stuck counters
        self.assertNotRegex(c, r'\bc\.(path|anchor|stuck|heavy|cooldown|teleport)\b')


if __name__ == '__main__':
    unittest.main()
