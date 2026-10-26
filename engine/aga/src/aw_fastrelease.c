/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_fastrelease.c: the releasers of re-makeable session memory (aw_fastrelease.h). */
#include <stddef.h>
#include "aw_fastrelease.h"

void Con_Printf (char *fmt, ...);	/* console.h's, without quakedef.h (host tests stub it) */

#if defined(AMIGA) && defined(__m68k__)
#include <proto/exec.h>
#include <exec/memory.h>
static unsigned long fast_free (int largest)
{
	return AvailMem (MEMF_FAST | (largest ? MEMF_LARGEST : 0));
}
#else
static unsigned long fast_free (int largest)
{
	(void)largest;
	return 0;	/* host tests: no exec to ask */
}
#endif

static struct {
	const char			*name;
	aw_fast_release_t	fn;
} releasers[AW_FAST_RELEASERS];
static int releaser_count;

int AW_FastReleaseRegister (const char *name, aw_fast_release_t fn)
{
	int i;
	if (!fn)
		return 0;
	for (i=0 ; i<releaser_count ; i++)
		if (releasers[i].fn == fn)
		{
			releasers[i].name = name;
			return 1;
		}
	if (releaser_count >= AW_FAST_RELEASERS)
		return 0;
	releasers[releaser_count].name = name;
	releasers[releaser_count].fn = fn;
	releaser_count++;
	return 1;
}

int AW_FastReleasers (void)
{
	return releaser_count;
}

unsigned long AW_FastReleaseAll (const char *why)
{
	unsigned long total = 0, given, free_before, largest_before;
	int i;
	for (i=0 ; i<releaser_count ; i++)
	{
		free_before = fast_free (0);
		largest_before = fast_free (1);
		given = releasers[i].fn ();
		total += given;
		if (given)
			Con_Printf ("Fast RAM for %s: %s gave back %lu KiB; free %lu -> %lu KiB, largest block %lu -> %lu KiB\n",
				why ? why : "?", releasers[i].name ? releasers[i].name : "?", given/1024, free_before/1024,
				fast_free (0)/1024, largest_before/1024, fast_free (1)/1024);
	}
	return total;
}
