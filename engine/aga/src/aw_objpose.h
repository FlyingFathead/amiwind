/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_OBJPOSE_H
#define AW_OBJPOSE_H
/* A script's animation group on a placed object (MWSCRIPT-PLAYGROUP-ACTORS-ONLY-68; aw_objpose.c).
 *
 * The original plays PlayGroup and LoopGroup on any object whose model holds the group, and keeps the group's last pose
 * when it ends (rule from OpenMW apps/openmw/mwmechanics/objects.cpp and character.cpp playGroup, updateAnimQueue); its
 * collision follows the moved parts (components/nifbullet/bulletnifloader.cpp, apps/openmw/mwphysics/object.cpp). A CHIM
 * room draws such an object as a placement with no entity: the room conversion stores the model of each group's end
 * pose (tools/chim/anim_poses.py) and names it in the store's pose table, <store>/poses.txt:
 *
 *   AWPG1
 *   R <room record> <reference> <group> <kind M|B|H> <store model> <seconds> <loop seconds> <x0 y0 z0 x1 y1 z1>
 *
 * kind M: the end pose is the model named (drawn and collided); B: the end pose is the model as placed (a lever's return,
 * a door's close: its own model and box); H: the end pose draws nothing (the placement leaves, as a Disable would, but
 * its disabled state is not touched). When a group has played (its seconds, plus a loop's for each extra loop of a
 * LoopGroup) the placement takes the row's model and box (chim_room.c ChimRoom_PoseModel). The pose stays: the named
 * fact "amiwind:pose:<reference>" holds the group (aw_state.h: saved with the world change list, cleared by New Game),
 * and a room that loads applies it at once. A call on an object whose model has no row (an actor, a placement outside
 * the CHIM rooms) is not taken here. Cost: the table (at most AW_POSE_ROWS rows) is read once per game from the store,
 * a lookup per call walks it; per frame nothing unless a swap waits (at most AW_POSE_PENDING), and a room load walks its
 * rows once. */

#define AW_POSE_ROWS 192        /* rows kept (tools/chim/anim_poses.py POSE_ROWS_MAX refuses more) */
#define AW_POSE_GROUP 11        /* the longest group name (POSE_GROUP_CHARS) */
#define AW_POSE_ROOM 23         /* the longest room record name (POSE_ROOM_CHARS) */
#define AW_POSE_PENDING 16      /* groups playing at once whose end waits for its swap */
#define AW_POSE_TABLE "chimi/poses.txt"
#define AW_POSE_HEADER "AWPG1"
#define AW_POSE_TEXT_BYTES 24576    /* the table's text at most (192 rows of about 70 bytes) */

typedef struct {
    char room[AW_POSE_ROOM+1];
    char group[AW_POSE_GROUP+1];
    char kind;                  /* 'M', 'B' or 'H' */
    unsigned ref;               /* the reference as the room record holds it */
    int model;                  /* the store model (-1 for H) */
    float seconds, loop;
    short box[6];               /* the drawn box with that model: mins, maxs */
} aw_pose_row_t;

/* What the module asks of the engine (AW_ObjPoseInit sets the engine's; a host test sets its own):
 *   loaded  the loaded CHIM room's record name into NAME and its load serial: 1, 0 no room
 *   swap    REF's placements in the loaded room take MODEL (-1 hide) and BOX: how many changed
 *   get/set the named fact ID (0 = none)
 *   now     the game's clock in seconds (it stands still in the menus)
 *   table   the pose table's text into BUF (at most SIZE-1 bytes, 0-terminated): bytes, -1 none */
typedef struct {
    int (*loaded)(char *name, int size, unsigned long *serial);
    int (*swap)(unsigned ref, int model, const short *box);
    long (*get)(const char *id);
    void (*set)(const char *id, long value);
    double (*now)(void);
    int (*table)(char *buf, int size);
} aw_objpose_host_t;

void AW_ObjPoseInit(void);
void AW_ObjPoseSetHost(const aw_objpose_host_t *host);
/* The table from its text: rows read, -1 not a pose table (AWPG1 first). Rows past AW_POSE_ROWS or malformed are counted
 * (AW_ObjPoseCounts) and left out. */
int AW_ObjPoseParse(const char *text);
/* A script's PlayGroup (count 0) or LoopGroup GROUP COUNT on REFERENCE (either form of the reference: the record's merged
 * number or its stable id) with the start MODE (0: after a group still playing, 1 and 2: at once): 1 when the reference
 * has a row for the group (the call is carried out: the fact now, the swap when the group has played), 0 none. */
int AW_ObjPosePlay(unsigned reference, const char *group, int count, int mode);
/* One frame: a room that has just loaded takes the poses of its facts; a swap whose group has played is made. */
void AW_ObjPoseTick(void);
/* New Game, a loaded game: the waiting swaps go (the facts are the world change list's own) and the next room load
 * applies the facts again. */
void AW_ObjPoseReset(void);
/* rows, plays carried out, swaps made, calls with no row */
void AW_ObjPoseCounts(unsigned long out[4]);
/* The fact's id of REFERENCE ("amiwind:pose:<reference>") and the value that names GROUP (never 0). */
void AW_ObjPoseFact(unsigned reference, char *out, int size);
long AW_ObjPoseGroupCode(const char *group);
extern void (*aw_objpose_tick)(void);   /* defined in aw_scene.c, which calls it every frame (set by AW_ObjPoseInit) */

#endif
