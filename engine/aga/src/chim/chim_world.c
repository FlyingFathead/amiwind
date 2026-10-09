/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM world: start-up probe, per-map activation, memory banks, the hooks
 * into the legacy engine and the "chim" console command.
 *
 * Memory (docs/WORLD_STREAMER.md, "Memory placement"): CHIM never grows the
 * Hunk at run time. A CHIM map takes one bank from the Hunk when it starts
 * (the map budget pays for it, Host_ClearMemory returns it), sized by
 * chim_zone_kib and never closer than chim_reserve_kib to the Hunk's end.
 * "-chimcache <KiB>" adds a bank of extra Fast RAM, allocated once at start-up
 * and only on request, that keeps shared models and textures across map
 * changes. Without it (the 2 MiB Chip + 16 MiB Fast baseline) everything goes
 * with the map, exactly as Quake drops brush models at a map change.
 */
#include "quakedef.h"
#include "aw_rcount.h"
#include "chim_local.h"
#include "aw_town.h"
#ifdef AMIGA
#include <proto/exec.h>
#include <exec/memory.h>
#endif

chim_world_t	chim_world;

/* The zone for a CHIM map (v0.0.33-dev1, measured in FS-UAE on Balmora's
 * CHIM frame map): the largest that keeps the 2 MiB Hunk-gap safety at the
 * load peak (peak 9,218,800 of 11,534,336 bytes with 6,656 KiB; 6,864 KiB
 * leaves 2,102,544), rounded down to 16 KiB. tools/engine_limits.py reads
 * these defaults for the builder's CHIM heap gate. */
static cvar_t	chim_zone_kib = {"chim_zone_kib", "6864"};
static cvar_t	chim_reserve_kib = {"chim_reserve_kib", "2048"};
/* When the zone leaves room for what a map used on its last load: 2 always
 * (the first method), 1 only on frame maps that state "_chim_hunk_rest" (the
 * default: a frame map from before the statement keeps its full zone and the
 * gap is said after loading, until its builder states the figure), 0 never. */
static cvar_t	chim_rest_measured = {"chim_rest_measured", "1"};
static cvar_t	chim_read_kib = {"chim_read_kib", "32"};
static cvar_t	chim_buffer_kib = {"chim_buffer_kib", "32"};
static cvar_t	chim_towns = {"chim_towns", "1"};	/* 0: towns use their region maps (A/B tests) */
cvar_t	chim_debug = {"chim_debug", "0"};
/* Ring and frame-world settings (CHIM-ZONE-RING-THRASH-33): the frame-world
 * pool reserved at map start, two slots of chim_pool_kib each (0: taken from
 * the zone at each rebuild, which can find no contiguous room in a full zone;
 * Balmora's largest pool is about 410 KB, a larger one falls back to a
 * per-rebuild allocation), and overrides of the world's draw distance (0: the
 * world's) and prefetch margin (-1: the world's) for measurements. */
cvar_t	chim_pool_kib = {"chim_pool_kib", "384"};
cvar_t	chim_draw_distance = {"chim_draw_distance", "0"};
cvar_t	chim_prefetch = {"chim_prefetch", "-1"};
/* 1: chunks beyond the active ring are prefetched only into free room (no
 * eviction); 0: prefetch may evict like any load (the first CHIM runs). */
cvar_t	chim_prefetch_room = {"chim_prefetch_room", "1"};
/* The frame world (CHIM-REBUILD-COST-33), read at map start: 1 incremental
 * (chunks join and leave the pool, nothing else moves), 0 a full rebuild on
 * every change (the first method). chim_graft_kib: frame-world bytes copied
 * per frame (at least one chunk; chunks within the collision margin never
 * wait; 0: no budget). chim_lookahead: prefetch towards the point this far
 * ahead of the player (-1: the world's prefetch margin; 0: off). */
cvar_t	chim_graft_mode = {"chim_graft_mode", "1"};
/* CHIM-GRAFT-REPACK-EMPTY-33: 1 = a repack without room for the whole ring keeps
 * the nearest chunks that fit its block; 0 = the first method (the block is let
 * go and the ring may come back empty). */
cvar_t	chim_graft_trim = {"chim_graft_trim", "1"};
cvar_t	chim_graft_kib = {"chim_graft_kib", "16"};
cvar_t	chim_lookahead = {"chim_lookahead", "-1"};
/* When the zone is full (CHIM-CHUNK-LOAD-FAIL-33), 0 being the first method
 * of each. chim_release 1: a chunk within the active radius keeps what it
 * has in the zone while it loads the rest (its catalogue, terrain and
 * models are locked during the load); when it finds no room it releases
 * the active chunk farthest from the player, farther than itself and
 * outside the collision margin (past the active radius first), and tries
 * again; a released chunk is not activated again for 50 ticks; a chunk
 * within the collision margin that failed tries again on the next tick.
 * chim_partial 1: a chunk whose model has no room is activated without it,
 * so its ground and its other placements are there; the model follows when
 * there is room. chim_zone_ends: blocks smaller than this many KiB come
 * from the zone's high end, larger ones first fit from the low end, so small
 * locked blocks (textures, chunk catalogues and terrain) do not split the
 * room large models need (chim_zone.c ChimZone_SetEnds); 0: first fit for
 * every block (the first method). */
cvar_t	chim_zone_ends = {"chim_zone_ends", "64"};
cvar_t	chim_release = {"chim_release", "1"};
cvar_t	chim_partial = {"chim_partial", "1"};
/* aw_fog.c: a CHIM map's view distance is limited by its world's data, not
 * by the region table. */
extern int (*aw_chim_view_reach)(void);
extern cvar_t aw_drawdistance;
int AW_DrawDistance (void);
int AW_OpeningStoryHidden (void);

static int		available;			/* chim/world.cwi exists */
static int		active;				/* the current map is a CHIM frame */
static int		primed, tick_frame = -1;
static int		map_bank = -1, cache_bank = -1;
static void		*cache_memory;
static long		cache_bytes;
static chim_user_t	buffer_user, index_user;
static chim_pack_t	open_files[CHIM_OPEN_FILES];
static int			open_rows[CHIM_OPEN_FILES];
static unsigned long	open_stamp[CHIM_OPEN_FILES], open_clock;
static char		failure[64];
static int		hunk_mark = -1;
/* The whole-map Hunk rule (CHIM-ZONE-RESERVE-EARLY-33): the zone is taken
 * before the map's entities and per-map allocations load, so it leaves room
 * for what follows: the frame map's statement ("_chim_hunk_rest" BYTES, the
 * builder's model of the Hunk the map uses after the zone), or what this map
 * was measured to use when it last loaded in this session, whichever is
 * larger. After loading, the engine measures it and says so when the gap
 * ends under chim_reserve_kib. */
int AW_HeapLoadPeak (void);
static int		zone_taken_at;		/* Hunk low + high right after the zone was taken */
static int		zone_bytes, rest_stated, rest_used, rest_checked;
#define CHIM_REST_MAPS	8
static struct { char map[MAX_QPATH]; int bytes; } rest_seen[CHIM_REST_MAPS];
static int		rest_next;

static int RestMeasured (const char *map)
{
	int i;
	for (i=0 ; i<CHIM_REST_MAPS ; i++)
		if (rest_seen[i].map[0] && !strcmp (rest_seen[i].map, map))
			return rest_seen[i].bytes;
	return 0;
}

static void RestRemember (const char *map, int bytes)
{
	int i;
	for (i=0 ; i<CHIM_REST_MAPS && strcmp (rest_seen[i].map, map) ; i++)
		;
	if (i < CHIM_REST_MAPS)
	{
		/* The most this map has used: loads differ by a few KiB (a temporary
		 * high-end block at the peak), and following the last one would let
		 * the zone grow back into the gap on the next load. */
		if (bytes > rest_seen[i].bytes)
			rest_seen[i].bytes = bytes;
		return;
	}
	i = rest_next;
	rest_next = (rest_next + 1) % CHIM_REST_MAPS;
	strncpy (rest_seen[i].map, map, MAX_QPATH-1);
	rest_seen[i].map[MAX_QPATH-1] = 0;
	rest_seen[i].bytes = bytes;
}
/* CHIM work per host frame (the ring tick and the client link), for dbg
 * rcount: the longest frame since the last line, in microseconds. */
static double	work_frame, work_worst;
static int		work_framecount = -1;

/* ---------------------------------------------------------------- packs */

int Chim_PackOpen (chim_pack_t *pack, const char *relative)
{
	FILE *f = NULL;
	int bytes;

	memset (pack, 0, sizeof(*pack));
	if (strlen (relative) > CHIM_PATH_CHARS)
		return 0;
	sprintf (pack->path, "chim/%s", relative);
	bytes = COM_FOpenFile (pack->path, &f);
	if (!f)
		return 0;
	pack->file = f;
	pack->base = ftell (f);
	pack->bytes = bytes;
	if (pack->base < 0 || bytes < 0)
	{
		Chim_PackClose (pack);
		return 0;
	}
	return 1;
}

void Chim_PackClose (chim_pack_t *pack)
{
	if (pack->file)
		fclose (pack->file);
	pack->file = NULL;
}

int Chim_PackRead (chim_pack_t *pack, long offset, void *out, long bytes)
{
	if (!pack->file || offset < 0 || bytes < 0 || offset > pack->bytes || bytes > pack->bytes - offset)
		return 0;
	if (fseek (pack->file, pack->base + offset, SEEK_SET) ||
		fread (out, 1, (size_t)bytes, pack->file) != (size_t)bytes)
		return 0;
	chim_world.bytes_read += bytes;
	chim_world.reads++;
	return 1;
}

/* A file of the index's file table, opened on demand; a few stay open (the
 * least recently used closes), and every open checks the recorded size. */
chim_pack_t *Chim_File (int row)
{
	int i, slot = 0;
	if (row < 0 || row >= chim_world.files)
		return NULL;
	for (i=0 ; i<CHIM_OPEN_FILES ; i++)
		if (open_files[i].file && open_rows[i] == row)
		{
			open_stamp[i] = ++open_clock;
			return &open_files[i];
		}
	for (i=1 ; i<CHIM_OPEN_FILES ; i++)
		if (!open_files[i].file || open_stamp[i] < open_stamp[slot])
			slot = i;
	if (!open_files[slot].file)
		;
	else
		Chim_PackClose (&open_files[slot]);
	if (!Chim_PackOpen (&open_files[slot], chim_world.file[row].path))
		return NULL;
	if ((unsigned long)open_files[slot].bytes != chim_world.file[row].bytes)
	{
		Chim_PackClose (&open_files[slot]);
		return NULL;
	}
	chim_world.opens++;
	open_rows[slot] = row;
	open_stamp[slot] = ++open_clock;
	return &open_files[slot];
}

void Chim_FilesClose (void)
{
	int i;
	for (i=0 ; i<CHIM_OPEN_FILES ; i++)
		Chim_PackClose (&open_files[i]);
}

int Chim_FileRow (const char *kind, int cx, int cy, int sector)
{
	int i;
	for (i=0 ; i<chim_world.files ; i++)
		if (!strcmp (chim_world.file[i].kind, kind) && chim_world.file[i].cx == cx &&
			chim_world.file[i].cy == cy && chim_world.file[i].sector == sector)
			return i;
	return -1;
}

/* ---------------------------------------------------------------- index */

/* One table of the index, decoded in pieces through the loading buffer. */
static int ReadTable (chim_pack_t *pack, unsigned at, unsigned count, int row_bytes, int kind, void *out)
{
	byte *raw = chim_world.buffer;
	unsigned i, per = (unsigned)(chim_world.buffer_bytes / row_bytes), n;
	for (i=0 ; i<count ; i+=n)
	{
		n = count - i < per ? count - i : per;
		if (!Chim_PackRead (pack, at + i*row_bytes, raw, (long)n*row_bytes))
			return 0;
		for (per=0 ; per<n ; per++)
		{
			const byte *p = raw + per*row_bytes;
			if (kind == 0 && !ChimFormat_File (p, (chim_file_t *)out + i + per))
				return 0;
			if (kind == 1)
				ChimFormat_ModelDir (p, (chim_asset_t *)out + i + per);
			if (kind == 2)
				ChimFormat_TextureDir (p, (chim_asset_t *)out + i + per);
		}
		per = (unsigned)(chim_world.buffer_bytes / row_bytes);
	}
	return 1;
}

/* Every model and texture lies inside the file its row names. */
static int AssetsValid (const chim_asset_t *a, unsigned count)
{
	unsigned i;
	for (i=0 ; i<count ; i++)
		if (a[i].file >= chim_world.files || strcmp (chim_world.file[a[i].file].kind, "SECT") ||
			(a[i].offset & 3) || a[i].offset < CHIM_HEADER_BYTES ||
			a[i].bytes > chim_world.file[a[i].file].bytes - a[i].offset || a[i].render > a[i].bytes)
			return 0;
	return 1;
}

/* world.cwi: header, settings, table of contents, then the file table and
 * the model and texture directories, kept in the zone while the map runs.
 * Names are not read: the engine finds models and textures by id. */
static int ReadIndex (void)
{
	chim_pack_t pack;
	byte head[CHIM_HEADER_BYTES + CHIM_SETTINGS_BYTES + CHIM_TOC_BYTES];
	chim_header_t h;
	chim_toc_t *t = &chim_world.toc;
	int ok = 0, size;

	if (!Chim_PackOpen (&pack, "world.cwi"))
		return 0;
	if (!Chim_PackRead (&pack, 0, head, sizeof(head)))
		goto done;
	if (!ChimFormat_Header (head, pack.bytes, "INDX", &h))
	{
		/* Said with the version found: a world of another format is refused
		 * whole, never read in part. */
		if (!memcmp (head, "CHIM", 4))
			Con_Printf ("CHIM: chim/world.cwi is world format %ld.%ld; this engine reads %ld.%ld to %ld.%ld\n",
				(long)ChimFormat_U16 (head+8), (long)ChimFormat_U16 (head+10), (long)CHIM_FORMAT_MAJOR,
				(long)CHIM_FORMAT_MINOR_OLDEST, (long)CHIM_FORMAT_MAJOR, (long)CHIM_FORMAT_MINOR);
		goto done;
	}
	chim_world.minor = h.minor;
	if (!ChimFormat_Settings (head + CHIM_HEADER_BYTES, &chim_world.settings))
		goto done;
	ChimFormat_Toc (head + CHIM_HEADER_BYTES + CHIM_SETTINGS_BYTES, t);
	if (t->files_at != sizeof(head) || t->files != h.count || t->files < 1 || t->files > 4096 ||
		t->models_at != t->files_at + t->files*CHIM_FILE_BYTES || t->models > 65536 ||
		t->order_at != t->models_at + t->models*CHIM_MODEL_DIR_BYTES ||
		t->textures_at != t->order_at + 4*t->models || t->textures > 65536 ||
		t->names_at != t->textures_at + t->textures*CHIM_TEXTURE_DIR_BYTES || t->names_at > h.bytes ||
		t->models != chim_world.settings.models || t->textures != chim_world.settings.textures)
		goto done;
	size = t->files*sizeof(chim_file_t) + (t->models + t->textures)*sizeof(chim_asset_t) +
		t->models*sizeof(chim_model_t *) + t->textures*sizeof(texture_t *);
	if (!ChimZone_Alloc (&index_user, size, CHIM_KIND_INDEX, 0))
		goto done;
	ChimZone_Lock (index_user.data);
	/* Pointers first: every table stays aligned for its type. */
	chim_world.model_slot = index_user.data;
	chim_world.texture_slot = (texture_t **)(chim_world.model_slot + t->models);
	chim_world.model = (chim_asset_t *)(chim_world.texture_slot + t->textures);
	chim_world.texture = chim_world.model + t->models;
	chim_world.file = (chim_file_t *)(chim_world.texture + t->textures);
	chim_world.files = (int)t->files;
	chim_world.models = t->models;
	chim_world.textures = t->textures;
	if (!ReadTable (&pack, t->files_at, t->files, CHIM_FILE_BYTES, 0, chim_world.file) ||
		!ReadTable (&pack, t->models_at, t->models, CHIM_MODEL_DIR_BYTES, 1, chim_world.model) ||
		!ReadTable (&pack, t->textures_at, t->textures, CHIM_TEXTURE_DIR_BYTES, 2, chim_world.texture) ||
		!AssetsValid (chim_world.model, t->models) || !AssetsValid (chim_world.texture, t->textures))
		goto done;
	/* Models and textures kept from an earlier map (the cache bank). */
	ChimModels_IndexSlots ();
	ok = 1;
done:
	Chim_PackClose (&pack);
	return ok;
}

/* ---------------------------------------------------------------- map */

static int KeepModel (void *data, unsigned id)
{
	chim_model_t *cm = data;
	int i;
	(void)id;
	if (!ChimZone_Persistent (cm))
		return 0;
	for (i=0 ; i<cm->model.numtextures ; i++)
		if (cm->model.textures[i] && cm->model.textures[i] != r_notexture_mip &&
			!ChimZone_Persistent (cm->model.textures[i]))
			return 0;
	return 1;
}

static int KeepPersistent (void *data, unsigned id)
{
	(void)id;
	return ChimZone_Persistent (data);
}

static void MapEnd (void)
{
	if (!active && map_bank < 0)
		return;
	ChimFar_End ();
	ChimGraft_End ();
	ChimChunks_End ();
	ChimStatics_End ();
	ChimModels_Abort ();
	Chim_FilesClose ();
	if (index_user.data)
	{
		ChimZone_Unlock (index_user.data);
		ChimZone_Free (&index_user);
	}
	chim_world.file = NULL;
	chim_world.model = chim_world.texture = NULL;
	chim_world.model_slot = NULL;
	chim_world.texture_slot = NULL;
	chim_world.files = 0;
	chim_world.models = chim_world.textures = 0;
	if (buffer_user.data)
	{
		ChimZone_Unlock (buffer_user.data);
		ChimZone_Free (&buffer_user);
	}
	chim_world.buffer = NULL;
	/* Shared models and textures kept only where they survive the Hunk. */
	ChimZone_EvictKind (CHIM_KIND_MODEL, KeepModel);
	ChimZone_EvictKind (CHIM_KIND_TEXTURE, KeepPersistent);
	ChimZone_DropTransient ();
	map_bank = -1;
	active = primed = 0;
	tick_frame = -1;
}

/* A frame map's worldspawn key: "_chim_edge" "closed" (world format 0.5,
 * M3): the frame touches no other frame; clip walls stand at its bounds and
 * the player who reaches one is told the area beyond is unavailable. */
static int		edge_closed;
static double	edge_said;
#define CHIM_EDGE_MESSAGE	"Area unavailable"
#define CHIM_EDGE_REACH		16		/* units from the frame's bound: at its clip wall */

static int WorldspawnKey (const char *entities, const char *key, char *value, int size)
{
	const char *end, *at;
	char quoted[48];
	int n = 0;
	if (!entities || *entities != '{' || !(end = strchr (entities, '}')) || strlen (key) > 40)
		return 0;
	sprintf (quoted, "\"%s\"", key);
	if (!(at = strstr (entities, quoted)) || at > end)
		return 0;
	at += strlen (quoted);
	while (at < end && *at != '"')
		at++;
	if (at >= end)
		return 0;
	for (at++ ; at < end && *at != '"' && n < size-1 ; at++)
		value[n++] = *at;
	value[n] = 0;
	return 1;
}

/* "_chim_frame" "X Y" in the map's worldspawn names its CHIM frame (the
 * underscore keeps QuakeC's entity parser from warning about the key). */
static int WorldspawnFrame (const char *entities, int *cx, int *cy)
{
	const char *end, *key;
	if (!entities || *entities != '{' || !(end = strchr (entities, '}')))
		return 0;
	key = strstr (entities, "\"_chim_frame\"");
	if (!key || key > end)
		return 0;
	return Q_sscanf (key + 13, " \"%d %d\"", cx, cy) == 2;
}

static void Fail (const char *why)
{
	strncpy (failure, why, sizeof(failure)-1);
	failure[sizeof(failure)-1] = 0;
	Con_Printf ("CHIM: %s; this map runs without its chunks.\n", why);
	active = 1;
	MapEnd ();
	/* Nothing else used the Hunk since the bank was taken: give it back. */
	if (hunk_mark >= 0)
		Hunk_FreeToLowMark (hunk_mark);
	hunk_mark = -1;
}

static void MapBegin (const char *entities)
{
	int cx, cy, size, free_bytes;
	void *memory;

	MapEnd ();
	failure[0] = 0;
	if (!available || !WorldspawnFrame (entities, &cx, &cy))
		return;
	{
		char text[24];
		rest_stated = WorldspawnKey (entities, "_chim_hunk_rest", text, sizeof(text)) ? atoi (text) : 0;
		if (rest_stated < 0)
			rest_stated = 0;
	}
	rest_used = rest_stated;
	if (chim_rest_measured.value >= 2 || (chim_rest_measured.value >= 1 && rest_stated > 0))
		if (RestMeasured (sv.name) > rest_used)
			rest_used = RestMeasured (sv.name);
	rest_checked = 0;
	size = (int)chim_zone_kib.value * 1024;
	/* Less the zone's own Hunk header and alignment (Hunk_AllocName). */
	free_bytes = host_parms.memsize - Hunk_LowMark () - Hunk_HighMark () - (int)chim_reserve_kib.value*1024 - rest_used - 64;
	if (size > free_bytes)
	{
		/* Said, not silent: the zone is what the Hunk has left once the map
		 * has loaded the rest. */
		Con_Printf ("CHIM: zone %ld KiB of %ld KiB asked (chim_zone_kib): the Hunk keeps chim_reserve_kib %ld and %ld KiB the map loads after the zone (%s)\n",
			(long)(free_bytes > 0 ? free_bytes/1024 : 0), (long)chim_zone_kib.value, (long)chim_reserve_kib.value,
			(long)(rest_used/1024), rest_used == rest_stated ? "stated by the frame map" : "measured on its last load");
		size = free_bytes;
	}
	if (size < CHIM_MIN_ZONE)
	{
		Fail ("not enough Hunk for the CHIM zone");
		return;
	}
	hunk_mark = Hunk_LowMark ();
	size &= ~15;
	memory = Hunk_AllocName (size, "chimzone");
	zone_taken_at = Hunk_LowMark () + Hunk_HighMark ();
	zone_bytes = size;
	map_bank = ChimZone_AddBank (memory, size, 0);
	ChimZone_SetEnds ((int)chim_zone_ends.value * 1024);
	ChimZone_LockedPeak (0, 1);
	ChimZone_LockedPeak (1, 1);
	chim_world.buffer_bytes = (int)chim_buffer_kib.value * 1024;
	if (chim_world.buffer_bytes < CHIM_MIN_BUFFER)
		chim_world.buffer_bytes = CHIM_MIN_BUFFER;
	if (map_bank < 0 || !ChimZone_Alloc (&buffer_user, chim_world.buffer_bytes, CHIM_KIND_BUFFER, 0))
	{
		Fail ("no CHIM loading buffer");
		return;
	}
	ChimZone_Lock (buffer_user.data);
	chim_world.buffer = buffer_user.data;
	if (!ReadIndex ())
	{
		Fail ("invalid chim/world.cwi");
		return;
	}
	if (!ChimChunks_Begin (cx, cy))
	{
		Fail ("invalid CHIM frame pack");
		return;
	}
	{
		/* Statics the frame map streams with their chunks (chim_statics.c). */
		char text[16];
		ChimStatics_Begin (WorldspawnKey (entities, "_chim_streamed_statics", text, sizeof(text)) ? atoi (text) : 0,
			chim_frame.count);
	}
	/* The frame's terrain becomes the map's world (chim_graft.c). */
	if (!sv.worldmodel || !ChimGraft_Begin (sv.worldmodel))
	{
		Fail ("no room for the CHIM frame world");
		return;
	}
	active = 1;
	hunk_mark = -1;
	/* The frame's far terrain (chim_far.c): low Hunk, given back with the map. */
	ChimFar_Begin (sv.worldmodel->name, (long)host_parms.memsize - Hunk_LowMark () - Hunk_HighMark ()
		- (long)chim_reserve_kib.value*1024);
	{
		char edge[16];
		edge_closed = WorldspawnKey (entities, "_chim_edge", edge, sizeof(edge)) && !strcmp (edge, "closed");
		edge_said = -1e9;
	}
	if (chim_debug.value)
		Con_Printf ("CHIM: map frame %ld %ld: %ld chunks, %ld files, %ld models, %ld textures, zone %ld KiB\n",
			(long)cx, (long)cy, (long)chim_frame.count, (long)chim_world.files, (long)chim_world.models,
			(long)chim_world.textures, (long)(size/1024));
	Con_DPrintf ("CHIM %s: frame %ld %ld, zone %ld KiB\n", CHIM_VERSION, (long)cx, (long)cy, (long)(size/1024));
}

/* ---------------------------------------------------------------- per frame */

/* CHIM's own work in this host frame, timed for dbg rcount ("cw"). */
static void Work (double started)
{
	if (work_framecount != host_framecount)
	{
		work_framecount = host_framecount;
		work_frame = 0;
	}
	work_frame += Sys_FloatTime () - started;
	if (work_frame > work_worst)
		work_worst = work_frame;
}

static void Tick (vec3_t origin)
{
	long budget;
	double started;
	if (!active || tick_frame == host_framecount)
		return;
	started = Sys_FloatTime ();
	tick_frame = host_framecount;
	/* Each frame reads its budget plus one unit (0: one unit a frame). */
	budget = (long)(chim_read_kib.value * 1024);
	/* The first tick loads the whole ring before the player moves. */
	ChimChunks_Tick (origin, budget, !primed);
	primed = 1;
	Work (started);
}

/* A closed frame edge: the player walking at one of the frame's bounds (its
 * clip walls) is told the area beyond is unavailable, at most every 3 s. */
int Chim_EdgeReached (const vec3_t origin)
{
	float x0 = chim_frame.frame.low[0], y0 = chim_frame.frame.low[1], g = (float)chim_frame.frame.grain;
	float x1 = x0 + g*chim_frame.frame.nx, y1 = y0 + g*chim_frame.frame.ny;
	if (!active || !edge_closed || !chim_frame.count)
		return 0;
	return origin[0] < x0 + CHIM_EDGE_REACH || origin[0] > x1 - CHIM_EDGE_REACH ||
		origin[1] < y0 + CHIM_EDGE_REACH || origin[1] > y1 - CHIM_EDGE_REACH;
}

static void Edge (const vec3_t origin)
{
	double now;
	if (!sv.active || svs.maxclients != 1 || !svs.clients || !svs.clients[0].edict ||
		svs.clients[0].edict->v.movetype != MOVETYPE_WALK || !Chim_EdgeReached (origin))
		return;
	now = Sys_FloatTime ();
	if (now < edge_said + 3 && now >= edge_said)
		return;
	edge_said = now;
	AW_UISubtitle ("", CHIM_EDGE_MESSAGE, 3);
}

/* Server side, from the player's physics (aw_walk.c). */
static void Player (vec3_t origin)
{
	Tick (origin);
	Edge (origin);
}

/* Once the map has loaded (the player is placed): what it used beyond the
 * zone, and whether the Hunk kept chim_reserve_kib. Said when it did not,
 * with the zone that would have kept it; remembered for the next load of
 * this map in the session. */
static void CheckRest (void)
{
	int peak, rest, gap, reserve = (int)chim_reserve_kib.value * 1024, keep;
	if (rest_checked || !active)
		return;
	rest_checked = 1;
	peak = AW_HeapLoadPeak ();
	rest = peak - zone_taken_at;
	if (rest < 0)
		rest = 0;
	gap = host_parms.memsize - peak;
	RestRemember (sv.name, rest);
	if (gap >= reserve)
		return;
	keep = (zone_bytes - (reserve - gap)) / 1024;
	Con_Printf ("CHIM: Hunk gap %ld bytes after loading, under chim_reserve_kib %ld: the map loads %ld bytes after the zone (stated %ld); a zone of %ld KiB keeps the gap (%s)\n",
		(long)gap, (long)chim_reserve_kib.value, (long)rest, (long)rest_stated, (long)(keep > 0 ? keep & ~15 : 0),
		chim_rest_measured.value >= 2 || (chim_rest_measured.value >= 1 && rest_stated > 0) ? "used on its next load" :
		"not used: the frame map states no figure; chim_rest_measured 2 uses it");
}

int Chim_HunkRest (int *stated, int *used, int *measured)
{
	*stated = rest_stated;
	*used = rest_used;
	*measured = RestMeasured (sv.name);
	return zone_bytes;
}

/* Server side, when the player is placed (aw_scene.c): the ring around the
 * arrival point is loaded and grafted before any clearance trace. */
static void Spawn (vec3_t origin)
{
	double started = Sys_FloatTime ();
	if (!active)
		return;
	CheckRest ();
	if (chim_debug.value)
		Con_Printf ("CHIM: prime at %ld %ld\n", (long)origin[0], (long)origin[1]);
	ChimChunks_Prime (origin, (long)chim_read_kib.value * 1024);
	if (chim_debug.value)
		Con_Printf ("CHIM: primed: %ld active, %ld loaded, %lu models, %lu textures, %lu KiB in %lu reads, %ld ms\n",
			(long)chim_frame.active, (long)chim_frame.loaded, chim_world.model_loads, chim_world.texture_loads,
			chim_world.bytes_read/1024, chim_world.reads, (long)((Sys_FloatTime () - started)*1000));
	primed = 1;
	tick_frame = host_framecount;
}

/* Server side, for each non-client edict (sv_phys.c). */
static int Frozen (edict_t *ent)
{
	return active && ChimChunks_Frozen (ent);
}

/* Client side, once per frame (aw_scenery.c AW_SceneryLink). */
static void Link (void)
{
	double started;
	if (!active)
		return;
	if (cls.signon == SIGNONS && cl.viewentity > 0 && cl.viewentity < MAX_EDICTS)
		Tick (cl_entities[cl.viewentity].origin);
	started = Sys_FloatTime ();
	ChimChunks_Link ();
	Work (started);
}

/* The view distance CHIM's ring follows: the effective one (aw_fog.c), which
 * on a CHIM map is limited only by the world's own data (ViewReach). */
float Chim_ViewDistance (void)
{
	return (float)AW_DrawDistance ();
}

/* The farthest a CHIM map can be seen: the builder's visibility rows and
 * placement lists reach the ring of draw distance + hysteresis it was built
 * with (world.cwi settings), nothing beyond. 0 when no CHIM map runs. */
static int ViewReach (void)
{
	return active ? (int)(chim_frame.settings.draw_distance + chim_frame.settings.hysteresis) : 0;
}

static void Clip (vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end, trace_t *best)
{
	if (active)
		ChimChunks_Clip (start, mins, maxs, end, best);
}

int Chim_Active (void)
{
	return active;
}

/* ---------------------------------------------------------------- towns */

/* A town of the town table runs as one CHIM frame map, maps/<town>-chim.bsp,
 * when that map exists: the region code (aw_region.c) then loads it instead
 * of the town's region maps and crosses no regions. Door links, sky, fog and
 * every other per-town table keep the town's name. Asked every frame, so the
 * answer for the last town asked is kept. */
static int TownFile (const char *town, char *path)
{
	FILE *f = NULL;
	if (!town || !*town || strlen (town) > 24)
		return 0;
	sprintf (path, "maps/%s-chim.bsp", town);
	COM_FOpenFile (path, &f);
	if (!f)
		return 0;
	fclose (f);
	return 1;
}

#define TOWN_ASKED	4
static const char *TownMap (const char *town)
{
	/* The last few names asked (a town and its intro docks are both asked
	 * every frame), least recently asked replaced. */
	static char name[TOWN_ASKED][32], path[TOWN_ASKED][MAX_QPATH+16];
	static int found[TOWN_ASKED], stamp[TOWN_ASKED], clock;
	int i, slot = 0;
	if (!chim_towns.value || !town || !*town || strlen (town) > 24)
		return NULL;
	for (i=0 ; i<TOWN_ASKED ; i++)
		if (stamp[i] && !strcmp (name[i], town))
		{
			stamp[i] = ++clock;
			return found[i] ? path[i] : NULL;
		}
	for (i=1 ; i<TOWN_ASKED ; i++)
		if (stamp[i] < stamp[slot])
			slot = i;
	strcpy (name[slot], town);
	found[slot] = TownFile (town, path[slot]);
	stamp[slot] = ++clock;
	return found[slot] ? path[slot] : NULL;
}

/* One line per town of the town table: which mode its exterior loads in. */
static int TownReport (int print)
{
	char path[MAX_QPATH+16];
	int i, on = 0, has;
	for (i=0 ; i<AW_TOWN_COUNT ; i++)
	{
		has = available && TownFile (AW_Town(i)->name, path);
		on += has && chim_towns.value;
		if (print)
			Con_Printf ("  %-12s %s%s\n", AW_Town(i)->name,
				has && chim_towns.value ? "CHIM: " : "legacy",
				has && chim_towns.value ? path : !available ? " (no CHIM world)" :
				has ? " (chim_towns 0)" : " (no frame map)");
	}
	return on;
}

/* ---------------------------------------------------------------- teleport */

/* chim_tp X Y: original Morrowind global coordinates inside this frame
 * (local = (world - frame origin) x 0.25). The ring there is loaded and
 * grafted first, then the player's standing hull is dropped onto the ground
 * from the frame ceiling, as dbg tp places on the ground. */
static void Teleport (void)
{
	edict_t *p;
	vec3_t top, bottom;
	trace_t tr;
	float x, y, span;

	if (!active || Cmd_Argc () != 3 || !sv.active || svs.maxclients != 1 || !svs.clients ||
		!(p = svs.clients[0].edict))
	{
		Con_Printf ("On a CHIM map: chim_tp X Y (original Morrowind global coordinates)\n");
		return;
	}
	x = (Q_atof (Cmd_Argv (1)) - chim_frame.frame.centre[0]) * 0.25f;
	y = (Q_atof (Cmd_Argv (2)) - chim_frame.frame.centre[1]) * 0.25f;
	span = (float)chim_frame.frame.grain;
	if (!(x >= chim_frame.frame.low[0] && x < chim_frame.frame.low[0] + span*chim_frame.frame.nx &&
		y >= chim_frame.frame.low[1] && y < chim_frame.frame.low[1] + span*chim_frame.frame.ny))
	{
		Con_Printf ("chim_tp: outside this frame\n");
		return;
	}
	top[0] = bottom[0] = x;
	top[1] = bottom[1] = y;
	top[2] = 1024;
	bottom[2] = -1024;
	Spawn (top);
	tr = SV_Move (top, p->v.mins, p->v.maxs, bottom, MOVE_NOMONSTERS, p);
	if (tr.fraction >= 1 || tr.allsolid)
	{
		Con_Printf ("chim_tp: no ground at %ld %ld\n", (long)x, (long)y);
		return;
	}
	VectorCopy (tr.endpos, p->v.origin);
	p->v.origin[2] += 1;
	p->v.velocity[0] = p->v.velocity[1] = p->v.velocity[2] = 0;
	SV_LinkEdict (p, false);
	Con_Printf ("chim_tp: local %ld %ld %ld\n", (long)p->v.origin[0], (long)p->v.origin[1], (long)p->v.origin[2]);
}

/* ---------------------------------------------------------------- status */

static void Status (void)
{
	chim_zone_stats_t s;
	ChimZone_Stats (&s);
	Con_Printf ("CHIM %s, reads world format %ld.%ld-%ld.%ld (this world: %ld.%ld): %s\n", CHIM_VERSION,
		(long)CHIM_FORMAT_MAJOR, (long)CHIM_FORMAT_MINOR_OLDEST, (long)CHIM_FORMAT_MAJOR, (long)CHIM_FORMAT_MINOR,
		(long)CHIM_FORMAT_MAJOR, (long)chim_world.minor, !available ? "no chim/world.cwi" : active ? "active" :
		failure[0] ? failure : "not used by this map");
	Con_Printf ("zone: %ld banks, %ld KiB used, %ld KiB free, largest free %ld KiB, %ld blocks, %ld locked\n",
		(long)s.banks, (long)(s.used_bytes/1024), (long)(s.free_bytes/1024), (long)(s.largest_free/1024),
		(long)s.blocks, (long)s.locked);
	Con_Printf ("models %ld (%ld KiB), textures %ld (%ld KiB), chunks %ld (%ld KiB), terrain %ld (%ld KiB)\n",
		(long)s.kind_blocks[CHIM_KIND_MODEL], (long)(s.kind_bytes[CHIM_KIND_MODEL]/1024),
		(long)s.kind_blocks[CHIM_KIND_TEXTURE], (long)(s.kind_bytes[CHIM_KIND_TEXTURE]/1024),
		(long)s.kind_blocks[CHIM_KIND_CHUNK], (long)(s.kind_bytes[CHIM_KIND_CHUNK]/1024),
		(long)s.kind_blocks[CHIM_KIND_TERRAIN], (long)(s.kind_bytes[CHIM_KIND_TERRAIN]/1024));
	Con_Printf ("loads: %lu models (%lu streamed), %lu textures, %lu chunks, %lu failed; %lu KiB in %lu reads, %lu opens\n",
		chim_world.model_loads, chim_world.streamed_models, chim_world.texture_loads, chim_world.chunk_loads,
		chim_world.failed_loads, chim_world.bytes_read/1024, chim_world.reads, chim_world.opens);
	Con_Printf ("zone: %lu allocations, %lu evictions, %lu failures; prefetch held for room %lu times\n",
		s.allocations, s.evictions, s.failures, ChimChunks_PrefetchHeld ());
	if (active)
		Con_Printf ("Hunk: zone %ld KiB; the map loads %ld KiB after it (stated %ld KiB, measured on its last load %ld KiB); chim_reserve_kib %ld kept beside both\n",
			(long)(zone_bytes/1024), (long)(rest_used/1024), (long)(rest_stated/1024), (long)(RestMeasured (sv.name)/1024),
			(long)chim_reserve_kib.value);
	Con_Printf ("zone: %ld KiB locked (needed now: ring, frame world, buffers), most since the map started %ld KiB\n",
		(long)(s.locked_bytes/1024), (long)(ChimZone_LockedPeak (1, 0)/1024));
	{
		unsigned long band, ring, partial, zone_failed, data_failed;
		int last = 0;
		unsigned long failures = ChimZone_Failures (&last);
		ChimChunks_Pressure (&band, &ring, &partial, &zone_failed, &data_failed);
		Con_Printf ("zone: largest run without a lock %ld KiB; %lu failed requests, the last %ld bytes\n",
			(long)(ChimZone_LargestUnlocked ()/1024), failures, (long)last);
		Con_Printf ("full zone: chunk loads failed %lu for room, %lu for bad data; released %lu chunks past the active radius and %lu inside it (chim_release %ld); %lu partial activations (chim_partial %ld)\n",
			zone_failed, data_failed, band, ring, (long)chim_release.value, partial, (long)chim_partial.value);
	}
	/* The engine's entity budgets, stated (the builder's checks read the same
	 * defines: tools/engine_limits.py): what this map uses of each. */
	Con_Printf ("limits: static entities %ld of %ld (MAX_STATIC_ENTITIES), edicts %ld of %ld (MAX_EDICTS), %ld entities drawn a frame (MAX_VISEDICTS)\n",
		(long)cl.num_statics, (long)MAX_STATIC_ENTITIES, (long)(sv.active ? sv.num_edicts : 0), (long)MAX_EDICTS,
		(long)MAX_VISEDICTS);
	Con_Printf ("limits: sign-on %ld of %ld bytes (MAX_MSGLEN), efrag links %ld in use, peak %ld, %ld allocated of %ld (AW_EFRAG_LIMIT)\n",
		(long)(sv.active ? sv.signon.cursize : 0), (long)MAX_MSGLEN, (long)aw_efrags_used, (long)aw_efrags_peak,
		(long)aw_efrags_capacity, (long)AW_EFRAG_LIMIT);
	Con_Printf ("towns (chim_towns %ld):\n", (long)chim_towns.value);
	TownReport (1);
	if (active)
	{
		int margin, ahead;
		unsigned long urgent;
		ChimChunks_Report ();
		ChimStatics_Report ();
		ChimGraft_Report ();
		Con_Printf ("ring: view %ld (aw_drawdistance %ld; this world's visibility data reaches %ld: draw %ld + hysteresis %ld)\n",
			(long)Chim_ViewDistance (), (long)aw_drawdistance.value, (long)ViewReach (),
			(long)chim_frame.settings.draw_distance, (long)chim_frame.settings.hysteresis);
		Con_Printf ("ring: active radius %ld%s, load radius %ld (prefetch %ld), look-ahead %ld, collision margin %ld\n",
			(long)ChimChunks_ActiveRadius (), chim_draw_distance.value > 0 ? " (chim_draw_distance)" : "",
			(long)ChimChunks_LoadRadius (),
			(long)(chim_prefetch.value >= 0 ? chim_prefetch.value : chim_frame.settings.prefetch_margin),
			(long)(chim_lookahead.value >= 0 ? chim_lookahead.value : chim_frame.settings.prefetch_margin),
			(long)chim_frame.settings.collision_margin);
		ChimChunks_Streaming (&margin, &urgent, &ahead);
		Con_Printf ("ring: nearest chunk without ground %ld units away (-1: none), %lu loads past the budget for the collision margin\n",
			(long)margin, urgent);
		Con_Printf ("budgets per frame: reads chim_read_kib %ld bytes + one unit, frame world chim_graft_kib %ld bytes + one chunk\n",
			(long)(chim_read_kib.value * 1024), (long)(chim_graft_kib.value * 1024));
		Con_Printf ("frame edge: %s\n", edge_closed ? "closed (\"" CHIM_EDGE_MESSAGE "\" at the bounds)" : "open");
		ChimFar_Report ();
	}
}

/* ---------------------------------------------------------------- dbg rcount */

/* Appended to the rcount line once a second on a CHIM map (counts first,
 * integer output only):
 *   chim act/grafted/loaded chunks, pl linked/sent placements (last frame),
 *   fz actors frozen, rb rebuilds in the second and their total/longest us,
 *   pool frame world KiB, zone used/free KiB and evictions, rd KiB read and
 *   reads, opens of CHIM files. */
static unsigned long last_bytes, last_reads, last_opens, last_evictions;

static int RCount (char *out, int size, long frames)
{
	chim_zone_stats_t s;
	int rebuilds, pool, sent, one, placements, grafted = 0, i, adds, removes, repacks, margin, ahead;
	long total, worst, bytes;
	unsigned long urgent, urgent_loads;
	(void)frames;
	if (!active || size < 2)
		return 0;
	ChimZone_Stats (&s);
	ChimGraft_Interval (&rebuilds, &total, &worst, &pool);
	ChimGraft_Work (&adds, &removes, &repacks, &bytes, &urgent);
	ChimChunks_LastFrame (&sent, &one, &placements);
	ChimChunks_Streaming (&margin, &urgent_loads, &ahead);
	for (i=0 ; i<chim_frame.count ; i++)
		grafted += chim_frame.entries[i].grafted;
	/* rb: frame-world updates, their total/longest us; gr: chunks joined/
	 * left/repacks and the most KiB one update copied; cw: the longest
	 * frame of CHIM work (us); sm: the nearest chunk without ground (units,
	 * -1: none); ur: urgent joins/loads past the budgets so far. */
	snprintf (out, size, " | chim %ld/%ld/%ld pl %ld/%ld/%ld hid %ld fz %ld rb %ld %ld/%ld gr %ld/%ld/%ld %ld cw %ld sm %ld ur %lu/%lu pool %ld zone %ld/%ld zl %ld/%ld ev %lu rd %lu/%lu op %lu",
		(long)chim_frame.active, (long)grafted, (long)chim_frame.loaded,
		(long)placements, (long)sent, (long)one, (long)ChimChunks_Hidden (), (long)ChimChunks_FrozenLast (),
		(long)rebuilds, total, worst, (long)adds, (long)removes, (long)repacks, (long)((bytes + 1023)/1024),
		(long)(work_worst*1e6 + .5), (long)margin, urgent, urgent_loads, (long)(pool/1024),
		(long)(s.used_bytes/1024), (long)(s.free_bytes/1024), (long)(s.locked_bytes/1024),
		(long)(ChimZone_LockedPeak (0, 1)/1024), s.evictions - last_evictions,
		(chim_world.bytes_read - last_bytes)/1024, chim_world.reads - last_reads, chim_world.opens - last_opens);
	{
		/* far terrain: blocks drawn/of, triangles, pixels, worst us (chim_far.c) */
		int used = (int)strlen (out);
		if (used < size-1)
			ChimFar_RCount (out + used, size - used);
	}
	work_worst = 0;
	last_bytes = chim_world.bytes_read;
	last_reads = chim_world.reads;
	last_opens = chim_world.opens;
	last_evictions = s.evictions;
	return 1;
}

/* ---------------------------------------------------------------- start-up */

#ifdef AMIGA
static void FreeCache (void)
{
	if (cache_memory)
		FreeMem (cache_memory, (ULONG)cache_bytes);
	cache_memory = NULL;
}
#endif

/* Extra Fast RAM for the caches role, only when asked for; never Chip RAM,
 * never the core heap. AvailMem is advisory, the allocation is checked. */
static void CacheBank (void)
{
	int p = COM_CheckParm ("-chimcache");
	if (!p || p >= com_argc-1)
		return;
	cache_bytes = (long)Q_atoi (com_argv[p+1]) * 1024;
	if (cache_bytes < 256*1024)
		return;
#ifdef AMIGA
	if ((long)AvailMem (MEMF_FAST|MEMF_LARGEST) < cache_bytes + 512*1024)
	{
		Con_Printf ("CHIM: -chimcache %ld KiB not available, using the standard budget\n", cache_bytes/1024);
		return;
	}
	cache_memory = AllocMem ((ULONG)cache_bytes, MEMF_FAST|MEMF_PUBLIC);
	if (cache_memory)
		atexit (FreeCache);
#else
	cache_memory = malloc ((size_t)cache_bytes);
#endif
	if (cache_memory)
		cache_bank = ChimZone_AddBank (cache_memory, (int)cache_bytes, 1);
}

void Chim_Init (void)
{
	FILE *f = NULL;

	Cvar_RegisterVariable (&chim_zone_kib);
	Cvar_RegisterVariable (&chim_reserve_kib);
	Cvar_RegisterVariable (&chim_rest_measured);
	Cvar_RegisterVariable (&chim_read_kib);
	Cvar_RegisterVariable (&chim_buffer_kib);
	Cvar_RegisterVariable (&chim_debug);
	Cvar_RegisterVariable (&chim_towns);
	Cvar_RegisterVariable (&chim_pool_kib);
	Cvar_RegisterVariable (&chim_draw_distance);
	Cvar_RegisterVariable (&chim_prefetch);
	Cvar_RegisterVariable (&chim_prefetch_room);
	Cvar_RegisterVariable (&chim_graft_mode);
	Cvar_RegisterVariable (&chim_graft_trim);
	Cvar_RegisterVariable (&chim_graft_kib);
	Cvar_RegisterVariable (&chim_lookahead);
	Cvar_RegisterVariable (&chim_zone_ends);
	Cvar_RegisterVariable (&chim_release);
	Cvar_RegisterVariable (&chim_partial);
	ChimFar_Init ();
	Cmd_AddCommand ("chim", Status);
	Cmd_AddCommand ("chim_tp", Teleport);
	ChimZone_Reset ();
	ChimModels_Init ();
	ChimChunks_Init ();
	COM_FOpenFile (CHIM_INDEX_NAME, &f);
	if (!f)
		return;		/* legacy data: no hook is set, nothing changes */
	fclose (f);
	available = 1;
	CacheBank ();
	aw_chim_map_begin = MapBegin;
	aw_chim_map_end = MapEnd;
	aw_chim_link = Link;
	aw_chim_clip = Clip;
	aw_chim_player = Player;
	aw_chim_spawn = Spawn;
	aw_chim_frozen = Frozen;
	aw_chim_rcount = RCount;
	aw_chim_town_map = TownMap;
	aw_chim_entity = ChimStatics_Capture;
#ifdef AMIGA
	chim_story_hidden = AW_OpeningStoryHidden;		/* aw_opening.c */
#endif
	aw_chim_view_reach = ViewReach;
	ChimFar_Hook ();
	Con_Printf ("CHIM %s: %ld of %ld towns on CHIM (\"chim\" lists them)\n", CHIM_VERSION,
		(long)TownReport (0), (long)AW_TOWN_COUNT);
}
