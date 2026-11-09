/* SPDX-License-Identifier: GPL-2.0-or-later
 * One follow implementation (v0.0.63, ESCORT-FOLLOW-63). The follow think of the debug companion (aw_companion.c), with its state per
 * follower, used by the companion and by the script packages (aw_ambient.c: AIFollow, AIFollowCell, AIEscort,
 * AIEscortCell): the budgeted path search (aw_npcpath.c), the speed rule, the stuck detectors and the kind's stuck
 * response. The packages' own rules (hours, the place, the end, GetAIPackageDone) stay in aw_ambient.c.
 */
#ifndef AW_FOLLOW_H
#define AW_FOLLOW_H
#include "aw_npcpath.h"
#include "aw_anim.h"

struct edict_s;
/* One follower's state: about 100 bytes (the path 48, the animation play state, the stuck counters). */
typedef struct {
    unsigned char walk_frames, idle_frames, near;
    unsigned char teleport;     /* teleport search: next candidate + 1 (0 = none) */
    unsigned char teleport_why; /* 1 far, 2 stuck */
    unsigned char heavy;        /* steps in a row that ran the unstick search */
    unsigned char unseen;       /* the placement must stay out of the player's view */
    unsigned char cooldown;     /* thinks before the stuck response may run again */
    unsigned char flee;         /* thinks of fleeing left (hostile kind) */
    unsigned char policy, last_policy;  /* last stuck response (AW_STUCK_*), last printed */
    int anchor[2];              /* net-movement anchor */
    unsigned short stuck;       /* thinks since the anchor */
    aw_path_t path;
    aw_anim_play_t play;        /* animation kit play state (aw_anim.c) */
} aw_follow_t;
/* What one caller asks of the think: the distance to keep (feet to feet, game units), the actor kind (AW_ACTOR_*,
 * its stuck policy), the speed rule (1 match the target's speed, 0 walk and run), whether the stuck response may
 * place the follower near the target (0: never, as OpenMW's packages inside a cell), and a name for the log. */
typedef struct {
    int distance, kind, mimic, place;
    const char *name;
} aw_follow_rules_t;

/* A fresh follower state at E's place (its animation frames read from its model). */
void AW_FollowStart(aw_follow_t *f, struct edict_s *e);
/* One think of E following toward GOAL (feet, game units; the target TARGET's feet for a follow, a point for an
 * escort; TARGET may be NULL for a point) for DT seconds. 1 when E stands within the distance this think. */
int AW_FollowThink(aw_follow_t *f, struct edict_s *e, struct edict_s *target, const float goal[3],
                   const aw_follow_rules_t *r, float dt);
#endif
