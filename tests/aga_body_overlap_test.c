/* SPDX-License-Identifier: GPL-2.0-or-later
 * DOOR-ARRIVAL-INSIDE-ACTOR-66: two bodies whose boxes already overlap (the player arriving at the Seyda Neen census
 * office's street door while the guard 128967 stands 8 units from its arrival point 266 36 55; an actor placed where
 * the player stands). The engine's own collision (world.c SV_Move through its area links, the body rule
 * AW_BodyOverlap, SV_TestWorldPosition), stuck search (sv_phys.c SV_CheckStuck) and walk (aw_walk.c AW_WalkPlayer,
 * AW_ActorStep; sv_phys.c SV_WalkMove) run here over a synthetic world: a flat floor at z 0, one empty leaf. The
 * bodies have the game's boxes (engine/aga/qc/world.qc: the player's centred, a resident's on its feet) at the
 * positions measured in the v0.0.66-dev7 opening journey, moved down onto that floor.
 * Under Quake's box clip (aw_body_overlap 0, the method before v0.0.66) neither body can move and the stuck search
 * fails every frame ("player is stuck."); under the original's rule (aw_body_overlap 1, OpenMW 0.51
 * actorconvexcallback.cpp) a move away passes, a move toward the other's centre stops, and the search leaves the
 * bodies alone. */
#include "quakedef.h"
#include <assert.h>
#include <stdarg.h>

server_t sv;
int pr_edict_size = sizeof(edict_t);
double host_frametime = 0.1;
globalvars_t *pr_global_struct;
static globalvars_t globals;
extern cvar_t sv_gravity, sv_maxvelocity;
extern unsigned long aw_stuck_searches, aw_stuck_failed;
void AW_WalkPlayer(edict_t *p);   /* aw_walk.c (aw_links.h) */
static int stuck_lines;
void Con_Printf(char *fmt, ...) { (void)fmt; }
void Con_DPrintf(char *fmt, ...) { if (!strcmp(fmt, "player is stuck.\n")) stuck_lines++; }
void Sys_Error(char *fmt, ...) { va_list ap; va_start(ap, fmt); vprintf(fmt, ap); va_end(ap); exit(2); }
void PR_ExecuteProgram(func_t f) { (void)f; }
eval_t *GetEdictFieldValue(edict_t *e, char *field) { (void)e; (void)field; return NULL; }
/* the opening's invisible walls (aw_barrier.c): none here */
void AW_BarrierClip(vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end, edict_t *entity, trace_t *trace)
{ (void)start; (void)mins; (void)maxs; (void)end; (void)entity; (void)trace; }
edict_t *EDICT_NUM(int n) { return (edict_t *)((byte *)sv.edicts + n*pr_edict_size); }   /* pr_edict.c's */
/* common.c's area links */
void ClearLink(link_t *l) { l->prev = l->next = l; }
void RemoveLink(link_t *l) { l->next->prev = l->prev; l->prev->next = l->next; }
void InsertLinkBefore(link_t *l, link_t *before) { l->next = before; l->prev = before->prev; l->prev->next = l; l->next->prev = l; }

#define FOOT 16.625f
static model_t world_model;
static mleaf_t leafs[2];
static mplane_t floor_planes[2];
static dclipnode_t floor_nodes[2];
static edict_t ents[3];
#define PLAYER (&ents[1])
#define GUARD (&ents[2])

/* hull 0 (points: SV_PointContents) has its floor at z 0; hull 1 (both bodies' boxes, 14.64 wide) at the box's foot */
static void floor_hull(hull_t *h, int i, float dist, const float *clip_mins, const float *clip_maxs)
{
    floor_planes[i].normal[2] = 1; floor_planes[i].dist = dist; floor_planes[i].type = 2;
    floor_nodes[i].planenum = 0; floor_nodes[i].children[0] = CONTENTS_EMPTY; floor_nodes[i].children[1] = CONTENTS_SOLID;
    h->planes = &floor_planes[i]; h->clipnodes = &floor_nodes[i]; h->firstclipnode = 0; h->lastclipnode = 0;
    VectorCopy(clip_mins, h->clip_mins); VectorCopy(clip_maxs, h->clip_maxs);
}
static void make_world(void)
{
    static vec3_t none = {0, 0, 0}, bmins = {-7.32f, -7.12f, -FOOT}, bmaxs = {7.32f, 7.12f, FOOT};
    int k;
    memset(&world_model, 0, sizeof world_model);
    world_model.type = mod_brush;
    for (k = 0; k < 3; k++) { world_model.mins[k] = -4096; world_model.maxs[k] = 4096; }
    leafs[1].contents = CONTENTS_EMPTY;
    world_model.leafs = leafs; world_model.nodes = (mnode_t *)&leafs[1];
    floor_hull(&world_model.hulls[0], 0, 0, none, none);
    floor_hull(&world_model.hulls[1], 1, FOOT, bmins, bmaxs);
    world_model.hulls[2] = world_model.hulls[1];
    memset(ents, 0, sizeof ents);
    sv.edicts = ents; sv.num_edicts = 3; sv.worldmodel = &world_model; sv.models[1] = &world_model;
    ents[0].v.solid = SOLID_BSP; ents[0].v.movetype = MOVETYPE_PUSH; ents[0].v.modelindex = 1;
    SV_ClearWorld();
}
/* the player standing at X Y (as the arrival installs it: a quarter unit above the floor) */
static void player_at(float x, float y)
{
    edict_t *p = PLAYER;
    p->v.solid = SOLID_SLIDEBOX; p->v.movetype = MOVETYPE_WALK; p->v.flags = FL_CLIENT;
    p->v.mins[0] = -7.32f; p->v.mins[1] = -7.12f; p->v.mins[2] = -FOOT;
    p->v.maxs[0] = 7.32f;  p->v.maxs[1] = 7.12f;  p->v.maxs[2] = FOOT;
    p->v.origin[0] = x; p->v.origin[1] = y; p->v.origin[2] = FOOT + .25f;
    VectorCopy(p->v.origin, p->v.oldorigin); VectorCopy(vec3_origin, p->v.velocity);
    SV_LinkEdict(p, false);
}
/* a resident (world.qc aw_npc_floor: SOLID_SLIDEBOX, its box on its feet) at X Y */
static void guard_at(float x, float y)
{
    edict_t *g = GUARD;
    g->v.solid = SOLID_SLIDEBOX; g->v.movetype = MOVETYPE_STEP;
    g->v.mins[0] = -7.32f; g->v.mins[1] = -7.12f; g->v.mins[2] = 0;
    g->v.maxs[0] = 7.32f;  g->v.maxs[1] = 7.12f;  g->v.maxs[2] = 33.25f;
    g->v.origin[0] = x; g->v.origin[1] = y; g->v.origin[2] = .03125f;
    VectorCopy(g->v.origin, g->v.oldorigin);
    SV_LinkEdict(g, false);
}
static float apart(void)
{
    float dx = PLAYER->v.origin[0] - GUARD->v.origin[0], dy = PLAYER->v.origin[1] - GUARD->v.origin[1];
    return sqrt(dx*dx + dy*dy);
}
/* FRAMES frames of the player's walk at VX VY units a second (the input sets the velocity every frame) */
static void walk(int frames, float vx, float vy)
{
    int i;
    for (i = 0; i < frames; i++) {
        PLAYER->v.velocity[0] = vx; PLAYER->v.velocity[1] = vy;
        AW_WalkPlayer(PLAYER);
        SV_LinkEdict(PLAYER, false);
    }
}

int main(void)
{
    vec3_t start, end;
    trace_t tr, stop;
    unsigned long searches, failed;
    float d0, dmin;
    int i, r;
    pr_global_struct = &globals;
    sv_gravity.value = 800;
    sv_maxvelocity.value = 2000;

    /* the measured arrival: the player at 266 36, the guard at 268 44 (boxes overlap 6.2 across, 12.6 along) */
    make_world();
    player_at(266, 36);
    guard_at(268, 44);
    assert(AW_BodyOverlapping(PLAYER) == GUARD && AW_BodyOverlapping(GUARD) == PLAYER);

    /* the rule itself */
    aw_body_overlap.value = 1;
    VectorCopy(PLAYER->v.origin, start);
    VectorCopy(start, end); end[1] -= 2;   /* away from the guard's centre */
    assert(AW_BodyOverlap(PLAYER, GUARD, start, PLAYER->v.mins, PLAYER->v.maxs, end, &stop) == 1);
    VectorCopy(start, end); end[1] += 2;   /* toward it: stopped at once, on the plane facing away from it */
    assert(AW_BodyOverlap(PLAYER, GUARD, start, PLAYER->v.mins, PLAYER->v.maxs, end, &stop) == 2);
    assert(stop.fraction == 0 && stop.ent == GUARD && VectorCompare(stop.endpos, start) && !stop.startsolid);
    assert(fabs(stop.plane.normal[0] + 2/sqrt(68.0f)) < 1e-5f && fabs(stop.plane.normal[1] + 8/sqrt(68.0f)) < 1e-5f);
    assert(stop.plane.normal[2] == 0);
    VectorCopy(start, end); end[0] += 8; end[1] -= 2;   /* along the circle round it */
    assert(AW_BodyOverlap(PLAYER, GUARD, start, PLAYER->v.mins, PLAYER->v.maxs, end, &stop) == 1);
    VectorCopy(start, end); end[2] -= 4;   /* down (the walk's ground test) */
    assert(AW_BodyOverlap(PLAYER, GUARD, start, PLAYER->v.mins, PLAYER->v.maxs, end, &stop) == 1);
    assert(AW_BodyOverlap(PLAYER, GUARD, start, PLAYER->v.mins, PLAYER->v.maxs, start, &stop) == 0);   /* a position test */
    VectorCopy(start, end); end[1] += 2;
    assert(AW_BodyOverlap(PLAYER, GUARD, start, vec3_origin, vec3_origin, end, &stop) == 0);         /* a point trace */
    assert(AW_BodyOverlap(&ents[0], GUARD, start, PLAYER->v.mins, PLAYER->v.maxs, end, &stop) == 0);  /* not a body */
    start[1] = 10;  end[1] = 12;   /* apart at the start: Quake's clip */
    assert(AW_BodyOverlap(PLAYER, GUARD, start, PLAYER->v.mins, PLAYER->v.maxs, end, &stop) == 0);
    start[0] = 268; start[1] = 44; end[0] = 268; end[1] = 46;   /* both centres in one place: passes */
    assert(AW_BodyOverlap(PLAYER, GUARD, start, PLAYER->v.mins, PLAYER->v.maxs, end, &stop) == 1);
    aw_body_overlap.value = 0;
    VectorCopy(PLAYER->v.origin, start); VectorCopy(start, end); end[1] += 2;
    assert(AW_BodyOverlap(PLAYER, GUARD, start, PLAYER->v.mins, PLAYER->v.maxs, end, &stop) == 0);

    /* through SV_Move and the area links, Quake's way: every sweep from the arrival is allsolid, the search fails */
    VectorCopy(PLAYER->v.origin, start); VectorCopy(start, end); end[1] -= 2;
    tr = SV_Move(start, PLAYER->v.mins, PLAYER->v.maxs, end, MOVE_NORMAL, PLAYER);
    assert(tr.allsolid && tr.fraction == 0);
    assert(SV_TestEntityPosition(PLAYER) && SV_TestWorldPosition(PLAYER));
    /* the original's way: away passes, toward stops at the start, the position test still sees the guard (the
     * placement searches keep bodies apart), the stuck search's test does not */
    aw_body_overlap.value = 1;
    tr = SV_Move(start, PLAYER->v.mins, PLAYER->v.maxs, end, MOVE_NORMAL, PLAYER);
    assert(!tr.allsolid && tr.fraction == 1 && fabs(tr.endpos[1] - 34) < .01f);
    end[1] = start[1] + 2;
    tr = SV_Move(start, PLAYER->v.mins, PLAYER->v.maxs, end, MOVE_NORMAL, PLAYER);
    assert(!tr.allsolid && tr.fraction == 0 && tr.ent == GUARD && tr.plane.normal[1] < -.9f);
    assert(SV_TestEntityPosition(PLAYER) && !SV_TestWorldPosition(PLAYER));
    tr = SV_Move(start, PLAYER->v.mins, PLAYER->v.maxs, start, MOVE_NOBODIES, PLAYER);
    assert(!tr.startsolid);
    end[1] = start[1] - 2;
    tr = SV_Move(start, PLAYER->v.mins, PLAYER->v.maxs, end, MOVE_NOMONSTERS, PLAYER);
    assert(tr.fraction == 1);

    /* the walk, Quake's way: ten frames walking away at 30 units a second, the player does not move and the stuck
     * search fails in every frame */
    for (r = 0; r < 2; r++) {
        aw_body_overlap.value = r;
        make_world(); player_at(266, 36); guard_at(268, 44);
        searches = aw_stuck_searches; failed = aw_stuck_failed; stuck_lines = 0;
        walk(10, 0, -30);
        printf("aw_body_overlap %d: walking away from the guard for 10 frames: at %.2f %.2f %.2f, %s, %lu stuck "
               "searches (%lu failed, %d \"player is stuck.\")\n", r, PLAYER->v.origin[0], PLAYER->v.origin[1],
               PLAYER->v.origin[2], AW_BodyOverlapping(PLAYER) ? "still inside the guard" : "clear of the guard",
               aw_stuck_searches - searches, aw_stuck_failed - failed, stuck_lines);
        if (!r) {
            assert(fabs(PLAYER->v.origin[1] - 36) < .01f && AW_BodyOverlapping(PLAYER) == GUARD);
            assert(aw_stuck_failed - failed == 10 && stuck_lines == 10);
        } else {
            assert(!AW_BodyOverlapping(PLAYER) && PLAYER->v.origin[1] < 7 && PLAYER->v.origin[1] > 5);
            assert(fabs(PLAYER->v.origin[0] - 266) < .01f && fabs(PLAYER->v.origin[2] - FOOT) < .1f);
            assert(aw_stuck_searches == searches && !stuck_lines);
        }
    }

    /* walking toward the guard's centre under the rule: never deeper into it (it may slide along it) */
    make_world(); player_at(266, 36); guard_at(268, 44);
    d0 = dmin = apart();
    for (i = 0; i < 10; i++) { walk(1, 0, 30); if (apart() < dmin) dmin = apart(); }
    printf("aw_body_overlap 1: walking toward the guard for 10 frames: centres %.2f apart at the start, %.2f at the "
           "least, %.2f at the end\n", d0, dmin, apart());
    assert(dmin > d0 - .01f);

    /* the guard's own step out of the player (aw_walk.c AW_ActorStep, as aw_ambient.c walks residents) */
    for (r = 0; r < 2; r++) {
        aw_body_overlap.value = r;
        make_world(); player_at(266, 36); guard_at(268, 44);
        start[0] = 0; start[1] = 2; start[2] = 0;
        i = AW_ActorStep(GUARD, start, host_frametime);
        printf("aw_body_overlap %d: the guard's step of 2 units away from the player: %s (at %.2f %.2f)\n", r,
               i ? "taken" : "refused", GUARD->v.origin[0], GUARD->v.origin[1]);
        assert(r ? i && fabs(GUARD->v.origin[1] - 46) < .01f : !i && GUARD->v.origin[1] == 44);
    }

    /* bodies that do not overlap still block each other as Quake's boxes do: a walk toward the guard from 26 units
     * away stops at its box and never enters it */
    for (r = 0; r < 2; r++) {
        aw_body_overlap.value = r;
        make_world(); player_at(266, 10); guard_at(266, 44);
        walk(12, 0, 30);
        assert(!AW_BodyOverlapping(PLAYER) && PLAYER->v.origin[1] > 29 && PLAYER->v.origin[1] < 29.77f);
    }

    /* AW_BodyOverlapping: a body that is not solid (SOLID_NOT) is nobody */
    make_world(); player_at(266, 36); guard_at(268, 44);
    GUARD->v.solid = SOLID_NOT;
    assert(!AW_BodyOverlapping(PLAYER));

    puts("body overlap: an actor on the player's spot no longer traps either of them; a move toward it still stops");
    return 0;
}
