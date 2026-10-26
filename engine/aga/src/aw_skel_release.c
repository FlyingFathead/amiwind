/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_skel_release.c: the skeletal actors' session memory given back before a room takes Fast RAM for its models
 * (chim_world.c Chim_RoomGrow; SKEL-ROOM-AFTER-TOWN-52). At 32 MB Akulakhan's Chamber loads when it is the first map
 * (its models take 4 MiB of the free Fast RAM) but failed after Balmora: the animation tables (about 1.9 MB) and the
 * large pose cache (384 KB) held since the town left it 2 MiB. Both are made again on demand: the skeletal models in
 * the model cache are flushed first (each holds a pointer into its table), so the next draw loads the model, which
 * looks its table up again (aw_skel_load.c). */
#include "quakedef.h"
#include "aw_skel.h"
#include "aw_fastrelease.h"

extern model_t	mod_known[];
extern int		mod_numknown;

static unsigned long AW_SkelReleaseAll (void)
{
	unsigned long given;
	int i, flushed = 0;
	for (i=0 ; i<mod_numknown ; i++)
	{
		model_t *m = &mod_known[i];
		const aliashdr_t *h;
		if (m->type != mod_alias || !(h = (const aliashdr_t *)Cache_Check (&m->cache)) || !h->aw_skel)
			continue;
		Cache_Free (&m->cache);
		flushed++;
	}
	given = R_AliasPoseCacheRelease () + AW_SkelTablesRelease ();
	if (given)
		Con_Printf ("Animation tables and posed frames given back: %lu KiB (%d skeletal models flushed)\n",
			given/1024, flushed);
	return given;
}

void AW_SkelReleaseInit (void)
{
	/* the first releaser of aw_fastrelease.c: called before a large block is sized from the free Fast RAM */
	AW_FastReleaseRegister ("animation tables and posed frames", AW_SkelReleaseAll);
}
