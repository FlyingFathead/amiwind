/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_census.c: dbg memcensus (HEART-CHAMBER-LOAD-HANG-62): exec's free Fast RAM and its largest block now, with the
 * map, and the Hunk in use, in one console line, so a session can take the measure at each step.
 * Counting every allocation by its owner by wrapping the C library's allocators (tried on 7 November 2026) does not
 * work on the target: the library's own allocations inside its archive are not wrapped, so a block without the
 * count's header reached the wrapped free, and the measuring engine stalled loading Balmora or did not start. */
#include "quakedef.h"
#include "aw_tryalloc.h"
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
#ifdef AW_TRYALLOC_CHECKED
    /* aw_memcensus owners (ROOM-LOAD-KEEPS-EXTERIOR-CACHE-64): the engine's live blocks of 4 KiB or more by the
     * address they were asked from, largest first; tools/map_pc.py names the function from the link map */
    if (Cmd_Argc() > 2 && !Q_strcasecmp(Cmd_Argv(1), "owners")) {
        /* off by default (the shipped engine): on starts the count, off stops it and forgets it */
        AW_TryOwnersEnable(!Q_strcasecmp(Cmd_Argv(2), "on") || !strcmp(Cmd_Argv(2), "1"));
        Con_Printf("Memory owners: the count is %s\n", AW_TryOwnersOn() ? "on (blocks from now on)" : "off");
        return;
    }
    if (Cmd_Argc() > 1 && !Q_strcasecmp(Cmd_Argv(1), "owners")) {
        static unsigned long pc[24], bytes[24], blocks[24];
        if (!AW_TryOwnersOn()) {
            Con_Printf("Memory owners: the count is off (aw_memcensus owners on)\n");
            return;
        }
        unsigned long total, dropped;
        int i, n = AW_TryOwners(pc, bytes, blocks, 24, &total, &dropped);
        Con_Printf("Memory owners (%s): %lu KiB live in blocks of 4 KiB or more, %d asking addresses%s\n",
            sv.active ? sv.name : "no map", total / 1024, n, dropped ? ", table full: some blocks not noted" : "");
        for (i = 0; i < n; i++)
            Con_Printf("  owner pc %08lx %7lu KiB in %lu blocks\n", pc[i], bytes[i] / 1024, blocks[i]);
    }
#endif
}
void AW_CensusInit(void) {
    Cmd_AddCommand("aw_memcensus", census_command);
#ifdef AW_TRYALLOC_CHECKED
    {
        /* A measuring session's play copy only (a file awowners.on written into its game folder): the count is
         * on before the first map loads, so the blocks a town takes on its first load are seen. No shipped image has the
         * file: the count stays off there. */
        int handle;
        if (Sys_FileOpenRead(va("%s/awowners.on", com_gamedir), &handle) >= 0) {
            Sys_FileClose(handle);
            AW_TryOwnersEnable(1);
            Con_Printf("Memory owners: the count is on from the start (awowners.on)\n");
        }
    }
#endif
}
