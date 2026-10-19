/* SPDX-License-Identifier: GPL-2.0-or-later
 * The game heap for this start (ENGINE-HEAP-FIXED-SIZE-43). The heap (Quake's
 * Hunk, sys_amiga.c Sys_Init) is the built size (AMIWIND_HEAP_MB, 11 MiB) on
 * the 16 MiB reference machine, exactly as before. A machine with plenty of
 * Fast RAM gets a larger heap, so Quake's own cache (actors, sounds) and the
 * gap the maps keep free have room; the rest of the spare RAM stays for CHIM's
 * caches (chim_world.c Chim_MemoryStart). -heapmb N stays the override, used
 * as asked.
 *
 * The rule: the margin left to the system is CHIM's (2 MiB plus an eighth of
 * all Fast RAM, chim_zone.h ChimZone_AutoMargin); the room is the largest free
 * Fast RAM block less that margin. The heap grows only when the room is at
 * least the built size plus AW_HEAP_GROW_MIN_MB, then by a quarter of what is
 * beyond the built size, to AW_HEAP_AUTO_MAX_MB at most. 16 MiB of Fast RAM
 * (about 14 MiB free, margin 4 MiB) never grows.
 */
#include "aw_heapsize.h"

int AW_HeapAuto (int built_mb, int asked_mb, unsigned long largest, unsigned long total, int off, int *grown)
{
	unsigned long mib = 1048576UL, margin, room;
	long extra;
	int heap;
	*grown = 0;
	if (asked_mb > 0)
		return asked_mb;		/* -heapmb N: exactly as asked */
	if (off || built_mb <= 0)
		return built_mb;
	if (total < largest)
		total = largest;
	margin = 2*mib + total/8;
	room = largest > margin ? (largest - margin)/mib : 0;
	if (room < (unsigned long)(built_mb + AW_HEAP_GROW_MIN_MB))
		return built_mb;
	extra = ((long)room - built_mb) / 4;
	heap = built_mb + (int)extra;
	if (heap > AW_HEAP_AUTO_MAX_MB)
		heap = AW_HEAP_AUTO_MAX_MB;
	if (heap <= built_mb)
		return built_mb;
	*grown = 1;
	return heap;
}

/* config.cfg turns the extra RAM off with aw_autoram 0 (Options > Extra RAM):
 * the heap is sized before the config runs, so the saved line is read here. */
int AW_HeapAutoOff (const char *config_text)
{
	const char *p = config_text;
	while (p && (p = strstr (p, "aw_autoram")) != NULL)
	{
		const char *v = p + 10;
		if (p == config_text || p[-1] == '\n' || p[-1] == '\r')
		{
			while (*v == ' ' || *v == '\t' || *v == '"')
				v++;
			if (*v == '0')
				return 1;
		}
		p = v;
	}
	return 0;
}
