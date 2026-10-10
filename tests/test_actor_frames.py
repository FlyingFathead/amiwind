"""Actor model frame layouts in one place (tools/actor_frames.py, ANIMKIT-ACTOR-ABI-SITES-35).

An animation kit model (idle + walk + run ...) and the previous 8-frame idle and 21-frame town actor models
go through every site that reads actor frames: the ground check, the guard torch companions, the item tag
tables and the payload preflight. The sweep test keeps hard-coded actor frame counts out of every other file.
"""
import re
import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

import actor_frames
from actor_frames import of_model, parse, audit_payload, UndeclaredLayout
from player_hull import pack_lumps

ROOT = Path(__file__).resolve().parents[1]
KIT = 'idle:0:8:0.3333 walk:8:8:0.1333:24.63 run:16:6:0.1556:50.56 @walk:2:right ~left:a.wav:b.wav:c.wav !attack:0123456789012345:rg80'


def header_only(frames):
    """An alias model header (numframes at byte 68) and nothing else: enough for the frame-count sites."""
    return struct.pack('<4si3f3ff3f8if', b'IDPO', 6, 1, 1, 1, 0, 0, 0, 4, 0, 0, 0, 1, 4, 4, 3, 1, frames, 0, 0, 1)


def bsp(entities):
    chunks = [b'' for _ in range(15)]
    chunks[0] = ('{\n"classname" "worldspawn"\n}\n' + entities).encode()
    return pack_lumps(chunks)


def npc(model, classname='aw_npc', intro=None):
    return ('{\n"classname" "%s"\n"model" "%s"\n' % (classname, model) +
            ('"aw_intro_role" "%s"\n' % intro if intro else '') + '}\n')


class LayoutTests(unittest.TestCase):
    def test_kit_model_groups_from_its_layout(self):
        layout = of_model(22, KIT)
        self.assertEqual(layout.kind, 'kit')
        self.assertEqual(layout.idle, (0, 8))
        self.assertEqual(layout.group('walk'), (8, 8))
        self.assertEqual(layout.group('run'), (16, 6))
        self.assertIsNone(layout.group('talk'))
        self.assertEqual(list(layout.idle_range()), list(range(8)))
        self.assertEqual(parse(KIT + ' >progs/a_m.mdl')[1], 'progs/a_m.mdl')

    def test_previous_layouts_are_explicit(self):
        self.assertEqual(of_model(8).kind, 'idle')
        self.assertEqual(of_model(8).idle, (0, 8))
        actor = of_model(21)
        self.assertEqual((actor.kind, actor.idle, actor.group('talk'), actor.group('blink'), actor.group('walk')),
                         ('actor', (0, 8), (8, 4), (12, 1), (13, 8)))
        self.assertEqual(of_model(21, intro=True).kind, 'actor')
        self.assertEqual(of_model(1, dead=True).kind, 'dead')
        with self.assertRaisesRegex(UndeclaredLayout, 'Undeclared'):
            of_model(1)

    def test_undeclared_layouts_fail_never_skip(self):
        with self.assertRaisesRegex(UndeclaredLayout, 'Undeclared ground-resident pose layout'):
            of_model(17)
        with self.assertRaisesRegex(UndeclaredLayout, 'Unexpected intro pose layout'):
            of_model(8, intro=True)
        with self.assertRaisesRegex(ValueError, 'without an idle group'):
            of_model(22, 'walk:8:8:0.1')
        with self.assertRaisesRegex(ValueError, 'run group outside'):
            of_model(20, KIT)
        with self.assertRaisesRegex(ValueError, 'frame count outside'):
            of_model(65)
        with self.assertRaisesRegex(ValueError, 'repeats'):
            parse('idle:0:8:1 idle:8:8:1')

    def test_kit_profiles_fit_the_helper(self):
        # Every configured kit profile: idle first, 8 frames (the QuakeC idle cycle), at most MAX_FRAMES.
        import npc_anim
        for name, groups in npc_anim.profiles().items():
            self.assertEqual(tuple(groups[0]), ('idle', actor_frames.IDLE_FRAMES), name)
            self.assertLessEqual(sum(c for _, c in groups), actor_frames.MAX_FRAMES, name)
            layout = ' '.join('%s:%d:%d:0.1' % (g, sum(c for _, c in groups[:i]), c) for i, (g, c) in enumerate(groups))
            self.assertEqual(of_model(sum(c for _, c in groups), layout).idle, (0, 8))


class GroundCheckTests(unittest.TestCase):
    def test_contact_samples_take_the_idle_group_of_every_layout(self):
        from check_actor_ground import contact_samples
        idle = [[(0, 0, 0), (2, 0, 0), (0, 2, 0)]] * 8
        up = [[(0, 0, 4), (2, 0, 4), (0, 2, 4)]]
        kit = idle + up * 14
        samples = contact_samples(kit, (0, 0, 0), layout=KIT)
        self.assertEqual({tuple(sorted(set(f))) for f in samples.values()}, {tuple(range(8))})
        self.assertEqual(samples, contact_samples(idle, (0, 0, 0)))                          # legacy 8
        self.assertEqual(samples, contact_samples(idle + up * 13, (0, 0, 0), intro=True))     # legacy 21 intro
        with self.assertRaisesRegex(ValueError, 'Undeclared'):
            contact_samples(kit, (0, 0, 0))


class GuardTorchTests(unittest.TestCase):
    def model(self, frames):
        from npc_geometry import animated_mdl
        points = np.zeros((frames, 3, 3)); points[:, 1, 0] = 1; points[:, 2, 1] = 1
        skin = Image.new('P', (16, 16))
        return animated_mdl(points, np.array([[0, 1, 2]]), np.array([[0, 0], [8, 0], [0, 8]]), skin)

    def test_guard_companion_frame_layouts(self):
        from prepare_guard_torches import _body, registry
        with self.assertRaisesRegex(ValueError, 'Undeclared'):
            _body(None, {}, None, self.model(17), bytes(768))
        with self.assertRaisesRegex(ValueError, 'must start with the 8-frame idle group'):
            _body(None, {}, None, self.model(17), bytes(768), 'death:0:6:0.3 idle:6:8:0.3 hit:14:3:0.3')
        # The registry keeps the engine's 8 / 21 companion frames (aw_guard_torch.c); a kit guard's companion
        # is its 8-frame idle group.
        row = dict(source_id='guard', base_model='progs/a.mdl', body_model='progs/gt_b_a.mdl',
                   torch_model='progs/gt_t_a.mdl', auto_inventory_eligible=True, frames=17, emitters=[[0, 0, 0]] * 17)
        with self.assertRaisesRegex(ValueError, 'Invalid guard frame'):
            registry([row])
        self.assertTrue(registry([dict(row, frames=8, emitters=[[0, 0, 0]] * 8)]))


class ItemTagTests(unittest.TestCase):
    def test_mover_tag_written_beside_the_mover(self):
        import npc_items
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp)
            (id1 / 'progs').mkdir()
            record = {'model': 'progs/a.mdl', '_item_tag': 'AWTG1 17\n', '_items': {},
                      '_mover_item_tag': 'AWTG1 64\n', 'anim': {'mover': {'model': 'progs/a_m.mdl'}}}
            npc_items.publish(id1, record)
            self.assertEqual(actor_frames.tag_frames((id1 / 'progs/a.tag').read_text()), 17)
            self.assertEqual(actor_frames.tag_frames((id1 / 'progs/a_m.tag').read_text()), 64)
            self.assertIn('mover_tag_sha256', record['items'])

    def test_resident_tags_follow_the_model_frames(self):
        # build_resident: the standing model's tag uses the standing frames, the mover's its own.
        source = (ROOT / 'tools/prepare_area.py').read_text(encoding='utf-8')
        self.assertIn('item_times=np.asarray(standing_index,dtype=float)', source)
        self.assertIn('mover_item_times=np.asarray(mover_index,dtype=float)', source)
        engine = (ROOT / 'engine/aga/src/aw_items.c').read_text(encoding='utf-8')
        self.assertIn('prep(sv.models[i],a->mover,sv.models[i]->numframes);', engine)
        self.assertIn('static int frames_match(model_t *m,int t)', engine)


class PayloadAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.id1 = Path(self.tmp.name)
        (self.id1 / 'maps').mkdir(); (self.id1 / 'progs').mkdir()

    def put(self, name, frames, layout=None, tag=None):
        (self.id1 / name).write_bytes(header_only(frames))
        if layout is not None:
            (self.id1 / name).with_suffix('.anm').write_text(layout + '\n')
        if tag is not None:
            (self.id1 / name).with_suffix('.tag').write_text('AWTG1 %d\nweapon -\nshield -\n' % tag)

    def test_kit_and_previous_models_pass(self):
        self.put('progs/kit.mdl', 17, 'idle:0:8:0.3 hit:8:3:0.3 death:11:6:0.3 >progs/kit_m.mdl', tag=17)
        self.put('progs/kit_m.mdl', 22, KIT, tag=22)
        self.put('progs/old.mdl', 8, tag=8)
        self.put('progs/intro.mdl', 21)
        self.put('progs/dead.mdl', 1)
        (self.id1 / 'maps/a.bsp').write_bytes(bsp(npc('progs/kit.mdl') + npc('progs/old.mdl') +
                                                  npc('progs/intro.mdl', intro='1') + npc('progs/old.mdl', 'aw_corpse') +
                                                  npc('progs/dead.mdl', 'aw_corpse')))
        self.assertEqual(audit_payload(self.id1), {'actor_models': 4, 'layouts': 2, 'item_tags': 3, 'other_maps': 0})

    def test_every_problem_is_listed(self):
        self.put('progs/kit.mdl', 17, 'idle:0:8:0.3 hit:8:3:0.3 death:11:6:0.3 >progs/gone_m.mdl', tag=64)
        self.put('progs/bad.mdl', 17)
        self.put('progs/late.mdl', 17, 'hit:0:3:0.3 idle:3:8:0.3 death:11:6:0.3')
        (self.id1 / 'maps/a.bsp').write_bytes(bsp(npc('progs/kit.mdl') + npc('progs/bad.mdl') + npc('progs/late.mdl')))
        with self.assertRaises(ValueError) as caught:
            audit_payload(self.id1)
        text = str(caught.exception)
        for part in ('progs/bad.mdl (17 frames): Undeclared', 'idle group at frames 0..7', 'mover progs/gone_m.mdl missing',
                     'item tags have 64 rows for 17 model frames'):
            self.assertIn(part, text)
        # a map the image removes is not checked; the layout and tag files still are
        with self.assertRaisesRegex(ValueError, '^2 actor frame'):
            audit_payload(self.id1, removed_maps={'maps/a.bsp'})

    def test_preflight_runs_it(self):
        source = (ROOT / 'tools/payload_preflight.py').read_text(encoding='utf-8')
        self.assertIn("('actor-frames', lambda: check_actor_frames(id1, removed))", source)


# Every site that reads an actor model's frame count or frame indices, with its verdict (the sweep table in
# docs/bugs/ANIMKIT-ACTOR-ABI-SITES-35.md). A new hard-coded actor frame count outside tools/actor_frames.py
# fails here: ask actor_frames instead, or add the site with its reason.
SWEEP = re.compile(r'(?:\b(?:len\(frames\)|count|frames|nf|numframes|n)\s*(?:!=|==|not in|in)\s*\(?\s*(?:8\s*,\s*21|21\b|8\b(?!\s*[,+*]))'
                   r'|\b(?:n|numframes)\s*>=\s*(?:21\b|8\b(?!\s*[+*]))'
                   r'|frames\[:8\]|\b13\.\.20\b|base\[G_RUN\]=13)')
ALLOWED = {
    # producers of the previous layouts (they write the 21-frame town actor / 8 idle models)
    'tools/npc_faces.py', 'tools/prepare_intro.py',
    # engine readers with an explicit previous-layout default beside the kit layout (aw_anim.c)
    'engine/aga/src/aw_anim.c', 'engine/aga/src/aw_combat.c', 'engine/aga/src/aw_companion.c',
    # the 21-frame town actor's talk poses only (np_ intro models), never a kit model
    'engine/aga/src/aw_speech.c',
    # guard companion registry: companions are 8 (idle, kit idle group) or 21 frames by construction
    'engine/aga/src/aw_guard_torch.c', 'tools/guard_torch_heap.py',
    # the helper itself
    'tools/actor_frames.py',
}


class SweepTests(unittest.TestCase):
    def test_no_hard_coded_actor_frame_counts_outside_the_helper(self):
        found = set()
        for pattern in ('tools/*.py', 'tools/chim/*.py', 'src/**/*.py', 'engine/aga/src/*.c', 'engine/aga/qc/*.qc'):
            for path in ROOT.glob(pattern):
                text = path.read_text(encoding='utf-8', errors='replace')
                if SWEEP.search(text):
                    found.add(path.relative_to(ROOT).as_posix())
        self.assertEqual(sorted(found - ALLOWED), [], 'hard-coded actor frame counts: use tools/actor_frames.py')

    def test_qc_idle_cycle_matches_the_helper(self):
        # world.qc aw_npc_idle plays frames 0..7; the payload preflight requires every aw_npc model's idle
        # group there (actor_frames.audit_payload).
        qc = (ROOT / 'engine/aga/qc/world.qc').read_text(encoding='utf-8')
        self.assertIn('if (self.frame >= 8) self.frame = 0;', qc)
        self.assertEqual(actor_frames.IDLE_FRAMES, 8)


if __name__ == '__main__':
    unittest.main()
