/* SPDX-License-Identifier: GPL-2.0-or-later
 * Budgeted local navigation for follower NPCs (aw_npcpath.c,
 * docs/DEBUG_OVERLAYS.md, "NPC companion test"). Integer only: no
 * allocation, no floats; the engine side (aw_companion.c) turns the
 * requests into hull traces.
 */
#ifndef AW_NPCPATH_H
#define AW_NPCPATH_H

#define AW_PATH_FAN 32          /* heading table entries (11.25 degrees) */
#define AW_PATH_FAN_RADIUS 64   /* table vector length */
#define AW_PATH_PING_DIRS 16    /* ping directions (every other heading) */
#define AW_PATH_PROBE 32        /* ping sweep length, world units */
#define AW_PATH_GRID 8          /* flood fill: 8 x 8 step cells */
#define AW_PATH_CELLS (AW_PATH_GRID*AW_PATH_GRID)
#define AW_PATH_CELL 16         /* cell size, world units */
#define AW_PATH_STEP 9          /* largest floor rise/drop between cells (player step 8.5) */
#define AW_PATH_ROUTE 14        /* route cells kept per follower */
#define AW_PATH_TRACES 2        /* hard cap: search traces per think */
#define AW_PATH_STALL 4         /* thinks without progress before a ping */
#define AW_PATH_COMMIT 5        /* thinks a ping's detour is kept */
#define AW_PATH_PINGS 3         /* failed detours before the flood fill */

enum {
    AW_PATH_FOLLOW,             /* greedy: walk straight at the goal */
    AW_PATH_PING,               /* fan of short sweeps, a few per think */
    AW_PATH_DETOUR,             /* walk the ping's heading for a few thinks */
    AW_PATH_FLOOD,              /* step-cell flood fill, a few cells per think */
    AW_PATH_WALK,               /* walk the flood fill's cells */
    AW_PATH_LOST                /* nothing found: the owner teleports or waits */
};

/* The engine's traces. Coordinates are whole world units at the follower's
 * feet. sweep: standing hull from the follower's position by (dx,dy), raised
 * by a step; 1 = clear. cell: standing hull dropped at (x,y) from z+step to
 * z-step; 1 = walkable floor there, *floor = its height. */
typedef struct {
    void *context;
    int (*sweep)(void *context, int dx, int dy);
    int (*cell)(void *context, int x, int y, int z, int *floor);
} aw_path_io_t;

/* One follower's whole navigation state: 48 bytes (int is 32 bits on the
 * 68k and on the host test compilers). */
typedef struct {
    int x, y;                   /* position at the previous think */
    int gx, gy, gz;             /* flood grid corner (cell 0,0) and reference height */
    unsigned char mode, heading;        /* mode, heading index of the last move */
    unsigned char cursor, base;         /* ping: next fan slot, goal heading at start */
    unsigned char stall, commit, pings; /* thinks without progress, detour left, failed detours */
    unsigned char run, fallback;        /* thinks of steady progress, first clear ping heading + 1 */
    unsigned char steps, at;            /* route length and position */
    unsigned char route[AW_PATH_ROUTE]; /* route cells (y*8+x) */
} aw_path_t;

/* Totals since the last reset, for dbg companiontest. */
typedef struct {
    unsigned long thinks, stuck, pings, ping_traces, detours;
    unsigned long floods, flood_cells, routes, lost, traces;
} aw_path_stats_t;

extern aw_path_stats_t aw_path_stats;
extern const signed char aw_path_fan[AW_PATH_FAN][2];

void AW_PathReset(aw_path_t *s, int x, int y);
/* The follower is close enough: stand, forget any search, no traces. */
void AW_PathIdle(aw_path_t *s, int x, int y);
/* One think. self and goal are feet positions in whole units. step is the
 * distance the owner walks this think. Writes the heading index to walk
 * (*heading) and returns 1, or returns 0 to stand this think (searching). */
int AW_PathThink(aw_path_t *s, const aw_path_io_t *io, const int self[3],
                 const int goal[3], int step, int *heading);
/* Heading index (0..31) closest to (dx,dy); fan entry 0 is +X, 8 is +Y. */
int AW_PathHeading(int dx, int dy);
/* Horizontal length without a square root: max + 3/8 min (within 7 %). */
int AW_PathLength(int dx, int dy);
/* Follow speed, units per second. gap and distance: feet to feet. mimic:
 * the player's own horizontal speed (a standing player is walked up to at
 * walking pace), a quarter more beyond twice the distance; mimic off: walk,
 * run beyond twice the distance. Never above AW_PATH_SPEED_MAX; eases down
 * over the last half distance (at least 16 units) so it never overshoots. */
#define AW_PATH_WALK_SPEED 120
#define AW_PATH_RUN_SPEED 200
#define AW_PATH_SPEED_MAX 360   /* the player's top speed (320) plus a little */
#define AW_PATH_SPEED_MIN 24
int AW_PathSpeed(int mimic, int player_speed, int gap, int distance);
/* Bytes of shared scratch (the flood fill's grid, queue, parents, heights). */
int AW_PathScratchBytes(void);

#endif
