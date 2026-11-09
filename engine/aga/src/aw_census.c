/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_census.c: dbg memcensus (HEART-CHAMBER-LOAD-HANG-62): exec's free Fast RAM and its largest block now, with the
 * map, and the Hunk in use, in one console line, so a session can take the measure at each step.
 * Counting every allocation by its owner by wrapping the C library's allocators (tried on 7 November 2026) does not
 * work on the target: the library's own allocations inside its archive are not wrapped, so a block without the
 * count's header reached the wrapped free, and the measuring engine stalled loading Balmora or did not start. */
#include "quakedef.h"
#if defined(AMIGA) && defined(__m68k__)
#include <proto/exec.h>
#include <exec/memory.h>
static unsigned long fast_free(int largest) {return AvailMem(MEMF_FAST | (largest ? MEMF_LARGEST : 0));}
#else
static unsigned long fast_free(int largest) {(void)largest;return 0;}
#endif

void AW_CensusInit(void);

static void census_command(void) {
    Con_Printf("Memory census (%s): Fast RAM free %lu KiB, largest block %lu KiB; Hunk %ld bytes low, %ld high\n",
        sv.active ? sv.name : "no map", fast_free(0) / 1024, fast_free(1) / 1024, (long)Hunk_LowMark(),
        (long)Hunk_HighMark());
}
void AW_CensusInit(void) {Cmd_AddCommand("aw_memcensus", census_command);}
