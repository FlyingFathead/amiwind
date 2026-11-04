# SPDX-License-Identifier: GPL-3.0-only
"""The ambient table (tools/ambient_lut.py, AWAM1) and its engine reader (engine/aga/src/aw_ambient.c pure part):
the Wander rules of OpenMW's aiwander.cpp on a synthetic master (allowed points within the distance and in the
closest point's strongly connected part, the one-point case, one-way links, the idle roll), the routes followed
hop by hop, and the C reader agreeing with the builder on every row, point, hop and idle profile."""
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import ambient_lut as A  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'


def sub(tag, data):
    return tag.encode() + struct.pack('<I', len(data)) + data


def rec(tag, subs, flags=0):
    body = b''.join(subs)
    return tag.encode() + struct.pack('<III', len(body), 0, flags) + body


def z(text, size=None):
    b = text.encode('latin-1') + b'\0'
    return b if size is None else b.ljust(size, b'\0')


def npc(ident, distance, idles=(0,) * 8, script='', tag='NPC_', first=None, cflags=0):
    subs = [sub('NAME', z(ident))]
    if script:
        subs.append(sub('SCRI', z(script)))
    if tag == 'CREA':
        subs.append(sub('FLAG', struct.pack('<I', cflags)))
    if first:
        subs.append(sub(first, b'\0' * 48))
    subs.append(sub('AI_W', struct.pack('<HHB', distance, 5, 0) + bytes(idles) + b'\x01'))
    return rec(tag, subs)


def levc(ident, entries, flags=1, chance=0):
    subs = [sub('NAME', z(ident)), sub('DATA', struct.pack('<I', flags)), sub('NNAM', bytes([chance])),
            sub('INDX', struct.pack('<I', len(entries)))]
    for name, level in entries:
        subs += [sub('CNAM', z(name)), sub('INTV', struct.pack('<H', level))]
    return rec('LEVC', subs)


def ref(number, ident, pos):
    return [sub('FRMR', struct.pack('<I', number)), sub('NAME', z(ident)),
            sub('DATA', struct.pack('<6f', *pos, 0, 0, 0))]


def cell(name, x, y, interior, refs):
    subs = [sub('NAME', z(name)), sub('DATA', struct.pack('<Iii', 1 if interior else 0, x, y))]
    for r in refs:
        subs += r
    return rec('CELL', subs)


def pgrd(name, x, y, points, links):
    """points [(x, y, z)], links {i: [j..]}"""
    pg = b''.join(struct.pack('<iiiBBH', *p, 0, len(links.get(i, ())), 0) for i, p in enumerate(points))
    pc = b''.join(struct.pack('<I', j) for i in range(len(points)) for j in links.get(i, ()))
    return rec('PGRD', [sub('DATA', struct.pack('<iiHH', x, y, 256, len(points))), sub('NAME', z(name)),
                        sub('PGRP', pg), sub('PGRC', pc)])


def master():
    """An interior with a chain of points 0-1-2-3 (two-way), a one-way spur 3->4 (4 cannot come back: another
    strongly connected part), and a far point 5; residents: a wanderer at point 0, a stationary one, one with a
    single point in reach, one whose first package is Travel, a scripted one; an exterior cell without a grid."""
    pts = [(0, 0, 0), (200, 0, 0), (400, 0, 0), (600, 0, 0), (800, 0, 0), (5000, 0, 0)]
    links = {0: [1], 1: [0, 2], 2: [1, 3], 3: [2, 4], 4: [], 5: []}
    gm = rec('GMST', [sub('NAME', z('fIdleChanceMultiplier')), sub('FLTV', struct.pack('<f', 0.75))])
    script = rec('SCPT', [sub('SCHD', z('scr_far', 32) + b'\0' * 20),
                          sub('SCTX', b'begin scr_far\n"Walker"->AiWander 900 0 0 40 20 20 0 0 0 0 0 0\nend\n')])
    out = rec('TES3', [sub('HEDR', b'\0' * 300)]) + gm + script
    out += npc('Walker', 700, (60, 20, 0, 0, 0, 0, 0, 0))
    out += npc('Stander', 0, (40, 20, 20, 0, 0, 0, 0, 0))
    out += npc('Single', 100)
    out += npc('Traveller', 300, first='AI_T')
    out += npc('Bird', 500, tag='CREA', cflags=0x20)
    out += npc('Crab', 200, (30, 0, 0, 0, 0, 0, 0, 0), tag='CREA')
    out += npc('Rat', 0, tag='CREA', first='AI_T')       # first package Travel: no package row
    out += levc('lev_inner', [('Crab', 1)])
    out += levc('lev_wild', [('Bird', 1), ('lev_inner', 3), ('Rat', 5)])
    out += cell('Test Room', 0, 0, True, [ref(7, 'Walker', (10, 0, 0)), ref(3, 'Stander', (400, 0, 0)),
                                         ref(9, 'Single', (590, 20, 0)), ref(11, 'Traveller', (0, 0, 0)),
                                         ref(12, 'Bird', (0, 0, 0)), ref(30, 'lev_wild', (200, 0, 0))])
    out += pgrd('Test Room', 0, 0, pts, links)
    out += cell('', 2, -3, False, [ref(20, 'Walker', (2 * 8192 + 100, -3 * 8192 + 100, 50))])
    return out


def follow(rowpts, hops, width, start, goal):
    at = start; seen = 0
    while at != goal:
        at = hops[at * width + goal]; seen += 1
        assert at != 255 and seen < 50
    return seen


class AmbientTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw, cls.report = A.build_master(master())
        cls.head, cls.rows, cls.points, cls.hops, cls.profiles = A.read_table(cls.raw)

    def row(self, ref):
        return next(r for r in self.rows if r['ref'] == ref)

    def blob(self, r):
        pts = self.points[r['first_point']:r['first_point'] + r['points']]
        hops = self.hops[r['first_hop']:r['first_hop'] + r['points'] * r['destinations']]
        return pts, hops

    def test_rows_sorted_and_only_wander_first(self):
        refs = [r['ref'] for r in self.rows]
        self.assertEqual(refs, sorted(refs))
        self.assertNotIn(11, refs)                          # its first package is Travel
        self.assertEqual(self.report['first_package']['travel'], 1)
        self.assertEqual(self.row(7)['hash'], A.fnv('walker'))
        self.assertTrue(self.row(12)['flags'] & A.F_FLYER)

    def test_allowed_points_follow_distance_and_strong_parts(self):
        r = self.row(7)                                     # radius 900 from the script (record 700)
        self.assertEqual(r['distance'], 700)
        pts, hops = self.blob(r)
        grid = [p for p in pts[:r['destinations']] if p[3] == A.K_GRID]
        xs = sorted(p[0] for p in grid)
        # points 0..3 (x 0..600, offsets -2..148); point 4 is one-way (another part); point 5 is too far
        self.assertEqual(xs, [-2, 48, 98, 148])
        self.assertEqual(self.report['counts']['scripted_radius'], 2)   # both placements of the scripted id

    def test_routes_reach_every_destination(self):
        r = self.row(7)
        pts, hops = self.blob(r)
        w = r['destinations']
        for a in range(w):
            for b in range(w):
                follow(pts, hops, w, a, b)
        # a route from the far end to the near end passes the middle points one by one
        far = max(range(w), key=lambda i: pts[i][0]); near = min(range(w), key=lambda i: pts[i][0])
        self.assertEqual(follow(pts, hops, w, far, near), 3)

    def test_one_point_case_adds_start_and_partway_points(self):
        r = self.row(9)                                     # distance 100: only point 3 (600,0) is in reach
        pts, hops = self.blob(r)
        kinds = sorted(p[3] for p in pts[:r['destinations']])
        self.assertEqual(kinds.count(A.K_GRID), 1)
        self.assertEqual(kinds.count(A.K_HOME), 1)
        self.assertEqual(kinds.count(A.K_PARTWAY), 2)       # links 3->2 and 3->4: max(100/2, 128) along each

    def test_no_grid_and_stationary(self):
        r = self.row(20)                                    # exterior without a grid: only its start
        self.assertEqual((r['points'], r['destinations']), (1, 1))
        self.assertEqual(self.points[r['first_point']][3], A.K_HOME)
        self.assertEqual(self.row(3)['distance'], 0)

    def test_levelled_reference_gets_routes_and_its_creatures_packages(self):
        # OpenMW 0.51: the picked creature runs its own record's packages (creaturelevlist.cpp, creature.cpp)
        routes = next(r for r in self.rows if r['ref'] == 30)
        self.assertEqual(routes['hash'], A.LEVELLED_HASH)
        self.assertTrue(routes['flags'] & A.F_LEVELLED)
        self.assertEqual(routes['distance'], 500)            # the largest Wander distance the list can give
        self.assertGreater(routes['destinations'], 1)        # grid points of the room within 500
        packages = {r['hash']: r for r in self.rows if r['ref'] == A.LEVELLED_REF}
        self.assertEqual(set(packages), {A.fnv('bird'), A.fnv('crab')})   # the nested list's Crab too; not Rat
        crab = packages[A.fnv('crab')]
        self.assertEqual((crab['distance'], crab['points'], crab['destinations']), (200, 1, 1))
        self.assertTrue(crab['flags'] & A.F_CREATURE)
        self.assertTrue(packages[A.fnv('bird')]['flags'] & A.F_FLYER)
        self.assertEqual(self.report['levelled'], {'references': 1, 'with_wander': 1, 'creatures': 2})

    def test_idle_profile(self):
        m = 49151                                           # 0.75
        self.assertEqual(A.idle_profile([0] * 8, m), [0] * 8)
        only = A.idle_profile([100, 0, 0, 0, 0, 0, 0, 0], m)
        self.assertAlmostEqual(only[0] / 65536, 0.75, places=3)
        self.assertEqual(len(set(only)), 1)
        # two equal chances split evenly; a larger chance wins more often
        even = A.idle_profile([50, 50, 0, 0, 0, 0, 0, 0], 65535)
        self.assertLess(abs(even[0] - (even[1] - even[0])), 70)
        self.assertGreater(A.idle_profile([80, 20] + [0] * 6, 65535)[0], 40000)
        # monte carlo of the original roll agrees within 1 %
        import random
        rnd = random.Random(5); c = [60, 20, 0, 30, 0, 0, 0, 10]; hits = [0] * 9; n = 40000
        for _ in range(n):
            best = 0; top = 0.0
            if rnd.random() <= 0.75:
                for i in range(8):
                    roll = rnd.random() * 100
                    if roll <= c[i] and roll > top:
                        best = i + 1; top = roll
            hits[best] += 1
        cdf = A.idle_profile(c, m); prev = 0
        for i in range(8):
            self.assertLess(abs((cdf[i] - prev) / 65536 - hits[i + 1] / n), 0.01)
            prev = cdf[i]


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class AmbientNativeTests(unittest.TestCase):
    def test_c_reader_agrees_with_the_builder(self):
        import test_aga_native_source as native
        raw, report = A.build_master(master())
        head, rows, points, hops, profiles = A.read_table(raw)
        with tempfile.TemporaryDirectory(prefix='ambient-native-') as tmp:
            table = Path(tmp) / A.NAME
            table.write_bytes(raw)
            lines = []
            for i, r in enumerate(rows):
                lines.append('row\t%d\t%d\t%d\t%d\t%d\t%d' % (r['ref'], r['hash'], i, r['points'], r['destinations'],
                                                             r['profile']))
                for k in range(r['points']):
                    p = points[r['first_point'] + k]
                    lines.append('point\t%d\t%d\t%d\t%d\t%d\t%d' % (i, k, p[0], p[1], p[2], p[3]))
                w = r['destinations']
                for a in range(r['points']):
                    for b in range(w):
                        h = hops[r['first_hop'] + a * w + b]
                        lines.append('hop\t%d\t%d\t%d\t%d' % (i, a, b, -1 if h == 255 else h))
            for k, prof in enumerate(profiles):
                lines.append('profile\t%d\t%s' % (k, '\t'.join(map(str, prof))))
            for c in ([60, 20, 0, 30, 0, 0, 0, 10], [100, 0, 0, 0, 0, 0, 0, 0], [40, 20, 20, 0, 0, 0, 0, 0],
                      [255, 3, 99, 1, 0, 50, 50, 7]):
                lines.append('idle\t%s\t%s' % ('\t'.join(map(str, c)),
                                               '\t'.join(map(str, A.idle_profile(c, head['multiplier'])))))
            lines.append('hash\tWalker\t%d' % A.fnv('walker'))
            lines.append('missing\t7\t%d' % A.fnv('nobody'))
            crab = next(r for r in rows if r['ref'] == A.LEVELLED_REF and r['hash'] == A.fnv('crab'))
            lines.append('levelled\t30\t%d\t%d\t%d\t%d\t%d' % (A.fnv('crab'), crab['distance'], crab['duration'],
                                                            crab['flags'] | A.F_LEVELLED, crab['profile']))
            (Path(tmp) / 'expect.tsv').write_text('\n'.join(lines) + '\n', encoding='utf-8')
            native.NativeSourceTests().compile_run(
                'aga_ambient_test.c', [SRC / 'aw_ambient.c'], defines=['AW_AMBIENT_HOST_TEST'],
                cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'],
                arguments=[str(table), str(Path(tmp) / 'expect.tsv')])

    def test_c_reader_reads_the_per_area_tables(self):
        """AMBIENT-WALK-PER-AREA-60: every table of npc-ambient.awa (the shared levelled packages and each area's) is a
        whole AWAM1 table the engine's reader opens and answers from, as aw_ambient.c amb_open does."""
        import test_aga_native_source as native
        import prepare_area_tables as P
        raw, _ = A.build_master(master())
        refs = sorted({r['ref'] for r in A.read_table(raw)[1] if r['ref']})
        keys_of = {x: 7 if k % 2 == 0 else 0x80000001 for k, x in enumerate(refs)}
        payload, _ = P.build_ambient(keys_of, raw)
        n, shared_at, shared_bytes = struct.unpack_from('<III', payload, 4)
        tables = [payload[shared_at:shared_at + shared_bytes]]
        for i in range(n):
            _, at, size = struct.unpack_from('<III', payload, 16 + 12 * i)
            tables.append(payload[at:at + size])
        with tempfile.TemporaryDirectory(prefix='ambient-areas-native-') as tmp:
            for k, t in enumerate(tables):
                head, rows, points, hops, profiles = A.read_table(t)
                lines = []
                for i, r in enumerate(rows):
                    lines.append('row\t%d\t%d\t%d\t%d\t%d\t%d' % (r['ref'], r['hash'], i, r['points'], r['destinations'],
                                                                 r['profile']))
                    for j in range(r['points']):
                        p = points[r['first_point'] + j]
                        lines.append('point\t%d\t%d\t%d\t%d\t%d\t%d' % (i, j, p[0], p[1], p[2], p[3]))
                    w = r['destinations']
                    for a in range(r['points']):
                        for b in range(w):
                            h = hops[r['first_hop'] + a * w + b]
                            lines.append('hop\t%d\t%d\t%d\t%d' % (i, a, b, -1 if h == 255 else h))
                for j, prof in enumerate(profiles):
                    lines.append('profile\t%d\t%s' % (j, '\t'.join(map(str, prof))))
                (Path(tmp) / ('t%d.lut' % k)).write_bytes(t)
                (Path(tmp) / ('e%d.tsv' % k)).write_text('\n'.join(lines) + '\n', encoding='utf-8')
                native.NativeSourceTests().compile_run(
                    'aga_ambient_test.c', [SRC / 'aw_ambient.c'], defines=['AW_AMBIENT_HOST_TEST'],
                    cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'],
                    arguments=[str(Path(tmp) / ('t%d.lut' % k)), str(Path(tmp) / ('e%d.tsv' % k)), 'area'])


class AmbientAreasTests(unittest.TestCase):
    """AMBIENT-WALK-PER-AREA-60: tools/prepare_area_tables.py build_ambient splits npc-ambient.lut per area."""

    def test_split_keeps_every_package_byte(self):
        import prepare_area_tables as P
        raw, _ = A.build_master(master())
        mult, rows, profiles = P.read_awam(raw)
        refs = sorted({f[0] for f, _, _ in rows if f[0]})
        self.assertGreaterEqual(len(refs), 2)
        keys_of = {refs[0]: 7, 999999: 11}
        keys_of.update({x: 9 for x in refs[1:]})
        payload, report = P.build_ambient(keys_of, raw)
        self.assertEqual(payload[:4], b'AWM1')
        n, shared_at, shared_bytes = struct.unpack_from('<III', payload, 4)
        self.assertEqual(n, 2)                                  # the room with no package gets no table
        keys = [struct.unpack_from('<I', payload, 16 + 12 * i)[0] for i in range(n)]
        self.assertEqual(keys, [7, 9])
        smult, srows, _ = P.read_awam(payload[shared_at:shared_at + shared_bytes])
        self.assertEqual(smult, mult)
        self.assertEqual(sorted(f[1] for f, _, _ in srows), sorted(f[1] for f, _, _ in rows if f[0] == 0))
        seen = []
        for i in range(n):
            _, at, size = struct.unpack_from('<III', payload, 16 + 12 * i)
            m2, arows, aprof = P.read_awam(payload[at:at + size])
            for f, pts, hop in arows:
                orig = next(o for o in rows if o[0][0] == f[0] and o[0][1] == f[1])
                self.assertEqual(f[:8], orig[0][:8])
                self.assertEqual((pts, hop), (orig[1], orig[2]))
                self.assertEqual(aprof[f[10]], profiles[orig[0][10]])
                seen.append((f[0], f[1]))
        self.assertEqual(sorted(seen), sorted((f[0], f[1]) for f, _, _ in rows if f[0]))
        self.assertEqual(report['refs_not_in_any_area'], 0)

    def test_places_name_every_placement(self):
        import prepare_area_tables as P
        from prepare_focus import exterior_key
        raw, report = A.build_master(master())
        self.assertEqual({int(r) for r in report['places']}, {r['ref'] for r in A.read_table(raw)[1] if r['ref']})
        self.assertEqual(P.area_keys({'5': ['e', -2, -9], '6': ['i', 'x room'], '8': ['i', 'no number']},
                                     {'x room': 42}), {5: exterior_key(-2, -9), 6: 42})

    def test_wired_behind_the_cvar(self):
        c = re.sub(r'/\*.*?\*/', '', (SRC / 'aw_ambient.c').read_text(encoding='utf-8'), flags=re.S)
        self.assertIn('{"aw_ambient_areas","1"}', c)
        self.assertIn('AW_AreaPlaceKeys(keys,AMB_AREAS,&gen)', c)
        self.assertIn('if(!m && !load())return;', c)            # aw_ambient_areas 0: the island-wide file as before
        b = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("aw_ambient_areas 1\\n", b)
        self.assertIn('ambient_table_step(', b)
        self.assertIn('stage_ambient(id1,', (ROOT / 'tools/ambient_lut.py').read_text(encoding='utf-8'))


class AmbientSourceContractTests(unittest.TestCase):
    def code(self, name):
        return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)

    def test_default_on_wired_and_listed(self):
        c = self.code('aw_ambient.c')
        self.assertIn('static int ambient_on=1;', c)        # on by default since v0.0.57, no cvar or command of its own
        self.assertIn('chim actors ambient on', (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8'))
        self.assertNotRegex(c, r'Cmd_AddCommand')
        # its one cvar: the per-area tables' A/B switch (AMBIENT-WALK-PER-AREA-60)
        self.assertEqual(re.findall(r'Cvar_RegisterVariable\s*\(([^)]*)\)', c), ['&ambient_areas_cvar'])
        self.assertIn('aw_ambient_cmd ();', self.code('aw_actors.c'))
        self.assertIn('aw_ambient_cmd=AW_AmbientCommand;', c)
        self.assertIn('AW_CombatSlotState', c)              # combat owns a fighting actor
        self.assertIn('ACTOR_RANGE', c)
        self.assertIn('aw_ambient.c', (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8'))
        self.assertIn('AW_AmbientPhysics', self.code('sv_phys.c'))
        self.assertIn('AW_AmbientInit', self.code('aw_debug.c'))
        self.assertIn('ambient_table_step', (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8'))

    def test_levelled_index_and_aggro_wired(self):
        c = self.code('aw_ambient.c')
        # levelled creatures: own id first, then the reference's routes with the creature's package
        self.assertIn('find_in(ref,AW_AMBIENT_LEVELLED_HASH,r,&found_t)', c)
        self.assertIn('find_in(AW_AMBIENT_LEVELLED_REF,hash,&pkg,&found_prof)', c)
        # the rows stay on disk: one key per block resident, a block read per lookup, absent actors remembered
        self.assertIn('resident_size=blocks*8+', c)
        self.assertNotIn('AW_AmbientOpen(&table', c)
        self.assertIn('none_ref[i]==ref', c)
        # aggro on sight in the world: the combat layer's rule, on the engage timer, 4 fighters; a creature's disposition
        # bias at 50, an NPC's from its derived disposition (DIALOGUE-FIGHT-DISPOSITION-57)
        self.assertIn('AW_CombatAggro(s->e,&sheet,NULL,disposition,NULL,NULL)', c)
        self.assertIn('AW_CombatFightRating(&aw_combat_ai,s->fight,disposition,', c)
        self.assertIn('if(npc)disposition=AW_DialNpcDisposition(s->e,&s->disp);', c)
        self.assertIn('static int aggro_on=1;', c)
        self.assertIn('AW_AMBIENT_CREATURE', c)
        # flyers wander off the ground: a straight 3D sweep, no floor test, one failed step ends the walk;
        # swimmers swim too (v0.0.57): no path grid, random spots near the start that are in water, never out of it
        self.assertIn('AW_AmbientAllow(&s->pkg,r.distance);', c)
        self.assertIn('if(!AW_AmbientInWater(at))', c)
        self.assertIn('(!AW_Interior() && p[2]<0)', c)   # outdoors below the sea level is water (CHIM seas)
        self.assertIn('(s->flags&AW_AMBIENT_SWIMMER) && !AW_AmbientInWater(tr.endpos)', c)
        self.assertIn('tr=SV_Move(e->v.origin,e->v.mins,e->v.maxs,end,MOVE_NORMAL,e);', c)
        self.assertRegex(c, r'if\(fly\(s,t3,speed\*dt\)\)')

    def test_no_stale_edict_after_a_map_change(self):
        # ACTOR-AMBIENT-STALE-EDICT-57: a teleport to another map crashed with "NUM_FOR_EDICT: bad pointer" when a
        # script asked for an actor's package while the slots still held the old map's edicts
        c = self.code('aw_ambient.c')
        self.assertIn('if(slots_world!=sv.worldmodel)reset_all();', c.split('static slot_t *slot_for')[1][:300])
        release = c.split('static void release')[1].split('static void reset_all')[0]
        self.assertNotIn('NUM_FOR_EDICT', release)
        self.assertIn('slots_world==sv.worldmodel', release)

    def test_flying_fighter_chases_through_the_air(self):
        # COMBAT-FLYER-FLEES-57: a hostile cliff racer fled ("cannot reach you") because the chase used the ground
        # route; a flyer now sweeps straight toward the player in 3D (OpenMW aipackage.cpp pathTo shortcut) and
        # never takes the unreachable-target flee; walkers keep the ground chase
        c = self.code('aw_combat.c')
        flyer = c.split('if(AW_AmbientFlags(s->e)&(AW_AMBIENT_FLYER|AW_AMBIENT_SWIMMER)){')[1].split('self[0]=')[0]
        self.assertIn('SV_Move(fe->v.origin,fe->v.mins,fe->v.maxs,end,MOVE_NORMAL,fe)', flyer)
        self.assertIn('return;', flyer)
        self.assertNotIn('S_FLEE', flyer)
        self.assertIn('AW_AmbientInWater(tr.endpos)', flyer)   # a fighting swimmer stays in water
        self.assertLess(c.index('AW_AmbientFlags(s->e)&(AW_AMBIENT_FLYER|AW_AMBIENT_SWIMMER)'), c.index('AW_PathThink(&s->path,&io,self,goal'))
        a = self.code('aw_ambient.c')
        self.assertIn('int AW_AmbientFlags(edict_t *e)', a)

    def test_fallen_fighters_free_their_slots(self):
        # COMBAT-PACK-SLOTS-57: four corpses kept every combat slot, so a fifth hostile of a pack never attacked; a
        # fallen fighter's slot is reused, its death handed to the actors' change list first (no respawn alive)
        c = self.code('aw_combat.c')
        engage = c.split('int AW_CombatEngage(edict_t *e,const aw_fighter_t *fighter,const char *layout) {')[1][:900]
        self.assertIn('slots[i].f.dead || slots[i].state==S_DEAD', engage)
        self.assertLess(engage.index('aw_combat_actor_died(slots[i].e)'), engage.index('release(&slots[i])'))
        a = self.code('aw_actors.c')
        self.assertIn('aw_combat_actor_died = Died;', a)
        self.assertIn('c->dead = 1;', a.split('static void Died (edict_t *e)')[1][:200])

    def test_no_search_at_run_time(self):
        c = self.code('aw_ambient.c')
        for word in ('aStar', 'dijkstra', 'heap', 'queue'):
            self.assertNotIn(word, c.lower())


if __name__ == '__main__':
    unittest.main()
