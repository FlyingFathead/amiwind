/* What the use key acts on (FOCUS-NPC-OVERRIDES-ITEM-62). As in OpenMW 0.51 the activation goes to the nearest object
 * along the view ray within the activation distance, never to the nearest actor by proximity: an item or plant the ray
 * meets before an actor, or inside the actor's box (the box is coarser than the drawn body: a standing actor's arms, a
 * body lying on the floor), is taken; an actor the ray meets wholly before the item is talked to or searched.
 * aw_activate_rules.c holds the rules as pure functions (host tested, tests/aga_activate_rules_test.c); aw_scene.c
 * applies them (AW_ActivateActor). */
#ifndef AW_ACTIVATE_H
#define AW_ACTIVATE_H

/* The ray ORIGIN + t*DIR (t from 0) against the box MINS..MAXS, all in the box's own frame: 1 when they meet, with the
 * entry *NEAR (0 when the ray starts inside) and the exit *FAR, in units of DIR's length. */
int AW_RayBox(const float origin[3],const float dir[3],const float mins[3],const float maxs[3],float *near_hit,
              float *far_hit);
/* 1 when the use goes to the item (or plant) at ITEM along the ray rather than to the actor whose box the ray enters
 * at ACTOR_NEAR and leaves at ACTOR_FAR; ITEM below 0: no item aimed at (the actor wins); ACTOR_FAR below 0: no actor
 * (the item wins). */
int AW_ActivateItemFirst(float item,float actor_near,float actor_far);
/* The nearest of two aim distances, each below 0 when nothing is aimed at that way; below 0 when neither. */
float AW_ActivateNearest(float a,float b);

/* The last choice of aw_scene.c AW_ActivateActor (map units from the eye; -1 when none), for `aw_placed aim`. */
typedef struct {float actor_near,actor_far,item,plant;int item_first;} aw_activate_aim_t;
extern aw_activate_aim_t aw_activate_last;

#endif
