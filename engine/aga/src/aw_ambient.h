/* SPDX-License-Identifier: GPL-2.0-or-later
 * Ambient behaviour: the residents' Wander packages (aw_ambient.c, docs/NPC_PATHFINDING.md; NPC-WANDER-NOT-EXECUTED-35).
 *
 * The builder compiles every placed actor's Wander package and its cell's path grid routes (tools/ambient_lut.py,
 * id1/npc-ambient.lut, AWAM1); the engine runs a tiny state machine per actor that is near the player and never
 * searches: idle (an Idle2..Idle9 group of the shared animation table, picked by the original's chances), walk a
 * precompiled route to a destination, idle again. The rules are the original's as OpenMW 0.51 implements them
 * (apps/openmw/mwmechanics/aiwander.cpp); our own code. Default OFF ("chim actors ambient on" switches it on, not saved) until the A/B is recorded.
 *
 * The pure part (no engine state, host-tested by tests/aga_ambient_test.c with AW_AMBIENT_HOST_TEST) reads the
 * table and makes every decision from integers; the engine part moves and animates.
 */
#ifndef AW_AMBIENT_H
#define AW_AMBIENT_H

#define AW_AMBIENT_HEADER	32
#define AW_AMBIENT_ROW		28
#define AW_AMBIENT_POINT	8
#define AW_AMBIENT_PROFILE	16
#define AW_AMBIENT_NONE		255
#define AW_AMBIENT_MAX_DEST	128	/* destinations per actor (the builder keeps 64 grid points + the extras) */
/* point kinds */
#define AW_AMBIENT_GRID		0
#define AW_AMBIENT_HOME		1
#define AW_AMBIENT_PARTWAY	2
/* row flags */
#define AW_AMBIENT_REPEAT	1
#define AW_AMBIENT_CREATURE	2
#define AW_AMBIENT_FLYER	4
#define AW_AMBIENT_SWIMMER	8

typedef struct {
	unsigned long	ref, hash;
	unsigned short	distance, duration;	/* original units; game hours */
	unsigned char	hour, flags, points, destinations;
	unsigned long	first_point, first_hop;
	unsigned short	profile;
} aw_ambient_row_t;

/* The resident part: header and rows (from the start of the file) and the idle profiles (its end). The points and
 * hops of one actor are read from the file when it starts its package (AW_AmbientBlobAt). */
typedef struct {
	const unsigned char	*rows_data;		/* rows x AW_AMBIENT_ROW */
	const unsigned char	*profile_data;	/* profiles x AW_AMBIENT_PROFILE */
	long	rows, points, hop_bytes, profiles;
	unsigned	multiplier;					/* fIdleChanceMultiplier x 65535 */
	long	points_at, hops_at, profiles_at;	/* file offsets */
} aw_ambient_table_t;

/* Bytes of the header and rows (the first resident part), or -1 when HEAD (AW_AMBIENT_HEADER bytes) is not AWAM1
 * or does not fit FILE_SIZE. */
long AW_AmbientRowsSize (const unsigned char *head, long file_size);
/* 1 and *t filled when ROWS (AW_AmbientRowsSize bytes) and PROFILES (the file's last profiles x 16 bytes) are a
 * valid table of a file of FILE_SIZE bytes: every row's points and hops inside the file, every profile index
 * inside, rows sorted. */
int AW_AmbientOpen (aw_ambient_table_t *t, const unsigned char *rows, long rows_size, const unsigned char *profiles,
	long file_size);
long AW_AmbientProfilesSize (const aw_ambient_table_t *t);
/* FNV-1a 32 of the lower-case id (tools/ambient_lut.py fnv). */
unsigned long AW_AmbientHash (const char *id);
/* The row of a placement (reference number and id hash), or -1. */
long AW_AmbientFind (const aw_ambient_table_t *t, unsigned long ref, unsigned long hash);
void AW_AmbientRow (const aw_ambient_table_t *t, long index, aw_ambient_row_t *out);
/* The file offsets and byte counts of a row's points and of its hops (two reads: they are not adjacent). */
void AW_AmbientBlobAt (const aw_ambient_table_t *t, const aw_ambient_row_t *r, long *points_at, long *points_bytes,
	long *hops_at, long *hops_bytes);
void AW_AmbientProfile (const aw_ambient_table_t *t, int index, unsigned short cdf[8]);

/* The idle roll (aiwander.cpp getRandomIdle) as a cumulative table: chances[8] (Idle2..Idle9, 0..100, larger
 * clamped), multiplier x 65535 (fIdleChanceMultiplier); exact at 1 % steps, the builder's rule (ambient_lut.py
 * idle_profile). For a script's AIWander. */
void AW_AmbientIdleProfile (const unsigned char chances[8], unsigned multiplier, unsigned short cdf[8]);
/* The idle a roll (0..65535) picks: 2..9, or 0 for none. */
int AW_AmbientPickIdle (const unsigned short cdf[8], unsigned roll);
/* 1 when an offset (engine units) is within DISTANCE (original units): 16 (x^2 + y^2 + z^2) <= distance^2. */
int AW_AmbientWithin (int x, int y, int z, unsigned distance);

/* One actor's compiled package (pure decisions). blob: points (AW_AMBIENT_POINT each) then the hop bytes
 * (points x destinations), as read from the file. */
typedef struct {
	const unsigned char	*blob;
	unsigned char	points, destinations;
	unsigned short	distance, record_distance;
	unsigned char	allowed[AW_AMBIENT_MAX_DEST / 8];	/* bit per destination */
	unsigned char	count;		/* allowed destinations */
	unsigned char	manual;		/* no destination: walk now and then to a random spot near the start */
	unsigned char	cur;		/* the destination the actor stands at (OpenMW mCurrentPosition) */
} aw_ambient_pkg_t;
void AW_AmbientPoint (const aw_ambient_pkg_t *p, int index, int xyz[3], int *kind);
/* The allowed destinations for DISTANCE (aiwander.cpp fillAllowedPositions): grid points within it; with exactly
 * one, also the starting position and (only at the record's own distance) the part-way points; with none, the
 * package wanders manually (distance > 0) or stands. cur = the allowed destination closest to the start. */
void AW_AmbientAllow (aw_ambient_pkg_t *p, unsigned distance);
/* A destination other than cur, picked uniformly by ROLL (setPathToAnAllowedPosition), or -1 with fewer than 2. */
int AW_AmbientPickDestination (const aw_ambient_pkg_t *p, unsigned roll);
/* The next local point from local point FROM toward destination GOAL, or -1 (no route). */
int AW_AmbientHop (const aw_ambient_pkg_t *p, int from, int goal);
/* The local point nearest an offset from the start (an actor put off its route, after a fight), or -1. */
int AW_AmbientNearest (const aw_ambient_pkg_t *p, int x, int y, int z);

#ifndef AW_AMBIENT_HOST_TEST
struct edict_s;
void AW_AmbientInit (void);
/* SV_Physics, after combat: every registered actor near the player thinks every think interval (0.1 s). */
void AW_AmbientPhysics (void);
/* "chim actors ambient [on|off|think S|list|reset]", forwarded by aw_actors.c (no command or cvar of its own). */
void AW_AmbientCommand (void);
/* MWScript's AIWander (the interpreter's call; v054-actorstate): the package of E becomes DISTANCE (original
 * units), DURATION (game hours), HOUR (stored, unused as in OpenMW), IDLE[8] (Idle2..Idle9 chances, 0..100) and
 * REPEAT, as OpenMW's OpAiWander stacks it. Returns 1 when set (the actor is then run by this module; an actor
 * outside the table walks manually when DISTANCE > 0 and its cell has no compiled route). */
int AW_AmbientWander (struct edict_s *e, int distance, int duration, int hour, const unsigned char idle[8], int repeat);
/* The speed attribute of an actor when the actor record has it (v054-actorstate sets it), else NULL / -1:
 * the walk speed then uses the attribute 50 (an AmiWind stand-in, said in docs/NPC_PATHFINDING.md). */
extern int (*aw_ambient_speed_attribute)(struct edict_s *e);
/* GetCurrentAIPackage / GetAIPackageDone for the interpreter (v054-mwscript sets its aw_mwscript_ai_package hook to
 * this): OpenMW's package number (-1 none, 0 Wander; Travel, Escort, Follow, Activate are not run yet and read as
 * none), *done 1 once a non-repeating Wander has run its duration. */
int AW_AmbientAiPackage (struct edict_s *e, int *done);
/* AW_ActorStep's failure diagnostics (aw_walk.c), filled only while aw_actor_step_diag is set ("chim actors ambient
 * steplog on"): the refusing test, the position the walk move reached, and that position's support trace as
 * fraction, plane normal x y z, startsolid. */
enum {AW_STEP_FAIL_MOVE=1,AW_STEP_FAIL_SUPPORT,AW_STEP_FAIL_HEIGHT,AW_STEP_FAIL_LAVA};
extern int aw_actor_step_diag,aw_actor_step_fail;
extern float aw_actor_step_reached[3],aw_actor_step_floor[5];
#endif

#endif
