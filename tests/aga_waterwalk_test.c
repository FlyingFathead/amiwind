/* SPDX-License-Identifier: GPL-2.0-or-later
 * Water Walking (WATER-WALKING-NOT-ON-SURFACE-68): the engine's own walk (aw_walk.c AW_WalkPlayer, sv_phys.c
 * SV_CheckWater / SV_WalkMove / SV_FlyMove) over a synthetic sea. With a Water Walking magnitude over 0 the water's
 * surface holds the player as ground holds him: he lands on it from a fall, stands, walks and jumps on it, steps off a
 * quay onto it, and is lifted onto it from under the water when the way up is clear (OpenMW 0.51 mwphysics/
 * physicssystem.cpp 656-665, actor.cpp 147-155 and 325-335, mtphysics.cpp 177-182). Without it (no hook, magnitude 0,
 * the effect gone) he swims as before. A roof over him or a slab beside him keeps him swimming; lava never counts; an
 * actor's trial step is never held. The world is axis-aligned solids extruded along y; the water is every point below
 * the surface height W (not 0, so no assumed sea level), as hull 0 answers it (a point on the plane is open air). */
#include "quakedef.h"
#include "aw_links.h"
#include <assert.h>
#include <stdarg.h>

server_t sv;
int pr_edict_size = sizeof(edict_t);
double host_frametime = 0.05;
globalvars_t *pr_global_struct;
static globalvars_t globals;
static edict_t world;
extern cvar_t sv_gravity, sv_maxvelocity;
void Con_Printf(char *fmt, ...) { (void)fmt; }
void Con_DPrintf(char *fmt, ...) { (void)fmt; }
void Sys_Error(char *fmt, ...) { va_list ap; va_start(ap, fmt); vprintf(fmt, ap); va_end(ap); exit(2); }
void SV_LinkEdict(edict_t *e, qboolean touch) { (void)e; (void)touch; }
void PR_ExecuteProgram(func_t f) { (void)f; }
eval_t *GetEdictFieldValue(edict_t *e, char *field) { (void)e; (void)field; return NULL; }
edict_t *SV_TestEntityPosition(edict_t *e) { (void)e; return NULL; }
extern qboolean AW_ActorStep(edict_t *p, vec3_t move, double dt);

#define W 3.3f                         /* the water's surface (map units) */
#define FOOT 16.625f
#define EPS 0.03125f
#define MAXSOLIDS 8
typedef struct { float x0, z0, x1, z1; } solid_t;
static solid_t solids[MAXSOLIDS];
static int nsolids, water_on = 1;
static float lava_x0 = 1e9f, lava_x1 = 1e9f;
static unsigned long contents_calls;

static void quad(float x0, float z0, float x1, float z1)
{
    solid_t *s = &solids[nsolids++];
    s->x0 = x0; s->z0 = z0; s->x1 = x1; s->z1 = z1;
}
int SV_PointContents(vec3_t p)
{
    int i;
    contents_calls++;
    for (i = 0; i < nsolids; i++)
        if (p[0] > solids[i].x0 && p[0] < solids[i].x1 && p[2] > solids[i].z0 && p[2] < solids[i].z1) return CONTENTS_SOLID;
    if (p[2] < W && p[0] >= lava_x0 && p[0] < lava_x1) return CONTENTS_LAVA;
    return water_on && p[2] < W ? CONTENTS_WATER : CONTENTS_EMPTY;
}
/* The box sweep against one axis-aligned solid in x/z (the solid grown by the box), a point on a face outside it. */
static void clip_solid(const solid_t *s, const vec3_t a, const vec3_t b, float ex, float ez, trace_t *tr)
{
    float lo[2], hi[2], pa[2], pb[2], enter = -1, leave = 1, n[2] = {0, 0};
    int k, startout = 0, getout = 0;
    lo[0] = s->x0 - ex; hi[0] = s->x1 + ex; lo[1] = s->z0 - ez; hi[1] = s->z1 + ez;
    pa[0] = a[0]; pa[1] = a[2]; pb[0] = b[0]; pb[1] = b[2];
    for (k = 0; k < 4; k++) {
        int axis = k >> 1, low = !(k & 1);
        float d1 = low ? lo[axis] - pa[axis] : pa[axis] - hi[axis], d2 = low ? lo[axis] - pb[axis] : pb[axis] - hi[axis], f;
        if (d2 >= 0) getout = 1;
        if (d1 >= 0) startout = 1;
        if (d1 >= 0 && d2 >= 0) return;
        if (d1 < 0 && d2 < 0) continue;
        if (d1 > d2) { f = (d1 - EPS)/(d1 - d2); if (f > enter) { enter = f; n[0] = axis ? 0 : (low ? -1 : 1); n[1] = axis ? (low ? -1 : 1) : 0; } }
        else { f = (d1 + EPS)/(d1 - d2); if (f < leave) leave = f; }
    }
    if (!startout) { tr->startsolid = true; if (!getout) tr->allsolid = true; return; }
    if (enter < leave && enter > -1 && enter < tr->fraction) {
        tr->fraction = enter < 0 ? 0 : enter;
        tr->plane.normal[0] = n[0]; tr->plane.normal[1] = 0; tr->plane.normal[2] = n[1];
        tr->ent = &world;
    }
}
trace_t SV_Move(vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end, int type, edict_t *passedict)
{
    trace_t tr;
    float ex = (maxs[0] - mins[0])*.5f, ez = (maxs[2] - mins[2])*.5f;
    int i;
    (void)type; (void)passedict;
    memset(&tr, 0, sizeof tr);
    tr.fraction = 1;
    for (i = 0; i < nsolids; i++) clip_solid(&solids[i], start, end, ex, ez, &tr);
    for (i = 0; i < 3; i++) tr.endpos[i] = start[i] + tr.fraction*(end[i] - start[i]);
    return tr;
}

/* The player's Water Walking magnitude as aw_move.c's hook gives it, and how often the walk asked it. */
static float magnitude;
static unsigned long asked;
static float hook(edict_t *p) { (void)p; asked++; return magnitude; }

static edict_t p;
static void player(float x, float feet)
{
    memset(&p, 0, sizeof p);
    p.v.movetype = MOVETYPE_WALK;
    p.v.mins[0] = -7.32f; p.v.mins[1] = -7.12f; p.v.mins[2] = -FOOT;
    p.v.maxs[0] = 7.32f;  p.v.maxs[1] = 7.12f;  p.v.maxs[2] = FOOT;
    p.v.view_ofs[2] = 14;
    p.v.origin[0] = x; p.v.origin[2] = feet + FOOT;
}
static float feet(void) { return p.v.origin[2] - FOOT; }
static int on_surface(void)
{
    return feet() >= W - .001f && feet() <= W + EPS + .001f && ((int)p.v.flags & FL_ONGROUND) && p.v.waterlevel == 0 &&
           p.v.velocity[2] == 0;
}
static void frames(int n, float vx) { int i; for (i = 0; i < n; i++) { p.v.velocity[0] = vx; AW_WalkPlayer(&p); } }

int main(void)
{
    unsigned long lifts, refused, before;
    int i, swam;
    pr_global_struct = &globals;
    sv.edicts = &world;
    world.v.solid = SOLID_BSP;
    sv_gravity.value = 800;
    sv_maxvelocity.value = 2000;
    nsolids = 0;
    quad(-4000, W - 400, 4000, W - 300);                /* the sea bed, 300 below the surface */

    /* Before (no hook, a build without it): a fall from 40 over the water goes in and swims. */
    aw_walk_water_walking = NULL;
    player(0, W + 40);
    for (i = 0, swam = 0; i < 20; i++) { AW_WalkPlayer(&p); if (p.v.waterlevel >= 2) swam = 1; }
    assert(swam && feet() < W - FOOT && feet() > W - 300);

    /* Magnitude 0: the same. */
    aw_walk_water_walking = hook; magnitude = 0;
    player(0, W + 40);
    for (i = 0, swam = 0; i < 20; i++) { AW_WalkPlayer(&p); if (p.v.waterlevel >= 2) swam = 1; }
    assert(swam && feet() < W - FOOT && feet() > W - 300);

    /* Water Walking: the fall from 40 lands on the surface and stands there, frame after frame. */
    magnitude = 10;
    player(0, W + 40);
    frames(30, 0);
    assert(on_surface());
    for (i = 0; i < 200; i++) { AW_WalkPlayer(&p); assert(on_surface()); }
    /* the cost of standing on it: about ten point tests and one box sweep a frame */
    before = contents_calls; AW_WalkPlayer(&p);
    assert(contents_calls - before <= 12 && on_surface());
    printf("standing on the water: %lu point tests a frame\n", contents_calls - before);

    /* Walks and runs on it. */
    frames(50, 40);
    assert(fabs(p.v.origin[0] - 100) < .01f && on_surface());
    frames(20, 100);
    assert(fabs(p.v.origin[0] - 200) < .01f && on_surface());

    /* Jumps from it and lands on it again; the magnitude is not asked while the feet are out of the water. */
    p.v.velocity[0] = 0; p.v.velocity[2] = 150;
    before = asked; AW_WalkPlayer(&p);
    assert(feet() > W + 5 && !((int)p.v.flags & FL_ONGROUND));
    AW_WalkPlayer(&p); assert(asked == before);
    frames(40, 0);
    assert(on_surface());

    /* Under the water when the effect comes: lifted onto the surface in one frame (OpenMW's step start). */
    magnitude = 0;
    player(0, W - 120);
    frames(3, 0);
    assert(p.v.waterlevel == 3 && feet() < W - 100);
    AW_WaterWalkCounts(&lifts, &refused);
    magnitude = 10; AW_WalkPlayer(&p);
    assert(on_surface());
    AW_WaterWalkCounts(&before, NULL); assert(before > lifts);

    /* The effect ends on the water: he drops in and swims as before. */
    magnitude = 0;
    for (i = 0, swam = 0; i < 40; i++) { AW_WalkPlayer(&p); if (p.v.waterlevel >= 2) swam = 1; }
    assert(swam && feet() < W - FOOT);

    /* A roof under the surface over him (a ledge, a sunken deck): no way up, he swims on. */
    magnitude = 10;
    quad(-30, W - 40, 30, W - 30);
    player(0, W - 120);
    AW_WaterWalkCounts(NULL, &refused);
    frames(5, 0);
    AW_WaterWalkCounts(NULL, &before);
    assert(before > refused && feet() < W - 100 && p.v.waterlevel == 3);
    /* A slab beside the column, over the box: the sweep up meets it (canMoveToWaterSurface), he swims on. */
    nsolids = 1;
    quad(4, W - 40, 40, W - 30);
    player(0, W - 120);
    AW_WaterWalkCounts(NULL, &refused);
    frames(5, 0);
    AW_WaterWalkCounts(NULL, &before);
    assert(before > refused && feet() < W - 100);
    nsolids = 1;

    /* A quay 4 over the water: he walks off its edge and on over the water. */
    quad(-400, W - 400, 0, W + 4);
    player(-40, W + 4 + EPS);
    p.v.flags = FL_ONGROUND;
    frames(60, 40);
    assert(p.v.origin[0] > 60 && on_surface());
    nsolids = 1;

    /* Lava is walked on already (docs/LAVA.md): never lifted by Water Walking. */
    lava_x0 = -100; lava_x1 = 100;
    player(0, W - 60);
    AW_WalkPlayer(&p);
    assert(feet() < W - 50);
    lava_x0 = lava_x1 = 1e9f;

    /* An actor's trial step (AW_ActorStep) is never held: the hook is not asked. */
    {
        vec3_t move = {2, 0, 0};
        player(0, W - 60); p.v.movetype = MOVETYPE_STEP;
        before = asked; AW_ActorStep(&p, move, host_frametime);
        assert(asked == before && feet() < W - 50);
    }
    puts("water walking: lands on the surface, stands, walks, runs and jumps on it, steps off a quay onto it, is lifted "
         "from under it, swims again when the effect ends; a roof or a slab keeps him swimming; lava and actors never");
    return 0;
}
