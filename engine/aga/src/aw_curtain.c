/* SPDX-License-Identifier: GPL-2.0-or-later
 * The Ghostfence curtain's own scroll in the engine (aw_curtain.h; GHOSTFENCE-NO-ANIMATION-46,
 * GHOSTFENCE-PARTICLES-NOT-DRAWN-68 C2, v0.0.68).
 *
 * aw_curtain (not saved; dbg curtain 0|1; the image's default-game.cfg states it): 0, the default until the A/B stills,
 * draws the curtain as before, Quake's warp of its texture (d_scan.c Turbulent8, aw_ghostfence); 1 draws every curtain
 * texture of the CHIM world straight from one block composed of the original's three scrolling layers. A turbulent
 * texture is a curtain texture when the 64 x 64 block it is drawn from hashes to one of id1/world/curtain.awc's
 * checksums (counted once per texture: CURTAIN_SEEN remembered by address and name, so a texture reloaded elsewhere or
 * another one at the same address is looked at again). The textures themselves are never written: d_edge.c draws from
 * this file's block instead, so aw_curtain 0 shows today's curtain at once.
 *
 * Cost: resident the table (at most AW_CURTAIN_BYTES), the composed texture and the two drawn blocks (9 KB of BSS),
 * the remembered textures; per drawn frame with a curtain in view and aw_curtain 1 one compose (32 x 32 texels, three
 * lookups and an add each) and one 64 x 64 block written; per curtain pixel the same span loop as before
 * (Turbulent8 on the still table). Nothing with aw_curtain 0 but one test a turbulent surface. */
#include "quakedef.h"
#include "r_local.h"
#include "aw_curtain.h"

#define CURTAIN_PATH	"world/curtain.awc"
#define CURTAIN_SEEN	64

static cvar_t aw_curtain = {"aw_curtain", "0"};
static unsigned char table_bytes[AW_CURTAIN_BYTES];
static aw_curtain_t table;
static int table_state;			/* 0 not read yet, 1 ready, -1 none in this image */
static unsigned char composed[AW_CURTAIN_SIZE * AW_CURTAIN_SIZE];
static unsigned char block_tiled[AW_CURTAIN_DRAWN * AW_CURTAIN_DRAWN], block_own[AW_CURTAIN_DRAWN * AW_CURTAIN_DRAWN];
static int composed_frame = -1, tiled_frame = -1, own_frame = -1;
typedef struct {const texture_t *tx; char name[16]; int size;} seen_t;
static seen_t seen[CURTAIN_SEEN];
static int seen_next;
extern unsigned char *(*aw_curtain_block) (texture_t *tx);	/* d_edge.c */

static void table_read (void)
{
	FILE *f = NULL;
	int size;
	table_state = -1;
	size = COM_FOpenFile (CURTAIN_PATH, &f);
	if (!f)
		return;
	if (size > 0 && size <= AW_CURTAIN_BYTES && fread (table_bytes, 1, (size_t)size, f) == (size_t)size &&
		AW_CurtainParse (table_bytes, (unsigned long)size, &table))
		table_state = 1;
	fclose (f);
	if (table_state < 0)
		Con_Printf ("%s: not a curtain table; the curtain ripples as before.\n", CURTAIN_PATH);
}

/* the size the table names TX's texture by (32 tiled, 64 its own), 0 when it is not a curtain texture */
static int curtain_size (const texture_t *tx)
{
	int i;
	seen_t *s;
	for (i = 0; i < CURTAIN_SEEN; i++)
		if (seen[i].tx == tx && !strncmp (seen[i].name, tx->name, sizeof(seen[i].name)))
			return seen[i].size;
	s = &seen[seen_next];
	seen_next = (seen_next + 1) % CURTAIN_SEEN;
	s->tx = tx;
	memcpy (s->name, tx->name, sizeof(s->name));
	s->size = tx->width == AW_CURTAIN_DRAWN && tx->height == AW_CURTAIN_DRAWN && tx->offsets[0] > 0 ?
		AW_CurtainFind (&table, AW_CurtainHash ((const unsigned char *)tx + tx->offsets[0],
			AW_CURTAIN_DRAWN * AW_CURTAIN_DRAWN)) : 0;
	return s->size;
}

/* d_edge.c: the block a turbulent surface of TX is drawn from, straight, or NULL to draw it as before */
static unsigned char *curtain_block (texture_t *tx)
{
	int size;
	if (!aw_curtain.value || !tx || tx->name[0] != '*')
		return NULL;
	if (!table_state)
		table_read ();
	if (table_state < 0 || !(size = curtain_size (tx)))
		return NULL;
	if (composed_frame != r_framecount)
	{
		AW_CurtainCompose (&table, (unsigned long)(cl.time * 1000.0), composed);
		composed_frame = r_framecount;
	}
	if (size == AW_CURTAIN_DRAWN)
	{
		if (own_frame != r_framecount)
		{
			AW_CurtainBlock (composed, AW_CURTAIN_DRAWN, block_own);
			own_frame = r_framecount;
		}
		return block_own;
	}
	if (tiled_frame != r_framecount)
	{
		AW_CurtainBlock (composed, AW_CURTAIN_SIZE, block_tiled);
		tiled_frame = r_framecount;
	}
	return block_tiled;
}

/* DemoWind's curtain effects (aw_demowind.c): the table, read when first asked for; NULL without one */
const aw_curtain_t *AW_CurtainTable (void)
{
	if (!table_state)
		table_read ();
	return table_state > 0 ? &table : NULL;
}

void AW_CurtainInit (void)
{
	Cvar_RegisterVariable (&aw_curtain);
	aw_curtain_block = curtain_block;
}
