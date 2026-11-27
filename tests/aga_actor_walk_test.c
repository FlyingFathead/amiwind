/* SPDX-License-Identifier: GPL-2.0-or-later
 * The actor's step against the player's walk (CHIM-COLLISION-WALKS-67, AMBIENT-WALK-STUCK-COLLISION-54,
 * ACTOR-STEP-STEEP-CONTACT-REFUSED-69): the engine's own walk (aw_walk.c AW_WalkPlayer, AW_ActorStep,
 * AW_ActorGroundSettle; sv_phys.c SV_WalkMove / SV_FlyMove) on synthetic shapes, convex solids extruded along y and
 * swept exactly by the box (as tests/aga_step_rules_test.c; the box may sit off its origin, as an actor's feet-origin
 * box does). Nothing here walks a real mesh.
 *   1. The foot of a too-steep face (normal z 0.55, the face a Seyda Neen resident met): the player walking along it
 *      slides on; the actor's step under aw_actor_steep 0 (the method before) is refused there, under 1 it slides on as
 *      the player, and a too-steep slope is still never climbed nor a drop off a ledge taken.
 *   2. The top edge of a crate (a steep face down, the street 11.2 below, a Balmora guard): the step off it holds
 *      under 1 (within OpenMW's 64-unit ground test), refused under 0; off a 40-unit ledge it is refused under both.
 *   3. AW_ActorGroundSettle, an actor back on held ground after a walk without collision: from above it lands, sunk
 *      into the ground it comes up onto it, under a low roof it stays below the roof, too far above it stays put. */
#include "quakedef.h"
#include "aw_ambient.h"
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
int SV_PointContents(vec3_t p) { (void)p; return CONTENTS_EMPTY; }
void PR_ExecuteProgram(func_t f) { (void)f; }
eval_t *GetEdictFieldValue(edict_t *e, char *field) { (void)e; (void)field; return NULL; }
edict_t *SV_TestEntityPosition(edict_t *e) { (void)e; return NULL; }

#define MAXSOLIDS 8
#define MAXPTS 8
typedef struct { int n; float x[MAXPTS], z[MAXPTS]; } solid_t;   /* convex, counter-clockwise in x/z */
static solid_t solids[MAXSOLIDS];
static int nsolids;
static void add_solid(int n, const float *xz)
{
    solid_t *s = &solids[nsolids++];
    int i;
    s->n = n;
    for (i = 0; i < n; i++) { s->x[i] = xz[2*i]; s->z[i] = xz[2*i+1]; }
}
static void quad(float x0, float z0, float x1, float z1)
{
    float q[8];
    q[0] = x0; q[1] = z0; q[2] = x1; q[3] = z0; q[4] = x1; q[5] = z1; q[6] = x0; q[7] = z1;
    add_solid(4, q);
}
#define EPS 0.03125f
/* One box sweep against one solid (CM_ClipBoxToBrush in x/z; a point on a plane is outside it, as Quake's hulls). */
static void clip_solid(const solid_t *s, const vec3_t a, const vec3_t b, float ex, float ez, trace_t *tr)
{
    float pn[MAXPTS+4][2], pd[MAXPTS+4], enter = -1, leave = 1, minx = 1e9f, maxx = -1e9f, minz = 1e9f, maxz = -1e9f;
    int i, np = 0, getout = 0, startout = 0, hit = -1;
    for (i = 0; i < s->n; i++) {
        int j = (i + 1) % s->n;
        float dx = s->x[j] - s->x[i], dz = s->z[j] - s->z[i], len = sqrt(dx*dx + dz*dz);
        pn[np][0] = dz/len; pn[np][1] = -dx/len;
        pd[np] = pn[np][0]*s->x[i] + pn[np][1]*s->z[i] + fabs(pn[np][0])*ex + fabs(pn[np][1])*ez;
        np++;
        if (s->x[i] < minx) minx = s->x[i];
        if (s->x[i] > maxx) maxx = s->x[i];
        if (s->z[i] < minz) minz = s->z[i];
        if (s->z[i] > maxz) maxz = s->z[i];
    }
    pn[np][0] = 1;  pn[np][1] = 0;  pd[np++] = maxx + ex;
    pn[np][0] = -1; pn[np][1] = 0;  pd[np++] = -(minx - ex);
    pn[np][0] = 0;  pn[np][1] = 1;  pd[np++] = maxz + ez;
    pn[np][0] = 0;  pn[np][1] = -1; pd[np++] = -(minz - ez);
    for (i = 0; i < np; i++) {
        float d1 = pn[i][0]*a[0] + pn[i][1]*a[2] - pd[i], d2 = pn[i][0]*b[0] + pn[i][1]*b[2] - pd[i], f;
        if (d2 >= 0) getout = 1;
        if (d1 >= 0) startout = 1;
        if (d1 >= 0 && d2 >= 0) return;
        if (d1 < 0 && d2 < 0) continue;
        if (d1 > d2) { f = (d1 - EPS)/(d1 - d2); if (f > enter) { enter = f; hit = i; } }
        else { f = (d1 + EPS)/(d1 - d2); if (f < leave) leave = f; }
    }
    if (!startout) { tr->startsolid = true; if (!getout) tr->allsolid = true; return; }
    if (enter < leave && enter > -1 && enter < tr->fraction) {
        if (enter < 0) enter = 0;
        tr->fraction = enter;
        tr->plane.normal[0] = pn[hit][0]; tr->plane.normal[1] = 0; tr->plane.normal[2] = pn[hit][1];
        tr->ent = &world;
    }
}
/* The box MINS..MAXS about its origin: swept as a centred box from the origin plus its centre offset. */
trace_t SV_Move(vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end, int type, edict_t *passedict)
{
    trace_t tr;
    vec3_t a, b;
    float ex = (maxs[0] - mins[0])*.5f, ez = (maxs[2] - mins[2])*.5f;
    int i;
    (void)type; (void)passedict;
    memset(&tr, 0, sizeof tr);
    tr.fraction = 1;
    for (i = 0; i < 3; i++) { float c = (mins[i] + maxs[i])*.5f; a[i] = start[i] + c; b[i] = end[i] + c; }
    for (i = 0; i < nsolids; i++) clip_solid(&solids[i], a, b, ex, ez, &tr);
    for (i = 0; i < 3; i++) tr.endpos[i] = start[i] + tr.fraction*(end[i] - start[i]);
    return tr;
}

/* The actor's box (engine/aga/qc/world.qc aw_npc_floor: the feet at the origin) and the player's (centred). */
static void actor(edict_t *p, float x, float z)
{
    memset(p, 0, sizeof *p);
    p->v.mins[0] = -7.32f; p->v.mins[1] = -7.12f; p->v.mins[2] = 0;
    p->v.maxs[0] = 7.32f;  p->v.maxs[1] = 7.12f;  p->v.maxs[2] = 33.25f;
    p->v.origin[0] = x; p->v.origin[2] = z + EPS;
    p->v.flags = FL_ONGROUND;
}
static void player(edict_t *p, float x, float z)
{
    memset(p, 0, sizeof *p);
    p->v.movetype = MOVETYPE_WALK;
    p->v.mins[0] = -7.32f; p->v.mins[1] = -7.12f; p->v.mins[2] = -16.625f;
    p->v.maxs[0] = 7.32f;  p->v.maxs[1] = 7.12f;  p->v.maxs[2] = 16.625f;
    p->v.origin[0] = x; p->v.origin[2] = z + 16.625f + EPS;
    p->v.flags = FL_ONGROUND;
}
/* Steps of MOVE map units every think (the ambient's 0.1 s think over one frame of host_frametime): how many held. */
static int steps(edict_t *p, float mx, float my, int n)
{
    int i, held = 0;
    for (i = 0; i < n; i++) {
        vec3_t move;
        move[0] = mx; move[1] = my; move[2] = 0;
        held += AW_ActorStep(p, move, host_frametime) ? 1 : 0;
    }
    return held;
}
static void walk(edict_t *p, float vx, float vy, int frames)
{
    int i;
    for (i = 0; i < frames; i++) { p->v.velocity[0] = vx; p->v.velocity[1] = vy; AW_WalkPlayer(p); }
}

/* the ground's top is z 0; a too-steep face of normal z COS rises from x X0 to the height H, a shelf beyond */
static void steep_foot(float x0, float nz, float h)
{
    float run = h*nz/sqrt(1 - nz*nz), t[6];
    nsolids = 0;
    quad(-4000, -400, 4000, 0);
    t[0] = x0; t[1] = 0; t[2] = x0 + run; t[3] = 0; t[4] = x0 + run; t[5] = h;
    add_solid(3, t);
    quad(x0 + run, 0, 4000, h);
}

int main(void)
{
    edict_t p, q;
    int old_held, new_held;
    float y0;
    setvbuf(stdout, NULL, _IONBF, 0);       /* every line printed before a failing check is kept */
    pr_global_struct = &globals;
    sv.edicts = &world;
    world.v.solid = SOLID_BSP;
    sv_gravity.value = 800;
    sv_maxvelocity.value = 2000;
    host_frametime = 0.05;

    /* 1. Along the foot of a face of normal z 0.55, 40 high, the walker heading into it at 37 degrees (4 into the
     * face, 3 along it a step). The player slides along: 30 frames later he is far along the face, on the ground. */
    steep_foot(20, 0.55f, 40);
    player(&q, 20 - 7.32f - 1, 0);
    walk(&q, 4/host_frametime, 3/host_frametime, 30);
    /* (under the Quake rules he also crawls a little up the face: SV_FlyMove turns his push into it into speed along
     * it, tests/aga_step_rules_test.c's ramps) */
    printf("steep foot, the player: %.1f along, feet z %.2f\n", q.v.origin[1], q.v.origin[2] - 16.625f);
    assert(q.v.origin[1] > 60);
    /* The actor, the method before: once its box touches the face every step is refused */
    aw_actor_steep = 0;
    actor(&p, 20 - 7.32f - 1, 0);
    old_held = steps(&p, 4, 3, 30);
    y0 = p.v.origin[1];
    printf("steep foot, old step: %d of 30 steps held, %.1f along, z %.2f\n", old_held, y0, p.v.origin[2]);
    assert(old_held < 5 && y0 < 15);
    /* ... now it slides on along the face as the player, never up it */
    aw_actor_steep = 1;
    actor(&p, 20 - 7.32f - 1, 0);
    new_held = steps(&p, 4, 3, 30);
    printf("steep foot, new step: %d of 30 steps held, %.1f along, z %.2f\n", new_held, p.v.origin[1], p.v.origin[2]);
    assert(new_held >= 25 && p.v.origin[1] > 60 && p.v.origin[2] < 8.75f);
    /* straight into the face for 60 steps: no climb (the point under its centre meets the face itself) */
    actor(&p, 20 - 7.32f - 1, 0);
    steps(&p, 4, 0, 60);
    printf("steep face head-on: x %.1f z %.2f\n", p.v.origin[0], p.v.origin[2]);
    assert(p.v.origin[2] < 8.75f && p.v.origin[0] < 20 + 40*0.55f/sqrt(1 - 0.55f*0.55f));

    /* 2. Off the top edge of a crate: a steep face (normal z 0.49) down to the street 11.2 below. */
    {
        float t[6], h = 11.2f, nz = 0.49f, run = h*nz/sqrt(1 - nz*nz);
        nsolids = 0;
        quad(-4000, -400, 4000, 0);                 /* the street */
        quad(-4000, 0, 0, h);                       /* the crate's top, its edge at x 0 */
        t[0] = 0; t[1] = 0; t[2] = run; t[3] = 0; t[4] = 0; t[5] = h;
        add_solid(3, t);                            /* its steep side: (0, h) down to (run, 0) */
        aw_actor_steep = 0;
        actor(&p, -6, h);
        old_held = steps(&p, 3, 0, 20);
        printf("crate edge, old step: %d of 20 held, x %.1f z %.2f\n", old_held, p.v.origin[0], p.v.origin[2]);
        assert(p.v.origin[2] > h - 1);              /* still up there */
        aw_actor_steep = 1;
        actor(&p, -6, h);
        new_held = steps(&p, 3, 0, 20);
        printf("crate edge, new step: %d of 20 held, x %.1f z %.2f\n", new_held, p.v.origin[0], p.v.origin[2]);
        assert(p.v.origin[2] < 1 && p.v.origin[0] > run);   /* down on the street, past the crate */
        /* a ledge 40 high with a steep side: no walkable ground under the centre within 16, refused under both */
        nsolids = 0;
        quad(-4000, -400, 4000, 0);
        h = 40; run = h*nz/sqrt(1 - nz*nz);
        quad(-4000, 0, 0, h);
        t[0] = 0; t[1] = 0; t[2] = run; t[3] = 0; t[4] = 0; t[5] = h;
        add_solid(3, t);
        actor(&p, -6, h);
        steps(&p, 3, 0, 20);
        printf("ledge 40, new step: x %.1f z %.2f\n", p.v.origin[0], p.v.origin[2]);
        assert(p.v.origin[2] > h - 1 - 16);          /* never down the ledge: at most onto its side within the test */
        assert(p.v.origin[2] > 20);
    }

    /* 3. Back on held ground after a walk without collision (the route's height): flat ground at z 0. */
    nsolids = 0;
    quad(-4000, -400, 4000, 0);
    actor(&p, 0, 10);                                       /* 10 above: lands */
    assert(AW_ActorGroundSettle(&p, 16, 32) && fabs(p.v.origin[2]) < .1f && ((int)p.v.flags & FL_ONGROUND));
    actor(&p, 0, -6);                                       /* sunk 6 into the ground: comes up onto it */
    assert(AW_ActorGroundSettle(&p, 16, 32) && fabs(p.v.origin[2]) < .1f);
    actor(&p, 0, 40);                                       /* 40 above: out of reach, it stays */
    assert(!AW_ActorGroundSettle(&p, 16, 32) && fabs(p.v.origin[2] - 40 - EPS) < .01f);
    /* a roof 45 above the ground (its underside 12 over the actor's head when sunk 6): the actor comes up onto the
     * ground, never onto the roof */
    quad(-4000, 45, 4000, 60);
    actor(&p, 0, -6);
    assert(AW_ActorGroundSettle(&p, 16, 32) && fabs(p.v.origin[2]) < .1f);
    puts("actor walk: the steep foot, the crate edge, the ledge and the settle as the player's walk and OpenMW's ground test");
    return 0;
}
