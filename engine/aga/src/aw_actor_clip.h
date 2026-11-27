/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_actor_clip.h: a creature collides only as high as its drawn body (SOL-SEA-INVISIBLE-BLOCKER-68,
 * ACTOR-CLIP-ABOVE-DRAWN-BODY-69). See aw_actor_clip.c. */
#ifndef AW_ACTOR_CLIP_H
#define AW_ACTOR_CLIP_H

#define AW_ACTOR_CLIP_MIN 1.0f      /* the lowest top a creature keeps (map units): a body is never flat */

/* 1 (the default, also written into id1/default-game.cfg): a creature's box collides up to its drawn body's top;
 * 0: the person box for every actor, the method before v0.0.69. Not saved. */
extern cvar_t aw_actor_clip;
/* world.c: the top a body collides up to (NULL: its box top) */
extern float (*aw_actor_clip_top)(const edict_t *e);

/* The rule (pure, host tested): the top a box of top BOX_TOP collides up to, for a body whose drawn top is DRAWN
 * model units above its origin, drawn at SCALE; BOX_TOP when DRAWN or SCALE is not a positive number. Never above
 * BOX_TOP, never below AW_ACTOR_CLIP_MIN. */
float AW_ActorClipTopRule(float box_top, float drawn, float scale);
/* The highest point above its origin of an alias model's drawn poses: a skeletal actor's rest frame (the idle pose
 * it stands in), every stored frame of any other; 0 when the model is no alias model or holds no frame. */
float AW_ActorModelTop(model_t *m);
/* After every new box of an entity (pr_cmds.c SetMinMaxSize: world.qc aw_npc_floor's person box, the arena's): a
 * creature's top from its model; any other entity keeps its box. */
void AW_ActorClipSet(edict_t *e);
/* The top E collides up to (world.c through aw_actor_clip_top): its own box top, or the lower one set above. */
float AW_ActorClipTop(const edict_t *e);
void AW_ActorClipInit(void);

#endif
