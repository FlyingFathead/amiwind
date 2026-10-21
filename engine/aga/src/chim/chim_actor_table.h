/* SPDX-License-Identifier: GPL-2.0-or-later
 * The CHIM actor table (EXPERIMENTAL; tools/chim/actors.py writes it, the
 * type 1 window reads it with "chim actors table 1"): every exterior NPC and
 * creature reference of the game data, outside the frames. Big-endian, layout
 * in tools/chim/actors.py and docs/chim/WORLD_FORMAT.md "Actor table". This
 * file only decodes; aw_actors.c reads the file and spawns. */
#ifndef CHIM_ACTOR_TABLE_H
#define CHIM_ACTOR_TABLE_H

#define CHIM_ACTOR_HEADER_BYTES	48
#define CHIM_ACTOR_CELL_BYTES	16
#define CHIM_ACTOR_RECORD_BYTES	24
#define CHIM_ACTOR_BASE_BYTES	12
#define CHIM_ACTOR_VERSION		1
#define CHIM_ACTOR_VERSION_LISTS	2	/* with the levelled creature lists */
#define CHIM_ACTOR_VERSION_SCALES	3	/* and the instance scales after them */
#define CHIM_ACTOR_SCALE_BYTES	8	/* u32 record index, f32 scale */
#define CHIM_ACTOR_LIST_BYTES	8
#define CHIM_ACTOR_ENTRY_BYTES	4
#define CHIM_ACTOR_NESTED		0x8000	/* entry target: a list, not a base */
#define CHIM_ACTOR_NOTHING		0xFFFF	/* entry target: names no record */
#define CHIM_ACTOR_ALL_LEVELS	1	/* list flag: calculate from all levels <= the player's */
#define CHIM_ACTOR_PICK_NONE	(-1)
#define CHIM_ACTOR_MAX_DEPTH	8
#define CHIM_ACTOR_BAKED		1	/* record flag: the origin is the baked ground point */
#define CHIM_ACTOR_BUILT		2	/* record flag: from a built actor row */
#define CHIM_ACTOR_SCALED_MODEL	4	/* record flag: the base's model is baked at the record's scale */
#define CHIM_ACTOR_KIND_NPC		0
#define CHIM_ACTOR_KIND_CREATURE	1
#define CHIM_ACTOR_KIND_LEVELLED	2
#define CHIM_ACTOR_KIND_CORPSE	3
#define CHIM_ACTOR_FILE			"maps/chim-actors.cca"

typedef struct
{
	unsigned	cells, cells_at, records, records_at, bases, bases_at, text_at, bytes;
	unsigned	version, lists, lists_at;	/* lists: 0 in a version 1 table */
} chim_actor_head_t;

typedef struct
{
	int			cx, cy;
	unsigned	first, count;
} chim_actor_cell_t;

typedef struct
{
	unsigned	key;
	int			base, flags;
	float		origin[3], yaw;
} chim_actor_record_t;

typedef struct
{
	unsigned	at, bytes, hash;
	int			kind;
} chim_actor_base_t;

/* 1 when the header is a table of this version whose parts lie inside FILE_BYTES. */
int ChimActors_Header (const unsigned char *p, long file_bytes, chim_actor_head_t *h);
void ChimActors_Cell (const unsigned char *p, chim_actor_cell_t *c);
/* 1 when the record's numbers are finite and inside a cell's range and its base exists. */
int ChimActors_Record (const unsigned char *p, const chim_actor_head_t *h, chim_actor_record_t *r);
/* 1 when the base's text lies inside the text block (a levelled base of a version 2 table: AT is its list). */
int ChimActors_Base (const unsigned char *p, const chim_actor_head_t *h, chim_actor_base_t *b);

/* Version 2: the list section (from LISTS_AT, BYTES long: u32 lists, the list heads, the entries) is whole and
 * every entry's target is a base below BASES, a list, or nothing. 1 when it is. */
int ChimActors_ListsValid (const unsigned char *s, unsigned long bytes, unsigned bases);

/* Version 3: the bytes of the list section that starts at S (AVAIL bytes up to the end of the file), the scale
 * section following it; 0 when the list heads do not fit. */
unsigned long ChimActors_ListBytes (const unsigned char *s, unsigned long avail);

/* Version 3: the scale section (u32 count, then per scaled record u32 record index and f32 scale, by record
 * index) is BYTES long, its records below RECORDS, its scales finite and positive. 1 when it is. */
int ChimActors_ScalesValid (const unsigned char *s, unsigned long bytes, unsigned records);

/* The instance scale of record INDEX in a valid scale section (1 when it is not listed). */
float ChimActors_Scale (const unsigned char *s, unsigned index);

/* The roll state of a reference (its key and the session seed) and the next value (xorshift32): the same numbers
 * as tools/chim/actors.py rng_seed / rng_next. */
unsigned ChimActors_RollSeed (unsigned key, unsigned seed);
unsigned ChimActors_Rand (unsigned *state);

/* One roll of list INDEX of a valid list section S at player LEVEL: the base index it gives, or
 * CHIM_ACTOR_PICK_NONE. The rule (read from OpenMW 0.51 getLevelledItem; our own implementation, the same as
 * tools/chim/actors.py levelled_pick): chance none first (a roll 0-99 below it gives nothing); the candidates are
 * every entry at or below the level when the list calculates from all levels, else only the entries at the
 * highest level at or below it; none = nothing; one candidate picked uniformly; a list picked is rolled again
 * at the same level (at most CHIM_ACTOR_MAX_DEPTH deep); an entry naming nothing gives nothing. */
int ChimActors_LevelledPick (const unsigned char *s, unsigned index, int level, unsigned *state);

#endif
