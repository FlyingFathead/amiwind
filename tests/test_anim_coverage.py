"""Every humanoid animation group hooked up (ANIM-GROUPS-NOT-HOOKED-54, docs/ANIMKIT.md "Every group hooked up").

The gate: every group of the default humanoid tables (tests/aga_animpick_groups.h, the names of progs/humanoid.awsk
and progs/humanoid_kna.awsk) is in the engine's catalogue with a hook; every "pick:" row comes out of the engine's
group choice for some state (tests/aga_animpick_test.c, OpenMW's rules case by case); every other row's hook is
in the source; the engine places the picked frame only around the send; the coverage tool reports a table's groups."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(Path(__file__).resolve().parent)]
import anim_coverage  # noqa: E402
import test_aga_native_source as native  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'
GROUPS = ROOT / 'tests' / 'aga_animpick_groups.h'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']


def fixture_groups():
    import re
    text = GROUPS.read_text(encoding='utf-8')
    return re.findall(r'"([^"]+)"', text[text.index('table_groups[]={'):])


def code(name):
    return (SRC / name).read_text(encoding='utf-8')


def awsk(groups, keys=()):
    """A minimal AWSK table (engine aw_skel.h layout): one bone, the GROUPS one frame each, KEYS (group, text)."""
    head = struct.pack('>4sHHIffHH', b'AWSK', 2, 1, len(groups), 8.0, 1.0, len(groups), len(keys))
    body = struct.pack('>h', -1) + b'\0\0' + bytes([0, 0, 0, 0])
    body += b''.join(struct.pack('>24sII', g.encode(), i, i) for i, g in enumerate(groups))
    body += b''.join(struct.pack('>32sHHI', t.encode(), groups.index(g), 0, groups.index(g)) for g, t in keys)
    return head + body


class Coverage(unittest.TestCase):
    def test_every_table_group_is_catalogued_and_reached_by_the_rules(self):
        # the C proof: OpenMW's rules case by case, then every "pick:" row reachable, every view row by its name
        native.NativeSourceTests().compile_run('aga_animpick_test.c', [SRC / 'aw_animkit_rules.c', SRC / 'aw_anim.c'],
                                               defines=['AW_ANIM_HOST_TEST'], cflags=UBSAN)

    def test_catalogue_is_exactly_the_tables_groups(self):
        rows = anim_coverage.catalogue()
        names = [n for n, _ in rows]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(sorted(names), sorted(fixture_groups()))
        self.assertGreaterEqual(len(names), 146)
        for name, hook in rows:
            self.assertRegex(hook, r'^(pick|layer|keys|view|combat): ', name)

    def test_rows_hooked_outside_the_rules_have_their_hook_in_the_source(self):
        hooks = dict(anim_coverage.catalogue())
        # torch: the left arm's layer while a light is carried (aw_items.c, the guards' torches)
        self.assertIn('AW_SkelGroup(tab,"torch")', code('aw_items.c'))
        self.assertTrue(hooks['torch'].startswith('layer: '))
        # idlestorm: the arm layer facing a storm (aw_items.c, the storm pose)
        self.assertIn('AW_SkelGroup(tab,"idlestorm")', code('aw_items.c'))
        self.assertTrue(hooks['idlestorm'].startswith('layer: '))
        # the beast file's second spellcast place: its keys are looked up there (key_frame, name_2 ...)
        kit = code('aw_animkit.c')
        self.assertIn('snprintf(name,sizeof(name),"%s_%d",gg.name,i)', kit)
        # the views: a woman's own groups and an NPC's own file answer the plain name first (AW_SkelGroup prefix)
        self.assertIn('prefix', code('aw_skel.h'))
        self.assertIn('aw_idle_base', (ROOT / 'engine/aga/qc/world.qc').read_text(encoding='utf-8'))
        # the dodge: the walkleft/walkright loops sampled as dodgel/dodger, played by combat
        self.assertIn("'dodgel': ('walkleft'", (ROOT / 'tools/skeletal_actor.py').read_text(encoding='utf-8'))
        self.assertIn('AW_ANIM_DODGEL', code('aw_combat.c'))

    def test_picked_frame_only_around_the_send(self):
        server = code('sv_main.c')
        body = server[server.index('void SV_SendClientMessages (void)'):]
        body = body[:body.index('\n}\n')]
        self.assertLess(body.index('AW_AnimPickPreSend ();'), body.index('SV_UpdateToReliableMessages ();'))
        self.assertLess(body.index('for (i=0, host_client'), body.index('AW_AnimPickPostSend ();'))
        # the drivers never see a changed frame: saved before, given back after
        self.assertIn('p->saved=e->v.frame;e->v.frame=(float)out;p->applied=1;', code('aw_animkit.c'))
        self.assertIn('if(p->e && !p->e->free)p->e->v.frame=p->saved;', code('aw_animkit.c'))
        # the previous method stays: dbg animkit pick off (no new command or setting: the resident registry budget)
        self.assertIn('static int pick_on=1;', code('aw_animkit.c'))
        self.assertIn('if(argc>=2 && !strcmp(argv[1],"pick")){pick_command();return;}', code('aw_animkit.c'))
        # no new engine source: the Makefile is an input of the world's heap-check key (STAGE-CONTENT-KEYS)
        self.assertIn('#include "aw_animpick_rules.inc"', code('aw_animkit_rules.c'))
        self.assertNotIn('aw_animpick', (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8'))

    def test_state_inputs_come_from_the_game(self):
        kit = code('aw_animkit.c')
        for item in ('AW_CombatAttackType(e)', 'AW_MwscriptWeaponType(e)', 'f->knocked==2',
                     'AW_PickWanderIdle(p->chances', 'AW_PE_EQUIP', 'AW_PE_UNEQUIP'):
            self.assertIn(item, kit)
        self.assertIn('int AW_CombatAttackType(edict_t *e)', code('aw_combat.c'))
        self.assertIn('int AW_ActorWeaponType(int row)', code('aw_actorstate.c'))
        self.assertIn('int AW_MwscriptWeaponType(struct edict_s *e)', code('aw_mwhost.c'))
        catalogue = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8')
        self.assertRegex(catalogue, r'(?m)^PLAYTESTING\|animkit\|aw_animkit_cmd\|.*/ pick \[on/off / cast / sneak / idle\]')
        self.assertNotIn('aw_animpick_cmd', kit + catalogue)


class Tool(unittest.TestCase):
    def test_report_marks_never_played_and_pending(self):
        groups = ['idle', 'walkforward', 'idle3', 'spellcast', 'moonwalk']
        data = awsk(groups, [('spellcast', 'self start')])
        names, keys = anim_coverage.table_groups(data)
        self.assertEqual(names, groups)
        self.assertEqual(keys, {'spellcast': ['self start']})
        rep = anim_coverage.report({'t.awsk': data})
        self.assertEqual(rep['never_played'], ['moonwalk'])
        by = {g['group']: g for g in rep['groups']}
        self.assertTrue(by['idle']['hooked'] and not by['idle']['pending_caller'])
        self.assertIn('ambient wander tables', by['idle3']['pending_caller'])
        self.assertIn('AW_AnimPickCast', by['spellcast']['pending_caller'])
        self.assertIn('knockdown', rep['absent_from_tables'])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 't.awsk'
            path.write_bytes(data)
            out = Path(tmp) / 'r.md'
            self.assertEqual(anim_coverage.main([str(path), '--markdown', str(out)]), 0)
            self.assertEqual(anim_coverage.main([str(path), '--check']), 1)
            self.assertIn('**NEVER PLAYED**', out.read_text(encoding='utf-8'))
        with self.assertRaises(ValueError):
            anim_coverage.table_groups(b'XXXX' + data[4:])

    def test_tool_ships_and_is_documented(self):
        import json
        files = json.loads((ROOT / 'tools/release-files.json').read_text(encoding='utf-8'))
        for path in ('tools/anim_coverage.py', 'engine/aga/src/aw_animpick.h', 'engine/aga/src/aw_animpick_rules.inc'):
            self.assertIn(path, files)
        page = (ROOT / 'docs/ANIMKIT.md').read_text(encoding='utf-8')
        for item in ('## Every group hooked up', 'tools/anim_coverage.py', 'dbg animkit pick', 'dbg animkit pick off',
                     'character.cpp'):
            self.assertIn(item, page)


if __name__ == '__main__':
    unittest.main()
