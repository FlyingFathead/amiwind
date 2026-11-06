/* SPDX-License-Identifier: GPL-2.0-or-later
 * AMBIENT-UNSTUCK-FLOOD-61: a walking resident whose standing box tests inside solid at the foot of a steep face
 * (the Seyda Neen case: a box snapped onto ground that touches a face of normal z 0.26) runs Quake's stuck search
 * (sv_phys.c SV_CheckStuck, called by aw_walk.c AW_WalkPlayer) at the start of every step. Its step into the face
 * fails (no walkable floor), and the failed step puts it back inside (AW_ActorStep restores where it stood), so the
 * next step searches again: one search per think, ten per walk. AW_ActorSettle (called by aw_ambient.c's walk after
 * such a step, "chim actors ambient settle on") runs the search once and keeps the clear spot. The engine's own walk, step and
 * search run here against a synthetic world (ground and a 76-degree wedge, extruded along y), the trace an exact box
 * sweep as in tests/aga_step_rules_test.c. */
#include "quakedef.h"
#include <assert.h>
#include <stdarg.h>

server_t sv;
int pr_edict_size = sizeof(edict_t);
double host_frametime = 0.1;
globalvars_t *pr_global_struct;
static globalvars_t globals;
static edict_t world;
extern cvar_t sv_gravity, sv_maxvelocity;
extern unsigned long aw_stuck_searches, aw_stuck_tests, aw_stuck_failed;
void Con_Printf(char *fmt, ...) { (void)fmt; }
void Con_DPrintf(char *fmt, ...) { (void)fmt; }
void Sys_Error(char *fmt, ...) { va_list ap; va_start(ap, fmt); vprintf(fmt, ap); va_end(ap); exit(2); }
void SV_LinkEdict(edict_t *e, qboolean touch) { (void)e; (void)touch; }
int SV_PointContents(vec3_t p) { (void)p; return CONTENTS_EMPTY; }
void PR_ExecuteProgram(func_t f) { (void)f; }
eval_t *GetEdictFieldValue(edict_t *e, char *field) { (void)e; (void)field; return NULL; }

#define MAXSOLIDS 4
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
/* One box sweep against one solid (as tests/aga_step_rules_test.c: a point on a plane is outside it). */
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
    if (!startout) { tr->startsolid = true; if (!getout) tr->allsolid = true; tr->ent = &world; return; }
    if (enter < leave && enter > -1 && enter < tr->fraction) {
        if (enter < 0) enter = 0;
        tr->fraction = enter;
        tr->plane.normal[0] = pn[hit][0]; tr->plane.normal[1] = 0; tr->plane.normal[2] = pn[hit][1];
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
/* world.c's test: the box at its origin starts in solid */
edict_t *SV_TestEntityPosition(edict_t *e)
{
    trace_t t = SV_Move(e->v.origin, e->v.mins, e->v.maxs, e->v.origin, MOVE_NORMAL, e);
    return t.startsolid ? sv.edicts : NULL;
}

#define FOOT 16.625f
/* The ground's top is z 0; a wedge whose 76-degree face rises from x 40 to x 50 at z 40 (normal x -0.97, z 0.24). */
static void scene(void)
{
    float t[6];
    nsolids = 0;
    quad(-4000, -400, 4000, 0);
    t[0] = 40; t[1] = 0; t[2] = 50; t[3] = 0; t[4] = 50; t[5] = 40;
    add_solid(3, t);
}
static void actor(edict_t *p, float x)
{
    memset(p, 0, sizeof *p);
    p->v.movetype = MOVETYPE_STEP;
    p->v.solid = SOLID_SLIDEBOX;
    p->v.mins[0] = -7.32f; p->v.mins[1] = -7.12f; p->v.mins[2] = -FOOT;
    p->v.maxs[0] = 7.32f;  p->v.maxs[1] = 7.12f;  p->v.maxs[2] = FOOT;
    p->v.origin[0] = x; p->v.origin[2] = FOOT + EPS;
    p->v.flags = FL_ONGROUND;
}
/* Ten steps of 2 units into the face (a walk's countBeforeReset), settling after a failed step that searched when
 * SETTLE is set (aw_ambient.c walk). The number of searches; *moved = steps that moved. */
static unsigned long walk_into_face(edict_t *p, int settle, int *moved)
{
    unsigned long before = aw_stuck_searches;
    vec3_t move;
    int i;
    *moved = 0;
    for (i = 0; i < 10; i++) {
        unsigned long s = aw_stuck_searches;
        move[0] = 2; move[1] = 0; move[2] = 0;
        if (AW_ActorStep(p, move, host_frametime)) (*moved)++;
        else if (settle && aw_stuck_searches != s) AW_ActorSettle(p);
    }
    return aw_stuck_searches - before;
}

int main(void)
{
    edict_t p;
    vec3_t at;
    unsigned long old_searches, new_searches, tests;
    int moved_old, moved_new;
    pr_global_struct = &globals;
    sv.edicts = &world;
    world.v.solid = SOLID_BSP;
    sv_gravity.value = 800;
    sv_maxvelocity.value = 2000;
    scene();

    /* clear ground: no search, settling moves nothing */
    actor(&p, 0);
    assert(!SV_TestEntityPosition(&p));
    assert(!AW_ActorSettle(&p) && p.v.origin[0] == 0);

    /* the box's lower front corner 0.01 inside the face: the box tests inside solid */
    actor(&p, 40 - 7.32f + .01f);
    assert(SV_TestEntityPosition(&p));
    VectorCopy(p.v.origin, at);

    /* the old way: every step searches, every step fails, the walker stays inside */
    old_searches = walk_into_face(&p, 0, &moved_old);
    printf("old way: %lu stuck searches in 10 steps into the face, %d steps moved, inside solid after: %s\n",
           old_searches, moved_old, SV_TestEntityPosition(&p) ? "yes" : "no");
    assert(old_searches == 10 && moved_old == 0);
    assert(p.v.origin[0] == at[0] && p.v.origin[2] == at[2] && SV_TestEntityPosition(&p));

    /* settled: one search in the first step, one by the settle, then every step starts clear */
    tests = aw_stuck_tests;
    new_searches = walk_into_face(&p, 1, &moved_new);
    printf("settled: %lu stuck searches in 10 steps, %d steps moved, %lu position tests, moved %.2f %.2f, inside "
           "solid after: %s\n", new_searches, moved_new, aw_stuck_tests - tests, p.v.origin[0] - at[0],
           p.v.origin[2] - at[2], SV_TestEntityPosition(&p) ? "yes" : "no");
    assert(new_searches == 2);
    assert(!SV_TestEntityPosition(&p));
    assert(fabs(p.v.origin[0] - at[0]) <= 1 && p.v.origin[2] >= at[2] && p.v.origin[2] - at[2] <= 17);

    /* no clear spot within the search's reach: the actor stays where it was */
    nsolids = 0;
    quad(-4000, -400, 4000, 400);
    actor(&p, 0);
    VectorCopy(p.v.origin, at);
    assert(!AW_ActorSettle(&p) && p.v.origin[0] == at[0] && p.v.origin[2] == at[2]);
    assert(aw_stuck_failed == 1);

    puts("unstuck: a walker put back inside solid by a failed step is settled once, then steps start clear");
    return 0;
}
