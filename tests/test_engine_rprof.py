# SPDX-License-Identifier: GPL-3.0-only
"""dbg rcount 3/4 ("rprof" line): the brush-model slot split into BSP clip walk and fragment emit, the
distance band x model size table and leaves per placement (engine/aga/src/aw_rcount.c).

The counters are a measurement tool: default off, and below aw_rcount 3 nothing is timed, binned or
counted beyond one integer test per site, so the frame is the same as without them. It has no console
variable of its own (resident registry budget, ENGINE-RESIDENT-REGISTRY-GROWTH-36): aw_rcount 3 and 4. These host tests
pin that contract in the source; the frames themselves are compared in the emulator (same pose, same
image, counters off against the engine without them).
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'


def read(name):
    return (SRC / name).read_text(encoding='latin-1')


class RProfContractTests(unittest.TestCase):
    def test_default_off_and_no_new_variable(self):
        text = read('aw_rcount.c')
        self.assertIn('static cvar_t aw_rcount_cvar = {"aw_rcount", "0"};', text)
        self.assertNotIn('aw_rprof_cvar', text)
        self.assertEqual(text.count('Cvar_RegisterVariable'), 1)
        # the switch follows aw_rcount 3/4, only while connected, and only with the EClock open
        self.assertRegex(text, r'int on = aw_rcount_cvar\.value >= 3 && cls\.state == ca_connected && TimerBase')
        self.assertIn('aw_rprof_on = on;', text)
        self.assertIn('if (aw_rcount_cvar.value >= 4)\n        Con_Printf("rprof %s\\n", rp_line);', text)
        self.assertIn('if (aw_rcount_cvar.value < 2 || aw_rcount_cvar.value >= 4)', text)

    def test_timers_only_while_on(self):
        header = read('aw_rcount.h')
        amiga = header.split('#ifdef AMIGA\nextern int aw_rprof_on;', 1)[1].split('#else', 1)[0]
        self.assertIn('#define AW_RP_BEGIN(t0) ((t0) = aw_rprof_on ? AW_RProfTicks() : 0)', amiga)
        self.assertIn('if (aw_rprof_on) { aw_rprof_ticks[slot]', amiga)
        host = header.split('#define aw_rprof_on 0', 1)[1].split('#endif', 1)[0]
        self.assertIn('#define AW_RProfModel(o, r, f, s, l, v) ((void)0)', host)

    def test_walk_and_emit_sites(self):
        bsp = read('r_bsp.c')
        emit = bsp.index('R_RenderBmodelFace (psideedges[i], psurf);')
        self.assertIn('if (aw_rprof_on)', bsp[emit - 300:emit])
        self.assertIn('AW_RP_END(RP_EMIT, rp_t0);', bsp[emit:emit + 120])
        # the unprofiled call is the original one, unchanged
        self.assertIn('else\n\t\t\t\t\t\t\tR_RenderBmodelFace (psideedges[i], psurf);', bsp)
        self.assertIn('AW_RP_END(RP_CLIP, rp_t0);', bsp)
        self.assertIn('else\n\t\t\t\t\tR_RecursiveClipBPoly (pbedge, currententity->topnode, psurf);', bsp)

    def test_model_table_and_leaves_only_while_on(self):
        main = read('r_main.c')
        body = main[main.index('void R_DrawBEntitiesOnList'):]
        body = body[:body.index('\n}\n')]
        self.assertIn('if (aw_rprof_on)\n\t\t\t\t\t\t\tR_RProfCountLeaves', body)
        self.assertIn('if (aw_rprof_on)\n\t\t\t\t\tAW_RProfModel', body)
        self.assertIn('AW_RP_END(RP_PASS, rp_t0);', body)
        self.assertIn('AW_RP_END(RP_ONELEAF, rp_t1);', body)

    def test_clock_cost_correction(self):
        text = read('aw_rcount.c')
        # a timer's own reads cost r; every read nested in it 2r (the emit inside the clip walk,
        # all three inside the pass)
        self.assertIn('emit = rp_ticks[RP_EMIT] - r * rp_pairs[RP_EMIT];', text)
        self.assertIn('clip = rp_ticks[RP_CLIP] - r * rp_pairs[RP_CLIP] - 2 * r * rp_pairs[RP_EMIT];', text)
        self.assertIn('pass = rp_ticks[RP_PASS] - r * rp_pairs[RP_PASS] - 2 * r * nested;', text)
        self.assertIn('RP_CAL_READS', text)

    def test_line_fields_and_remote_state(self):
        text = read('aw_rcount.c')
        for field in ('| r ', 'walk ', 'emit ', 'oneleaf ', 'setup ', 'added ', 'so ', 'eo '):
            self.assertIn(field, text)
        for table in ('"hp"', '"hf"', '"hs"', ' | lv '):
            self.assertIn(table, text)
        self.assertEqual(re.findall(r'#define RP_(BANDS|SIZES) (\d)', read('aw_rcount.h')),
                         [('BANDS', '5'), ('SIZES', '4')])
        self.assertIn('fprintf(f,"rprof %s\\n",AW_RProfLine());', read('aw_remote.c'))

    def test_console_catalogue_and_docs(self):
        rows = [line.split('|') for line in (ROOT / 'config' / 'debug-commands.txt').read_text().splitlines()]
        rcount = [row for row in rows if row[:3] == ['DIAGNOSTICS', 'rcount', 'aw_rcount']]
        self.assertEqual(len(rcount), 1)
        self.assertIn('[0/1/2/3/4]', rcount[0][3])
        self.assertNotIn('aw_rprof', [row[2] for row in rows if len(row) > 2])
        page = (ROOT / 'docs' / 'performance' / 'RENDERER-COUNTERS.md').read_text(encoding='utf-8')
        self.assertIn('## The brush-model profile (`dbg rcount 3`)', page)
        for field in ('`walk` / `nodes`', '`emit` / `frag`', '`hp`, `hf`, `hs`', '`lv`'):
            self.assertIn(field, page)


if __name__ == '__main__':
    unittest.main()
