/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM interiors (docs/chim/INTERIOR_STORE.md): a room map whose worldspawn
 * names "_chim_room" "<room>" takes its placements from the room record
 * <store>/rooms/<room>.crm. As in the original game a room loads on its own:
 * under the loading plaque (SV_SpawnServer, chim_world.c MapBeginWork) the
 * record is read, every model it lists is loaded whole from the store with
 * its textures (chim_models.c, into the map's zone and the cache banks; a
 * room they do not fit grows into the free Fast RAM and the Hunk's rest,
 * ChimRoom_Begin) and locked, and every
 * placed record becomes a run-time placement. Nothing streams while the room
 * runs: no terrain, no frames, no chunk ring. The client links each placement
 * into the room map's own world with efrags (as ChimChunks_Link does), the
 * server collides with them through the placed collision path
 * (ChimChunks_ClipPlace: the piece table, then the turned or yawed model).
 * Everything goes at the next map (chim_world.c MapEnd).
 */
#include "quakedef.h"
#include "chim_local.h"

extern efrag_t	**lastlink;
extern vec3_t	r_emins, r_emaxs;
extern entity_t	*r_addent;
extern mnode_t	*r_pefragtopnode;
void R_SplitEntityOnNode (mnode_t *node);

static struct
{
	int				on;
	char			name[CHIM_ROOM_NAME_CHARS+1];
	chim_user_t		block;			/* the record, the placements, their matrices, the model list */
	chim_place_t	*places;
	float			*rot;			/* 9 floats per placement */
	chim_model_t	**model;		/* by the record's model list */
	int				count, models;
	vec3_t			mins, maxs;		/* the drawn boxes of every placement */
	model_t			*link_world;	/* the client map its efrags were made in */
	int				linked, efrags, waiting;
	int				doors;			/* hinged door placements (aw_hinged_door.c) */
	long			bytes, model_bytes;
	double			seconds;
} room;

int ChimRoom_Active (void)
{
	return room.on;
}

/* Placement i's yaw: its entity (drawn), its sine and cosine (the yaw
 * collision path) and its matrix (the turned and piece-table paths). */
static void RoomYaw (int i, float yaw)
{
	chim_place_t *p = &room.places[i];
	p->ent.angles[YAW] = yaw;
	Q_SinCosDeg (yaw, &p->s, &p->c);
	ChimPlaced_AnglesMatrix (p->ent.angles, (float (*)[3])(room.rot + 9*i));
}

/* Hinged doors in a CHIM room (aw_hinged_door.c through ChimChunks_DoorYaw):
 * the door placement pid gets the yaw. Its box holds every pose, so its
 * efrags and the collision broadphase stay as they are. Returns 1 when pid is
 * a door of this room. */
int ChimRoom_DoorYaw (unsigned pid, float yaw)
{
	int i;
	if (!room.on)
		return 0;
	for (i=0 ; i<room.count ; i++)
		if (room.places[i].pid == pid && (room.places[i].flags & CHIM_PLACE_HINGED))
		{
			RoomYaw (i, yaw);
			return 1;
		}
	return 0;
}

/* The trace against door placement pid alone (through ChimChunks_DoorClip):
 * the same placed collision path as every room placement. 0: not a door. */
int ChimRoom_DoorClip (unsigned pid, vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end, trace_t *trace)
{
	int i;
	if (!room.on)
		return 0;
	for (i=0 ; i<room.count ; i++)
	{
		chim_place_t *p = &room.places[i];
		if (p->pid != pid || !(p->flags & CHIM_PLACE_HINGED) || !p->ent.model)
			continue;
		ChimChunks_ClipPlace (p, room.rot + 9*i, start, mins, maxs, end, trace);
		return 1;
	}
	return 0;
}

void ChimRoom_End (void)
{
	int i;
	if (room.model)
		for (i=0 ; i<room.models ; i++)
			if (room.model[i])
				ChimZone_Unlock (room.model[i]);
	if (room.block.data)
	{
		ChimZone_Unlock (room.block.data);
		ChimZone_Free (&room.block);
	}
	memset (&room, 0, sizeof(room));
}

/* Why the last try failed (RoomLoad): ChimRoom_Begin says it once it gives up. */
static const char	*room_why;
/* The last ChimRoom_Begin's tries and the growth steps between them: each step follows a request the full zone
 * refused (the zone counts it failed), so a room that grew twice and loaded shows 2 failed requests with every model
 * in place (CHIM-ROOM-HEART-CHAMBER-LOAD-50); ChimRoom_Report says so. */
static int	room_tries, room_grown;

static int Fail (const char *why)
{
	room_why = why;
	ChimRoom_End ();
	return 0;
}

static int RoomLoad (const char *name);

/* The room whole, under the loading plaque (RoomLoad). A try that finds the
 * zone full (its record, a model or one of their textures got no room: the
 * zone's failure count moved) lets go of what it loaded, the room grows by
 * the next step of chim_world.c Chim_RoomGrow (the free Fast RAM, then the
 * Hunk's rest; ROOM-AKULAKHAN-HEAP-52) and it is loaded again. A room that
 * fits loads once, as before. With nothing more to take, a room that loaded
 * with an untextured surface loads so once more; one that did not load is
 * refused (chim_world.c RefuseRoom). */
int ChimRoom_Begin (const char *name)
{
	unsigned long failures;
	int ok, full, settle = 0;
	room_tries = room_grown = 0;
	for (;;)
	{
		failures = ChimZone_Failures (NULL);
		room_why = NULL;
		room_tries++;
		ok = RoomLoad (name);
		full = ChimZone_Failures (NULL) != failures;
		if (ok && (!full || settle))
			return 1;
		if (!full || settle)
			break;
		ChimRoom_End ();
		/* the models this try loaded (one may hold an untextured surface) go; textures stay cached */
		ChimZone_EvictKind (CHIM_KIND_MODEL, NULL);
		if (!Chim_RoomGrow (name))
		{
			if (!ok)
				break;
			settle = 1;
		}
		else
			room_grown++;
	}
	Con_Printf ("CHIM: room %s: %s\n", ChimFormat_RoomNameValid (name) ? name : "?", room_why ? room_why :
		"it does not load");
	return 0;
}

/* ROOM-LOADS-THRICE-54: a room whose models clearly do not fit grows before its first try. The record's listed models
 * that are not resident are summed from the store index (their stored bytes plus a block's overheads) and set against
 * what the zone and the banks can give now (free plus unlocked, evictable blocks); while the need is larger, the room
 * grows by the next Chim_RoomGrow step. Before, Akulakhan's Chamber at 32 MB loaded every model three times (two tries
 * refused by the full zone, a grow after each) and on the slow preset outlasted the session's stall check. The tries
 * stay the fallback: a room the estimate passes but the zone refuses still grows and loads again. */
#define ROOM_PREGROW_MODEL_EXTRA	512		/* block header, chim_model_t past model_t, model_t, alignment */
static void RoomPreGrow (const char *name, const byte *file, long directory)
{
	unsigned long need = 0, have;
	chim_zone_stats_t s;
	int i;
	for (i=0 ; i<room.models ; i++)
	{
		unsigned id = ChimFormat_U32 (file + directory + 4*i);
		if (id < chim_world.models && !ChimModels_Find (id))
			need += (unsigned long)chim_world.model[id].bytes + ROOM_PREGROW_MODEL_EXTRA;
	}
	for (;;)
	{
		ChimZone_Stats (&s);
		have = s.free_bytes + ((unsigned long)s.used_bytes > (unsigned long)s.locked_bytes
		                       ? (unsigned long)s.used_bytes - (unsigned long)s.locked_bytes : 0UL);
		if (need <= have)
			return;
		Con_Printf ("CHIM: room %s: its models need about %lu KiB, the zone and banks give %lu KiB: grown before loading\n",
			name, need/1024, have/1024);
		if (!Chim_RoomGrow (name))
			return;
		room_grown++;
	}
}

static int RoomLoad (const char *name)
{
	char path[CHIM_PATH_CHARS+1];
	chim_pack_t pack;
	chim_header_t h;
	chim_room_t r;
	chim_record_t rec;
	byte head[CHIM_HEADER_BYTES + CHIM_ROOM_BLOCK_BYTES], *file;
	long size, budget;
	int i, j, k, step;
	double started = Sys_FloatTime ();

	ChimRoom_End ();
	if (!ChimFormat_RoomNameValid (name))
	{
		Con_Printf ("CHIM: room name \"%s\" refused: 1 to %ld of a-z, 0-9, _ and -\n", name ? name : "",
			(long)CHIM_ROOM_NAME_CHARS);
		room_why = "its name is refused";
		return 0;
	}
	strcpy (room.name, name);
	sprintf (path, "rooms/%s.crm", name);
	if (!Chim_PackOpen (&pack, path))
		return Fail ("no room record in the store");
	if (pack.bytes < (long)sizeof(head) || !Chim_PackRead (&pack, 0, head, sizeof(head)) ||
		!ChimFormat_Header (head, pack.bytes, "ROOM", &h))
	{
		Chim_PackClose (&pack);
		return Fail ("not a room record of a world format this engine reads");
	}
	/* One block: the file, then the placements, their matrices and the model
	 * list (the whole file is checked once it is read). */
	room.models = (int)ChimFormat_U32 (head + CHIM_HEADER_BYTES + 24);
	size = ((pack.bytes + 3) & ~3L) + (long)h.count*(long)sizeof(chim_place_t) + 9L*h.count*(long)sizeof(float) +
		(long)room.models*(long)sizeof(chim_model_t *);
	if (h.count > 65535 || room.models < 0 || room.models > 65535 || size > 0x7fffff00L ||
		!ChimZone_Alloc (&room.block, (int)size, CHIM_KIND_CHUNK, 0x7f10))
	{
		Chim_PackClose (&pack);
		return Fail ("no room in the zone for its record");
	}
	ChimZone_Lock (room.block.data);
	file = room.block.data;
	if (!Chim_PackRead (&pack, 0, file, pack.bytes) || !ChimFormat_Room (file, pack.bytes, &h, &r))
	{
		Chim_PackClose (&pack);
		return Fail ("its record does not check out");
	}
	Chim_PackClose (&pack);
	room.bytes = pack.bytes;
	room.count = (int)h.count;
	if ((int)r.models != room.models)
		return Fail ("its record does not check out");
	room.places = (chim_place_t *)(file + ((pack.bytes + 3) & ~3L));
	room.rot = (float *)(room.places + room.count);
	room.model = (chim_model_t **)(room.rot + 9*room.count);
	if (room_tries == 1)
		RoomPreGrow (room.name, file, (long)h.directory);
	/* Every model whole, now: the plaque is up and nothing else loads. Each
	 * stays locked (its textures with it) until the next map. */
	for (i=0 ; i<room.models ; i++)
	{
		unsigned id = ChimFormat_U32 (file + h.directory + 4*i);
		chim_model_t *cm;
		if (id >= chim_world.models)
			return Fail ("a model id past the store's models");
		for (step=0 ; ; step++)
		{
			budget = 0x7fffffffL;
			k = ChimModels_Step (id, &budget);
			if (k)
				break;
			if (step > 1000000)
				return Fail ("a model load did not finish");
		}
		if (k < 0 || !(cm = ChimModels_Find (id)))
			return Fail ("a model of the store could not be loaded");
		ChimZone_Lock (cm);
		room.model[i] = cm;
		room.model_bytes += ChimZone_Size (cm);
	}
	room.mins[0] = room.mins[1] = room.mins[2] = 1e30f;
	room.maxs[0] = room.maxs[1] = room.maxs[2] = -1e30f;
	for (i=0 ; i<room.count ; i++)
	{
		chim_place_t *p = &room.places[i];
		if (!ChimFormat_RecordPlaced (file + h.data + (long)i*CHIM_RECORD_BYTES_PLACED, &rec))
			return Fail ("a placed record does not check out");
		for (j=0 ; j<room.models && ChimFormat_U32 (file + h.directory + 4*j) != rec.model ; j++)
			;
		if (j == room.models)
			return Fail ("a placement names a model the record does not list");
		p->pid = rec.pid;
		p->flags = rec.flags;
		p->model = rec.model;
		p->owner = 0;
		VectorCopy (rec.origin, p->ent.origin);
		p->ent.angles[YAW] = rec.yaw;
		p->ent.angles[PITCH] = rec.pitch;
		p->ent.angles[ROLL] = rec.roll;
		ChimPlaced_AnglesMatrix (p->ent.angles, (float (*)[3])(room.rot + 9*i));
		p->ent.colormap = vid.colormap;
		p->ent.aw_light = ChimFormat_RecordLight (h.minor, rec.flags);
		p->ent.aw_tint = ChimFormat_RecordTint (h.minor, rec.flags);
		p->ent.model = &room.model[j]->model;
		Q_SinCosDeg (rec.yaw, &p->s, &p->c);
		for (k=0 ; k<3 ; k++)
		{
			p->mins[k] = rec.mins[k];
			p->maxs[k] = rec.maxs[k];
		}
		/* A hinged door (aw_hinged_door.c, the frames' hook): its present
		 * pose and a drawn box that holds every pose, so nothing is relinked
		 * while it turns. The record keeps the door's reference. */
		if (chim_hinged_door)
		{
			float radius = ChimChunks_HingeRadius (p), yaw = rec.yaw;
			if (chim_hinged_door (rec.pid, rec.ref, p->ent.origin, radius, &yaw))
			{
				p->flags |= CHIM_PLACE_HINGED;
				if (yaw != rec.yaw)
					RoomYaw (i, yaw);
				for (k=0 ; k<2 ; k++)
				{
					p->mins[k] = p->ent.origin[k] - radius;
					p->maxs[k] = p->ent.origin[k] + radius;
				}
				room.doors++;
			}
		}
		for (k=0 ; k<3 ; k++)
		{
			if (p->mins[k] < room.mins[k]) room.mins[k] = p->mins[k];
			if (p->maxs[k] > room.maxs[k]) room.maxs[k] = p->maxs[k];
		}
		p->linked = 1;
	}
	room.on = 1;
	room.seconds = Sys_FloatTime () - started;
	if (chim_debug.value)
		Con_Printf ("CHIM: room %s: %ld placements, %ld models (%ld KiB), record %ld bytes, %ld ms\n", room.name,
			(long)room.count, (long)room.models, room.model_bytes/1024, room.bytes, (long)(room.seconds*1000));
	return 1;
}

/* Client side, once per frame: once per client map, every placement linked
 * into the room map's world with its drawn box (R_AddEfrags would use the
 * model's unrotated bounds). */
void ChimRoom_Link (void)
{
	int i;
	if (!room.on || cls.signon != SIGNONS || !cl.worldmodel || cl.worldmodel == room.link_world)
		return;
	room.link_world = cl.worldmodel;
	room.linked = room.efrags = room.waiting = 0;
	for (i=0 ; i<room.count ; i++)
	{
		chim_place_t *p = &room.places[i];
		int before = aw_efrags_used;
		p->ent.efrag = NULL;
		p->leaves = 0;
		if (aw_efrags_used + CHIM_EFRAG_RESERVE/4 > chim_efrag_limit)
		{
			room.waiting++;
			continue;
		}
		VectorCopy (p->mins, r_emins);
		VectorCopy (p->maxs, r_emaxs);
		r_addent = &p->ent;
		lastlink = &p->ent.efrag;
		r_pefragtopnode = NULL;
		R_SplitEntityOnNode (cl.worldmodel->nodes);
		p->ent.topnode = r_pefragtopnode;
		p->leaves = aw_efrags_used - before;
		room.efrags += p->leaves;
		room.linked++;
	}
	if (room.waiting)
		Con_Printf ("CHIM: room %s: %ld placements not drawn, the efrag pool is full\n", room.name, (long)room.waiting);
}

/* Server side (world.c SV_Move through aw_chim_clip): every placement whose
 * drawn box the move's box meets. */
void ChimRoom_Clip (vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end, trace_t *best)
{
	vec3_t low, high;
	int i, k;
	if (!room.on)
		return;
	for (k=0 ; k<3 ; k++)
	{
		low[k] = (start[k] < end[k] ? start[k] : end[k]) + mins[k] - 1;
		high[k] = (start[k] > end[k] ? start[k] : end[k]) + maxs[k] + 1;
		if (low[k] > room.maxs[k] || high[k] < room.mins[k])
			return;
	}
	for (i=0 ; i<room.count ; i++)
	{
		chim_place_t *p = &room.places[i];
		for (k=0 ; k<3 ; k++)
			if (low[k] > p->maxs[k] || high[k] < p->mins[k])
				break;
		if (k != 3)
			continue;
		ChimChunks_ClipPlace (p, room.rot + 9*i, start, mins, maxs, end, best);
		if (best->allsolid)
			return;
	}
}

void ChimRoom_Report (void)
{
	if (!room.on)
		return;
	Con_Printf ("room: %s, %ld placements (%ld linked, %ld efrags, %ld waiting, %ld hinged doors), %ld models %ld KiB, record %ld bytes, loaded in %ld ms\n",
		room.name, (long)room.count, (long)room.linked, (long)room.efrags, (long)room.waiting, (long)room.doors,
		(long)room.models, room.model_bytes/1024, room.bytes, (long)(room.seconds*1000));
	if (room_grown)
		Con_Printf ("room: loaded whole on try %d; it grew %d time%s, each after a request the full zone refused (counted as failed, then loaded again)\n",
			room_tries, room_grown, room_grown == 1 ? "" : "s");
}
