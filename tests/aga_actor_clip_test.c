/* SPDX-License-Identifier: GPL-2.0-or-later
 * SOL-SEA-INVISIBLE-BLOCKER-68, ACTOR-CLIP-ABOVE-DRAWN-BODY-69: a creature collides only up to its drawn body.
 * The measured case: in Solstheim's sea at cell -19,17 (the v0.0.68 release crossing session) the levelled list
 * bm_ex_horker_h20 rolls a horker (bm_horker_large, progs/c_9d8917efa100_k.mdl) at its placed depth, 22.2 units below
 * the water surface; its idle pose is drawn from 0.59 below to 11.34 above its origin, wholly under the surface, while
 * the person box every actor stood in (world.qc aw_npc_floor, 0 .. 33.25) reached 11.05 units above it. A player on
 * the water (feet on the surface, the box world.qc gives him, centred on his origin) stopped there. The engine's own
 * collision (world.c SV_Move through its area links, AW_BodyOverlap, AW_BodyOverlapping), walk (aw_walk.c
 * AW_WalkPlayer; sv_phys.c SV_WalkMove) and the rule (aw_actor_clip.c) run here over a synthetic world: a flat floor,
 * one empty leaf, and an alias model with the horker's measured rest frame height.
 * aw_actor_clip 0 (the method before v0.0.69) keeps the person box: the walker is stopped above the horker;
 * aw_actor_clip 1 (the default): he passes over it, still meets a creature where its body is drawn, and never steps
 * onto a low one. */
#include "quakedef.h"
#include "aw_actor_clip.h"
#include <assert.h>
#include <stdarg.h>

server_t sv;
int pr_edict_size = sizeof(edict_t);
double host_frametime = 0.1;
globalvars_t *pr_global_struct;
static globalvars_t globals;
static char strings[256];
char *pr_strings = strings;
extern cvar_t sv_gravity, sv_maxvelocity;
void AW_WalkPlayer(edict_t *p);   /* aw_walk.c (aw_links.h) */
int (*aw_actor_creature)(edict_t *e);   /* aw_scene.c's slot answer; NULL here: by the model's name */
void Con_Printf(char *fmt, ...) { (void)fmt; }
void Con_DPrintf(char *fmt, ...) { (void)fmt; }
void Sys_Error(char *fmt, ...) { va_list ap; va_start(ap, fmt); vprintf(fmt, ap); va_end(ap); exit(2); }
void PR_ExecuteProgram(func_t f) { (void)f; }
static eval_t scale_value;
static int scale_on;
eval_t *GetEdictFieldValue(edict_t *e, char *field) { (void)e; return scale_on && !strcmp(field, "aw_scale") ? &scale_value : NULL; }
void AW_BarrierClip(vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end, edict_t *entity, trace_t *trace)
{ (void)start; (void)mins; (void)maxs; (void)end; (void)entity; (void)trace; }
edict_t *EDICT_NUM(int n) { return (edict_t *)((byte *)sv.edicts + n*pr_edict_size); }   /* pr_edict.c's */
int NUM_FOR_EDICT(edict_t *e) { return (int)(((byte *)e - (byte *)sv.edicts) / pr_edict_size); }
void ClearLink(link_t *l) { l->prev = l->next = l; }
void RemoveLink(link_t *l) { l->next->prev = l->prev; l->prev->next = l->next; }
void InsertLinkBefore(link_t *l, link_t *before) { l->next = before; l->prev = before->prev; l->prev->next = l; l->next->prev = l; }
/* the setting's registration (aw_actor_clip.c AW_ActorClipInit), not exercised here */
void Cvar_RegisterVariable(cvar_t *v) { (void)v; }
void *Mod_Extradata(model_t *m) { return m->cache.data; }

#define FOOT 16.625f
#define PERSON_TOP 33.25f
static model_t world_model;
static mleaf_t leafs[2];
static mplane_t floor_planes[2];
static dclipnode_t floor_nodes[2];
static edict_t ents[4];
#define PLAYER (&ents[1])
#define ACTOR (&ents[2])

/* an alias model with one rest frame whose drawn height runs from LOW to HIGH (two vertices) */
static struct { aliashdr_t h; mdl_t md; trivertx_t v[2]; } bodies[3];
static model_t models[3];
static void body_model(int k, const char *name, float low, float high)
{
    memset(&bodies[k], 0, sizeof bodies[k]);
    memset(&models[k], 0, sizeof models[k]);
    bodies[k].h.model = (int)((byte *)&bodies[k].md - (byte *)&bodies[k].h);
    bodies[k].h.aw_skel = 1;   /* a skeletal actor: one stored frame, its rest pose */
    bodies[k].h.frames[0].type = ALIAS_SINGLE;
    bodies[k].h.frames[0].frame = (int)((byte *)bodies[k].v - (byte *)&bodies[k].h);
    bodies[k].md.numverts = 2; bodies[k].md.numframes = 1;
    bodies[k].md.scale[0] = bodies[k].md.scale[1] = 1;
    bodies[k].md.scale[2] = (high - low) / 255; bodies[k].md.scale_origin[2] = low;
    bodies[k].v[0].v[2] = 0; bodies[k].v[1].v[2] = 255;
    models[k].type = mod_alias; models[k].cache.data = &bodies[k].h;
    strcpy(models[k].name, name);
    strcpy(strings + 1 + 64*k, name);
}

/* hull 0 has its floor at FLOOR; hull 1 (the bodies' 14.64-wide boxes) at FLOOR + the player's foot */
static void floor_hull(hull_t *h, int i, float dist, const float *clip_mins, const float *clip_maxs)
{
    floor_planes[i].normal[2] = 1; floor_planes[i].dist = dist; floor_planes[i].type = 2;
    floor_nodes[i].planenum = 0; floor_nodes[i].children[0] = CONTENTS_EMPTY; floor_nodes[i].children[1] = CONTENTS_SOLID;
    h->planes = &floor_planes[i]; h->clipnodes = &floor_nodes[i]; h->firstclipnode = 0; h->lastclipnode = 0;
    VectorCopy(clip_mins, h->clip_mins); VectorCopy(clip_maxs, h->clip_maxs);
}
static void make_world(float floor)
{
    static vec3_t none = {0, 0, 0}, bmins = {-7.32f, -7.12f, -FOOT}, bmaxs = {7.32f, 7.12f, FOOT};
    int k;
    memset(&world_model, 0, sizeof world_model);
    world_model.type = mod_brush;
    for (k = 0; k < 3; k++) { world_model.mins[k] = -4096; world_model.maxs[k] = 4096; }
    leafs[1].contents = CONTENTS_EMPTY;
    world_model.leafs = leafs; world_model.nodes = (mnode_t *)&leafs[1];
    floor_hull(&world_model.hulls[0], 0, floor, none, none);
    floor_hull(&world_model.hulls[1], 1, floor + FOOT, bmins, bmaxs);
    world_model.hulls[2] = world_model.hulls[1];
    memset(ents, 0, sizeof ents);
    sv.edicts = ents; sv.num_edicts = 3; sv.worldmodel = &world_model; sv.models[1] = &world_model;
    for (k = 0; k < 3; k++) sv.models[2 + k] = &models[k];
    ents[0].v.solid = SOLID_BSP; ents[0].v.movetype = MOVETYPE_PUSH; ents[0].v.modelindex = 1;
    SV_ClearWorld();
}
/* the player with his feet at FEET (his box centred on his origin, world.qc) at X */
static void player_at(float x, float feet)
{
    edict_t *p = PLAYER;
    p->v.solid = SOLID_SLIDEBOX; p->v.movetype = MOVETYPE_WALK; p->v.flags = FL_CLIENT;
    p->v.mins[0] = -7.32f; p->v.mins[1] = -7.12f; p->v.mins[2] = -FOOT;
    p->v.maxs[0] = 7.32f;  p->v.maxs[1] = 7.12f;  p->v.maxs[2] = FOOT;
    p->v.origin[0] = x; p->v.origin[1] = 0; p->v.origin[2] = feet + FOOT;
    VectorCopy(p->v.origin, p->v.oldorigin); VectorCopy(vec3_origin, p->v.velocity);
    SV_LinkEdict(p, false);
}
/* an actor of model K (2: the horker, 3: a low creature, 4: a person) as world.qc aw_npc_floor makes it: SOLID_SLIDEBOX,
 * the person box on its feet, then the clip rule (pr_cmds.c SetMinMaxSize -> AW_ActorClipSet) */
static void actor_at(int index, float z)
{
    edict_t *a = ACTOR;
    a->v.solid = SOLID_SLIDEBOX; a->v.movetype = MOVETYPE_STEP;
    a->v.mins[0] = -7.32f; a->v.mins[1] = -7.12f; a->v.mins[2] = 0;
    a->v.maxs[0] = 7.32f;  a->v.maxs[1] = 7.12f;  a->v.maxs[2] = PERSON_TOP;
    a->v.origin[0] = 0; a->v.origin[1] = 0; a->v.origin[2] = z;
    a->v.modelindex = index; a->v.model = 1 + 64*(index - 2);
    VectorCopy(a->v.origin, a->v.oldorigin);
    SV_LinkEdict(a, false);
    AW_ActorClipSet(a);
}
static trace_t sweep_west(float from, float to)
{
    vec3_t start, end;
    VectorCopy(PLAYER->v.origin, start); start[0] = from;
    VectorCopy(start, end); end[0] = to;
    return SV_Move(start, PLAYER->v.mins, PLAYER->v.maxs, end, MOVE_NORMAL, PLAYER);
}
static void walk(int frames, float vx)
{
    int i;
    for (i = 0; i < frames; i++) {
        PLAYER->v.velocity[0] = vx; PLAYER->v.velocity[1] = 0;
        AW_WalkPlayer(PLAYER);
        SV_LinkEdict(PLAYER, false);
    }
}

int main(void)
{
    trace_t tr, stop;
    vec3_t start, end;
    float top;
    int r;
    pr_global_struct = &globals;
    sv_gravity.value = 800;
    sv_maxvelocity.value = 2000;
    aw_actor_clip_top = AW_ActorClipTop;   /* AW_ActorClipInit's binding */
    body_model(0, "progs/c_9d8917efa100_k.mdl", -0.59f, 11.34f);   /* the horker's measured rest frame */
    body_model(1, "progs/c_000000000003_k.mdl", 0, 4);            /* a low creature (a rat's height) */
    body_model(2, "progs/n_0000000000000004.mdl", 0, 30.5f);      /* a person: keeps the person box */

    /* the rule */
    assert(fabs(AW_ActorClipTopRule(PERSON_TOP, 11.34f, 1) - 11.34f) < 1e-4f);
    assert(AW_ActorClipTopRule(PERSON_TOP, 50, 1) == PERSON_TOP);          /* a tall creature: never above its box */
    assert(AW_ActorClipTopRule(PERSON_TOP, 0, 1) == PERSON_TOP);           /* no drawn height known */
    assert(AW_ActorClipTopRule(PERSON_TOP, 11.34f, 0) == PERSON_TOP);      /* no scale */
    assert(fabs(AW_ActorClipTopRule(PERSON_TOP, 11.34f, 2) - 22.68f) < 1e-4f);
    assert(AW_ActorClipTopRule(PERSON_TOP, .2f, 1) == AW_ACTOR_CLIP_MIN);  /* never flat */
    assert(fabs(AW_ActorModelTop(&models[0]) - 11.34f) < .05f);
    assert(AW_ActorModelTop(&world_model) == 0);                          /* not an alias model */

    /* the stop: a player on the water (feet on the surface, z 0) walking west at the horker 22.2 units under it */
    for (r = 0; r < 2; r++) {
        aw_actor_clip.value = r;
        make_world(-256);
        actor_at(2, -22.2f);
        player_at(40, 0);
        top = AW_ActorClipTop(ACTOR);
        tr = sweep_west(40, -40);
        printf("aw_actor_clip %d: the horker collides up to %.2f (its box %.2f), its drawn top %.2f under the surface; "
               "the walk west %s\n", r, ACTOR->v.origin[2] + top, ACTOR->v.origin[2] + PERSON_TOP,
               ACTOR->v.origin[2] + AW_ActorModelTop(&models[0]),
               tr.fraction < 1 ? "stops against nothing drawn" : "passes over it");
        if (!r) {
            assert(top == PERSON_TOP && tr.fraction < 1 && tr.ent == ACTOR && fabs(tr.endpos[0] - 14.64f) < .1f);
        } else {
            assert(fabs(top - 11.34f) < .05f && tr.fraction == 1 && tr.endpos[0] == -40);
        }
        /* standing right over it: overlapping only the person box */
        player_at(0, 0);
        assert(r ? AW_BodyOverlapping(PLAYER) == NULL : AW_BodyOverlapping(PLAYER) == ACTOR);
        VectorCopy(PLAYER->v.origin, start); start[0] = 4; VectorCopy(start, end); end[0] = 2;   /* toward its centre */
        assert(AW_BodyOverlap(PLAYER, ACTOR, start, PLAYER->v.mins, PLAYER->v.maxs, end, &stop) == (r ? 0 : 2));
    }
    aw_actor_clip.value = 1;

    /* on land the same horker still stops the walker where its body is drawn */
    make_world(0);
    actor_at(2, .03125f);
    player_at(40, .25f);
    tr = sweep_west(40, -40);
    assert(tr.fraction < 1 && tr.ent == ACTOR && fabs(tr.endpos[0] - 14.64f) < .1f);
    /* and a player over its back (feet 12 units up, above its drawn top) passes */
    player_at(40, 12);
    tr = sweep_west(40, -40);
    assert(tr.fraction == 1);

    /* a person keeps the person box; a drawn scale scales the top; a model change forgets it */
    make_world(-256);
    actor_at(4, -22.2f);
    assert(AW_ActorClipTop(ACTOR) == PERSON_TOP);
    scale_on = 1; scale_value._float = 2;
    actor_at(2, -22.2f);
    assert(fabs(AW_ActorClipTop(ACTOR) - 22.68f) < .1f);
    scale_on = 0;
    ACTOR->v.modelindex = 3;
    assert(AW_ActorClipTop(ACTOR) == PERSON_TOP);

    /* a low creature (4 units) on the floor: the walker meets it and is held at its side, never stepping onto it */
    for (r = 0; r < 2; r++) {
        aw_actor_clip.value = r;
        make_world(0);
        actor_at(3, .03125f);
        player_at(36, .25f);
        PLAYER->v.flags = (int)PLAYER->v.flags | FL_ONGROUND;
        walk(12, -30);
        printf("aw_actor_clip %d: walking into a creature 4 units tall: at %.2f %.2f (its side at 14.64), %s\n", r,
               PLAYER->v.origin[0], PLAYER->v.origin[2], PLAYER->v.origin[2] > FOOT + 1 ? "on top of it" : "beside it");
        assert(PLAYER->v.origin[0] > 14.6f && PLAYER->v.origin[0] < 15.5f);
        assert(fabs(PLAYER->v.origin[2] - FOOT) < 1);
    }

    puts("actor clip: a creature collides only up to its drawn body; the walker on the water passes over the swimming "
         "horker, meets it on land, and never steps onto a low creature");
    return 0;
}
