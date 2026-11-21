# SPDX-License-Identifier: GPL-3.0-only
"""GHOSTFENCE-PARTICLES-NOT-DRAWN-68 (v0.0.68): the Ghostfence pylons' glow and the blight cloud's plume
(world/glow.awg, glow.spr) and the curtain's own scroll (world/curtain.awc, engine aw_curtain.c): the tables against the
engine's readers, the plume bake on a made-up particle system, the pylon pairs and the hide row of every row, the
curtain's motion against its keys, the engine's compose against the builder's Python twin natively, and the wiring
(the settings and their defaults, the catalogue, the image step). The real records are checked by the image step
itself (ghostfence_effects.write: check_glow) and by `tools/ghostfence_effects.py measure` on the game data."""
import json
import math
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
for _p in (ROOT / 'tools', ROOT / 'src'):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ghostfence_effects as G  # noqa: E402

GREY = bytes(v for i in range(256) for v in (i, i, i))


def code(name):
    return (SRC / name).read_text(encoding='utf-8')


def system(additive=True):
    """A made-up particle system: an emitter at the model's origin throwing along +X (its local Z turned onto X, as the
    Ghostfence's emitter node), a wind of 100 pulling down, 30 particles a second living one second, 20 units big."""
    import numpy as np
    turn = np.eye(4)
    turn[:3, :3] = [[0, 0, -1], [0, 1, 0], [1, 0, 0]]
    return {'speed': 200.0, 'speed_random': 20.0, 'vertical': (0.0, 0.5), 'horizontal': (1.57, 1.0), 'size': 20.0,
            'rate': 30.0, 'lifetime': 1.0, 'lifetime_random': 0.0, 'box': (0.0, 0.0, 0.0), 'emitter': turn,
            'particles': turn, 'winds': [(100.0, (1.0, 0.0, 0.0))], 'point_forces': 0, 'grow': 0.05, 'fade': 0.3,
            'colours': None if additive else [(0.0, (0.0, 0.0, 0.0, 1.0)), (1.0, (1.0, 1.0, 1.0, 0.0))],
            'texture': 'made_up', 'additive': additive}


def disc(n=8):
    import numpy as np
    y, x = np.mgrid[0:n, 0:n]
    r = np.hypot(x - (n - 1) / 2, y - (n - 1) / 2) / (n / 2)
    out = np.zeros((n, n, 4))
    out[:, :, :3] = (0.8, 0.9, 1.0)
    out[:, :, 3] = np.clip(1 - r, 0, 1) * 0.25
    return out


class TableLayout(unittest.TestCase):
    def test_the_glow_row_is_the_engines(self):
        self.assertEqual(G.GLOW_ROW.size, 28)
        atmos = code('aw_atmos.c')
        self.assertIn('#define GLOW_ROW %d' % G.GLOW_ROW.size, atmos)
        self.assertIn('#define GLOW_PATH "%s"' % G.GLOW_TABLE, atmos)
        self.assertIn('#define GLOW_SPRITE "%s"' % G.GLOW_SPRITE, atmos)
        self.assertIn('!memcmp(head,"AWG1",4)', atmos)
        # the engine's field offsets: width at 16, first frame 21, frames 22, phase 23, reference 24
        for fmt, at in (('<hh3f', 16), ('<hh3fHHB', 21), ('<hh3fHHBB', 22), ('<hh3fHHBBB', 23), ('<hh3fHHBBBB', 24)):
            self.assertEqual(struct.calcsize(fmt), at)
        self.assertIn('g->width=(float)(row[16]|(row[17]<<8));', atmos)
        self.assertIn('g->frame0=row[21];g->frames=row[22];g->phase=row[23];g->reference=le32(row+24);', atmos)
        rows = [(-1, 9, -4000.0, 75000.0, 9000.0, 437, 724, 1, 0, 4, 17, 123456),
                (2, 8, 20000.0, 66000.0, 12000.0, 2550, 3226, 2, 4, 4, 200, 244899)]
        back = G.read_glow_table(G.glow_table(rows))
        self.assertEqual([r['reference'] for r in back], [123456, 244899])
        self.assertEqual(back[1]['frame0'], 4)

    def test_the_curtain_head_is_the_engines(self):
        self.assertEqual(G.CURTAIN_HEAD.size, 28)
        header = code('aw_curtain.h')
        self.assertIn('#define AW_CURTAIN_HEAD\t\t%d' % G.CURTAIN_HEAD.size, header)
        self.assertIn('#define AW_CURTAIN_SIZE\t\t%d' % G.CURTAIN_SIZE, header)
        self.assertIn('#define AW_CURTAIN_STEPS\t%d' % G.CURTAIN_STEPS, header)
        self.assertIn('#define AW_CURTAIN_MAGIC\t"%s"' % G.CURTAIN_MAGIC.decode('ascii'), header)
        self.assertIn('#define CURTAIN_PATH\t"%s"' % G.CURTAIN_TABLE, code('aw_curtain.c'))


class PylonPairs(unittest.TestCase):
    @staticmethod
    def rows():
        out = []
        for k in range(3):
            for side in (-1, 1):
                out.append((0, 0, 4000.0 * k + side * 225, 0.0, 9000.0, 400, 700, 1, 0, 4, 0, 100 + 2 * k + (side > 0)))
        out.append((0, 1, 9000.0, 9000.0, 12000.0, 2500, 3200, 2, 4, 4, 0, 244899))
        return out

    def test_every_pylon_has_its_two_plumes(self):
        pairs, alone = G.pylon_pairs(self.rows())
        self.assertEqual(len(pairs), 3)
        self.assertEqual(alone, [])
        self.assertEqual(G.check_glow(self.rows()), [])

    def test_a_lone_plume_a_missing_and_a_repeated_reference_are_refused(self):
        rows = self.rows() + [(0, 0, 30000.0, 0.0, 9000.0, 400, 700, 1, 0, 4, 0, 999)]
        self.assertIn('1 Ghostfence plumes without the other of their pylon: 999', '; '.join(G.check_glow(rows)))
        rows = self.rows()
        rows[0] = rows[0][:11] + (0,)
        self.assertIn('1 glow rows without a reference', G.check_glow(rows))
        rows = self.rows()
        rows[1] = rows[1][:11] + (rows[0][11],)
        self.assertIn('a reference on two glow rows', G.check_glow(rows))


class Bake(unittest.TestCase):
    def test_a_plume_is_baked_into_frames_beside_and_below_its_emitter(self):
        b = G.bake(system(), disc(), GREY, 11)
        again = G.bake(system(), disc(), GREY, 11)
        self.assertEqual(b['frames'], again['frames'])                      # the same build, the same sprite
        self.assertEqual(len(b['frames']), G.GLOW_FRAMES)
        for w, h, pixels in b['frames']:
            self.assertLessEqual(max(w, h), G.GLOW_SPRITE_SIZE)
            self.assertEqual(len(pixels), w * h)
        self.assertTrue(all(v > 0 for v in b['visible']))
        self.assertEqual(b['particles'], 30)                                # birth rate x life
        cx, _, cz = b['centre']
        self.assertGreater(cx, 0)                                           # thrown along +X
        self.assertLess(cz, 0)                                              # and bent down by the wind
        self.assertTrue(all(math.isfinite(v) for v in b['centre']))
        self.assertLessEqual(b['width'], b['box'][0] + 1e-6)                # cut to what any frame shows

    def test_a_blended_plume_with_colour_keys_bakes_too(self):
        b = G.bake(system(additive=False), disc(), GREY, 12)
        self.assertTrue(all(v > 0 for v in b['visible']))

    def test_the_sprite_holds_every_frame(self):
        frames = [(4, 6, bytes(24)), (8, 2, bytes(16))]
        raw = G.sprite_bytes(frames)
        ident, version, kind, _, w, h, n, _, _ = struct.unpack_from('<4siifiiifi', raw)
        self.assertEqual((ident, version, kind, w, h, n), (b'IDSP', 1, 2, 8, 6, 2))
        self.assertEqual(struct.unpack_from('<5i', raw, 36), (0, -2, 3, 4, 6))
        self.assertEqual(len(raw), 36 + 20 + 24 + 20 + 16)


class CurtainMotion(unittest.TestCase):
    SWAY = [(0.0, 0.0, -0.0, 0.1), (2.0, 0.05, 0.0, 0.0), (4.0, 0.0, -0.1, -0.1), (6.0, -0.05, 0.0, 0.0),
            (8.0, 0.0, 0.1, 0.1)]

    def test_keys_are_read_as_openmw_reads_quadratic_keys(self):
        for t, v, _, _ in self.SWAY:
            self.assertAlmostEqual(G.key_value(self.SWAY, t), v)
        linear = [(0.0, 0.0, 2.0, 2.0), (8.0, 2.0, 2.0, 2.0)]
        for t in (0.0, 1.0, 2.5, 8.0):
            self.assertAlmostEqual(G.key_value(linear, t), t / 4)
        a, b = self.SWAY[0], self.SWAY[1]
        x = 0.25
        expect = (a[1] * (2 * x ** 3 - 3 * x ** 2 + 1) + b[1] * (-2 * x ** 3 + 3 * x ** 2) + a[3] * (x ** 3 - 2 * x ** 2 + x)
                  + b[2] * (x ** 3 - x ** 2))
        self.assertAlmostEqual(G.key_value(self.SWAY, 0.5), expect)

    def test_the_tables_are_the_keys_in_texels(self):
        layers = [{'texture': 'a', 'u': self.SWAY, 'v': [(0.0, 0.0, 2.0, 2.0), (8.0, 2.0, 2.0, 2.0)], 'start': 0.0,
                   'stop': 8.0},
                  {'texture': 'b', 'u': [], 'v': [(0.0, 0.0, 1.0, 1.0), (8.0, 1.0, 1.0, 1.0)], 'start': 0.0, 'stop': 8.0}]
        motion = G.motion_tables(layers, ['a', 'b'], 8.0)
        self.assertEqual([m[0] for m in motion], [0, 1])
        (_, us, vs), (_, us2, vs2) = motion
        self.assertEqual(len(us), G.CURTAIN_STEPS)
        self.assertEqual(vs, [k % G.CURTAIN_SIZE for k in range(G.CURTAIN_STEPS)])      # 2 heights in 8 s
        self.assertEqual(vs2, [k // 2 for k in range(G.CURTAIN_STEPS)])                 # 1 height in 8 s
        self.assertEqual(us[16], round(0.05 * G.CURTAIN_SIZE))                           # the sway's top at 2 s
        self.assertEqual(us[48], round(-0.05 * G.CURTAIN_SIZE))
        self.assertEqual(us2, [0] * G.CURTAIN_STEPS)

    def test_the_ramp_never_names_the_transparent_or_a_sky_bank_index(self):
        from sky_palette_overlay import BANK
        ramp = G.ramp_indices((0.55, 0.65, 0.8), 46, GREY, tuple(BANK))
        self.assertEqual(len(ramp), G.CURTAIN_PULSES * 46)
        self.assertFalse(set(ramp) & ({255} | set(BANK)))
        self.assertLess(ramp[0], ramp[45])                                               # dim to bright
        self.assertLessEqual(ramp[30], ramp[G.CURTAIN_PULSES * 46 - 16])                 # the pulse's top is brighter


NATIVE = r'''
#include <stdio.h>
#include <stdlib.h>
#include "aw_curtain.h"
static unsigned char raw[AW_CURTAIN_BYTES], out[AW_CURTAIN_SIZE*AW_CURTAIN_SIZE], block[AW_CURTAIN_DRAWN*AW_CURTAIN_DRAWN];
int main(int argc, char **argv) {
    FILE *f = fopen(argv[1], "rb"); size_t n; aw_curtain_t c; int i, k;
    if (!f) return 2;
    n = fread(raw, 1, sizeof(raw), f); fclose(f);
    printf("parse %d\n", AW_CurtainParse(raw, (unsigned long)n, &c));
    if (argc > 2 && argv[2][0] == 'h') {printf("hash %lu\n", AW_CurtainHash(raw, (unsigned long)n)); return 0;}
    for (i = 2; i < argc; i++) {
        unsigned long t = strtoul(argv[i], NULL, 10);
        AW_CurtainCompose(&c, t, out);
        printf("t %lu ", t);
        for (k = 0; k < AW_CURTAIN_SIZE*AW_CURTAIN_SIZE; k++) printf("%02x", out[k]);
        AW_CurtainBlock(out, AW_CURTAIN_SIZE, block);
        printf(" tiled %lu", AW_CurtainHash(block, sizeof(block)));
        AW_CurtainBlock(out, AW_CURTAIN_DRAWN, block);
        printf(" own %lu find %d\n", AW_CurtainHash(block, sizeof(block)), AW_CurtainFind(&c, c.hash[0]));
    }
    return 0;
}
'''


@unittest.skipUnless(shutil.which('cc'), 'no C compiler')
class NativeCompose(unittest.TestCase):
    """The engine's AW_CurtainCompose (aw_curtain_rules.c) against the builder's curtain_compose on a made-up table."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='aw-curtain-'))
        (cls.tmp / 't.c').write_text(NATIVE, encoding='utf-8')
        built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wshadow', '-fsanitize=undefined,address',
                                '-I', str(SRC), str(cls.tmp / 't.c'), str(SRC / 'aw_curtain_rules.c'), '-o',
                                str(cls.tmp / 't')], capture_output=True, text=True)
        assert built.returncode == 0, built.stdout + built.stderr
        rng = random.Random(68)
        size = G.CURTAIN_SIZE
        levels = [bytes(rng.randrange(16) for _ in range(size * size)) for _ in range(2)]
        motion = [(s, [rng.randrange(-3, 4) for _ in range(G.CURTAIN_STEPS)],
                   [rng.randrange(size) for _ in range(G.CURTAIN_STEPS)]) for s in (0, 1, 0)]
        ramp = bytes(rng.randrange(255) for _ in range(G.CURTAIN_PULSES * 46))
        cls.hashes = {0x1234ABCD: 32, 0x0BADF00D: 64}
        cls.raw = G.curtain_bytes(cls.hashes, levels, motion, 46, 8000, G.pulse_steps(), ramp)
        (cls.tmp / 'c.awc').write_bytes(cls.raw)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_native(self, *args, table='c.awc'):
        return subprocess.run([str(self.tmp / 't'), str(self.tmp / table)] + [str(a) for a in args],
                              capture_output=True, text=True, check=True).stdout.splitlines()

    @staticmethod
    def blocks(composed):
        size, drawn = G.CURTAIN_SIZE, G.DRAWN
        tiled = bytes(composed[(y % size) * size + x % size] for y in range(drawn) for x in range(drawn))
        own = bytes(composed[(y // 2) * size + x // 2] for y in range(drawn) for x in range(drawn))
        return G.fnv1a(tiled), G.fnv1a(own)

    def test_the_engine_composes_what_the_builder_composes(self):
        table = G.read_curtain_table(self.raw)
        times = (0, 1, 999, 2000, 4125, 7999, 8000, 123456, 4000000000)
        lines = self.run_native(*times)
        self.assertEqual(lines[0], 'parse 1')
        for t, line in zip(times, lines[1:]):
            composed = G.curtain_compose(table, t)
            tiled, own = self.blocks(composed)
            first = self.hashes[min(self.hashes)]                          # the table keeps its hashes sorted
            self.assertEqual(line, 't %d %s tiled %d own %d find %d' % (t, composed.hex(), tiled, own, first))

    def test_the_hash_is_the_builders(self):
        self.assertEqual(self.run_native('h'), ['parse 1', 'hash %d' % G.fnv1a(self.raw)])

    def test_a_short_or_wrong_table_is_refused(self):
        (self.tmp / 'short.awc').write_bytes(self.raw[:-1])
        self.assertEqual(self.run_native(table='short.awc')[0], 'parse 0')
        bad = bytearray(self.raw)
        at = G.CURTAIN_HEAD.size + 8 * len(self.hashes) + 2 * G.CURTAIN_SIZE * G.CURTAIN_SIZE
        bad[at] = 7                                                           # a layer naming a source not there
        (self.tmp / 'bad.awc').write_bytes(bytes(bad))
        self.assertEqual(self.run_native(table='bad.awc')[0], 'parse 0')
        loud = bytearray(self.raw)
        loud[G.CURTAIN_HEAD.size + 8 * len(self.hashes)] = 40                 # a level past what the ramp holds
        (self.tmp / 'loud.awc').write_bytes(bytes(loud))
        self.assertEqual(self.run_native(table='loud.awc')[0], 'parse 0')


class DrawnBlock(unittest.TestCase):
    def test_a_small_texture_is_hashed_as_the_loader_tiles_it(self):
        small = bytes(range(256)) * 4
        block = G.drawn_block(small, 32)
        self.assertEqual(len(block), 64 * 64)
        self.assertEqual(block[64 * 33 + 40], small[32 * 1 + 8])
        self.assertEqual(G.drawn_block(bytes(4096), 64), bytes(4096))
        self.assertIn('dst[y*dw + x] = src[(y % sh)*sw + x % sw];', (SRC / 'chim' / 'chim_format.c').read_text(
            encoding='utf-8'))


class Wiring(unittest.TestCase):
    def test_the_curtain_is_drawn_straight_from_its_own_block(self):
        edge = code('d_edge.c')
        self.assertIn('unsigned char *(*aw_curtain_block) (texture_t *tx);', edge)
        self.assertIn('own = aw_curtain_block ? aw_curtain_block (pface->texinfo->texture) : NULL;', edge)
        self.assertIn('cacheblock = (pixel_t *)own;', edge)
        self.assertIn('r_turb_sintable = stillturbtable;', edge)
        curtain = code('aw_curtain.c')
        self.assertIn('static cvar_t aw_curtain = {"aw_curtain", "0"};', curtain)       # today's ripple by default
        self.assertIn('aw_curtain_block = curtain_block;', curtain)
        self.assertNotIn('tx->offsets[0]) =', curtain)                                   # never writes a texture
        self.assertIn('AW_CurtainInit();', code('aw_atmos.c'))
        makefile = (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8')
        self.assertIn('aw_curtain_rules.c aw_curtain.c', makefile)

    def test_the_glow_settings_and_their_shipped_defaults(self):
        atmos = code('aw_atmos.c')
        defaults = {}
        for name in ('aw_glow', 'aw_glow_draw', 'aw_glow_range'):
            line = next(l for l in atmos.splitlines() if l.startswith('static cvar_t %s=' % name))
            defaults[name] = line.split('"')[3]
            self.assertNotIn('true', line)                                                # not saved
        curtain = next(l for l in code('aw_curtain.c').splitlines() if 'static cvar_t aw_curtain' in l)
        defaults['aw_curtain'] = curtain.split('"')[3]
        self.assertEqual(defaults, {'aw_glow': '0', 'aw_glow_draw': '8', 'aw_glow_range': '2048', 'aw_curtain': '0'})
        stated = dict(l.split() for l in G.GLOW_CONFIG_LINES.decode('ascii').splitlines() if not l.startswith('//'))
        self.assertEqual(stated, defaults)
        self.assertIn('if(AW_ObjectDisabled(glows[i].reference))continue;', atmos)        # the hide row
        self.assertIn('if(aw_glow.value)glow_update();', atmos)
        self.assertIn('"aw_glow"', code('aw_boolean.h'))
        catalogue = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        for line in ('VIDEO|glow|aw_glow|', 'VIDEO|glow draw|aw_glow_draw|', 'VIDEO|glow range|aw_glow_range|',
                     'VIDEO|curtain|aw_curtain|'):
            self.assertIn(line, catalogue)

    def test_the_image_step_writes_them_after_the_world_ui(self):
        aga = (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8')
        at = aga.index('    validate_world_ui(boot/\'id1\')\n    # The Ghostfence')
        self.assertLess(at, aga.index('    write_ghostfence(args,boot/\'id1\',out)'))
        files = json.loads((ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8'))
        for name in ('tools/ghostfence_effects.py', 'tests/test_ghostfence_effects.py', 'engine/aga/src/aw_curtain.c',
                     'engine/aga/src/aw_curtain.h', 'engine/aga/src/aw_curtain_rules.c'):
            self.assertIn(name, files)

    def test_without_game_data_only_the_settings_are_written(self):
        tmp = Path(tempfile.mkdtemp(prefix='aw-ghostfence-'))
        try:
            (tmp / 'id1').mkdir()
            (tmp / 'id1' / 'default-game.cfg').write_bytes(b'aw_mwscript 1')
            receipt = G.write(SimpleNamespace(data_files=None), tmp / 'id1', tmp)
            self.assertEqual(receipt['config'], ['aw_glow 0', 'aw_glow_draw 8', 'aw_glow_range 2048', 'aw_curtain 0'])
            text = (tmp / 'id1' / 'default-game.cfg').read_bytes()
            self.assertTrue(text.startswith(b'aw_mwscript 1\n//'))
            self.assertTrue(text.endswith(G.GLOW_CONFIG_LINES))
            self.assertFalse((tmp / 'id1' / 'world').exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
