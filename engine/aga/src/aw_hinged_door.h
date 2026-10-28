/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_HINGED_DOOR_H
#define AW_HINGED_DOOR_H
/* Ordinary hinged doors: placed DOOR records without a destination
 * (aw_hinged_door.c, the builder's id1/hinged-doors.txt). Needs quakedef.h. */

/* The turn of an open door and its speed (rule from OpenMW
 * apps/openmw/mwworld/worldimp.cpp World::rotateDoor: the reference's Z
 * rotation goes from its placed value to +90 degrees at 90 degrees a second).
 * Morrowind's Z rotation is clockwise seen from above and the converted yaw is
 * its negative, so an opening door's yaw falls by 90. */
#define AW_HINGE_OPEN_DEGREES 90.f
#define AW_HINGE_DEGREES_PER_SECOND 90.f

/* Table row flags, written by the builder (tools/prepare_door_audio.py). */
#define AW_HINGE_LOCKED 1	/* a lock level above 0 or a key (OpenMW CellRef: content files) */
#define AW_HINGE_KEY 2		/* the reference names a key (KNAM) */
#define AW_HINGE_TRAP 4		/* the reference names a trap spell (TNAM) */
#define AW_HINGE_SCRIPT 8	/* the DOOR record has a script (not run) */

/* Story rules on a hinged door (aw_opening.c AW_OpeningHingedStory, the
 * census hall door): the hook answers -1 for a reference it has no rule for.
 *   LOCK     0 the story has unlocked it, 1 the story keeps it locked (in
 *            place of the table's lock flag)
 *   REFUSED  a use while it is locked (the locked sound plays as well)
 *   OPEN     it starts to open; CLOSED it has come back shut
 *   SPAWN    1 when it stands open as its map spawns (a saved state) */
#define AW_HINGE_STORY_LOCK 0
#define AW_HINGE_STORY_REFUSED 1
#define AW_HINGE_STORY_OPEN 2
#define AW_HINGE_STORY_CLOSED 3
#define AW_HINGE_STORY_SPAWN 4
extern int (*aw_hinged_story)(unsigned ref,int event);
int AW_OpeningHingedStory(unsigned ref,int event);
/* What the player reads when a turning door holds against them. The original
 * game holds the door without a word (OpenMW World::rotateDoor; no game
 * setting or script says anything); the words are AmiWind's, the ones the
 * census hall door's story rule used before it became a hinged door. */
#define AW_HINGE_HELD_TEXT "The door is obstructed. Step aside."

void AW_HingedDoorInit(void);
/* The LockedDoor sound to the player (not at a door): 1 when played. */
int AW_HingedDoorLockedSound(void);
/* A new map: forget the doors of the last one (aw_scenery.c AW_SceneryBegin). */
void AW_HingedDoorMapBegin(void);
/* The map's entities exist: take its door edicts (aw_scene.c, after spawn). */
void AW_HingedDoorSpawn(void);
/* One server frame: turn the moving doors. No work while none moves. */
void AW_HingedDoorTick(double seconds);
/* The use key and the prompt: the hinged door under the crosshair. */
int AW_HingedDoorUse(void);
int AW_HingedDoorHint(const char **name,const char **action);
/* 1: this func_wall must stay an edict (aw_scenery.c capture). */
int AW_HingedDoorProtect(edict_t *e);
/* Table lookup by reference number: the row, -1 none (also for host tests). */
int AW_HingedDoorRow(unsigned reference);
/* Object state (v0.0.51): the game data's lock level of a placed door, -1 when it is not one; and the scripts'
 * lock (aw_mwhost.c sets it: the level the scripts left, ORIGINAL when none). */
int AW_HingedDoorOriginalLock(unsigned reference);
extern int (*aw_object_lock_level)(unsigned reference,int original);
/* DEBUG-GOD-LOCKED-DOORS-51: a load door's lock (the table's K rows; aw_scene.c through aw_load_door_lock).
 * USE 0: 1 when locked now; USE 1: the player's use, 1 = refused (LockedDoor played), 0 = through (unlocked,
 * the key, god mode with AW_DOOR_GOD_TEXT in the message box, dbg doorlocks off). */
int AW_HingedDoorLoadLock(unsigned reference,int use);
/* The maintainer's words (TG, 25 October 2026). */
#define AW_DOOR_GOD_TEXT "God mode used to enter a locked door"
/* Activation: a script that reads OnActivate takes the use (aw_mwhost.c sets it); its Activate opens the door. */
extern int (*aw_hinged_intercept)(unsigned reference);
int AW_HingedDoorActivate(unsigned reference);
/* CHIM placements (chim/chim_chunks.c, through chim_hinged_door): 1 when the
 * reference is a hinged door; *yaw gets its current pose. */
int AW_HingedDoorPlacement(unsigned pid,unsigned reference,const float *origin,float radius,float *yaw);
void AW_HingedDoorRecentre(const float *d);

#endif
