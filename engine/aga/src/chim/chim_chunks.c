/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM chunks: the frame's chunk directory, the ring around the player,
 * placement catalogues, collision and the link into Quake's renderer.
 *
 * Quake mechanisms reused:
 * - Static entities and efrags (cl_parse.c CL_ParseStatic, r_efrag.c): every
 *   placement is an entity_t linked to the world leaves its drawn box touches
 *   (R_SplitEntityOnNode), stored for drawing only when one of those leaves
 *   is visible (R_StoreEfrags from R_RecursiveWorldNode, after the PVS and
 *   frustum). No edict, no signon message, no 16-leaf edict limit, and no
 *   modelindex: placements never reach MAX_EDICTS or MAX_MODELS.
 * - Brush entity collision (world.c SV_ClipMoveToEntity): the same hull
 *   choice, offset, yaw rotation, SV_RecursiveHullCheck and DIST_EPSILON
 *   pull-back, with each placement's yaw sine and cosine computed once.
 * - The placement catalogue of aw_scenery.c: the same drawn box and the same
 *   merge into the world trace (AW_MergeCollisionTrace).
 *
 * Chunk terrain is world geometry (chim_graft.c grafts it into the map's
 * world model whenever the active set changes).
 *
 * A placement is stored once as its owner record and copied, as a record
 * only, into every other chunk its drawn box touches (reach copies). The
 * engine draws and collides each placement exactly once: the owner record
 * when the owner chunk is active, else one active reach copy (Reconcile).
 */
#include "quakedef.h"
#include "r_local.h"
#include "chim_local.h"
#include "../aw_actors.h"
#include "aw_spike.h"

extern efrag_t	**lastlink;
extern vec3_t	r_emins, r_emaxs;
extern entity_t	*r_addent;
extern mnode_t	*r_pefragtopnode;
void R_SplitEntityOnNode (mnode_t *node);
void R_RemoveEfrags (entity_t *ent);
qboolean SV_RecursiveHullCheck (hull_t *hull, int num, float p1f, float p2f, vec3_t p1, vec3_t p2, trace_t *trace);
void AW_MergeCollisionTrace (trace_t *best, trace_t *candidate, edict_t *touch);

#define CHIM_DIST_EPSILON	(0.03125f)	/* world.c DIST_EPSILON */

chim_frame_state_t	chim_frame;
static short		*grid;				/* chunk (cx, cy) -> entry */
/* A cell's region map name (aw_world.c sets it): a window's frame reads its
 * streamed statics from that frame map (type 1 crossings). */
int (*chim_cell_map)(int cx, int cy, char *name, int size);
/* PROTOTYPE (branch v0.0.46-type1-stateful): the window's actors (aw_actors.c):
 * a joining frame's actors are spawned from its frame map (offset: its place in
 * the session), a leaving frame's actors are kept or written to the change list,
 * and every tick the actors outside the window are looked at again. */
void (*chim_actors_join)(int cx, int cy, const char *map, const float *offset);
void (*chim_actors_leave)(int cx, int cy);
void (*chim_actors_tick)(void);
void (*chim_actors_cmd)(void);
/* Fire light (CHIM-EXTERIOR-FLAMES-MISSING-48; the maintainer 2026-10-23: "set
 * it on by default but add some dbg command like dbg campfires on|off"): the
 * frame map's flame rows that carry "aw_flame_light" "R L" (the fire's light
 * record: radius in map units, brightness 0..255; tools/chim/flames.py) light
 * the placed models around them. A placement without a stored level gets the
 * rooms' rule at its drawn-box centre: the sum of L x the original attenuation
 * (full to R/3, then R/3d, faded out between R and 2R), rounded to steps of 8,
 * none under 4 (tools/chim/placement_light.py level). Computed once, when the
 * chunk's records are read; r_surf.c adds it to the dimmed ambient outdoors and
 * dbg campfires off (r_campfires 0) leaves it out. A frame map has at most
 * CHIM_FIRE_LIGHTS fires (the engine's static flame table is 128 flames). */
#define CHIM_FIRE_LIGHTS	128
typedef struct {float origin[3], radius, luma;} chim_fire_light_t;
static chim_fire_light_t	fire_lights[CHIM_FIRE_LIGHTS];
static int					fire_light_count;

/* Up to N numbers of TEXT (decimal, as the builder writes them) into OUT; the count read. */
static int FireNumbers (const char *text, float *out, int n)
{
	int k = 0;
	while (k < n)
	{
		double v = 0, scale = 1;
		int sign = 1, digits = 0;
		while (*text == ' ')
			text++;
		if (*text == '-' || *text == '+')
			sign = *text++ == '-' ? -1 : 1;
		for (; *text >= '0' && *text <= '9'; text++, digits++)
			v = v*10 + (*text - '0');
		if (*text == '.')
			for (text++; *text >= '0' && *text <= '9'; text++, digits++)
				v += (*text - '0') * (scale *= 0.1);
		if (!digits)
			break;
		out[k++] = (float)(sign*v);
	}
	return k;
}

/* One key's value inside an entity body [body, end): copied into VALUE; 0 when absent. */
static int FireKey (const char *body, const char *end, const char *key, char *value, int size)
{
	char quoted[24];
	const char *at, *q;
	int n;
	sprintf (quoted, "\"%s\"", key);
	for (at = body; (at = strstr (at, quoted)) && at < end; at += strlen (quoted))
	{
		q = strchr (at + strlen (quoted), '"');
		if (!q || q >= end)
			return 0;
		for (n = 0, q++; *q && *q != '"' && q < end && n < size-1; q++)
			value[n++] = *q;
		value[n] = 0;
		return 1;
	}
	return 0;
}

void ChimChunks_FireLights (const char *entities)
{
	const char *body, *end;
	char text[64];
	float light[2];
	chim_fire_light_t *f;
	fire_light_count = 0;
	for (body = entities ? strchr (entities, '{') : NULL; body; body = strchr (end, '{'))
	{
		if (!(end = strchr (body, '}')))
			break;
		if (fire_light_count >= CHIM_FIRE_LIGHTS)
			break;
		f = &fire_lights[fire_light_count];
		if (FireKey (body, end, "classname", text, sizeof(text)) && !strcmp (text, "aw_flame") &&
			FireKey (body, end, "aw_flame_light", text, sizeof(text)) && FireNumbers (text, light, 2) == 2 &&
			FireKey (body, end, "origin", text, sizeof(text)) && FireNumbers (text, f->origin, 3) == 3 &&
			light[0] > 0 && light[0] < 65536 && light[1] > 0 && light[1] <= 255)
		{
			f->radius = light[0];
			f->luma = light[1];
			fire_light_count++;
		}
	}
}

int ChimChunks_FireCount (void)
{
	return fire_light_count;
}

int ChimChunks_FireLevel (const vec3_t mins, const vec3_t maxs)
{
	float value = 0, d, r, w, t;
	vec3_t centre, delta;
	int i, level;
	if (!fire_light_count)
		return 0;
	for (i=0 ; i<3 ; i++)
		centre[i] = (mins[i] + maxs[i]) * 0.5f;
	for (i=0 ; i<fire_light_count ; i++)
	{
		r = fire_lights[i].radius;
		VectorSubtract (fire_lights[i].origin, centre, delta);
		d = DotProduct (delta, delta);
		if (d >= 4*r*r)
			continue;
		d = (float)sqrt (d);
		w = d <= r/3 ? 1.0f : r / (3*d);
		t = d/r - 1;
		t = t < 0 ? 0 : t > 1 ? 1 : t;
		t = 1 - t*t;
		t = 1 - t*t;
		value += fire_lights[i].luma * w * (1 - t);
	}
	if (!(value >= 4))
		return 0;
	level = (int)(value/8 + 0.5f) * 8;
	return level < 8 ? 8 : level > 255 ? 255 : level;
}

static chim_user_t	index_user;
static model_t		*link_world;		/* cl.worldmodel the efrags belong to */
static unsigned long	ticks;
static int			world_dirty;
static unsigned long	world_retry;
static unsigned long	frozen_frame, frozen_now, frozen_last;
/* The ring around the player: where it was last tick and which way it
 * moves (prefetch ahead), how far the nearest chunk without ground in the
 * frame world is (the safety margin), and loads past the budget for chunks
 * within the collision margin. */
static struct
{
	vec3_t			last, ahead;
	int				moved, has_ahead;
	float			margin, margin_min;	/* units; -1: every chunk of the frame grafted */
	unsigned long	urgent_loads;
} ring;
static struct
{
	int		efrags, placements_linked, one_leaf, max_leaves, hidden;
	unsigned long	activations, deactivations, reconciles;
	unsigned long	zone_maps;
	/* CHIM-EFRAG-UNCAPPED-35: placements waiting for efrag room this frame,
	 * all frames, and frames whose view leaf had no PVS row (H15). */
	int				efrag_waiting;
	unsigned long	efrag_capped, novis_frames;
} counts;

/* The efrag limit CHIM placements stop at (a variable for the host tests),
 * and the chunk distance (squared) past which placements wait while the
 * limit is near; it opens again when the ring changes. */
int chim_efrag_limit = AW_EFRAG_LIMIT - CHIM_EFRAG_RESERVE;
static float			efrag_horizon = 1e30f;
static unsigned long	efrag_ring;
static int				efrag_short, efrag_calm;
/* A full zone (CHIM-CHUNK-LOAD-FAIL-33): chunks released for a nearer one
 * (past the active radius, inside it), partial activations, and failed
 * loads by reason. Kept across maps, like the zone's own counters. */
static struct
{
	unsigned long	band, ring, partial, zone, data;
} pressure;

void ChimChunks_Pressure (unsigned long *released_band, unsigned long *released_ring, unsigned long *partial,
	unsigned long *zone_failures, unsigned long *data_failures)
{
	*released_band = pressure.band;
	*released_ring = pressure.ring;
	*partial = pressure.partial;
	*zone_failures = pressure.zone;
	*data_failures = pressure.data;
}

/* ---------------------------------------------------------------- directory */

/* The FRAM row of frame (cx, cy), -1: none. */
static int FrameRow (int cx, int cy)
{
	int i;
	for (i=0 ; i<chim_world.files ; i++)
		if (!strcmp (chim_world.file[i].kind, "FRAM") && chim_world.file[i].cx == cx && chim_world.file[i].cy == cy)
			return i;
	return -1;
}

static int FrameHeader (int row, chim_header_t *h, chim_frame_t *f)
{
	byte head[CHIM_HEADER_BYTES + CHIM_FRAME_BYTES];
	chim_pack_t *pack;
	return row >= 0 && (pack = Chim_File (row)) != NULL && Chim_PackRead (pack, 0, head, sizeof(head)) &&
		ChimFormat_Header (head, pack->bytes, "FRAM", h) && ChimFormat_Frame (head + CHIM_HEADER_BYTES, f);
}

/* Placement ids run on across the frames of a world, in pack order (the
 * index's file table): a frame's ids start after the earlier frames'. With the
 * prefetch on (spare Fast RAM) the earlier frames' placement counts are kept
 * from their first reading, instead of opening every earlier frame's file on
 * each map start (CHIM-CROSSING-SYNC-LOAD-43). Same values either way. */
static int FirstPid (int row, unsigned *first)
{
	int i, fast = ChimPrefetch_Active ();
	*first = 0;
	for (i=0 ; i<row ; i++)
	{
		chim_header_t oh;
		chim_frame_t of;
		unsigned kept;
		if (strcmp (chim_world.file[i].kind, "FRAM"))
			continue;
		if (fast && ChimPrefetch_Owned (i, &kept))
		{
			*first += kept;
			continue;
		}
		if (!FrameHeader (i, &oh, &of))
			return 0;
		*first += of.owned_total;
		if (fast)
			ChimPrefetch_SetOwned (i, of.owned_total);
	}
	return 1;
}

/* The frame file's directory checked against the world (count, grain,
 * sectors, layout); the sector count in *sectors. */
static int FrameValid (const chim_header_t *h, const chim_frame_t *f, int cx, int cy, int *sectors)
{
	int n = (int)h->count, cells = f->nx * f->ny;
	*sectors = f->sector_chunks > 0 ? cells / (f->sector_chunks * f->sector_chunks) : 0;
	return !(n < 1 || n > CHIM_MAX_CHUNKS || n != cells || f->grain != chim_world.settings.grain ||
		f->cx != cx || f->cy != cy || f->sector_chunks != chim_world.settings.sector_chunks ||
		h->directory != CHIM_HEADER_BYTES + CHIM_FRAME_BYTES || h->directory + (unsigned)n*CHIM_CHUNK_ENTRY_BYTES != h->data ||
		h->data + (unsigned)*sectors*CHIM_SECTOR_ENTRY_BYTES != h->bytes || f->owned_total > 0x7fffffffu - 7);
}

/* The chunk directory of the frame at row into entries[base, base + n) and
 * its grid (frame-local chunk -> local entry), placed at offset (session
 * coordinates; 0 without a window). With the prefetch on (spare Fast RAM):
 * the frame's sector rows from one pass over the file table (the same values). */
static int ReadDirectory (int row, const chim_header_t *h, const chim_frame_t *f, int base, short *local_grid,
	const float *offset, int slot)
{
	chim_pack_t *pack;
	int i, n = (int)h->count, cells = f->nx * f->ny, sectors;
	byte *raw = chim_world.buffer;
	int per = chim_world.buffer_bytes / CHIM_CHUNK_ENTRY_BYTES;
	int fast = ChimPrefetch_Active ();
	int sector_row[256];

	sectors = cells / (f->sector_chunks * f->sector_chunks);
	if (fast && sectors <= 256)
	{
		/* The first row of each sector, as Chim_FileRow finds it. */
		for (i=0 ; i<sectors ; i++)
			sector_row[i] = -1;
		for (i=0 ; i<chim_world.files ; i++)
		{
			const chim_file_row_t *fr = &chim_world.file[i];
			if (fr->cx == f->cx && fr->cy == f->cy && fr->sector < sectors && sector_row[fr->sector] < 0 &&
				!strcmp (fr->kind, "SECT"))
				sector_row[fr->sector] = i;
		}
	}
	else
		fast = 0;
	for (i=0 ; i<cells ; i++)
		local_grid[i] = -1;
	for (i=0 ; i<n ; i++)
	{
		chim_entry_t *e = &chim_frame.entries[base + i];
		unsigned bytes;
		if (!(i % per) && (!(pack = Chim_File (row)) || !Chim_PackRead (pack, h->directory + i*CHIM_CHUNK_ENTRY_BYTES,
			raw, (long)((n - i < per ? n - i : per) * CHIM_CHUNK_ENTRY_BYTES))))
			return 0;
		ChimFormat_ChunkEntry (raw + (i % per)*CHIM_CHUNK_ENTRY_BYTES, &e->disk);
		e->file = e->disk.sector >= sectors ? -1 : fast ? sector_row[e->disk.sector] :
			Chim_FileRow ("SECT", f->cx, f->cy, e->disk.sector);
		if (e->file < 0 || e->disk.cx >= f->nx || e->disk.cy >= f->ny)
			return 0;
		bytes = chim_world.file[e->file].bytes;
		if (local_grid[e->disk.cy*f->nx + e->disk.cx] >= 0 || e->disk.offset < CHIM_HEADER_BYTES ||
			(e->disk.offset & 3) || e->disk.offset > bytes ||
			e->disk.render < CHIM_CHUNK_HEAD_BYTES || e->disk.render > bytes - e->disk.offset ||
			e->disk.collision > bytes - e->disk.offset - e->disk.render ||
			e->disk.owned + e->disk.reach > CHIM_MAX_RECORDS)
			return 0;
		local_grid[e->disk.cy*f->nx + e->disk.cx] = (short)i;
		e->low[0] = f->low[0] + e->disk.cx*f->grain + offset[0];
		e->low[1] = f->low[1] + e->disk.cy*f->grain + offset[1];
		e->high[0] = e->low[0] + f->grain;
		e->high[1] = e->low[1] + f->grain;
		e->distance = e->priority = 1e30f;
		e->graft = -1;
		e->shift[0] = e->shift[1] = e->shift[2] = 0;
		e->terrain_bytes = 0;
		e->slot = (short)slot;
		e->shadow = -1;
		e->terrain_locked = 0;
	}
	return 1;
}

static int WindowBegin (int row, const chim_header_t *h);
static void WindowUpdate (const vec3_t origin);
static void SlotRelease (int s);

/* The frame file (chunk directory, sector table) of frame (cx, cy); each
 * chunk record lives in one of the frame's sector files. */
int ChimChunks_Begin (int cx, int cy)
{
	chim_header_t h;
	int n, cells, bits, size, row, sectors;
	static const float zero[2] = {0, 0};

	memset (&chim_frame, 0, sizeof(chim_frame));
	memset (&counts, 0, sizeof(counts));
	link_world = NULL;
	row = FrameRow (cx, cy);
	if (!FrameHeader (row, &h, &chim_frame.frame))
		return 0;
	chim_frame.settings = chim_world.settings;
	if (ChimPrefetch_Active ())
		ChimPrefetch_SetOwned (row, chim_frame.frame.owned_total);
	if (!FirstPid (row, &chim_frame.first_pid) || !Chim_File (row))
		return 0;
	if (!FrameValid (&h, &chim_frame.frame, cx, cy, &sectors))
		return 0;
	if ((n = WindowBegin (row, &h)) != 0)
		return n > 0;
	n = (int)h.count;
	cells = chim_frame.frame.nx * chim_frame.frame.ny;
	bits = (int)((chim_frame.frame.owned_total + 7) / 8);
	size = n*sizeof(chim_entry_t) + cells*sizeof(short) + 2*bits;
	if (!ChimZone_Alloc (&index_user, size, CHIM_KIND_INDEX, 1))
		return 0;
	ChimZone_Lock (index_user.data);
	chim_frame.entries = index_user.data;
	grid = (short *)(chim_frame.entries + n);
	chim_frame.drawn = (unsigned char *)(grid + cells);
	chim_frame.visible = chim_frame.drawn + bits;
	chim_frame.view_entry = -2;
	if (!ReadDirectory (row, &h, &chim_frame.frame, 0, grid, zero, 0))
		return 0;
	chim_frame.count = n;
	ticks = 0;
	memset (&ring, 0, sizeof(ring));
	ring.margin = ring.margin_min = -1;
	return 1;
}

/* ---------------------------------------------------------------- linking */

static int LinksValid (void)
{
	return link_world && cls.signon == SIGNONS && cl.worldmodel == link_world;
}

static int CountLeaves (const entity_t *ent)
{
	const efrag_t *ef;
	int n = 0;
	for (ef=ent->efrag ; ef ; ef=ef->entnext)
		n++;
	return n;
}

/* R_SplitEntityOnNode's walk, counting the leaves it would link. */
static int CountBoxLeaves (mnode_t *node)
{
	int sides, n = 0;
	if (node->contents == CONTENTS_SOLID)
		return 0;
	if (node->contents < 0)
		return 1;
	sides = BOX_ON_PLANE_SIDE (r_emins, r_emaxs, node->plane);
	if (sides & 1)
		n += CountBoxLeaves (node->children[0]);
	if (sides & 2)
		n += CountBoxLeaves (node->children[1]);
	return n;
}

/* R_AddEfrags with an explicit drawn box: R_AddEfrags uses the model's
 * unrotated bounds, which miss leaves of a yawed placement. Within a
 * quarter of the reserve of chim_efrag_limit the leaves are counted first
 * and a placement that would pass the limit waits unlinked (0 leaves,
 * efrag_short), instead of the efrag pool's Host_Error ending the map. */
static int AddEfrags (entity_t *ent, const vec3_t mins, const vec3_t maxs)
{
	ent->efrag = NULL;
	VectorCopy (mins, r_emins);
	VectorCopy (maxs, r_emaxs);
	if (aw_efrags_used + CHIM_EFRAG_RESERVE/4 > chim_efrag_limit &&
		aw_efrags_used + CountBoxLeaves (cl.worldmodel->nodes) > chim_efrag_limit)
	{
		counts.efrag_waiting++;
		counts.efrag_capped++;
		efrag_short = 1;
		return 0;
	}
	r_addent = ent;
	lastlink = &ent->efrag;
	r_pefragtopnode = NULL;
	R_SplitEntityOnNode (cl.worldmodel->nodes);
	ent->topnode = r_pefragtopnode;
	return CountLeaves (ent);
}

/* Its ground is in the frame world: grafted, or (a window's chunk whose
 * place another frame's chunk holds) that chunk is. */
static int Grounded (const chim_entry_t *e)
{
	return e->grafted || (chim_frame.window && e->shadow >= 0 && chim_frame.entries[e->shadow].grafted);
}

int ChimChunks_Grounded (int entry)
{
	return entry >= 0 && entry < chim_frame.count && Grounded (&chim_frame.entries[entry]);
}

/* A chunk whose placements may be linked: active and, with the incremental
 * frame world, grafted (its leaves exist). */
static int Linkable (int index)
{
	chim_entry_t *e = &chim_frame.entries[index];
	return e->state == CHIM_STATE_ACTIVE && (Grounded (e) || !ChimGraft_Incremental ()) && e->distance <= efrag_horizon;
}

static void DropEfrags (entity_t *ent)
{
	if (ent->efrag && LinksValid ())
		ChimGraft_RemoveEfrags (ent);
	ent->efrag = NULL;
}

/* A placement's bit in the frame's rows: its id less the frame's first. */
static unsigned Local (unsigned pid)
{
	return pid - chim_frame.first_pid;
}

/* The opening story hides some placements (aw_opening.c's rule for
 * "aw_story_hidden"): not drawn, not solid. */
int (*chim_story_hidden)(void);

static int Hidden (const chim_place_t *p)
{
	return (p->flags & CHIM_RECORD_STORY_HIDDEN) && chim_story_hidden && chim_story_hidden ();
}

/* Hinged doors (aw_hinged_door.c): a door turns about its origin, so its
 * drawn box becomes the square of the farthest corner's distance in X and Y
 * (every pose fits; efrags and the collision broadphase need no relink while
 * it turns). The record box was drawn at the placed yaw. */
int (*chim_hinged_door)(unsigned pid, unsigned ref, const float *origin, float radius, float *yaw);
void (*chim_hinged_recentre)(const float *d);

float ChimChunks_HingeRadius (const chim_place_t *p)
{
	int i;
	float x, y, best = 0;
	for (i=0 ; i<4 ; i++)
	{
		x = (i & 1 ? p->maxs[0] : p->mins[0]) - p->ent.origin[0];
		y = (i & 2 ? p->maxs[1] : p->mins[1]) - p->ent.origin[1];
		if (x*x + y*y > best)
			best = x*x + y*y;
	}
	return (float)sqrt (best);
}

static void PlaceYaw (chim_chunk_t *c, int j, float yaw)
{
	chim_place_t *p = &c->places[j];
	p->ent.angles[YAW] = yaw;
	Q_SinCosDeg (yaw, &p->s, &p->c);
	if (c->rot)
		ChimPlaced_AnglesMatrix (p->ent.angles, (float (*)[3])(c->rot + 9*j));
}

/* Every copy of placement pid in a catalogue in the zone (owner and reach
 * copies, active or only loaded) gets the yaw. Called only while a door
 * turns. Returns the copies changed. A CHIM room's doors are its own
 * placements (chim_room.c). */
int ChimChunks_DoorYaw (unsigned pid, float yaw)
{
	int i, j, n = 0;
	if (ChimRoom_Active ())
		return ChimRoom_DoorYaw (pid, yaw);
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_entry_t *e = &chim_frame.entries[i];
		chim_chunk_t *c = e->chunk.data;
		if (e->state == CHIM_STATE_ABSENT || !c)
			continue;
		for (j=0 ; j<c->records ; j++)
			if (c->places[j].pid == pid && (c->places[j].flags & CHIM_PLACE_HINGED))
			{
				PlaceYaw (c, j, yaw);
				n++;
			}
	}
	return n;
}

/* A window's slot holding placement id pid (ids of frames do not overlap). */
static chim_slot_t *PidSlot (unsigned pid)
{
	int s;
	for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
		if (chim_frame.slot[s].used && pid - chim_frame.slot[s].first_pid < chim_frame.slot[s].frame.owned_total)
			return &chim_frame.slot[s];
	return NULL;
}

/* The drawn bits holding pid and its bit (a window: its frame's). */
static unsigned char *DrawnBits (unsigned pid, unsigned *bit)
{
	chim_slot_t *s;
	if (!chim_frame.window)
	{
		*bit = Local (pid);
		return chim_frame.drawn;
	}
	if (!(s = PidSlot (pid)))
		return NULL;
	*bit = pid - s->first_pid;
	return s->drawn;
}

static void SetDrawn (unsigned pid, int on)
{
	unsigned char *bits = DrawnBits (pid, &pid);
	if (!bits)
		return;
	if (on)
		bits[pid>>3] |= (unsigned char)(1u << (pid & 7));
	else
		bits[pid>>3] &= (unsigned char)~(1u << (pid & 7));
}

static int Drawn (unsigned pid)
{
	unsigned char *bits = DrawnBits (pid, &pid);
	return bits ? (bits[pid>>3] >> (pid & 7)) & 1 : 0;
}

/* A window: each placement is drawn by the frame whose cell holds it (two
 * frames may both carry an object near their shared border); one in no
 * window frame's cell by any frame that has it. Always 1 without a window. */
static int CoreKeeps (const chim_entry_t *e, const float *origin)
{
	int s;
	if (!chim_frame.window)
		return 1;
	for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
	{
		const chim_slot_t *w = &chim_frame.slot[s];
		if (w->used && !w->leaving && origin[0] >= w->core[0] && origin[0] < w->core[2] &&
			origin[1] >= w->core[1] && origin[1] < w->core[3])
			return s == e->slot;
	}
	return 1;
}

static void Unlink (chim_place_t *p)
{
	if (!p->linked)
		return;
	if (p->leaves)
	{
		counts.efrags -= p->leaves;
		if (p->leaves == 1)
			counts.one_leaf--;
	}
	DropEfrags (&p->ent);
	p->leaves = 0;
	p->linked = 0;
	counts.placements_linked--;
	SetDrawn (p->pid, 0);
}

/* The owner chunk of a reach copy draws the placement: it is active and,
 * when partially active, holds the placement's model. */
static int OwnerDraws (const chim_place_t *p)
{
	chim_entry_t *o = &chim_frame.entries[p->owner];
	chim_chunk_t *c;
	int j;
	if (o->state != CHIM_STATE_ACTIVE)
		return 0;
	if (!o->partial)
		return 1;
	c = o->chunk.data;
	for (j=0 ; j<c->owned ; j++)
		if (c->places[j].pid == p->pid)
			return c->places[j].ent.model != NULL;
	return 0;
}

/* Each placement drawn and collided once: by its owner chunk when that is
 * active (and holds its model), else by the first active chunk holding a
 * reach copy of it. */
static void Reconcile (void)
{
	int i, j;
	chim_chunk_t *c;

	counts.reconciles++;
	for (i=0 ; i<chim_frame.count ; i++)
	{
		if (chim_frame.entries[i].state != CHIM_STATE_ACTIVE)
			continue;
		c = chim_frame.entries[i].chunk.data;
		for (j=c->owned ; j<c->records ; j++)
			if (c->places[j].linked && OwnerDraws (&c->places[j]))
				Unlink (&c->places[j]);
		/* A window that changed: placements another frame now draws. */
		if (chim_frame.window)
			for (j=0 ; j<c->records ; j++)
				if (c->places[j].linked && !CoreKeeps (&chim_frame.entries[i], c->places[j].ent.origin))
					Unlink (&c->places[j]);
	}
	for (i=0 ; i<chim_frame.count ; i++)
	{
		if (chim_frame.entries[i].state != CHIM_STATE_ACTIVE)
			continue;
		c = chim_frame.entries[i].chunk.data;
		for (j=0 ; j<c->records ; j++)
		{
			chim_place_t *p = &c->places[j];
			if (p->linked || Drawn (p->pid) || Hidden (p) || !p->ent.model ||
				!CoreKeeps (&chim_frame.entries[i], p->ent.origin))
				continue;
			if (j >= c->owned && OwnerDraws (p))
				continue;
			p->linked = 1;
			counts.placements_linked++;
			SetDrawn (p->pid, 1);
		}
	}
}

/* The view chunk's placement row (format 0.3), decompressed: Quake's zero
 * runs as in Mod_DecompressVis. Returns 0 when the row is missing or bad
 * (then every linked placement is drawn). */
static int ViewRow (int entry)
{
	chim_chunk_t *c;
	int nbytes = (int)((chim_frame.frame.owned_total + 7) >> 3), out = 0, in = 0, k;
	if (entry < 0 || chim_frame.entries[entry].state != CHIM_STATE_ACTIVE)
		return 0;
	if (chim_frame.window)
	{
		/* The row covers the view chunk's own frame (its slot's bits). */
		chim_slot_t *s = &chim_frame.slot[chim_frame.entries[entry].slot];
		nbytes = (int)((s->frame.owned_total + 7) >> 3);
		chim_frame.visible = s->visible;
		chim_frame.view_slot = chim_frame.entries[entry].slot;
	}
	c = chim_frame.entries[entry].chunk.data;
	if (!c->pvl_bytes)
		return 0;
	while (out < nbytes)
	{
		if (in >= c->pvl_bytes)
			return 0;
		if (c->pvl[in])
		{
			chim_frame.visible[out++] = c->pvl[in++];
			continue;
		}
		if (in + 1 >= c->pvl_bytes || out + c->pvl[in+1] > nbytes)
			return 0;
		for (k=c->pvl[in+1] ; k ; k--)
			chim_frame.visible[out++] = 0;
		in += 2;
	}
	return in == c->pvl_bytes;
}

static int ViewSees (const chim_place_t *p)
{
	unsigned bit = Local (p->pid);	/* bit k of the row = the frame's first id + k */
	if (chim_frame.view_entry < 0)
		return 1;
	if (chim_frame.window)
	{
		/* Another frame's placement: the view chunk's row does not cover it. */
		const chim_slot_t *s = &chim_frame.slot[chim_frame.view_slot];
		bit = p->pid - s->first_pid;
		if (bit >= s->frame.owned_total)
			return 1;
		return (s->visible[bit >> 3] >> (bit & 7)) & 1;
	}
	return bit < chim_frame.frame.owned_total && ((chim_frame.visible[bit >> 3] >> (bit & 7)) & 1);
}

static int ViewEntry (void)
{
	const float *o;
	int x, y;
	if (cl.viewentity <= 0 || cl.viewentity >= MAX_EDICTS)
		return -1;
	o = cl_entities[cl.viewentity].origin;
	if (o[0] < chim_frame.frame.low[0] || o[1] < chim_frame.frame.low[1])
		return -1;
	x = (int)((o[0] - chim_frame.frame.low[0]) / chim_frame.frame.grain);
	y = (int)((o[1] - chim_frame.frame.low[1]) / chim_frame.frame.grain);
	return ChimChunks_CellEntry (x, y);
}

/* Client side, once per frame: efrags for what Reconcile linked and the
 * view chunk's placement list allows. Placements outside the list keep
 * their collision; they are only not drawn (format 0.3 placement lists). */
void ChimChunks_Link (void)
{
	int i, j, view;
	chim_entry_t *e;
	chim_chunk_t *c;

	if (cls.signon != SIGNONS || !cl.worldmodel)
		return;
	if (cl.worldmodel != link_world)
	{
		/* A new client map reset the efrag pool: forget the old links. */
		for (i=0 ; i<chim_frame.count ; i++)
		{
			e = &chim_frame.entries[i];
			if (e->state != CHIM_STATE_ACTIVE)
				continue;
			c = e->chunk.data;
			for (j=0 ; j<c->records ; j++)
			{
				c->places[j].ent.efrag = NULL;
				c->places[j].leaves = 0;
			}
		}
		counts.efrags = counts.one_leaf = 0;
		link_world = cl.worldmodel;
		efrag_horizon = 1e30f;
	}
	/* The ring changed: every active chunk may link again (the limit
	 * pushes the horizon back in if it is still near). */
	/* Or the pool has stayed well below the limit for a while (256 frames
	 * with no wait: no relink-and-drop cycle every frame). */
	if (efrag_calm < 256)
		efrag_calm++;
	if (counts.activations + counts.deactivations != efrag_ring ||
		(efrag_calm >= 256 && aw_efrags_used + CHIM_EFRAG_RESERVE/2 < chim_efrag_limit))
	{
		efrag_ring = counts.activations + counts.deactivations;
		efrag_horizon = 1e30f;
	}
	counts.efrag_waiting = 0;
	/* H15: a view leaf without a PVS row (void, grid leaves, a chunk without
	 * a row) sees everything; counted for dbg rcount ("nv"). */
	if (r_viewleaf && (r_viewleaf == cl.worldmodel->leafs || !r_viewleaf->compressed_vis))
		counts.novis_frames++;
	view = ViewEntry ();
	if (view != chim_frame.view_entry && view >= 0 && chim_frame.entries[view].state == CHIM_STATE_ACTIVE)
		chim_frame.view_entry = ViewRow (view) ? view : -1;
	else if (view < 0 || chim_frame.entries[view].state != CHIM_STATE_ACTIVE)
		chim_frame.view_entry = -1;
	counts.hidden = 0;
	for (i=0 ; i<chim_frame.count ; i++)
	{
		e = &chim_frame.entries[i];
		if (e->state != CHIM_STATE_ACTIVE)
			continue;
		c = e->chunk.data;
		for (j=0 ; j<c->records ; j++)
		{
			chim_place_t *p = &c->places[j];
			if (!p->linked)
				continue;
			/* Incremental frame world: a chunk waiting for its ground is
			 * drawn once grafted (it is at the ring's edge), so its
			 * placements are not linked into the grid's empty leaves
			 * only to be linked again a frame later. */
			if (!Grounded (e) && ChimGraft_Incremental ())
				continue;
			/* Past the efrag horizon: the farthest chunks give their links
			 * to the nearer ones while the limit is near. */
			if (e->distance > efrag_horizon)
			{
				if (p->leaves)
				{
					counts.efrags -= p->leaves;
					if (p->leaves == 1)
						counts.one_leaf--;
					DropEfrags (&p->ent);
					p->leaves = 0;
				}
				counts.efrag_waiting++;
				continue;
			}
			if (!ViewSees (p))
			{
				counts.hidden++;
				if (p->leaves)
				{
					counts.efrags -= p->leaves;
					if (p->leaves == 1)
						counts.one_leaf--;
					DropEfrags (&p->ent);
					p->leaves = 0;
				}
				continue;
			}
			if (p->leaves)
				continue;
			p->leaves = AddEfrags (&p->ent, p->mins, p->maxs);
			if (efrag_short)
			{
				efrag_short = 0;
				efrag_calm = 0;
				if (e->distance < efrag_horizon)
					efrag_horizon = e->distance;
			}
			counts.efrags += p->leaves;
			if (p->leaves == 1)
				counts.one_leaf++;
			if (p->leaves > counts.max_leaves)
				counts.max_leaves = p->leaves;
		}
	}
	/* Streamed statics (chim_statics.c): placed while their chunk is active. */
	ChimStatics_Link (AddEfrags, Linkable);
	efrag_short = 0;
}

/* CHIM-EFRAG-UNCAPPED-35: placements waiting for efrag room in the last
 * frame and in all; frames whose view leaf had no PVS row. */
void ChimChunks_EfragCounts (int *waiting, unsigned long *capped, unsigned long *novis_frames)
{
	*waiting = counts.efrag_waiting;
	*capped = counts.efrag_capped;
	*novis_frames = counts.novis_frames;
}

/* ---------------------------------------------------------------- catalogue */

static void ChunkEvicted (void *data, unsigned id)
{
	(void)data;
	if (id >= (unsigned)chim_frame.count)
		return;
	if (chim_frame.entries[id].state == CHIM_STATE_ACTIVE)
		Sys_Error ("CHIM: active chunk %lu evicted", (unsigned long)id);
	if (chim_frame.entries[id].state == CHIM_STATE_LOADED)
		chim_frame.loaded--;
	chim_frame.entries[id].state = CHIM_STATE_ABSENT;
	chim_frame.entries[id].ready = 0;
}

/* 0.9: where the reach references being read and the owner records they
 * name sit in the read buffer (references at the start, a span of one owner
 * chunk's owned records in the second half). */
typedef struct
{
	int		half;					/* bytes of each half */
	int		ref_first, ref_count;	/* the references in the buffer */
	int		owner, span_first, span_count;	/* owner entry and its records in the buffer */
	int		last_owner;				/* the owner (frame index) of the last record returned */
} chim_reach_read_t;

/* 0.9: how the reach references were served (dbg and tests): from the owner
 * chunk's catalogue already in the zone, or read from its record list. */
chim_reach_stats_t chim_reach_stats;
/* 1: a reference whose owner catalogue is in the zone is copied from it (no
 * read); 0: every reference reads its record (tests compare both ways). */
int chim_reach_resident = 1;

/* 0.9: the owner record that reach reference K (of REFS) of chunk INDEX
 * names. When the owner chunk's catalogue is in the zone, its run-time
 * placement (FROM, and its matrix FROM_ROT) is copied with no read;
 * otherwise the record (REC) is read from the owner chunk's own record list
 * in the same frame: one read per owner chunk, from the first to the last
 * record its references in the buffer name (the references come in owner
 * and record order). 0 on bad data: an owner outside the frame, the chunk
 * itself, or a record its owner does not hold. */
static int ReachRecord (int index, int base, int frame_count, int owned, int k, int refs,
	chim_reach_read_t *s, long *budget, const byte **rec, const chim_place_t **from, const float **from_rot)
{
	const chim_entry_t *e = &chim_frame.entries[index], *o;
	byte *raw = chim_world.buffer;
	const int rb = CHIM_RECORD_BYTES_PLACED;
	chim_pack_t *pack;
	int owner, record, take;

	if (k < s->ref_first || k >= s->ref_first + s->ref_count)
	{
		take = refs - k;
		if (take > s->half / CHIM_REACH_REF_BYTES)
			take = s->half / CHIM_REACH_REF_BYTES;
		if (!(pack = Chim_File (e->file)) ||
			!Chim_PackRead (pack, e->disk.offset + CHIM_CHUNK_HEAD_BYTES + (long)owned*rb + (long)k*CHIM_REACH_REF_BYTES,
			raw, (long)take*CHIM_REACH_REF_BYTES))
			return 0;
		*budget -= (long)take*CHIM_REACH_REF_BYTES;
		s->ref_first = k;
		s->ref_count = take;
	}
	ChimFormat_ReachRef (raw + (k - s->ref_first)*CHIM_REACH_REF_BYTES, &owner, &record);
	if (owner >= frame_count || owner + base == index)
		return 0;
	o = &chim_frame.entries[owner + base];
	if (record >= o->disk.owned)
		return 0;
	*rec = NULL;
	*from = NULL;
	*from_rot = NULL;
	s->last_owner = owner;
	if (chim_reach_resident && (o->state == CHIM_STATE_LOADED || o->state == CHIM_STATE_ACTIVE) && o->chunk.data)
	{
		const chim_chunk_t *oc = o->chunk.data;
		if (record >= oc->owned || (oc->rot == NULL) != (chim_world.minor < CHIM_PLACED_MINOR))
			return 0;
		*from = &oc->places[record];
		*from_rot = oc->rot ? oc->rot + 9*record : NULL;
		chim_reach_stats.resident++;
		return 1;
	}
	chim_reach_stats.read++;
	if (owner + base != s->owner || record < s->span_first || record >= s->span_first + s->span_count)
	{
		/* from this record to the last one the following references in the
		 * buffer take from the same owner (they come in record order) */
		int j, last = record, o2, r2;
		for (j=k+1 ; j<s->ref_first + s->ref_count ; j++)
		{
			ChimFormat_ReachRef (raw + (j - s->ref_first)*CHIM_REACH_REF_BYTES, &o2, &r2);
			if (o2 != owner)
				break;
			if (r2 > last && r2 < o->disk.owned)
				last = r2;
		}
		take = last - record + 1;
		if (take > s->half / rb)
			take = s->half / rb;
		if (!(pack = Chim_File (o->file)) ||
			!Chim_PackRead (pack, o->disk.offset + CHIM_CHUNK_HEAD_BYTES + (long)record*rb, raw + s->half, (long)take*rb))
			return 0;
		*budget -= (long)take*rb;
		chim_reach_stats.span_reads++;
		s->owner = owner + base;
		s->span_first = record;
		s->span_count = take;
	}
	*rec = raw + s->half + (record - s->span_first)*rb;
	return 1;
}

/* Read the chunk head and its placement records; one catalogue block holds
 * the chunk, a run-time placement per record and its distinct models. */
static int LoadCatalogue (int index, long *budget)
{
	chim_entry_t *e = &chim_frame.entries[index];
	chim_chunk_head_t head;
	chim_record_t r;
	chim_chunk_t *c;
	chim_pack_t *pack = Chim_File (e->file);
	byte *raw = chim_world.buffer;
	/* 0.8: 56-byte records with pitch and roll, and a matrix per record */
	int placed = chim_world.minor >= CHIM_PLACED_MINOR, rb = ChimFormat_RecordBytes (chim_world.minor);
	int i, j, n, per = chim_world.buffer_bytes / rb;
	long rot_bytes, rows;
	/* 0.9: reach entries are references to records owned in the frame */
	int refs, lim;
	chim_reach_read_t span;
	/* Its frame's placement ids, entries and offset (a window: its slot's). */
	unsigned first = chim_frame.first_pid, total = chim_frame.frame.owned_total;
	int base = 0, frame_count = chim_frame.count;
	float dx = 0, dy = 0;

	if (chim_frame.window)
	{
		const chim_slot_t *s = &chim_frame.slot[e->slot];
		first = s->first_pid;
		total = s->frame.owned_total;
		base = s->base;
		frame_count = s->count;
		dx = s->offset[0];
		dy = s->offset[1];
	}
	if (!pack || !Chim_PackRead (pack, e->disk.offset, raw, CHIM_CHUNK_HEAD_BYTES) ||
		!ChimFormat_ChunkHead (raw, &head) || head.owned != e->disk.owned || head.reach != e->disk.reach ||
		(placed && head.record_bytes != CHIM_RECORD_BYTES_PLACED && chim_world.minor < CHIM_TERC_MINOR) ||
		(head.reach_refs && chim_world.minor < CHIM_REACH_MINOR))
		return -1;
	if (chim_world.minor >= CHIM_TERC_MINOR)
	{
		/* 0.10: the chunk head says its record size (0: the 48-byte record, 56: placed), so a world of compact
		 * terrain records keeps whichever placement format it was built with */
		if (head.record_bytes != 0 && head.record_bytes != CHIM_RECORD_BYTES_PLACED)
			return -1;
		placed = head.record_bytes == CHIM_RECORD_BYTES_PLACED;
		rb = placed ? CHIM_RECORD_BYTES_PLACED : CHIM_RECORD_BYTES;
		per = chim_world.buffer_bytes / rb;
		if (head.reach_refs && !placed)
			return -1;
	}
	n = head.owned + head.reach;
	refs = head.reach_refs;
	lim = refs ? head.owned : n;
	rows = refs ? (long)head.owned*rb + (long)head.reach*CHIM_REACH_REF_BYTES : (long)n*rb;
	if (head.image_at < (unsigned)(CHIM_CHUNK_HEAD_BYTES + rows + head.pvs_bytes + head.pvl_bytes) ||
		head.image_at + head.image_render != e->disk.render)
		return -1;
	span.half = (chim_world.buffer_bytes / 2) & ~3;
	span.ref_first = span.ref_count = span.span_first = span.span_count = 0;
	span.owner = span.last_owner = -1;
	if (refs && span.half < rb)
		return -1;
	/* an even number of floats keeps the model list behind them aligned */
	rot_bytes = placed ? (long)((9*n + 1) & ~1)*(long)sizeof(float) : 0;
	c = ChimZone_Alloc (&e->chunk, sizeof(*c) + n*(sizeof(chim_place_t) + sizeof(chim_chunk_model_t)) + rot_bytes +
		head.pvs_bytes + head.pvl_bytes, CHIM_KIND_CHUNK, (unsigned)index);
	if (!c)
		return -1;
	c->entry = index;
	c->records = n;
	c->owned = head.owned;
	c->places = (chim_place_t *)(c+1);
	c->rot = placed ? (float *)(c->places + n) : NULL;
	c->model_list = (chim_chunk_model_t *)((byte *)(c->places + n) + rot_bytes);
	*budget -= CHIM_CHUNK_HEAD_BYTES;
	for (i=0 ; i<n ; i++)
	{
		chim_place_t *p = &c->places[i];
		const byte *rec;
		if (i >= lim)
		{
			/* 0.9: the owner record a reach reference names */
			const chim_place_t *from;
			const float *from_rot;
			if (!ReachRecord (index, base, frame_count, head.owned, i - head.owned, head.reach, &span, budget,
				&rec, &from, &from_rot))
				goto bad;
			if (from)
			{
				/* the owner's catalogue is in the zone: its run-time placement
				 * as this loop made it from the same record (same frame, same
				 * slot offset), the per-chunk fields left as allocated */
				if (from->pid < first || from->pid - first >= total || from->owner != span.last_owner + base)
					goto bad;
				p->pid = from->pid;
				p->flags = from->flags;
				p->model = from->model;
				p->owner = from->owner;
				VectorCopy (from->ent.origin, p->ent.origin);
				VectorCopy (from->ent.angles, p->ent.angles);
				if (placed)
					memcpy (c->rot + 9*i, from_rot, 9*sizeof(float));
				p->ent.colormap = vid.colormap;
				p->ent.aw_cut_box = from->ent.aw_cut_box;
				p->ent.aw_light = from->ent.aw_light;
				p->s = from->s;
				p->c = from->c;
				VectorCopy (from->mins, p->mins);
				VectorCopy (from->maxs, p->maxs);
				goto counted;
			}
		}
		else
		{
			if (!(i % per))
			{
				int take = lim - i < per ? lim - i : per;
				if (!(pack = Chim_File (e->file)) ||
					!Chim_PackRead (pack, e->disk.offset + CHIM_CHUNK_HEAD_BYTES + (long)i*rb,
					raw, (long)take*rb))
					goto bad;
				*budget -= (long)take*rb;
			}
			rec = raw + (i % per)*rb;
		}
		if (!(placed ? ChimFormat_RecordPlaced (rec, &r) : ChimFormat_Record (rec, &r)) ||
			r.pid < first ||
			r.pid - first >= total || r.owner >= frame_count || (i < head.owned) != (r.owner + base == index) ||
			(i >= lim && (int)r.owner != span.last_owner))
			goto bad;
		p->pid = r.pid;
		p->flags = r.flags;
		p->model = r.model;
		p->owner = r.owner + base;
		VectorCopy (r.origin, p->ent.origin);
		p->ent.origin[0] += dx;
		p->ent.origin[1] += dy;
		p->ent.angles[YAW] = r.yaw;
		p->ent.angles[PITCH] = r.pitch;		/* 0 before 0.8 */
		p->ent.angles[ROLL] = r.roll;
		if (placed)
			ChimPlaced_AnglesMatrix (p->ent.angles, (float (*)[3])(c->rot + 9*i));
		p->ent.colormap = vid.colormap;
		/* A piece of a long structure: its structure's cut box (chim_cuts.c). */
		p->ent.aw_cut_box = ChimCuts_Box (r.pid);
		/* 0.12: the placement's light level (flags bits 8-15); 0 before 0.12 */
		p->ent.aw_light = ChimFormat_RecordLight (chim_world.minor, r.flags);
		Q_SinCosDeg (r.yaw, &p->s, &p->c);
		/* The record's drawn box (the AW_SceneryCapture box, rounded
		 * outward) serves efrags and the collision broadphase. */
		for (j=0 ; j<3 ; j++)
		{
			p->mins[j] = r.mins[j] + (j == 0 ? dx : j == 1 ? dy : 0);
			p->maxs[j] = r.maxs[j] + (j == 0 ? dx : j == 1 ? dy : 0);
		}
		/* No stored level: the light of the frame map's fires (ChimChunks_FireLights) */
		if (!p->ent.aw_light)
			p->ent.aw_light = ChimChunks_FireLevel (p->mins, p->maxs);
		/* A hinged door (aw_hinged_door.c): its present pose, a box for every
		 * pose. Reach copies made from the owner above copy all of it. */
		if (chim_hinged_door)
		{
			float radius = ChimChunks_HingeRadius (p), yaw = r.yaw;
			if (chim_hinged_door (r.pid, r.ref, p->ent.origin, radius, &yaw))
			{
				p->flags |= CHIM_PLACE_HINGED;
				if (yaw != r.yaw)
					PlaceYaw (c, i, yaw);
				for (j=0 ; j<2 ; j++)
				{
					p->mins[j] = p->ent.origin[j] - radius;
					p->maxs[j] = p->ent.origin[j] + radius;
				}
			}
		}
	counted:
		if (p->flags & CHIM_RECORD_OVER_16_LEAVES)
			c->over_16_leaves++;
		for (j=0 ; j<c->models && c->model_list[j].id != p->model ; j++)
			;
		if (j == c->models)
			c->model_list[c->models++].id = p->model;
	}
	/* The PVS row follows the records; it moves up behind the model list. */
	c->pvs = (byte *)(c->model_list + c->models);
	c->pvs_bytes = head.pvs_bytes;
	c->pvl = c->pvs + head.pvs_bytes;
	c->pvl_bytes = head.pvl_bytes;
	c->terrain_leaves = head.terrain_leaves;
	if (head.pvs_bytes + head.pvl_bytes)
	{
		if (!(pack = Chim_File (e->file)) ||
			!Chim_PackRead (pack, e->disk.offset + CHIM_CHUNK_HEAD_BYTES + rows,
			c->pvs, head.pvs_bytes + head.pvl_bytes))
			goto bad;
		*budget -= head.pvs_bytes + head.pvl_bytes;
	}
	/* 0.7: a referenced terrain's bytes, for the prefetch room (its own
	 * directory sizes hold only the reference block). */
	if (ChimModels_TerrainPlace (index, NULL, NULL, &e->terrain_bytes) < 0)
		goto bad;
	ChimZone_Trim (c, sizeof(*c) + n*sizeof(chim_place_t) + rot_bytes + c->models*sizeof(chim_chunk_model_t) +
		head.pvs_bytes + head.pvl_bytes);
	e->state = CHIM_STATE_LOADED;
	chim_frame.loaded++;
	chim_world.chunk_loads++;
	return 1;
bad:
	ChimZone_Free (&e->chunk);
	return -1;
}

/* Lock what the chunk uses and instantiate its placements. Returns 0 when a
 * model or the terrain is not resident (the caller loads it first). With
 * partial set, only the terrain must be resident: a placement whose model
 * is missing stays out (not drawn, not solid) until Complete finds it. */
static int Activate (int index, int partial)
{
	chim_entry_t *e = &chim_frame.entries[index];
	chim_chunk_t *c = e->chunk.data;
	chim_model_t *terrain = ChimModels_Terrain (index);
	int i, j, k, missing = 0;
	/* A window's chunk whose ground another frame's chunk holds: its
	 * placements only, its own terrain neither needed nor locked. */
	int own_ground = !(chim_frame.window && e->shadow >= 0);

	e->ready = 0;
	if (!terrain && own_ground)
		return 0;
	for (i=0 ; i<c->models ; i++)
		if (!(c->model_list[i].model = ChimModels_Find (c->model_list[i].id)))
		{
			if (!partial)
				return 0;
			missing++;
		}
	e->ready = !missing;
	e->partial = missing != 0;
	ChimZone_Lock (c);
	if (own_ground)
	{
		ChimZone_Lock (terrain);
		e->terrain_locked = 1;
		/* A referenced terrain (0.7) is chunk-local: its box moves by the shift,
		 * as the graft moves the terrain itself (chim_graft.c CopyGraft). */
		VectorAdd (terrain->model.mins, e->shift, c->mins);
		VectorAdd (terrain->model.maxs, e->shift, c->maxs);
		if (terrain->leafs - 1 != c->terrain_leaves)
			Con_DPrintf ("CHIM: chunk %ld terrain leaves differ from its head\n", (long)index);
	}
	else
	{
		e->terrain_locked = 0;
		c->mins[0] = c->mins[1] = c->mins[2] = 1e30f;
		c->maxs[0] = c->maxs[1] = c->maxs[2] = -1e30f;
	}
	for (i=0 ; i<c->models ; i++)
		if (c->model_list[i].model)
			ChimZone_Lock (c->model_list[i].model);
	for (i=0 ; i<c->records ; i++)
	{
		chim_place_t *p = &c->places[i];
		for (j=0 ; c->model_list[j].id != p->model ; j++)
			;
		p->ent.model = c->model_list[j].model ? &c->model_list[j].model->model : NULL;
		p->ent.efrag = NULL;
		p->linked = p->leaves = 0;
		for (k=0 ; k<3 ; k++)
		{
			if (p->mins[k] < c->mins[k]) c->mins[k] = p->mins[k];
			if (p->maxs[k] > c->maxs[k]) c->maxs[k] = p->maxs[k];
		}
	}
	/* Its streamed statics whose models are resident; the rest follow
	 * (Complete) like a partial chunk's models. */
	if (ChimStatics_Activate (index))
	{
		missing++;
		e->ready = 0;
		e->partial = 1;
	}
	if (missing)
		pressure.partial++;
	e->state = CHIM_STATE_ACTIVE;
	chim_frame.active++;
	counts.activations++;
	world_dirty = 1;
	return 1;
}

static void Deactivate (int index)
{
	chim_entry_t *e = &chim_frame.entries[index];
	chim_chunk_t *c = e->chunk.data;
	int i;

	for (i=0 ; i<c->records ; i++)
	{
		Unlink (&c->places[i]);
		/* Whatever the counters say: no link may outlive the model
		 * (CHIM-FRAME-EDGE-EFRAG-CRASH-36). */
		DropEfrags (&c->places[i].ent);
		c->places[i].leaves = 0;
		c->places[i].ent.model = NULL;
	}
	ChimStatics_Deactivate (index);
	for (i=0 ; i<c->models ; i++)
	{
		if (c->model_list[i].model)
			ChimZone_Unlock (c->model_list[i].model);
		c->model_list[i].model = NULL;
	}
	if (e->terrain_locked)
		ChimZone_Unlock (e->terrain.data);
	e->terrain_locked = 0;
	ChimZone_Unlock (c);
	e->partial = 0;
	e->ready = 0;
	e->state = CHIM_STATE_LOADED;
	chim_frame.active--;
	counts.deactivations++;
	world_dirty = 1;
}

/* A partially active chunk: lock the models that have arrived since and
 * give their placements their model; Reconcile links them. Returns 1 when
 * any placement got its model. */
static int Complete (int index)
{
	chim_entry_t *e = &chim_frame.entries[index];
	chim_chunk_t *c = e->chunk.data;
	int i, j, added = 0, missing = 0;

	for (i=0 ; i<c->models ; i++)
	{
		if (c->model_list[i].model)
			continue;
		if (!(c->model_list[i].model = ChimModels_Find (c->model_list[i].id)))
		{
			missing++;
			continue;
		}
		ChimZone_Lock (c->model_list[i].model);
		for (j=0 ; j<c->records ; j++)
			if (c->places[j].model == c->model_list[i].id)
			{
				c->places[j].ent.model = &c->model_list[i].model->model;
				added = 1;
			}
	}
	{
		/* Streamed statics whose models arrived are placed (and linked by
		 * ChimChunks_Link); the count is what still waits. */
		int before = ChimStatics_Missing (index) != 0;
		int waiting = ChimStatics_Activate (index);
		if (before && !waiting)
			added = 1;
		missing += waiting;
	}
	e->partial = missing != 0;
	e->ready = !missing;
	return added;
}

/* ---------------------------------------------------------------- the ring */

static float Distance (const chim_entry_t *e, const float *p)
{
	float dx = p[0] < e->low[0] ? e->low[0] - p[0] : p[0] > e->high[0] ? p[0] - e->high[0] : 0;
	float dy = p[1] < e->low[1] ? e->low[1] - p[1] : p[1] > e->high[1] ? p[1] - e->high[1] : 0;
	/* Compared against radii squared: no square root. */
	return dx*dx + dy*dy;
}

/* What the chunk still needs: 1 catalogue, 2 terrain, 3 a model, 4 activation,
 * 5 completion (a partially active chunk whose missing models arrived), 0 nothing. */
unsigned long chim_need_calls;	/* scheduler work, for the tests */

static int Need (int index, float active2, unsigned *model)
{
	chim_entry_t *e = &chim_frame.entries[index];
	chim_chunk_t *c;
	int i;
	chim_need_calls++;
	if (e->state == CHIM_STATE_ACTIVE)
	{
		if (!e->partial)
			return 0;
		c = e->chunk.data;
		for (i=0 ; i<c->models ; i++)
			if (!c->model_list[i].model && !ChimModels_Find (c->model_list[i].id))
			{
				*model = c->model_list[i].id;
				return 3;
			}
		if ((*model = ChimStatics_Missing (index)) != 0)
			return 3;
		return 5;
	}
	if (e->state == CHIM_STATE_ABSENT || !e->chunk.data)
		return 1;
	if (!ChimModels_Terrain (index) && !(chim_frame.window && e->shadow >= 0))
		return 2;
	c = e->chunk.data;
	/* A prefetched chunk outside the active ring that was complete stays
	 * so as far as scheduling goes; Activate checks again. */
	if (e->ready && e->distance > active2)
		return 0;
	for (i=0 ; i<c->models ; i++)
		if (!ChimModels_Find (c->model_list[i].id))
		{
			e->ready = 0;
			*model = c->model_list[i].id;
			return 3;
		}
	if ((*model = ChimStatics_Missing (index)) != 0)
	{
		e->ready = 0;
		return 3;
	}
	e->ready = 1;
	return e->distance <= active2 ? 4 : 0;
}

/* The frame world follows the active set. An update that finds no room
 * waits 25 ticks: each try may evict prefetched data to make room. Phase 0
 * (after chunks left): give their terrain back; 1 (end of a tick): join
 * within the per-frame budget, more next tick; 2 (prime): everything. */
static void Graft (int phase)
{
	int r;
	if (!world_dirty || ticks < world_retry)
		return;
	r = ChimGraft_Update (phase);
	if (r == 1)
		world_dirty = 0;
	else if (!r)
		world_retry = ticks + 25;
}

/* Prefetch (work for a chunk beyond the active ring) goes only into free
 * room: twice the bytes it reads next, plus 64 KiB, must fit the largest
 * free block, so it never evicts. With eviction, two prefetched chunks whose
 * models do not fit together evicted each other's models in turn, reading
 * all the time while standing still (CHIM-ZONE-RING-THRASH-33). Chunks in
 * the active ring still evict, least recently used first. */
static unsigned long	prefetch_held;
static int PrefetchRoom (int index, int need, unsigned model, float active2)
{
	chim_entry_t *e = &chim_frame.entries[index];
	long bytes;
	if (!chim_prefetch_room.value || e->distance <= active2)
		return 1;
	if (need == 1)
		bytes = 16384;
	else if (need == 2)
		bytes = e->terrain_bytes ? e->terrain_bytes : (long)e->disk.render + (long)e->disk.collision;
	else if (need == 3 && ChimStatics_IsStatic (model))
		bytes = ChimStatics_Bytes (model);
	else if (need == 3)
		bytes = model < chim_world.models ? (long)chim_world.model[model].bytes : 0;
	else
		return 1;
	if (bytes < 0x3ff00000L && ChimZone_HasFree ((int)(2*bytes + 65536)))
		return 1;
	prefetch_held++;
	return 0;
}

unsigned long ChimChunks_PrefetchHeld (void)
{
	return prefetch_held;
}

static void MapLine (const char *line)
{
	Con_Printf ("CHIM zone %s\n", line);
}

/* A chunk that could not be loaded waits (50 ticks; one tick for a chunk
 * without its ground within the collision margin, with chim_release), or
 * less: every release of an active chunk lets the waiting ones try again
 * (Released). The line
 * says which part failed and why: the zone had no room (with the request
 * and what the zone holds), or the data did not decode. */
static void Failed (int index, int need, unsigned model, int zone, int asked, int wait)
{
	static const char *part[] = {"", "catalogue", "terrain", "model", "", ""};
	chim_zone_stats_t s;
	chim_entry_t *e = &chim_frame.entries[index];
	e->failed_until = ticks + wait;
	chim_world.failed_loads++;
	if (zone)
		pressure.zone++;
	else
		pressure.data++;
	/* One line per chunk and 50 ticks: a chunk that tries again every tick
	 * does not fill the console. */
	if (e->failed_said && ticks + 1 < e->failed_said + 50)
		return;
	e->failed_said = ticks + 1;
	if (!zone)
	{
		if (need == 3 && ChimStatics_IsStatic (model))
			Con_Printf ("CHIM: chunk %ld: streamed static model %s unavailable; its statics stay out\n", (long)index, ChimStatics_Name (model));
		else if (need == 3)
			Con_Printf ("CHIM: chunk %ld not loaded: bad data in model %lu; retrying\n", (long)index, (unsigned long)model);
		else
			Con_Printf ("CHIM: chunk %ld not loaded: bad data in its %s; retrying\n", (long)index, part[need]);
		return;
	}
	ChimZone_Stats (&s);
	/* The zone's layout with the first such failure of a map (all of them
	 * with chim_debug): where the locked blocks split the room. */
	if (!counts.zone_maps++ || chim_debug.value)
		ChimZone_Map (MapLine);
	if (need == 3 && ChimStatics_IsStatic (model))
		Con_Printf ("CHIM: chunk %ld: streamed static model %s waits: zone full (%ld bytes; largest free %ld, free %lu, locked %ld of %lu); retrying\n",
			(long)index, ChimStatics_Name (model), (long)asked, (long)s.largest_free, s.free_bytes, (long)s.locked_bytes,
			s.used_bytes + s.free_bytes);
	else if (need == 3)
		Con_Printf ("CHIM: chunk %ld not loaded: zone full (model %lu, %ld bytes; largest free %ld, free %lu, locked %ld of %lu); retrying\n",
			(long)index, (unsigned long)model, (long)asked, (long)s.largest_free, s.free_bytes, (long)s.locked_bytes,
			s.used_bytes + s.free_bytes);
	else
		Con_Printf ("CHIM: chunk %ld not loaded: zone full (its %s, %ld bytes; largest free %ld, free %lu, locked %ld of %lu); retrying\n",
			(long)index, part[need], (long)asked, (long)s.largest_free, s.free_bytes, (long)s.locked_bytes,
			s.used_bytes + s.free_bytes);
}

/* An active chunk went: chunks waiting after a failed load try again now. */
static void Released (void)
{
	int i;
	for (i=0 ; i<chim_frame.count ; i++)
		chim_frame.entries[i].failed_until = 0;
}

/* The zone has no room for chunk index (within the active radius): release
 * the active chunk farthest from the player that is farther than it and
 * outside the collision margin, so the nearer chunk wins (chim_release).
 * Chunks past the active radius (kept only by the load radius's
 * hysteresis) go first, being the farthest. Returns 1 when one went.
 *
 * chim_release 2 (the default; CHIM-ZONE-RELEASE-FLICKER-42): only what makes
 * room goes. The locks the farther chunks hold (catalogue, terrain and its
 * frame-world lock, models) are counted farthest first until the request
 * (need bytes, header included) would fit a run of unlocked blocks
 * (ChimZone_FitsWithout); then exactly those chunks go, at once. When even
 * all of them would not make a run that large (the room is split by locked
 * blocks of nearer chunks), nothing goes: the first method (chim_release 1)
 * released chunk after chunk for a request that still failed, and the
 * released chunks came back 50 ticks later, so buildings and their outlines
 * popped in and out while the player stood still (Ebonheart, v0.0.42-dev1).
 * The catalogue or terrain of a chunk within the collision margin (its
 * ground) still releases as the first method does: no hole to fall into for
 * a steadier picture. */
#define CHIM_RELEASE_LOCKS	(4*1024)	/* locks a release plan can count */
static void			*release_locks[CHIM_RELEASE_LOCKS];
static short		release_order[CHIM_MAX_CHUNKS];
unsigned long		chim_release_refused;	/* plans that found no room: nothing released */

static int ReleaseLocks (int index, int n)
{
	chim_entry_t *e = &chim_frame.entries[index];
	chim_chunk_t *c = e->chunk.data;
	int i;
	if (!c || n + 3 + c->models > CHIM_RELEASE_LOCKS)
		return -1;
	release_locks[n++] = c;
	if (e->terrain.data)
	{
		if (e->terrain_locked)	/* a window's chunk on another frame's ground locks none */
			release_locks[n++] = e->terrain.data;
		if (e->grafted)			/* the frame world's lock, dropped by ChimGraft_Update (0) */
			release_locks[n++] = e->terrain.data;
	}
	for (i=0 ; i<c->models ; i++)
		if (c->model_list[i].model)
			release_locks[n++] = c->model_list[i].model;
	return n;
}

static void ReleaseDone (int far, float active2, int index)
{
	if (chim_frame.entries[far].distance > active2)
		pressure.band++;
	else
	{
		pressure.ring++;
		if (chim_debug.value)
			Con_Printf ("CHIM: zone full: chunk %ld released for nearer chunk %ld\n", (long)far, (long)index);
	}
	Deactivate (far);
	/* Not active again for 50 ticks (unless the player comes within the
	 * collision margin of it): else the next nearer chunk short of room
	 * releases it again at once, and loads chase each other. */
	chim_frame.entries[far].released_until = ticks + 50;
}

static int Release (int index, float active2, float urgent2, int need, int part)
{
	int i, k, far = -1, count = 0, locks = 0;
	float d = chim_frame.entries[index].distance;
	/* The ground under the player outranks a steady picture: the catalogue
	 * or terrain of a chunk within the collision margin lets go as the first
	 * method does. A model it lacks leaves no hole (chim_partial). */
	if (chim_release.value >= 2 && need > 0 && (d > urgent2 || part == 3))
	{
		/* The farther active chunks, farthest first. */
		for (i=0 ; i<chim_frame.count ; i++)
		{
			chim_entry_t *e = &chim_frame.entries[i];
			if (e->state != CHIM_STATE_ACTIVE || e->distance <= d || e->distance <= urgent2)
				continue;
			for (k=count ; k>0 && chim_frame.entries[release_order[k-1]].distance < e->distance ; k--)
				release_order[k] = release_order[k-1];
			release_order[k] = (short)i;
			count++;
		}
		for (k=0 ; k<count ; k++)
		{
			if ((locks = ReleaseLocks (release_order[k], locks)) < 0)
				break;
			if (ChimZone_FitsWithout (need, release_locks, locks))
			{
				for (i=0 ; i<=k ; i++)
					ReleaseDone (release_order[i], active2, index);
				Reconcile ();
				ChimGraft_Update (0);
				Released ();
				return 1;
			}
		}
		chim_release_refused++;
		if (chim_debug.value)
			Con_Printf ("CHIM: zone full: chunk %ld waits; releasing %ld farther chunks would not make %ld bytes in one run\n",
				(long)index, (long)count, (long)need);
		return 0;
	}
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_entry_t *e = &chim_frame.entries[i];
		if (e->state != CHIM_STATE_ACTIVE || e->distance <= d || e->distance <= urgent2)
			continue;
		if (far < 0 || e->distance > chim_frame.entries[far].distance)
			far = i;
	}
	if (far < 0)
		return 0;
	ReleaseDone (far, active2, index);
	Reconcile ();
	/* Its terrain leaves the frame world now, which drops the world's lock. */
	ChimGraft_Update (0);
	Released ();
	return 1;
}

static short	candidate[CHIM_MAX_CHUNKS];

/* Lock (on) or unlock what chunk index has in the zone: its catalogue,
 * its terrain and its resident models (index < 0: nothing). Between the
 * two calls nothing may be loaded or evicted but by the zone itself. */
#define CHIM_MAX_PIN	256		/* past this many models a chunk pins only the first */
static void			*pinned[CHIM_MAX_PIN];
static int			npinned;
static void Pin (int index, int on)
{
	chim_entry_t *e;
	chim_chunk_t *c;
	int i;
	if (index < 0)
		return;
	if (!on)
	{
		for (i=0 ; i<npinned ; i++)
			ChimZone_Unlock (pinned[i]);
		npinned = 0;
		return;
	}
	e = &chim_frame.entries[index];
	c = e->chunk.data;
	npinned = 0;
	if (c)
		pinned[npinned++] = c;
	if (e->terrain.data && ChimModels_Terrain (index))
		pinned[npinned++] = e->terrain.data;
	for (i=0 ; c && i<c->models && npinned<CHIM_MAX_PIN ; i++)
	{
		chim_model_t *m = ChimModels_Find (c->model_list[i].id);
		if (m)
			pinned[npinned++] = m;
	}
	for (i=0 ; i<npinned ; i++)
		ChimZone_Lock (pinned[i]);
}

/* A chunk within the collision margin still needs work. */
static int UrgentPending (int candidates, float urgent2)
{
	int j;
	unsigned model;
	for (j=0 ; j<candidates ; j++)
	{
		chim_entry_t *e = &chim_frame.entries[candidate[j]];
		if ((e->state != CHIM_STATE_ACTIVE || e->partial) && e->distance <= urgent2 && Need (candidate[j], 1e30f, &model))
			return 1;
	}
	return 0;
}

/* The safety margin: how far the nearest chunk of the frame without its
 * ground in the frame world is (0: the player stands on one). */
static void Margin (void)
{
	float nearest = 1e30f;
	int i;
	for (i=0 ; i<chim_frame.count ; i++)
		if (!Grounded (&chim_frame.entries[i]) && chim_frame.entries[i].distance < nearest)
			nearest = chim_frame.entries[i].distance;
	ring.margin = nearest >= 1e30f ? -1 : (float)sqrt (nearest);
	if (ring.margin >= 0 && (ring.margin_min < 0 || ring.margin < ring.margin_min))
		ring.margin_min = ring.margin;
}

/* The smallest safety margin since the last call (units; -1: every chunk
 * grafted), the loads made past the budget, and whether there is a point
 * ahead (the player moves). */
void ChimChunks_Streaming (int *margin, unsigned long *urgent_loads, int *ahead)
{
	*margin = ring.margin_min < 0 ? -1 : (int)ring.margin_min;
	*urgent_loads = ring.urgent_loads;
	*ahead = ring.has_ahead;
	ring.margin_min = ring.margin;
}

/* The ring's radii: chunks within the active radius are active (drawn,
 * solid); within the load radius they are loaded (the prefetch margin, also
 * the hysteresis before a chunk is released). The active radius follows
 * the view distance (chim_draw_distance 0) plus the world's hysteresis. */
float ChimChunks_ActiveRadius (void)
{
	return (chim_draw_distance.value > 0 ? chim_draw_distance.value : Chim_ViewDistance ()) +
		chim_frame.settings.hysteresis;
}

float ChimChunks_LoadRadius (void)
{
	return ChimChunks_ActiveRadius () + (chim_prefetch.value >= 0 ? chim_prefetch.value : chim_frame.settings.prefetch_margin);
}

/* Which way the player moves: the step since the last tick (a step of a
 * chunk or more is a teleport, not a direction). The point ahead is the
 * look-ahead distance (chim_lookahead; -1: the prefetch margin) that way;
 * standing still, there is none. */
static void Ahead (const vec3_t origin)
{
	vec3_t step;
	/* The world's margin, times Chim_LookaheadScale with extra memory (1 without). */
	float length, look = chim_lookahead.value >= 0 ? chim_lookahead.value :
		chim_frame.settings.prefetch_margin * Chim_LookaheadScale ();
	VectorSubtract (origin, ring.last, step);
	step[2] = 0;
	length = (float)sqrt (step[0]*step[0] + step[1]*step[1]);
	ring.has_ahead = 0;
	if (ring.moved && length > 0.5f && length < chim_frame.frame.grain && look > 0)
	{
		ring.ahead[0] = origin[0] + step[0] / length * look;
		ring.ahead[1] = origin[1] + step[1] / length * look;
		ring.ahead[2] = origin[2];
		ring.has_ahead = 1;
	}
	VectorCopy (origin, ring.last);
	ring.moved = 1;
}

void ChimChunks_Tick (const vec3_t origin, long budget, int prime)
{
	float load2, active2, urgent2, r, ahead;
	int i, j, k, best, need, changed = 0, guard, candidates = 0, result, pin;
	unsigned model = 0;
	unsigned long zone_before;

	if (!chim_frame.count)
		return;
	/* Type 1: the window's frames follow the player first (chim_window). */
	WindowUpdate (origin);
	r = ChimChunks_ActiveRadius ();
	active2 = r*r;
	r = ChimChunks_LoadRadius ();
	load2 = r*r;
	urgent2 = chim_frame.settings.collision_margin * chim_frame.settings.collision_margin;
	Ahead (origin);
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_entry_t *e = &chim_frame.entries[i];
		e->distance = e->priority = Distance (e, origin);
		if (ring.has_ahead && (ahead = Distance (e, ring.ahead)) < e->priority)
			e->priority = ahead;
		if (e->state == CHIM_STATE_ACTIVE && e->distance > load2)
		{
			Deactivate (i);
			changed = 1;
		}
	}
	if (changed)
	{
		Reconcile ();
		Released ();
	}
	/* Before anything is loaded: a deactivated chunk's terrain must not be
	 * evicted while the world still points into it (the world holds its
	 * own locks, released by the update). */
	Graft (prime ? 2 : 0);
	changed = 0;
	/* The chunks within the load radius of the player or of the point ahead
	 * that are not active, by priority (the nearer of the two distances;
	 * insertion sort: a ring holds a few dozen). */
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_entry_t *e = &chim_frame.entries[i];
		if (e->priority > load2 || (e->state == CHIM_STATE_ACTIVE && !e->partial) ||
			(chim_frame.window && chim_frame.slot[e->slot].leaving))
			continue;
		for (k=candidates ; k>0 && chim_frame.entries[candidate[k-1]].priority > e->priority ; k--)
			candidate[k] = candidate[k-1];
		candidate[k] = (short)i;
		candidates++;
	}
	if (prime && chim_debug.value)
		Con_Printf ("CHIM: %ld candidates\n", (long)candidates);
	for (guard=0 ; guard<4*CHIM_MAX_CHUNKS ; guard++)
	{
		/* Past the budget only for a chunk within the collision margin:
		 * the ground under the player never waits for a later frame. */
		int urgent = !prime && budget <= 0;
		if (prime && chim_debug.value && !(guard % 64))
			Con_Printf ("CHIM: step %ld: %ld active, %ld loaded, %lu models\n",
				(long)guard, (long)chim_frame.active, (long)chim_frame.loaded, chim_world.model_loads);
		if (ChimModels_Busy ())
		{
			/* A stream in progress continues before anything else. */
			if (urgent && !UrgentPending (candidates, urgent2))
				break;
			if (urgent)
				ring.urgent_loads++;
			if (ChimModels_Step ((unsigned)-1, &budget) < 0)
				break;
			continue;
		}
		best = -1;
		need = 0;
		for (j=0 ; j<candidates && best < 0 ; j++)
		{
			i = candidate[j];
			if ((chim_frame.entries[i].state == CHIM_STATE_ACTIVE && !chim_frame.entries[i].partial) ||
				ticks < chim_frame.entries[i].failed_until ||
				(chim_frame.entries[i].state != CHIM_STATE_ACTIVE && ticks < chim_frame.entries[i].released_until &&
				chim_frame.entries[i].distance > urgent2))
				continue;
			if (urgent && chim_frame.entries[i].distance > urgent2)
				continue;
			if ((need = Need (i, active2, &model)) != 0 && PrefetchRoom (i, need, model, active2))
				best = i;
		}
		if (best < 0)
			break;
		if (urgent)
			ring.urgent_loads++;
		if (chim_debug.value >= 2)
			Con_Printf ("CHIM: chunk %ld need %ld model %lu\n", (long)best, (long)need, (unsigned long)model);
		zone_before = ChimZone_Failures (NULL);
		result = 0;
		switch (need)
		{
		case 1:
			result = LoadCatalogue (best, &budget);
			break;
		case 2:
			/* With chim_release, a chunk the player can see keeps what it
			 * has while it loads the rest (Pin): making room for its
			 * terrain or one model must not evict its catalogue, terrain or
			 * another of its models. The first method could, and a chunk
			 * whose models did not fit together evicted them in turn,
			 * loading for ever. */
			pin = chim_release.value && chim_frame.entries[best].distance <= active2 ? best : -1;
			Pin (pin, 1);
			result = ChimModels_TerrainStep (best, &budget);
			Pin (pin, 0);
			break;
		case 3:
			pin = chim_release.value && chim_frame.entries[best].distance <= active2 ? best : -1;
			Pin (pin, 1);
			result = ChimStatics_IsStatic (model) ? ChimStatics_Step (model, &budget) : ChimModels_Step (model, &budget);
			Pin (pin, 0);
			break;
		case 4:
			if (Activate (best, 0))
				changed = 1;
			break;
		case 5:
			if (Complete (best))
				changed = 1;
			break;
		}
		if (result < 0)
		{
			chim_entry_t *e = &chim_frame.entries[best];
			int asked, zone = ChimZone_Failures (&asked) != zone_before;
			/* No room for a chunk the player can see: farther chunks give
			 * theirs (chim_release), and the same chunk tries again. */
			if (zone && chim_release.value && e->distance <= active2 && Release (best, active2, urgent2, asked, need))
				continue;
			Failed (best, need, model, zone, asked,
				chim_release.value && e->distance <= urgent2 && e->state != CHIM_STATE_ACTIVE ? 1 : 50);
			/* Its ground and its other placements do not wait for a model
			 * that has no room (chim_partial): never a hole to fall into. */
			if (need == 3 && chim_partial.value && e->state == CHIM_STATE_LOADED && e->distance <= active2 &&
				Activate (best, 1))
				changed = 1;
		}
		if (changed && !prime)
		{
			Reconcile ();
			changed = 0;
		}
	}
	if (changed)
		Reconcile ();
	Graft (prime ? 2 : 1);
	Margin ();
	ticks++;
}

/* The whole ring at once (a spawn or the first frame of a map). */
void ChimChunks_Prime (const vec3_t origin, long budget)
{
	ChimChunks_Tick (origin, budget, 1);
}

/* ---------------------------------------------------------------- collision */

/* SV_ClipMoveToEntity for a placed brush model, origin and yaw given. */
static void ClipModel (model_t *m, const vec3_t origin, float s, float c, vec3_t start, vec3_t mins,
	vec3_t maxs, vec3_t end, trace_t *best)
{
	trace_t trace;
	vec3_t offset, start_l, end_l, delta, temp;
	hull_t *hull;
	float speed;
	int rotated = s != 0 || c != 1;

	memset (&trace, 0, sizeof(trace));
	trace.fraction = 1;
	trace.allsolid = true;
	VectorCopy (end, trace.endpos);
	if (maxs[0] - mins[0] < 3)
		hull = &m->hulls[0];
	else if (maxs[0] - mins[0] <= 32)
		hull = &m->hulls[1];
	else
		hull = &m->hulls[2];
	if (!hull->clipnodes)
		return;
	VectorSubtract (hull->clip_mins, mins, offset);
	VectorAdd (offset, origin, offset);
	VectorSubtract (start, offset, start_l);
	VectorSubtract (end, offset, end_l);
	if (rotated)
	{
		VectorCopy (start_l, temp);
		start_l[0] = c*temp[0] + s*temp[1];
		start_l[1] = -s*temp[0] + c*temp[1];
		VectorCopy (end_l, temp);
		end_l[0] = c*temp[0] + s*temp[1];
		end_l[1] = -s*temp[0] + c*temp[1];
	}
	SV_RecursiveHullCheck (hull, hull->firstclipnode, 0, 1, start_l, end_l, &trace);
	if (!trace.allsolid && trace.fraction < 1)
	{
		VectorSubtract (end_l, start_l, delta);
		speed = DotProduct (delta, trace.plane.normal);
		if (speed < 0)
			speed = -speed;
		if (speed > 0)
		{
			trace.fraction -= CHIM_DIST_EPSILON/speed;
			if (trace.fraction < 0)
				trace.fraction = 0;
			VectorMA (start_l, trace.fraction, delta, trace.endpos);
		}
	}
	if (rotated && trace.fraction != 1)
	{
		VectorCopy (trace.endpos, temp);
		trace.endpos[0] = c*temp[0] - s*temp[1];
		trace.endpos[1] = s*temp[0] + c*temp[1];
		VectorCopy (trace.plane.normal, temp);
		trace.plane.normal[0] = c*temp[0] - s*temp[1];
		trace.plane.normal[1] = s*temp[0] + c*temp[1];
	}
	if (trace.fraction != 1)
		VectorAdd (trace.endpos, offset, trace.endpos);
	if (trace.allsolid)
	{
		trace.fraction = 0;
		VectorCopy (start, trace.endpos);
	}
	AW_MergeCollisionTrace (best, &trace, sv.edicts);
}

/* ClipModel with the model turned by a matrix (model -> world): the 0.8
 * fallback for a tilted placement whose model has no usable piece table. The
 * stored hull was expanded in the model's frame, so the box turns with it
 * (the yaw path's approximation, on three axes). */
static void ClipModelTurned (model_t *m, const vec3_t origin, float rot[3][3], vec3_t start, vec3_t mins,
	vec3_t maxs, vec3_t end, trace_t *best)
{
	trace_t trace;
	vec3_t offset, start_l, end_l, delta, temp;
	hull_t *hull;
	float speed;
	int i;

	memset (&trace, 0, sizeof(trace));
	trace.fraction = 1;
	trace.allsolid = true;
	VectorCopy (end, trace.endpos);
	if (maxs[0] - mins[0] < 3)
		hull = &m->hulls[0];
	else if (maxs[0] - mins[0] <= 32)
		hull = &m->hulls[1];
	else
		hull = &m->hulls[2];
	if (!hull->clipnodes)
		return;
	VectorSubtract (hull->clip_mins, mins, offset);
	VectorAdd (offset, origin, offset);
	VectorSubtract (start, offset, temp);
	for (i=0 ; i<3 ; i++)
		start_l[i] = rot[0][i]*temp[0] + rot[1][i]*temp[1] + rot[2][i]*temp[2];
	VectorSubtract (end, offset, temp);
	for (i=0 ; i<3 ; i++)
		end_l[i] = rot[0][i]*temp[0] + rot[1][i]*temp[1] + rot[2][i]*temp[2];
	SV_RecursiveHullCheck (hull, hull->firstclipnode, 0, 1, start_l, end_l, &trace);
	if (!trace.allsolid && trace.fraction < 1)
	{
		VectorSubtract (end_l, start_l, delta);
		speed = DotProduct (delta, trace.plane.normal);
		if (speed < 0)
			speed = -speed;
		if (speed > 0)
		{
			trace.fraction -= CHIM_DIST_EPSILON/speed;
			if (trace.fraction < 0)
				trace.fraction = 0;
			VectorMA (start_l, trace.fraction, delta, trace.endpos);
		}
	}
	if (trace.fraction != 1)
	{
		VectorCopy (trace.endpos, temp);
		for (i=0 ; i<3 ; i++)
			trace.endpos[i] = DotProduct (rot[i], temp);
		VectorCopy (trace.plane.normal, temp);
		for (i=0 ; i<3 ; i++)
			trace.plane.normal[i] = DotProduct (rot[i], temp);
		VectorAdd (trace.endpos, offset, trace.endpos);
	}
	if (trace.allsolid)
	{
		trace.fraction = 0;
		VectorCopy (start, trace.endpos);
	}
	AW_MergeCollisionTrace (best, &trace, sv.edicts);
}

/* One placement's collision. 0.4-0.7: ClipModel (the yaw path, unchanged).
 * 0.8: the model's piece table placed by the record's matrix and expanded by
 * the world-aligned box (chim_placed_clip.c); without a usable table (or
 * when a trace meets more than the scratch holds) the stored hull: by the
 * yaw path for a yaw-only record, turned by the matrix otherwise. */
void ChimChunks_ClipPlace (chim_place_t *p, float *rot9, vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end,
	trace_t *best)
{
	if (rot9)
	{
		chim_model_t *cm = (chim_model_t *)p->ent.model;	/* the model is the block's first member */
		float (*rot)[3] = (float (*)[3])rot9;
		if (cm->pieces)
		{
			trace_t trace;
			memset (&trace, 0, sizeof(trace));
			trace.fraction = 1;
			VectorCopy (end, trace.endpos);
			if (ChimPlaced_TraceTable (cm->model.visdata, (const float (*)[3])rot, p->ent.origin, start, mins, maxs,
				end, &trace))
			{
				AW_MergeCollisionTrace (best, &trace, sv.edicts);
				return;
			}
		}
		if (p->ent.angles[PITCH] || p->ent.angles[ROLL])
		{
			ClipModelTurned (p->ent.model, p->ent.origin, rot, start, mins, maxs, end, best);
			return;
		}
	}
	ClipModel (p->ent.model, p->ent.origin, p->s, p->c, start, mins, maxs, end, best);
}

static void ClipPlacement (const chim_chunk_t *c, int j, vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end,
	trace_t *best)
{
	ChimChunks_ClipPlace (&c->places[j], c->rot ? c->rot + 9*j : NULL, start, mins, maxs, end, best);
}

/* Hinged doors (aw_hinged_door.c): the trace against placement pid alone,
 * its linked copy (the one drawn and solid). 0: not linked anywhere now.
 * A CHIM room's doors are its own placements (chim_room.c). */
int ChimChunks_DoorClip (unsigned pid, vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end, trace_t *trace)
{
	int i, j;
	if (ChimRoom_Active ())
		return ChimRoom_DoorClip (pid, start, mins, maxs, end, trace);
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_entry_t *e = &chim_frame.entries[i];
		chim_chunk_t *c;
		if (e->state != CHIM_STATE_ACTIVE)
			continue;
		c = e->chunk.data;
		for (j=0 ; j<c->records ; j++)
		{
			chim_place_t *p = &c->places[j];
			if (p->pid != pid || !(p->flags & CHIM_PLACE_HINGED) || !p->linked || !p->ent.model)
				continue;
			ClipPlacement (c, j, start, mins, maxs, end, trace);
			return 1;
		}
	}
	return 0;
}

void ChimChunks_Clip (vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end, trace_t *best)
{
	vec3_t low, high;
	int i, j, k;

	for (k=0 ; k<3 ; k++)
	{
		low[k] = (start[k] < end[k] ? start[k] : end[k]) + mins[k] - 1;
		high[k] = (start[k] > end[k] ? start[k] : end[k]) + maxs[k] + 1;
	}
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_entry_t *e = &chim_frame.entries[i];
		chim_chunk_t *c;
		if (e->state != CHIM_STATE_ACTIVE)
			continue;
		c = e->chunk.data;
		for (k=0 ; k<3 ; k++)
			if (low[k] > c->maxs[k] || high[k] < c->mins[k])
				break;
		if (k != 3)
			continue;
		for (j=0 ; j<c->records ; j++)
		{
			chim_place_t *p = &c->places[j];
			if (!p->linked)
				continue;
			for (k=0 ; k<3 ; k++)
				if (low[k] > p->maxs[k] || high[k] < p->mins[k])
					break;
			if (k != 3)
				continue;
			ClipPlacement (c, j, start, mins, maxs, end, best);
			if (best->allsolid)
				return;
		}
	}
}

/* dbg hud pin (INSPECT-CHIM-PLACEMENT-UNNAMED-42): the nearest linked placement a
 * point ray hits, with ClipModel's own hull test (the same collision SV_Move sees),
 * then its record re-read from the sector and its model name from the index. One
 * click = a handful of small reads; nothing is kept, the runtime placement is not
 * enlarged. 0: no placement on the ray. */
int ChimChunks_Pick (const vec3_t start, const vec3_t end, aw_chim_pick_t *out)
{
	vec3_t low, high, zero = {0, 0, 0}, s, e2;
	trace_t best;
	int i, j, k, hit_entry = -1, hit_record = -1;
	float nearest = 1;
	unsigned char raw[CHIM_RECORD_BYTES], row[CHIM_MODEL_DIR_BYTES];
	chim_record_t r;
	chim_pack_t *pack, index;

	memset (out, 0, sizeof(*out));
	VectorCopy (start, s);
	VectorCopy (end, e2);
	for (k=0 ; k<3 ; k++)
	{
		low[k] = (start[k] < end[k] ? start[k] : end[k]) - 1;
		high[k] = (start[k] > end[k] ? start[k] : end[k]) + 1;
	}
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_entry_t *e = &chim_frame.entries[i];
		chim_chunk_t *c;
		if (e->state != CHIM_STATE_ACTIVE)
			continue;
		c = e->chunk.data;
		for (k=0 ; k<3 ; k++)
			if (low[k] > c->maxs[k] || high[k] < c->mins[k])
				break;
		if (k != 3)
			continue;
		for (j=0 ; j<c->records ; j++)
		{
			chim_place_t *p = &c->places[j];
			if (!p->linked || !p->ent.model)
				continue;
			for (k=0 ; k<3 ; k++)
				if (low[k] > p->maxs[k] || high[k] < p->mins[k])
					break;
			if (k != 3)
				continue;
			memset (&best, 0, sizeof(best));
			best.fraction = 1;
			VectorCopy (e2, best.endpos);
			ClipPlacement (c, j, s, zero, zero, e2, &best);
			if (best.fraction < nearest && !best.allsolid)
			{
				nearest = best.fraction;
				hit_entry = i;
				hit_record = j;
			}
		}
	}
	if (hit_entry < 0)
		return 0;
	out->fraction = nearest;
	{
		chim_entry_t *e = &chim_frame.entries[hit_entry];
		chim_place_t *p = &((chim_chunk_t *)e->chunk.data)->places[hit_record];
		out->pid = p->pid;
		out->model = p->model;
		VectorCopy (p->ent.origin, out->origin);
		out->yaw = p->ent.angles[YAW];
		out->cell_x = chim_frame.window ? chim_frame.slot[e->slot].cx : chim_frame.frame.cx;
		out->cell_y = chim_frame.window ? chim_frame.slot[e->slot].cy : chim_frame.frame.cy;
		{
			/* the record's place: its own chunk's list, or (0.9) the owner's
			 * list that the chunk's reach reference names */
			const chim_entry_t *home = e;
			long at = (long)hit_record*(((chim_chunk_t *)e->chunk.data)->rot ? CHIM_RECORD_BYTES_PLACED :
				ChimFormat_RecordBytes (chim_world.minor));
			chim_chunk_head_t head;
			int owner, record;
			if (chim_world.minor >= CHIM_REACH_MINOR && hit_record >= ((chim_chunk_t *)e->chunk.data)->owned &&
				(pack = Chim_File (e->file)) && Chim_PackRead (pack, e->disk.offset, raw, CHIM_CHUNK_HEAD_BYTES) &&
				ChimFormat_ChunkHead (raw, &head) && head.reach_refs)
			{
				home = NULL;
				if (Chim_PackRead (pack, e->disk.offset + CHIM_CHUNK_HEAD_BYTES + (long)head.owned*CHIM_RECORD_BYTES_PLACED +
					(long)(hit_record - head.owned)*CHIM_REACH_REF_BYTES, raw, CHIM_REACH_REF_BYTES))
				{
					int slot_base = chim_frame.window ? chim_frame.slot[e->slot].base : 0;
					ChimFormat_ReachRef (raw, &owner, &record);
					if (owner + slot_base < chim_frame.count)
					{
						home = &chim_frame.entries[owner + slot_base];
						at = (long)record*CHIM_RECORD_BYTES_PLACED;
					}
				}
			}
			if (home && (pack = Chim_File (home->file)) &&
				Chim_PackRead (pack, home->disk.offset + CHIM_CHUNK_HEAD_BYTES + at,
				raw, CHIM_RECORD_BYTES) && ChimFormat_Record (raw, &r) && r.pid == p->pid)
			{
				out->ref = r.ref;
				out->cell_x += r.cell_dx;
				out->cell_y += r.cell_dy;
			}
		}
	}
	/* Model row: u32 name offset at +16, relative to the names table. */
	if (out->model < chim_world.models && Chim_PackOpen (&index, "world.cwi"))
	{
		if (Chim_PackRead (&index, chim_world.toc.models_at + (long)out->model*CHIM_MODEL_DIR_BYTES, row, sizeof(row)))
		{
			unsigned at = ChimFormat_U32 (row+16);
			char name[sizeof(out->name)];
			long left = index.bytes - (long)chim_world.toc.names_at - (long)at;
			int n = left < (long)sizeof(name) ? (int)left : (int)sizeof(name);
			if (n > 1 && Chim_PackRead (&index, chim_world.toc.names_at + (long)at, name, n))
			{
				name[n-1] = 0;
				for (k=0 ; name[k] ; k++)
					if ((unsigned char)name[k] < 32 || (unsigned char)name[k] > 126)
						name[k] = '?';
				memcpy (out->name, name, sizeof(out->name));
			}
		}
		Chim_PackClose (&index);
	}
	return 1;
}

/* ---------------------------------------------------------------- end */

void ChimChunks_End (void)
{
	int i;
	if (!chim_frame.entries)
		return;
	/* Host_ClearMemory has already reset the efrag pool. */
	link_world = NULL;
	ChimStatics_PoolReset ();
	for (i=0 ; i<chim_frame.count ; i++)
		if (chim_frame.entries[i].state == CHIM_STATE_ACTIVE)
			Deactivate (i);
	ChimModels_Abort ();
	ChimZone_EvictKind (CHIM_KIND_CHUNK, NULL);
	ChimZone_EvictKind (CHIM_KIND_TERRAIN, NULL);
	world_dirty = 0;
	world_retry = 0;
	if (chim_frame.window)
		for (i=0 ; i<CHIM_WINDOW_SLOTS ; i++)
			SlotRelease (i);
	ChimZone_Unlock (index_user.data);
	ChimZone_Free (&index_user);
	memset (&chim_frame, 0, sizeof(chim_frame));
	grid = NULL;
}

extern const char *(*aw_efrag_describe)(const entity_t *ent, char *out, int size);	/* r_efrag.c */
void ChimChunks_Init (void)
{
	ChimZone_SetEvict (CHIM_KIND_CHUNK, ChunkEvicted);
	aw_efrag_describe = ChimChunks_Describe;
}

/* What the renderer did with the placements in its last frame: stored for
 * drawing from a visible leaf (R_StoreEfrags sets visframe), and of those
 * how many stayed in one leaf (the cheap R_DrawSubmodelPolygons path, no
 * clipping down the world BSP). Counted on request only. */
void ChimChunks_LastFrame (int *sent, int *one_leaf_path, int *placements)
{
	int i, j;
	*sent = *one_leaf_path = *placements = 0;
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_chunk_t *c = chim_frame.entries[i].chunk.data;
		if (chim_frame.entries[i].state != CHIM_STATE_ACTIVE)
			continue;
		for (j=0 ; j<c->records ; j++)
		{
			chim_place_t *p = &c->places[j];
			if (!p->linked)
				continue;
			(*placements)++;
			if (p->ent.visframe != r_framecount)
				continue;
			(*sent)++;
			if (p->ent.topnode && p->ent.topnode->contents < 0)
				(*one_leaf_path)++;
		}
	}
}

void ChimChunks_Report (void)
{
	int sent, one_path, placements, i, flagged = 0;
	Con_Printf ("frame %ld %ld: %ld chunks, %ld loaded, %ld active (grain %ld)\n",
		(long)chim_frame.frame.cx, (long)chim_frame.frame.cy, (long)chim_frame.count, (long)chim_frame.loaded,
		(long)chim_frame.active, (long)chim_frame.frame.grain);
	Con_Printf ("placements linked %ld, efrags %ld (one leaf %ld, max leaves %ld)\n",
		(long)counts.placements_linked, (long)counts.efrags, (long)counts.one_leaf, (long)counts.max_leaves);
	Con_Printf ("actors frozen outside the ring: %lu; placements hidden by the view's list: %ld\n",
		frozen_last, (long)counts.hidden);
	Con_Printf ("activations %lu, deactivations %lu, reconciles %lu\n",
		counts.activations, counts.deactivations, counts.reconciles);
	ChimChunks_LastFrame (&sent, &one_path, &placements);
	for (i=0 ; i<chim_frame.count ; i++)
		if (chim_frame.entries[i].state == CHIM_STATE_ACTIVE)
			flagged += ((chim_chunk_t *)chim_frame.entries[i].chunk.data)->over_16_leaves;
	Con_Printf ("active records over 16 leaves (builder flag): %ld\n", (long)flagged);
	Con_Printf ("efrags in use %ld of %ld for CHIM (limit %ld, reserve %ld): %ld placements waiting, %lu waits so far; view leaf without a PVS row in %lu frames\n",
		(long)aw_efrags_used, (long)chim_efrag_limit, (long)AW_EFRAG_LIMIT, (long)CHIM_EFRAG_RESERVE,
		(long)counts.efrag_waiting, counts.efrag_capped, counts.novis_frames);
	Con_Printf ("last frame: %ld of %ld placements sent from visible leaves, %ld of them unclipped (one leaf)\n",
		(long)sent, (long)placements, (long)one_path);
}

/* For the host tests: the link counters as numbers. */
int ChimChunks_Hidden (void)
{
	return counts.hidden;
}

void ChimChunks_Counts (int *linked, int *efrags, int *one_leaf, int *max_leaves)
{
	*linked = counts.placements_linked;
	*efrags = counts.efrags;
	*one_leaf = counts.one_leaf;
	*max_leaves = counts.max_leaves;
}

/* ---------------------------------------------------------------- frame world support */

/* The efrag safety net (r_efrag.c): which placement or static an entity is, read only. */
const char *ChimChunks_Describe (const entity_t *ent, char *out, int size)
{
	int i;
	(void)size;
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_chunk_t *c = chim_frame.entries[i].chunk.data;
		const chim_place_t *p = (const chim_place_t *)ent;
		if (chim_frame.entries[i].state == CHIM_STATE_ABSENT || !c || p < c->places || p >= c->places + c->records)
			continue;
		sprintf (out, "CHIM placement %lu (chunk %d, state %d, linked %d, leaves %d)",
			(unsigned long)p->pid, i, chim_frame.entries[i].state, p->linked, p->leaves);
		return out;
	}
	return ChimStatics_Describe (ent, out, size);
}

/* An entity the frame world took out of its leaves (R_RemoveEfrags): when
 * it is a placement, ChimChunks_Link links it again. */
int ChimChunks_Forget (entity_t *ent)
{
	int i;
	if (ChimStatics_Forget (ent))
		return 1;
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_chunk_t *c = chim_frame.entries[i].chunk.data;
		chim_place_t *p = (chim_place_t *)ent;
		if (chim_frame.entries[i].state != CHIM_STATE_ACTIVE || p < c->places || p >= c->places + c->records)
			continue;
		if (p->leaves)
		{
			counts.efrags -= p->leaves;
			if (p->leaves == 1)
				counts.one_leaf--;
			p->leaves = 0;
		}
		return 1;
	}
	return 0;
}

int ChimChunks_CellEntry (int x, int y)
{
	if (!grid || x < 0 || y < 0 || x >= chim_frame.frame.nx || y >= chim_frame.frame.ny)
		return -1;
	return grid[y*chim_frame.frame.nx + x];
}

/* Before the world's leaves are replaced: every placement's efrags go back
 * to the pool unlinked; ChimChunks_Link links them into the new leaves. */
void ChimChunks_ReleaseEfrags (void)
{
	int i, j;
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_chunk_t *c = chim_frame.entries[i].chunk.data;
		if (chim_frame.entries[i].state != CHIM_STATE_ACTIVE)
			continue;
		for (j=0 ; j<c->records ; j++)
			if (c->places[j].leaves || c->places[j].ent.efrag)
			{
				ChimGraft_ReleaseEfrags (&c->places[j].ent);
				c->places[j].leaves = 0;
			}
	}
	counts.efrags = counts.one_leaf = counts.max_leaves = 0;
	ChimStatics_ReleaseEfrags ();
}

/* Actors stand on chunk terrain: outside the active ring they are frozen.
 * Only moving kinds; doors, platforms, triggers and timers run as before. */
int ChimChunks_Frozen (edict_t *ent)
{
	int movetype = (int)ent->v.movetype, x, y, e;
	float g = (float)chim_frame.frame.grain;
	if (!chim_frame.count || (movetype != MOVETYPE_STEP && movetype != MOVETYPE_TOSS &&
		movetype != MOVETYPE_BOUNCE && movetype != MOVETYPE_FLY && movetype != MOVETYPE_FLYMISSILE))
		return 0;
	if ((unsigned long)host_framecount != frozen_frame)
	{
		frozen_last = frozen_now;
		frozen_now = 0;
		frozen_frame = (unsigned long)host_framecount;
	}
	x = ent->v.origin[0] < chim_frame.frame.low[0] ? -1 : (int)((ent->v.origin[0] - chim_frame.frame.low[0]) / g);
	y = ent->v.origin[1] < chim_frame.frame.low[1] ? -1 : (int)((ent->v.origin[1] - chim_frame.frame.low[1]) / g);
	e = ChimChunks_CellEntry (x, y);
	if (e >= 0 && chim_frame.entries[e].grafted)
		return 0;
	frozen_now++;
	return 1;
}

int ChimChunks_FrozenLast (void)
{
	return (int)(frozen_now > frozen_last ? frozen_now : frozen_last);
}

/* ---------------------------------------------------------------- the window (type 1 crossings) */

/* Type 1 crossings (docs/chim/CELL_CROSSINGS.md, "Type 1: one continuous
 * world"; the design note of 19 October 2026, sections 3 and 5): the region
 * frames around the player are one window in one frame world, so walking
 * from one frame into the next is ordinary streaming, not a level change.
 *
 * - The window is the 2 x 2 block of cells (= region frames) meeting at the
 *   corner nearest the player: the quadrant of the cell the player stands in
 *   names it, as the prefetch picks its block (chim_prefetch.c); it moves to
 *   another corner only WINDOW_MARGIN past the cell's midline (hysteresis),
 *   well outside the active ring (draw distance + hysteresis, about 640 of
 *   the 1,024 units from the midline to the border).
 * - Fixed origin: every frame is placed at its offset from the frame the map
 *   started on (cell steps of 2,048 units); the session's coordinates are that
 *   frame's. Nothing is moved (no rebase).
 * - One frame world: the window's chunk grid (frame.low/nx/ny) covers the
 *   block; each place of it takes the chunk of the frame whose cell holds the
 *   chunk's centre (or, outside every cell, of the frame whose cell is
 *   nearest), so ground two frames share is grafted once. The other frames'
 *   chunks there keep only their placements (shadow: their ground is the
 *   owner's).
 * - Placements: each is drawn and collided by the frame whose cell holds its
 *   origin (CoreKeeps), never twice at a border.
 * - Joining reads the frame's chunk directory (a few KiB) and its streamed
 *   statics; leaving deactivates its chunks, waits until the frame world has
 *   let their ground go (Graft phase 0), then frees their zone blocks.
 *
 * Quake/CHIM machinery reused: the incremental frame world (chim_graft.c,
 * one world model, Mod_LeafPVS rows, SV_LinkEdict), efrags (R_SplitEntityOnNode),
 * the chunk scheduler and its budgets (ChimChunks_Tick), terrain references
 * placed by their shift (chim_graft.c Shift), the zone (Cache_*'s LRU).
 * Selected with "chim crossing 1" before the map starts; 0 (the default) is
 * type 0, the level change, unchanged. */

static int			window_wanted;		/* "chim crossing 1": the next map start runs a window */
#define WINDOW_MARGIN	256				/* units past a cell's midline before the block moves */
#define WINDOW_FAR		1e9f			/* an unused slot's entries: never within any ring */
static chim_frame_t	home;				/* the frame the map started on (the session's origin) */
static int			home_row;
static unsigned		home_first;
static int			missing[4][2], missing_count;	/* cells of the block without a frame the window can hold */

int ChimChunks_WindowOn (int on)
{
	if (on >= 0)
		window_wanted = on != 0;
	return window_wanted;
}

/* A frame a window can hold: one cell, centred on it, its chunks on the cell
 * lattice (region frames are; town frames are not). */
static int WindowFits (const chim_frame_t *f)
{
	return f->grain > 0 && !(CHIM_CELL_UNITS % f->grain) && f->nx == f->ny && f->nx * f->grain > CHIM_CELL_UNITS &&
		f->centre[0] == f->cx * 4.0f * CHIM_CELL_UNITS + 2.0f * CHIM_CELL_UNITS &&
		f->centre[1] == f->cy * 4.0f * CHIM_CELL_UNITS + 2.0f * CHIM_CELL_UNITS;
}

/* A neighbour the window can hold beside the home frame: the same layout. */
static int SameLayout (const chim_frame_t *f)
{
	return WindowFits (f) && f->nx == home.nx && f->ny == home.ny && f->grain == home.grain &&
		f->low[0] == home.low[0] && f->low[1] == home.low[1] && f->sector_chunks == home.sector_chunks;
}

/* First placement id of the frame at row, counted from the home frame's
 * (only the frames between are read, or their counts the prefetch kept). */
static int FirstPidNear (int row, unsigned *first)
{
	int i, from = row < home_row ? row : home_row, to = row < home_row ? home_row : row;
	int fast = ChimPrefetch_Active ();
	unsigned sum = 0, kept;
	for (i=from ; i<to ; i++)
	{
		chim_header_t oh;
		chim_frame_t of;
		if (strcmp (chim_world.file[i].kind, "FRAM"))
			continue;
		if (fast && ChimPrefetch_Owned (i, &kept))
		{
			sum += kept;
			continue;
		}
		if (!FrameHeader (i, &oh, &of))
			return 0;
		sum += of.owned_total;
		if (fast)
			ChimPrefetch_SetOwned (i, of.owned_total);
	}
	*first = row < home_row ? home_first - sum : home_first + sum;
	return 1;
}

/* An unused slot's entries: absent, out of every ring. */
static void SlotEntriesClear (int s)
{
	int i, base = s * chim_frame.slot_entries;
	for (i=base ; i<base + chim_frame.slot_entries ; i++)
	{
		chim_entry_t *e = &chim_frame.entries[i];
		memset (e, 0, sizeof(*e));
		e->file = -1;
		e->graft = -1;
		e->shadow = -1;
		e->slot = (short)s;
		e->low[0] = e->low[1] = e->high[0] = e->high[1] = WINDOW_FAR;
		e->distance = e->priority = 1e30f;
	}
}

/* The entries of the slot being released: every other block is kept. */
static int release_first, release_end;
static int KeepOtherSlots (void *data, unsigned id)
{
	(void)data;
	return (int)id < release_first || (int)id >= release_end;
}

/* Frees what a slot holds in the zone (nothing of it may be locked by a
 * chunk or grafted any more). Catalogues and terrain go as an eviction does
 * (their callbacks: a chunk's state, a terrain model's texture locks). */
static void SlotRelease (int s)
{
	chim_slot_t *w = &chim_frame.slot[s];
	if (!w->used)
		return;
	ChimStatics_SlotEnd (s);
	release_first = w->base;
	release_end = w->base + w->count;
	ChimZone_EvictKind (CHIM_KIND_CHUNK, KeepOtherSlots);
	ChimZone_EvictKind (CHIM_KIND_TERRAIN, KeepOtherSlots);
	release_first = release_end = 0;
	if (w->user.data)
	{
		ChimZone_Unlock (w->user.data);
		ChimZone_Free (&w->user);
	}
	memset (w, 0, sizeof(*w));
	SlotEntriesClear (s);
}

/* Frame (cx, cy) into slot s: its directory, grid, placement bits and
 * streamed statics, at its offset from the home frame. */
static int SlotJoin (int s, int row, const chim_header_t *h, const chim_frame_t *f, unsigned first)
{
	chim_slot_t *w = &chim_frame.slot[s];
	int cells = f->nx * f->ny, bits = (int)((f->owned_total + 7) / 8), size;
	char map[MAX_QPATH];
	size = cells * (int)sizeof(short) + 2*bits + 16;
	memset (w, 0, sizeof(*w));
	if (!ChimZone_Alloc (&w->user, size, CHIM_KIND_INDEX, 2 + (unsigned)s))
		return 0;
	ChimZone_Lock (w->user.data);
	memset (w->user.data, 0, size);
	w->grid = w->user.data;
	w->drawn = (unsigned char *)(w->grid + cells);
	w->visible = w->drawn + bits;
	w->frame = *f;
	w->cx = f->cx;
	w->cy = f->cy;
	w->row = row;
	w->first_pid = first;
	w->base = s * chim_frame.slot_entries;
	w->count = (int)h->count;
	w->offset[0] = (float)((f->cx - home.cx) * CHIM_CELL_UNITS);
	w->offset[1] = (float)((f->cy - home.cy) * CHIM_CELL_UNITS);
	w->core[0] = w->offset[0] - CHIM_CELL_UNITS/2;
	w->core[1] = w->offset[1] - CHIM_CELL_UNITS/2;
	w->core[2] = w->offset[0] + CHIM_CELL_UNITS/2;
	w->core[3] = w->offset[1] + CHIM_CELL_UNITS/2;
	w->used = 1;
	if (w->count > chim_frame.slot_entries || !ReadDirectory (row, h, f, w->base, w->grid, w->offset, s))
	{
		SlotRelease (s);
		return 0;
	}
	/* Its streamed statics: the frame map's tagged entities (the home frame's
	 * came with the map's own entity text, ED_LoadFromFile). */
	if (s != 0 || chim_frame.joins)
	{
		map[0] = 0;
		if (chim_cell_map && chim_cell_map (f->cx, f->cy, map, sizeof(map)))
			ChimStatics_SlotJoin (s, w->base, w->count, map, w->offset);
		if (map[0] && chim_actors_join)
			chim_actors_join (f->cx, f->cy, map, w->offset);
	}
	chim_frame.joins++;
	return 1;
}

static int InWindow (int cx, int cy)
{
	int s;
	for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
		if (chim_frame.slot[s].used && !chim_frame.slot[s].leaving && chim_frame.slot[s].cx == cx &&
			chim_frame.slot[s].cy == cy)
			return 1;
	return 0;
}

/* Frame (cx, cy) joins the window in a free slot: 1, 0 none free (it tries
 * again next tick), -1 no frame there the window can hold. */
static int Join (int cx, int cy)
{
	chim_header_t h;
	chim_frame_t f;
	int s, row, sectors;
	unsigned first;
	for (s=0 ; s<CHIM_WINDOW_SLOTS && chim_frame.slot[s].used ; s++)
		;
	if (s == CHIM_WINDOW_SLOTS)
		return 0;
	row = FrameRow (cx, cy);
	if (row < 0 || !FrameHeader (row, &h, &f) || !FrameValid (&h, &f, cx, cy, &sectors) || !SameLayout (&f) ||
		!FirstPidNear (row, &first) || !SlotJoin (s, row, &h, &f, first))
		return -1;
	if (chim_debug.value)
		Con_Printf ("CHIM: window: frame %ld %ld joins (slot %ld, %ld chunks)\n", (long)cx, (long)cy, (long)s,
			(long)chim_frame.slot[s].count);
	return 1;
}

/* A slot leaves: its chunks are deactivated now; the zone blocks go once the
 * frame world has let their ground go (SlotFinish). */
static void SlotLeave (int s)
{
	chim_slot_t *w = &chim_frame.slot[s];
	int i;
	if (chim_actors_leave)
		chim_actors_leave (w->cx, w->cy);
	for (i=w->base ; i<w->base + w->count ; i++)
		if (chim_frame.entries[i].state == CHIM_STATE_ACTIVE)
			Deactivate (i);
	w->leaving = 1;
	if (chim_debug.value)
		Con_Printf ("CHIM: window: frame %ld %ld leaves (slot %ld)\n", (long)w->cx, (long)w->cy, (long)s);
}

static int SlotFinish (int s)
{
	chim_slot_t *w = &chim_frame.slot[s];
	int i, job = ChimModels_JobTerrain ();
	for (i=w->base ; i<w->base + w->count ; i++)
		if (chim_frame.entries[i].grafted || chim_frame.entries[i].state == CHIM_STATE_ACTIVE)
			return 0;
	if (job >= w->base && job < w->base + w->count)
		ChimModels_Abort ();
	SlotRelease (s);
	chim_frame.leaves++;
	return 1;
}

/* The block's first cell along one axis (absolute cell numbers): from the
 * session coordinate v, the home frame's cell, and the current block start
 * (hysteresis). */
static int BlockAxis (float v, int home_cell, int current, int set)
{
	int cell = (int)floor ((v + CHIM_CELL_UNITS/2) / (float)CHIM_CELL_UNITS);
	float in = v + CHIM_CELL_UNITS/2 - (float)cell * CHIM_CELL_UNITS;		/* 0 .. 2,048 inside the cell */
	int natural = in >= CHIM_CELL_UNITS/2 ? cell : cell - 1;
	cell += home_cell;
	natural += home_cell;
	if (set && (cell == current || cell == current + 1))
	{
		if (cell == current && in < CHIM_CELL_UNITS/2 - WINDOW_MARGIN)
			return current - 1;
		if (cell == current + 1 && in >= CHIM_CELL_UNITS/2 + WINDOW_MARGIN)
			return current + 1;
		return current;
	}
	return natural;
}

/* The window's grid over the block and which chunk holds each place (the
 * frame whose cell holds the chunk's centre, else the nearest cell's frame);
 * chunks whose place another frame's chunk holds become shadows (an active
 * one whose role changed starts again, with or without its ground). */
static void Layout (void)
{
	int g = home.grain, nx = chim_frame.frame.nx, ny = chim_frame.frame.ny, vx, vy, s, i, best, lx, ly;
	float low0 = (float)((chim_frame.block[0] - home.cx) * CHIM_CELL_UNITS) + home.low[0];
	float low1 = (float)((chim_frame.block[1] - home.cy) * CHIM_CELL_UNITS) + home.low[1];
	float px, py, d, dx, dy, nearest;

	chim_frame.frame.low[0] = low0;
	chim_frame.frame.low[1] = low1;
	for (vy=0 ; vy<ny ; vy++)
		for (vx=0 ; vx<nx ; vx++)
		{
			px = low0 + (vx + 0.5f) * g;
			py = low1 + (vy + 0.5f) * g;
			best = -1;
			nearest = 1e30f;
			for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
			{
				const chim_slot_t *w = &chim_frame.slot[s];
				int e;
				if (!w->used || w->leaving)
					continue;
				lx = (int)floor ((px - w->offset[0] - w->frame.low[0]) / g);
				ly = (int)floor ((py - w->offset[1] - w->frame.low[1]) / g);
				if (lx < 0 || ly < 0 || lx >= w->frame.nx || ly >= w->frame.ny || (e = w->grid[ly*w->frame.nx + lx]) < 0)
					continue;
				/* Inside its cell (half-open, as CoreKeeps): this frame's; else the nearest cell's. */
				if (px >= w->core[0] && px < w->core[2] && py >= w->core[1] && py < w->core[3])
				{
					best = w->base + e;
					break;
				}
				dx = px < w->core[0] ? w->core[0] - px : px - w->core[2] + 1;
				dy = py < w->core[1] ? w->core[1] - py : py >= w->core[3] ? py - w->core[3] + 1 : 0;
				if (px >= w->core[0] && px < w->core[2])
					dx = 0;
				d = dx*dx + dy*dy;
				if (d < nearest)
				{
					nearest = d;
					best = w->base + e;
				}
			}
			grid[vy*nx + vx] = (short)best;
		}
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_entry_t *e = &chim_frame.entries[i];
		int shadow = -1, owner;
		if (chim_frame.slot[e->slot].used && !chim_frame.slot[e->slot].leaving)
		{
			vx = (int)floor ((e->low[0] - low0) / g + 0.5f);
			vy = (int)floor ((e->low[1] - low1) / g + 0.5f);
			owner = vx >= 0 && vy >= 0 && vx < nx && vy < ny ? grid[vy*nx + vx] : -1;
			if (owner >= 0 && owner != i)
				shadow = owner;
		}
		if (shadow != e->shadow)
		{
			if (e->state == CHIM_STATE_ACTIVE)
				Deactivate (i);
			e->shadow = (short)shadow;
			e->ready = 0;
		}
	}
	chim_frame.view_entry = -2;
	Reconcile ();
	Released ();
	world_dirty = 1;
}

/* Server side, at the start of each ring tick: the block follows the player;
 * frames that left it go, frames of it join. */
static void WindowUpdate (const vec3_t origin)
{
	int s, bx, by, x, y, k, r, changed = 0, leaving = 0, joined = 0, left = 0;
	double started = 0;
	unsigned long joins = chim_frame.joins, leaves = chim_frame.leaves;
	/* The actors' tick (aw_actors.c) also runs in a type 0 map while type 1 is asked: a town frame never starts a
	 * window, and entering it must still apply the change list to its residents (a killed one stays dead) */
	if (chim_actors_tick && (chim_frame.window || window_wanted))
		chim_actors_tick ();
	if (!chim_frame.window)
		return;
	bx = BlockAxis (origin[0], home.cx, chim_frame.block[0], chim_frame.block_set);
	by = BlockAxis (origin[1], home.cy, chim_frame.block[1], chim_frame.block_set);
	if (!chim_frame.block_set || bx != chim_frame.block[0] || by != chim_frame.block[1])
	{
		started = Sys_FloatTime ();
		chim_frame.block[0] = bx;
		chim_frame.block[1] = by;
		chim_frame.block_set = 1;
		missing_count = 0;
		for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
		{
			chim_slot_t *w = &chim_frame.slot[s];
			if (w->used && !w->leaving && (w->cx < bx || w->cx > bx + 1 || w->cy < by || w->cy > by + 1))
				SlotLeave (s);
		}
		changed = 1;
	}
	for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
		leaving += chim_frame.slot[s].used && chim_frame.slot[s].leaving;
	if (leaving)
	{
		/* Their ground leaves the frame world first, then their blocks go. */
		if (changed)
			Layout ();
		changed = 0;
		Graft (0);
		for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
			if (chim_frame.slot[s].used && chim_frame.slot[s].leaving && SlotFinish (s))
				changed = 1;
	}
	for (y=by ; y<=by+1 ; y++)
		for (x=bx ; x<=bx+1 ; x++)
		{
			if (InWindow (x, y))
				continue;
			for (k=0 ; k<missing_count && (missing[k][0] != x || missing[k][1] != y) ; k++)
				;
			if (k < missing_count)
				continue;
			for (s=0 ; s<CHIM_WINDOW_SLOTS && chim_frame.slot[s].used ; s++)
				;
			if (s == CHIM_WINDOW_SLOTS)
				continue;		/* no free slot yet: a leaving frame still holds one */
			if (!started)
				started = Sys_FloatTime ();
			if ((r = Join (x, y)) > 0)
				changed = 1;
			else if (r < 0 && missing_count < 4)
			{
				missing[missing_count][0] = x;
				missing[missing_count][1] = y;
				missing_count++;
			}
		}
	if (changed)
		Layout ();
	if (started > 0)
	{
		/* What the window's changes cost this tick (one console line with chim_debug 1; "chim spikes"). */
		double took = Sys_FloatTime () - started;
		joined = (int)(chim_frame.joins - joins);
		left = (int)(chim_frame.leaves - leaves);
		AW_SpikeAdd (AW_SP_WINDOW, took, 0);
		if (chim_debug.value && (joined || left))
			Con_Printf ("CHIM: window block %ld %ld: %ld joined, %ld left, %ld us\n", (long)bx, (long)by, (long)joined,
				(long)left, (long)(took * 1e6));
	}
}

/* The map starts a window (type 1) when asked ("chim crossing 1") and its
 * frame is a region frame: 1, 0 not a window (type 0), -1 failed. */
static int WindowBegin (int row, const chim_header_t *h)
{
	int n = (int)h->count, total, size, s;
	char map[MAX_QPATH];
	if (!window_wanted || !WindowFits (&chim_frame.frame))
		return 0;
	/* A town frame (its cell has no region map: AW_CellMap) never becomes the window's home, even when its layout
	 * fits: it could never join the window again once it left, so its ground and residents would stay gone until
	 * a level change (CHIM-ACTORS-TOWN-RETURN-EMPTY-47). Crossings into and out of towns stay level changes (type
	 * 0), as Seyda Neen's do; the open world between towns keeps the window. */
	if (chim_cell_map && !chim_cell_map (chim_frame.frame.cx, chim_frame.frame.cy, map, sizeof(map)))
		return 0;
	total = n * CHIM_WINDOW_SLOTS;
	if (total > CHIM_MAX_CHUNKS)
		return 0;
	home = chim_frame.frame;
	home_row = row;
	home_first = chim_frame.first_pid;
	chim_frame.window = 1;
	chim_frame.slot_entries = n;
	chim_frame.count = total;
	/* The window's grid: a 2 x 2 block of frames, a cell apart. */
	chim_frame.frame.nx = chim_frame.frame.ny = home.nx + CHIM_CELL_UNITS / home.grain;
	size = total * (int)sizeof(chim_entry_t) + chim_frame.frame.nx * chim_frame.frame.ny * (int)sizeof(short);
	if (!ChimZone_Alloc (&index_user, size, CHIM_KIND_INDEX, 1))
	{
		memset (&chim_frame, 0, sizeof(chim_frame));
		return -1;
	}
	ChimZone_Lock (index_user.data);
	chim_frame.entries = index_user.data;
	grid = (short *)(chim_frame.entries + total);
	chim_frame.view_entry = -2;
	for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
		SlotEntriesClear (s);
	chim_frame.block[0] = home.cx;
	chim_frame.block[1] = home.cy;
	if (!SlotJoin (0, row, h, &home, home_first))
	{
		ChimZone_Unlock (index_user.data);
		ChimZone_Free (&index_user);
		memset (&chim_frame, 0, sizeof(chim_frame));
		return -1;
	}
	missing_count = 0;
	Layout ();
	ticks = 0;
	memset (&ring, 0, sizeof(ring));
	ring.margin = ring.margin_min = -1;
	return 1;
}

/* PROTOTYPE (aw_actors.c): the cell whose centre is the session's origin:
 * the home frame of a window, else the running frame; 0 without a CHIM frame. */
int ChimChunks_OriginCell (int *cx, int *cy)
{
	if (chim_frame.window)
	{
		*cx = home.cx;
		*cy = home.cy;
		return 1;
	}
	if (!chim_frame.entries || !WindowFits (&chim_frame.frame))
		return 0;
	*cx = chim_frame.frame.cx;
	*cy = chim_frame.frame.cy;
	return 1;
}

/* PROTOTYPE (aw_actors.c): the cell of a session position (absolute cell
 * numbers) and whether the window holds that cell's frame; 0 without a window. */
int ChimChunks_WindowCell (const vec3_t origin, int *cx, int *cy, int *held)
{
	if (!chim_frame.window)
		return 0;
	*cx = home.cx + (int)floor ((origin[0] + CHIM_CELL_UNITS/2) / (float)CHIM_CELL_UNITS);
	*cy = home.cy + (int)floor ((origin[1] + CHIM_CELL_UNITS/2) / (float)CHIM_CELL_UNITS);
	*held = InWindow (*cx, *cy);
	return 1;
}

/* The player passed into another frame's cell (aw_scene.c's crossing, type 1):
 * 1 when the window holds that frame (the crossing streams, no level change),
 * with its cell; 0: the level change as before. */
int ChimChunks_WindowCross (const vec3_t origin, int *cx, int *cy)
{
	int s;
	if (!chim_frame.window)
		return 0;
	for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
	{
		const chim_slot_t *w = &chim_frame.slot[s];
		if (w->used && !w->leaving && origin[0] >= w->core[0] && origin[0] < w->core[2] &&
			origin[1] >= w->core[1] && origin[1] < w->core[3])
		{
			*cx = w->cx;
			*cy = w->cy;
			chim_frame.crossings++;
			return 1;
		}
	}
	return 0;
}

/* "chim crossing 1 recentre": a test setting (design note section 5, weak point
 * 5): after every streamed crossing the session's origin moves to the frame
 * the player entered, so every place that stores a position is moved at every
 * crossing and a missed one shows at once. Production keeps one origin over
 * many crossings (a rebase only when the loaded surroundings near the
 * coordinate range's end). */
static int recentre_wanted;

int ChimChunks_RecentreOn (int on)
{
	if (on >= 0)
		recentre_wanted = on != 0;
	return recentre_wanted;
}

/* The session's origin moves to frame (cx, cy): every session position of the
 * window moves by d = that frame's offset (written to d), as one step: the
 * frames' offsets and cells, every chunk's square and terrain place,
 * placements, streamed statics, the far terrain, the cut boxes, the window's
 * grid; then the frame world is laid out again at the new places
 * (ChimGraft_Recentre). Server and client positions are the caller's
 * (aw_scene.c), moved before this. 0: no window or no move. */
int ChimChunks_WindowOffset (int cx, int cy, float *d)
{
	if (!chim_frame.window)
		return 0;
	d[0] = (float)((cx - home.cx) * CHIM_CELL_UNITS);
	d[1] = (float)((cy - home.cy) * CHIM_CELL_UNITS);
	d[2] = 0;
	return d[0] || d[1];
}

int ChimChunks_WindowRecentre (int cx, int cy, float *d)
{
	int s, i, j, k;
	if (!ChimChunks_WindowOffset (cx, cy, d))
		return 0;
	home.cx = cx;
	home.cy = cy;
	home.centre[0] += 4 * d[0];
	home.centre[1] += 4 * d[1];
	for (k=0 ; k<2 ; k++)
		chim_frame.frame.centre[k] += 4 * d[k];
	for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
	{
		chim_slot_t *w = &chim_frame.slot[s];
		if (!w->used)
			continue;
		for (k=0 ; k<2 ; k++)
		{
			w->offset[k] -= d[k];
			w->core[k] -= d[k];
			w->core[k+2] -= d[k];
		}
	}
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_entry_t *e = &chim_frame.entries[i];
		chim_chunk_t *c = e->chunk.data;
		if (!chim_frame.slot[e->slot].used)
			continue;
		for (k=0 ; k<2 ; k++)
		{
			e->low[k] -= d[k];
			e->high[k] -= d[k];
			e->shift[k] -= d[k];
		}
		if (!c)
			continue;
		if (e->state == CHIM_STATE_ACTIVE)
			for (k=0 ; k<2 ; k++)
			{
				c->mins[k] -= d[k];
				c->maxs[k] -= d[k];
			}
		for (j=0 ; j<c->records ; j++)
			for (k=0 ; k<2 ; k++)
			{
				c->places[j].ent.origin[k] -= d[k];
				c->places[j].mins[k] -= d[k];
				c->places[j].maxs[k] -= d[k];
			}
	}
	for (k=0 ; k<2 ; k++)
	{
		ring.last[k] -= d[k];
		ring.ahead[k] -= d[k];
	}
	ChimStatics_Recentre (d);
	ChimFar_Recentre (d);
	ChimCuts_Recentre (d);
	if (chim_hinged_recentre)
		chim_hinged_recentre (d);
	Layout ();
	ChimGraft_Recentre ();
	world_dirty = 1;
	chim_frame.recentres++;
	return 1;
}

/* The chunk count a chunk's PVS row covers: its own frame's. */
int ChimChunks_RowEntries (int entry)
{
	if (!chim_frame.window)
		return chim_frame.count;
	return chim_frame.slot[chim_frame.entries[entry].slot].count;
}

/* Does chunk from's PVS row see chunk to? The row covers from's own frame;
 * another frame's chunk is looked up at its place in from's frame, and seen
 * when it lies outside it (no data: distance and the frustum decide). */
int ChimChunks_RowSees (const byte *row, int from, int to)
{
	const chim_entry_t *a, *b;
	const chim_slot_t *w;
	int x, y, local;
	if (!chim_frame.window)
		return (row[to >> 3] >> (to & 7)) & 1;
	a = &chim_frame.entries[from];
	b = &chim_frame.entries[to];
	w = &chim_frame.slot[a->slot];
	if (a->slot == b->slot)
		local = to - w->base;
	else
	{
		x = (int)floor ((b->low[0] - w->offset[0] - w->frame.low[0]) / w->frame.grain + 0.5f);
		y = (int)floor ((b->low[1] - w->offset[1] - w->frame.low[1]) / w->frame.grain + 0.5f);
		if (x < 0 || y < 0 || x >= w->frame.nx || y >= w->frame.ny || (local = w->grid[y*w->frame.nx + x]) < 0)
			return 1;
	}
	return (row[local >> 3] >> (local & 7)) & 1;
}

void ChimChunks_WindowReport (void)
{
	int s;
	if (!chim_frame.window)
	{
		Con_Printf ("crossing: type %ld (%s)\n", (long)window_wanted,
			window_wanted ? "type 1 asked; this map is not a region frame, its crossings change the level" :
			"type 0: a crossing changes the level");
		return;
	}
	Con_Printf ("crossing: type 1, window block %ld %ld (2 x 2 cells), origin frame %ld %ld; %lu joins, %lu leaves, %lu streamed crossings, %lu recentres\n",
		(long)chim_frame.block[0], (long)chim_frame.block[1], (long)home.cx, (long)home.cy, chim_frame.joins,
		chim_frame.leaves, chim_frame.crossings, chim_frame.recentres);
	for (s=0 ; s<CHIM_WINDOW_SLOTS ; s++)
	{
		const chim_slot_t *w = &chim_frame.slot[s];
		int i, active = 0, loaded = 0, shadows = 0;
		if (!w->used)
			continue;
		for (i=w->base ; i<w->base + w->count ; i++)
		{
			active += chim_frame.entries[i].state == CHIM_STATE_ACTIVE;
			loaded += chim_frame.entries[i].state == CHIM_STATE_LOADED;
			shadows += chim_frame.entries[i].shadow >= 0;
		}
		Con_Printf ("  slot %ld: frame %ld %ld%s, offset %ld %ld, %ld chunks (%ld active, %ld loaded, %ld on another frame's ground), ids %lu+%lu\n",
			(long)s, (long)w->cx, (long)w->cy, w->leaving ? " (leaving)" : "", (long)w->offset[0], (long)w->offset[1],
			(long)w->count, (long)active, (long)loaded, (long)shadows, (unsigned long)w->first_pid,
			(unsigned long)w->frame.owned_total);
	}
}
