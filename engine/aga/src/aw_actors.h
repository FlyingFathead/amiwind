/* SPDX-License-Identifier: GPL-2.0-or-later
 * PROTOTYPE (branch v0.0.46-type1-stateful): stateful actors of the type 1
 * window (aw_actors.c) and the small helpers it uses in aw_combat.c and
 * chim/chim_chunks.c. */
#ifndef AW_ACTORS_H
#define AW_ACTORS_H

void AW_ActorsInit (void);
void AW_ActorsRoomTick (void);
/* The model the world draws a creature or NPC record ID with (its actor table base); 1 found (MODEL filled), 0 none.
 * The combat playground's creatures (COMBAT-PLAYGROUND-CREATURE-HUMANOID-61). */
int AW_ActorsBaseModel (const char *id, char *model, int size);
/* Object state: a script's Disable keeps an actor of the CHIM window from spawning (aw_mwhost.c sets it). */
extern int (*aw_actor_disabled)(unsigned reference);
/* A script's Enable of REFERENCE (aw_mwhost.c calls it; AW_ActorsInit sets it): an actor of a joined cell that was not
 * spawned while disabled spawns on the next tick (SCRIPTED-EVENT-FALLING-MAGE-61). */
extern void (*aw_actor_enabled)(unsigned reference);

/* PositionCell of an actor (v0.0.62, MWSCRIPT-POSITIONCELL-ACTORS-62; aw_mwhost.c AWF_POSITIONCELL). The actor's row of
 * the world change list says where it is now: ROOM a room's stable number with ORIGIN in that room map's own units, or
 * 0 with ORIGIN on the island (game units / 4); YAW Quake's. 1 kept, 0 the list could not take it. */
int AW_ActorsMoveTo (unsigned reference, long room, const float origin[3], float yaw);
/* The actor's row from its edict as it stands now (place, position, health), as a leaving actor's is kept. */
void AW_ActorsCapture (edict_t *e);
/* The actor's edict leaves this map (moved elsewhere): its combat slot let go, the edict freed; its row stays. */
void AW_ActorsRemove (edict_t *e);
/* Resurrect (v0.0.62): REFERENCE back to its game data (change row, live record, body contents gone). */
void AW_ActorsReset (unsigned reference);
/* A placed row's place in this session's units and its angles (v0.0.62: a placed object spawns there); 1 when kept. */
int AW_ActorsRowPlace (unsigned reference, float origin[3], float angles[3]);
/* An actor of another place arrives here: TEXT its entity block ("{" .. "}", LENGTH bytes) spawned as a joining frame's
 * actor is (its row's place and position applied); the edict, or NULL (dead, disabled, alive here already, no memory). */
edict_t *AW_ActorsSpawnVisitor (const char *text, unsigned long length);
/* The row of REFERENCE: 1 when it was moved (*ROOM its room, 0 outdoors), 0 none or never moved. */
int AW_ActorsMovedPlace (unsigned reference, long *room);
/* The loaded room's stable number, 0 outdoors (v0.0.62: AIFollowCell / AIEscortCell compare their place with it). */
long AW_ActorsRoom (void);
/* A follower through a door (v0.0.62): REFERENCE's row puts it in the place loaded now at ORIGIN (this map's units). */
int AW_ActorsArriveHere (unsigned reference, const float origin[3], float yaw);
/* The CHIM frame map an outdoor actor E was joined from (v0.0.62: its entity is read there when it goes through a
 * door with the player): the frame of its baked home point among the frames joined this session. 1 found. */
int AW_ActorsFrameMap (edict_t *e, char *map, int size);
/* A room's arrivals: called when a room's actors take their rows (aw_mwhost.c sets it: the VISI rows of ROOM). */
extern void (*aw_actors_visitors)(long room);
/* An actor a levelled list gave has spawned (MWSCRIPT-UNPLACED-ATTACH-62; aw_mwhost.c sets it: its record's script,
 * the LACT row of HASH, the actor table's base hash of the record, attached under the list's reference). */
extern void (*aw_actors_levelled_spawned)(edict_t *ent, unsigned hash);

/* Actors a script placed (v0.0.62, MWSCRIPT-PLACE-OBJECTS-62; aw_mwhost.c AWF_PLACE*): new references in the block
 * AW_ACTORS_PLACED .. AW_ACTORS_PLACED | 0xFFFFF (content file index 15, which no game file has; aw_mwhost.c: the
 * object's PLAC row << 12 | a serial). */
#define AW_ACTORS_PLACED 0xF00000U
/* Summoned creatures (v0.0.62, SUMMONED-CREATURES-62; aw_mwhost.c summons): AW_ACTORS_SUMMONED | slot, content file
 * index 14, which no game file AmiWind reads has. Their rows follow the player (follow set) and are never spawned by
 * AW_ActorsPlacedTick: the summon itself spawns them while its effect lasts. */
#define AW_ACTORS_SUMMONED 0xE00000U
#define AW_ACTORS_SUMMONED_SLOTS 0x100U
/* REFERENCE's row (a placed or a summoned key): placed here, at LOCAL (this map's units) facing YAW; the row is made
 * new (1 kept, 0 refused). */
int AW_ActorsPlaceRow (unsigned reference, const float local[3], float yaw);
/* REFERENCE's row emptied (a placement that could not spawn): not saved, the key free again. */
void AW_ActorsPlacedForget (unsigned reference);
/* 1 when REFERENCE has no row with a field and no live edict (a key a new placement may take). */
int AW_ActorsPlacedFree (unsigned reference);
/* The actor table's entity text of record ID ("{" .. "}", a copy to free, *LENGTH its bytes), or NULL. */
char *AW_ActorsBaseText (const char *id, unsigned long *length);
/* Once a second: the placed actors whose row puts them here and that do not live are spawned by SPAWN (1 spawned). */
void AW_ActorsPlacedTick (int (*spawn)(unsigned reference));
/* "placed actors: ..." for aw_mwscript_status. */
void AW_ActorsPlacedStatus (void);

/* aw_combat.c: 0 not fighting, 1 fighting, 2 dead (health written if asked) */
int AW_CombatSlotState (edict_t *e, float *health);
/* aw_combat.c: a test fight with this resident (dead: it dies at once) */
int AW_CombatTestEngage (edict_t *t, int dead);
/* aw_combat.c: a fighter's health (a resumed fight); 0 when it has no combat slot */
int AW_CombatSetHealth (edict_t *e, float health);
/* aw_combat.c: the resident's combat slot is let go (before its edict is freed) */
void AW_CombatForget (edict_t *e);

/* chim/chim_chunks.c: the cell of a session position and whether the window holds it */
int ChimChunks_WindowCell (const vec3_t origin, int *cx, int *cy, int *held);
/* chim/chim_chunks.c: the cell whose centre is the session's origin */
int ChimChunks_OriginCell (int *cx, int *cy);

#endif
