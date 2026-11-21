/* SPDX-License-Identifier: GPL-2.0-or-later
 * NPCs drown (ACTOR-DROWNING-NOT-CARRIED-67, v0.0.68).
 *
 * The rule is OpenMW 0.51's (apps/openmw/mwmechanics/actors.cpp updateDrowning, lines 989-1047, run at line 1663 for
 * an NPC in the actors processing range only: creatures never drown, nor does the player here, aw_breath.c has him):
 * while the NPC is submerged (World::isSubmerged, mwworld/worldimp.cpp 2112-2132: the point 1/fSwimHeightScale (0.9) of
 * its height over its feet is under water) and has no Water Breathing, its breath left falls from fHoldBreathTime (20 s)
 * by the time passed; at 0 it loses fSuffocationDamage (3) health a second; out of the water the breath is full again.
 * The same pure steps as the player's (aw_breath_rules.c AW_BreathStep, AW_BreathDamage).
 *
 * Here: only while the loaded map is a room whose cell has the water flag (aw_mwhost.c AW_MwscriptRoomWater; the
 * Mournhold districts are outdoor maps here: their water is not checked for actors, named in the status), every server
 * frame, one point test of hull 0 per NPC. The NPCs under water are rows of a fixed table (AW_DROWN_ROWS); a row goes
 * when its NPC is out of the water with a full breath, dies, or the map changes. The breath left is kept in the world
 * change list as the named fact "amiwind:breath:<reference>" (the float's bits), so a save made under water loads with
 * the same breath (OpenMW keeps it in the NPC's stats); New Game clears the facts and the table. The health is lost
 * through the NPC's own record and its death through the scripts' death path (aw_mwhost.c AW_MwscriptActorHurt).
 * Not yet: an NPC swimming up for air (AiBreathe, ACTOR-BREATHE-SWIM-UP-68), the knocked-out case
 * (ACTOR-KNOCKED-OUT-IN-WATER-DROWNS-68), the "drown" sound for NPCs. */
#ifndef AW_DROWN_H
#define AW_DROWN_H

#include <stdint.h>

#define AW_DROWN_ROWS 32
#define AW_DROWN_SWIM_HEIGHT_SCALE 0.9f    /* fSwimHeightScale, Morrowind.esm */

typedef struct {uint32_t reference;float left;} aw_drown_row_t;
typedef struct {aw_drown_row_t row[AW_DROWN_ROWS];int count;unsigned long full;} aw_drown_table_t;

/* The row of REFERENCE in T: its index, or with CREATE a new row (its breath LEFT -1: full, not yet set); -1 when it has
 * none and CREATE is 0, or the table is full (counted in T->full). */
int AW_DrownRow(aw_drown_table_t *t,uint32_t reference,int create);
/* Row INDEX out of T (the last row takes its place). */
void AW_DrownDrop(aw_drown_table_t *t,int index);
/* The height over an actor's feet that must be under water for it to be submerged: HEIGHT / fSwimHeightScale. */
float AW_DrownHeadHeight(float height);
/* Whether a resident NPC's edict is checked (ACTOR-DROWNING-NOT-CARRIED-67 seen again in play, 2026-11-20: the first
 * check read the edict's own health field, which a resident NPC never sets, so no NPC was ever checked): FIGHT_STATE the
 * combat layer's (aw_actors.h AW_CombatSlotState: 0 not fighting, 1 fighting, 2 dead), DRAWN 1 while the NPC is shown
 * (a Disable hides it: OpenMW leaves a disabled reference out of the scene). Its health is the actor record's. */
int AW_DrownTakes(int fight_state,int drawn);
/* One NPC for DT seconds: the breath left of row INDEX of T after the step (SUBMERGED, BREATHING with Water
 * Breathing; S the hold and suffocation settings), the health it loses now in *LOSS. Returns 1 when the row is to stay
 * (under water, or its breath not full yet), 0 when it can go (out of the water, full). */
int AW_DrownStep(aw_drown_table_t *t,int index,int submerged,int breathing,float hold,float suffocation,float dt,
                 float *loss);
/* The saved fact of REFERENCE's breath: "amiwind:breath:<reference>" into OUT; the breath left in its 32 bits and back. */
void AW_DrownFactId(char out[32],uint32_t reference);
long AW_DrownFactValue(float left);
float AW_DrownFactLeft(long value);

/* Engine glue (aw_drown.c): every server frame after the player's breath (aw_breath.c AW_BreathPhysics); the status
 * lines of aw_breath; the reset at init. */
void AW_DrownPhysics(void);
void AW_DrownStatus(void);
void AW_DrownInit(void);
/* aw_mwhost.c: 1 while the loaded map is a room whose cell has the water flag; an NPC's health less LOSS through its
 * record and the scripts' death path (1 when the loss killed it, -1 when the edict has no NPC record). */
int AW_MwscriptRoomWater(void);
struct edict_s;
int AW_MwscriptActorHurt(struct edict_s *e,float loss);
uint32_t AW_MwscriptNpcReference(struct edict_s *e);

#endif
