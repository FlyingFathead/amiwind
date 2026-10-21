/* SPDX-License-Identifier: GPL-2.0-or-later
 * PROTOTYPE (branch v0.0.46-type1-stateful): stateful actors of the type 1
 * window (aw_actors.c) and the small helpers it uses in aw_combat.c and
 * chim/chim_chunks.c. */
#ifndef AW_ACTORS_H
#define AW_ACTORS_H

void AW_ActorsInit (void);

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
