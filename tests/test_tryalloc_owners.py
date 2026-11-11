# SPDX-License-Identifier: GPL-2.0-or-later
"""The per-asker block count of the checked allocators (engine/aga/src/aw_tryalloc.c, aw_memcensus owners;
ROOM-LOAD-KEEPS-EXTERIOR-CACHE-64), compiled for the host with a stub exec: blocks of 4 KiB or more are noted with their
asking address and forgotten on free, a free of a block never noted (every small one, the C library's own) does not
search the whole table, and the totals match the blocks still live after thousands of mixed allocations and frees."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'engine/aga/src'

EXEC = '''#define MEMF_PUBLIC 1
#define MEMF_FAST 4
#define MEMF_LARGEST 0x20000
'''
PROTO = '''static unsigned long AvailMem (unsigned long flags) {(void)flags; return 0x7fffffffUL;}
'''
DRIVER = r'''
#include <stdio.h>
#include <stdlib.h>
#include "aw_tryalloc.h"
/* two asking addresses: the helpers are not inlined, so each has its own */
__attribute__((noinline)) static void *ask_a (unsigned long n) {return AW_TryMalloc (n);}
__attribute__((noinline)) static void *ask_b (unsigned long n) {return AW_TryCalloc (1, n);}
int main (void)
{
	static void *live[5000];
	static unsigned long size[5000];
	unsigned long pc[24], bytes[24], blocks[24], total, dropped, want = 0, seed = 7;
	int i, n, k;
	void *before;
	/* off by default: a large block is not noted, and its free leaves the table as it was */
	before = ask_a (100000);
	n = AW_TryOwners (pc, bytes, blocks, 24, &total, &dropped);
	printf ("off %d %d total %lu\n", AW_TryOwnersOn (), n, total);
	free (before);
	AW_TryOwnersEnable (1);
	for (i=0 ; i<200000 ; i++)
	{
		seed = seed * 1103515245UL + 12345UL;
		k = (int)((seed >> 8) % 5000);
		if (live[k])
		{
			if (size[k] >= AW_TRYALLOC_OWNED)
				want -= size[k];
			free (live[k]);
			live[k] = NULL;
			continue;
		}
		size[k] = (seed >> 4) % 3 ? 16 + (seed >> 12) % 3000 : 4096 + (seed >> 12) % 60000;
		live[k] = (seed >> 20) & 1 ? ask_a (size[k]) : ask_b (size[k]);
		if (size[k] >= AW_TRYALLOC_OWNED)
			want += size[k];
	}
	n = AW_TryOwners (pc, bytes, blocks, 24, &total, &dropped);
	printf ("owners %d total %lu want %lu dropped %lu\n", n, total, want, dropped);
	for (k=0 ; k<n ; k++)
		printf ("pc %lx bytes %lu blocks %lu\n", pc[k], bytes[k], blocks[k]);
	for (k=0 ; k<5000 ; k++)
		free (live[k]);
	n = AW_TryOwners (pc, bytes, blocks, 24, &total, &dropped);
	printf ("after %d total %lu\n", n, total);
	/* switched off again: the table is forgotten, a new block is not noted */
	before = ask_a (100000);
	AW_TryOwnersEnable (0);
	free (before);
	before = ask_a (100000);
	n = AW_TryOwners (pc, bytes, blocks, 24, &total, &dropped);
	printf ("off again %d %d total %lu\n", AW_TryOwnersOn (), n, total);
	free (before);
	return 0;
}
'''


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class TryAllocOwners(unittest.TestCase):
    def test_owned_blocks_are_counted_and_forgotten(self):
        with tempfile.TemporaryDirectory() as scratch:
            s = Path(scratch)
            (s / 'proto').mkdir()
            (s / 'exec').mkdir()
            (s / 'proto/exec.h').write_text(PROTO)
            (s / 'exec/memory.h').write_text(EXEC)
            (s / 'driver.c').write_text(DRIVER)
            exe = s / 'owners'
            # the target side of aw_tryalloc.h (AMIGA and __m68k__), on the host with the stub exec
            built = subprocess.run(['cc', '-std=gnu89', '-O1', '-DAMIGA', '-D__m68k__', '-I' + str(s), '-I' + str(SOURCE),
                                    str(s / 'driver.c'), str(SOURCE / 'aw_tryalloc.c'), '-o', str(exe)],
                                   capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        lines = run.stdout.splitlines()
        # off by default (the shipped engine) and after owners off: nothing noted
        self.assertEqual(lines[0], 'off 0 0 total 0')
        self.assertEqual(lines[-1], 'off again 0 0 total 0')
        lines = lines[1:-1]
        head = lines[0].split()
        n, total, want, dropped = int(head[1]), int(head[3]), int(head[5]), int(head[7])
        self.assertEqual(dropped, 0)
        self.assertEqual(total, want)
        self.assertEqual(n, 2)                                   # the two asking addresses
        self.assertEqual(sum(int(l.split()[3]) for l in lines[1:1 + n]), total)
        self.assertEqual(lines[-1], 'after 0 total 0')         # every noted block forgotten on free


if __name__ == '__main__':
    unittest.main()
