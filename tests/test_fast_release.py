# SPDX-License-Identifier: GPL-3.0-only
"""CHIM-ROOM-HEART-CHAMBER-LOAD-50: the releasers of re-makeable session memory (engine/aga/src/aw_fastrelease.c).

Before a large block is sized from the free Fast RAM, the engine gives back what it holds and can make again (the
skeletal animation tables and posed frames first): one registry, at most AW_FAST_RELEASERS releasers, run in order
with one console line each. It is called where a large allocation is sized from the free Fast RAM (the automatic CHIM
cache banks, -chimcache, a room's growth), never from a per-frame path. The registry runs natively here with a
stubbed console; the call sites are checked in the sources."""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine/aga/src'
COMPILER = os.environ.get('CC') or shutil.which('cc') or shutil.which('gcc')

DRIVER = r'''
#include <stdarg.h>
#include <stdio.h>
#include "aw_fastrelease.h"
void Con_Printf (char *fmt, ...) { va_list a; va_start (a, fmt); vprintf (fmt, a); va_end (a); }
static int order[16], calls;
static unsigned long r1 (void) { order[calls++] = 1; return 3 * 1024; }
static unsigned long r2 (void) { order[calls++] = 2; return 0; }
static unsigned long r3 (void) { order[calls++] = 3; return 5 * 1024; }
static unsigned long f4 (void) { return 0; }
static unsigned long f5 (void) { return 0; }
static unsigned long f6 (void) { return 0; }
static unsigned long f7 (void) { return 0; }
static unsigned long f8 (void) { return 0; }
static unsigned long f9 (void) { return 0; }
static aw_fast_release_t more[] = {f4, f5, f6, f7, f8, f9};
int main (void)
{
	int i, full = 0;
	printf ("empty %lu %d\n", AW_FastReleaseAll ("t"), AW_FastReleasers ());
	{	/* one statement each: argument order is unspecified */
		int a = AW_FastReleaseRegister ("one", r1), b, c, d;
		b = AW_FastReleaseRegister ("two", r2);
		c = AW_FastReleaseRegister ("three", r3);
		d = AW_FastReleaseRegister ("one again", r1);
		printf ("reg %d %d %d %d\n", a, b, c, d);
	}
	printf ("null %d\n", AW_FastReleaseRegister ("none", 0));
	printf ("count %d\n", AW_FastReleasers ());
	printf ("total %lu\n", AW_FastReleaseAll ("a room's models"));
	printf ("order");
	for (i=0 ; i<calls ; i++)
		printf (" %d", order[i]);
	printf ("\n");
	/* the table holds AW_FAST_RELEASERS (8): five more fill it, the sixth is refused */
	for (i=0 ; i<6 ; i++)
		full += AW_FastReleaseRegister ("more", more[i]);
	printf ("filled %d count %d\n", full, AW_FastReleasers ());
	return 0;
}
'''


@unittest.skipUnless(COMPILER, 'no host C compiler')
class Registry(unittest.TestCase):
    def run_driver(self):
        with tempfile.TemporaryDirectory() as tmp:
            driver = Path(tmp) / 'driver.c'
            driver.write_text(DRIVER, encoding='utf-8')
            exe = Path(tmp) / 'driver'
            subprocess.run([COMPILER, '-std=gnu99', '-Wall', '-Werror', '-I', str(SRC), str(driver),
                            str(SRC / 'aw_fastrelease.c'), '-o', str(exe)], check=True)
            return subprocess.run([str(exe)], check=True, capture_output=True, text=True).stdout

    def test_releasers_run_in_order_once_each_with_one_line_per_release(self):
        out = self.run_driver()
        self.assertIn('empty 0 0\n', out)
        self.assertIn('reg 1 1 1 1\n', out)              # the same function again: kept once, renamed
        self.assertIn('null 0\n', out)
        self.assertIn('count 3\n', out)
        self.assertIn('total 8192\n', out)
        self.assertIn('order 1 2 3\n', out)
        # one line per releaser that gave something back (none for 0 bytes), named by its latest registration
        lines = [l for l in out.splitlines() if l.startswith('Fast RAM for ')]
        self.assertEqual(lines, [
            "Fast RAM for a room's models: one again gave back 3 KiB; free 0 -> 0 KiB, largest block 0 -> 0 KiB",
            "Fast RAM for a room's models: three gave back 5 KiB; free 0 -> 0 KiB, largest block 0 -> 0 KiB"])
        self.assertIn('filled 5 count 8\n', out)

    def test_the_table_is_fixed(self):
        header = (SRC / 'aw_fastrelease.h').read_text(encoding='utf-8')
        self.assertIn('#define AW_FAST_RELEASERS\t8', header)


class CallSites(unittest.TestCase):
    """Called where a large block is sized from the free Fast RAM, never from a per-frame path."""

    def calls(self):
        out = {}
        for path in sorted(SRC.rglob('*.c')):
            text = path.read_text(encoding='utf-8', errors='replace')
            for m in re.finditer(r'AW_FastReleaseAll \("([^"]*)"\)', text):
                out.setdefault(path.relative_to(SRC).as_posix(), []).append(m.group(1))
        return out

    def test_the_callers_are_the_large_block_sizings(self):
        self.assertEqual(self.calls(), {'chim/chim_world.c': ['a room\'s models', '-chimcache',
                                                              'the CHIM cache banks']})
        world = (SRC / 'chim/chim_world.c').read_text(encoding='utf-8')
        grow = world[world.index('int Chim_RoomGrow (const char *name)'):]
        self.assertLess(grow.index('AW_FastReleaseAll ("a room\'s models")'), grow.index('ChimZone_RoomStep ('))
        start = world[world.index('static void Chim_MemoryStart (void)'):]
        self.assertLess(start.index('AW_FastReleaseAll ("the CHIM cache banks")'),
                        start.index('memory_free = chim_fast_avail ? chim_fast_avail (0) : 0;'))
        bank = world[world.index('static void CacheBank (void)'):]
        self.assertLess(bank.index('AW_FastReleaseAll ("-chimcache")'), bank.index('AvailMem (MEMF_FAST|MEMF_LARGEST)'))

    def test_every_largest_block_sizing_is_known(self):
        # a new AvailMem(...MEMF_LARGEST) sizing must decide whether it releases first (and join the list above)
        known = {'aw_skel_load.c': 'a table load: the releaser\'s own consumer',
                 'aw_tryalloc.c': 'every checked allocation: per-frame paths too',
                 'aw_fastrelease.c': 'the registry\'s own console line',
                 'chim/chim_world.c': 'the cache banks and a room: released first',
                 'sys_amiga.c': 'the heap at start-up, before anything is held',
                 'zone.c': 'a report'}
        found = set()
        for path in sorted(SRC.rglob('*.c')):
            if 'MEMF_LARGEST' in path.read_text(encoding='utf-8', errors='replace'):
                found.add(path.relative_to(SRC).as_posix())
        self.assertEqual(found, set(known))

    def test_the_skeletal_memory_is_the_first_releaser(self):
        release = (SRC / 'aw_skel_release.c').read_text(encoding='utf-8')
        self.assertIn('AW_FastReleaseRegister ("animation tables and posed frames", AW_SkelReleaseAll);', release)
        self.assertNotIn('chim_fast_release', (SRC / 'chim/chim_world.c').read_text(encoding='utf-8'))
        makefile = (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8')
        self.assertIn(' aw_fastrelease.c ', makefile)


if __name__ == '__main__':
    unittest.main()
