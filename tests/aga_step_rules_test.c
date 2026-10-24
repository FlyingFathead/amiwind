/* SPDX-License-Identifier: GPL-2.0-or-later
 * Step rules (STEP-MOVEMENT-OPENMW-RULES-48, docs/STEP_MOVEMENT.md): the engine's own walk (aw_walk.c
 * AW_WalkPlayer, sv_phys.c SV_WalkMove / SV_FlyMove) drives the standing box over synthetic stairs and slopes,
 * under the Quake rules (aw_step_rules 0, the default) and under Morrowind's rules as OpenMW 0.51 states them
 * (aw_step_rules 1). The world is a few convex solids extruded along y; the trace is the exact box sweep against
 * them (each solid's planes moved out by the box, plus the box's own faces), on-the-plane counting as outside as
 * Quake's hull traces do. Nothing here walks a real mesh: the cases are arithmetic-sized shapes.
 * Prints the table docs/STEP_MOVEMENT.md quotes. */
#include "quakedef.h"
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

#define MW .25f                      /* Morrowind units to map units (tools/chimport.py SCALE) */
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
/* One box sweep against one solid (Quake 2's CM_ClipBoxToBrush in x/z, with Quake 1's rule that a point on a plane is outside it). */
static void clip_solid(const solid_t *s, const vec3_t a, const vec3_t b, float ex, float ez, trace_t *tr)
{
    float pn[MAXPTS+4][2], pd[MAXPTS+4], enter = -1, leave = 1, minx = 1e9f, maxx = -1e9f, minz = 1e9f, maxz = -1e9f;
    int i, np = 0, getout = 0, startout = 0, hit = -1;
    for (i = 0; i < s->n; i++) {
        int j = (i + 1) % s->n;
        float dx = s->x[j] - s->x[i], dz = s->z[j] - s->z[i], len = sqrt(dx*dx + dz*dz);
        pn[np][0] = dz/len; pn[np][1] = -dx/len;          /* outward for counter-clockwise */
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
        if (d1 >= 0 && d2 >= 0) return;            /* both ends in front of one plane: a miss (Quake 1) */
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

/* The scenes, in Morrowind units (converted by MW). The ground's top is z 0; everything starts at x 20 MW*4. */
#define FOOT 16.625f
static void ground(void) { nsolids = 0; quad(-4000, -400, 4000, 0); }
static void stairs(float riser, int n, float tread)
{
    int i;
    ground();
    for (i = 0; i < n; i++) quad((80 + i*tread)*MW, 0, 4000, riser*(i + 1)*MW);
}
static void ramp(float degrees, float rise)
{
    float run = rise/tan(degrees*M_PI/180), t[8];
    ground();
    t[0] = 80*MW; t[1] = 0; t[2] = (80 + run)*MW; t[3] = 0; t[4] = (80 + run)*MW; t[5] = rise*MW;
    add_solid(3, t);
    quad((80 + run)*MW, 0, 4000, rise*MW);
}

typedef struct { float x, z; int airborne; } walk_t;
static walk_t walk(float x0, float z0, float vx, int frames)
{
    edict_t p;
    walk_t w;
    int i;
    memset(&p, 0, sizeof p);
    p.v.movetype = MOVETYPE_WALK;
    p.v.mins[0] = -7.32f; p.v.mins[1] = -7.12f; p.v.mins[2] = -FOOT;
    p.v.maxs[0] = 7.32f;  p.v.maxs[1] = 7.12f;  p.v.maxs[2] = FOOT;
    p.v.origin[0] = x0; p.v.origin[2] = z0 + FOOT + EPS;
    p.v.flags = FL_ONGROUND;
    w.airborne = 0;
    for (i = 0; i < frames; i++) {
        p.v.velocity[0] = vx; p.v.velocity[1] = 0;
        AW_WalkPlayer(&p);
        if (i > 2 && !((int)p.v.flags & FL_ONGROUND)) w.airborne++;
    }
    w.x = p.v.origin[0]; w.z = p.v.origin[2] - FOOT;
    return w;
}

/* Climbed: the walker ends on the top, past where it begins. */
static int climbs(float top, float vx, double dt)
{
    walk_t w;
    host_frametime = dt;
    w = walk(0, 0, vx, (int)(6/dt));
    return w.z > top*MW - .5f && w.x > 120*MW;
}

static const char *yes(int v) { return v ? "climbs" : "blocked"; }

int main(void)
{
    static const float risers[] = { 8, 16, 18, 24, 32, 34, 34.8f, 36, 40 };
    static const float ramps[] = { 30, 44, 45, 45.9f, 46, 46.2f, 46.5f, 50 };
    static const float drops[] = { 34, 36, 48, 62, 70 };
    static const double dts[] = { 0.05, 0.02 };
    static const float speeds[] = { 40, 100 };     /* map units a second: 160 and 400 Morrowind units */
    int i, k, s, old_v, new_v, failures = 0;
    pr_global_struct = &globals;
    sv.edicts = &world;
    world.v.solid = SOLID_BSP;
    sv_gravity.value = 800;
    sv_maxvelocity.value = 2000;

    printf("case | Quake rules (aw_step_rules 0) | step rules (aw_step_rules 1) | OpenMW's rules say\n");
    for (i = 0; i < (int)(sizeof risers/sizeof *risers); i++) {
        int expect = risers[i] < 35;            /* sStepSizeUp 34 over the 1-unit ground offset */
        int expect_old = risers[i]*MW <= 8.5f + EPS;
        for (k = 0; k < 2; k++) for (s = 0; s < 2; s++) {
            stairs(risers[i], 4, 48);
            aw_step_rules.value = 0; old_v = climbs(4*risers[i], speeds[s], dts[k]);
            aw_step_rules.value = 1; new_v = climbs(4*risers[i], speeds[s], dts[k]);
            if (!k && !s) printf("riser %.1f MW (4 steps) | %s | %s | %s\n", risers[i], yes(old_v), yes(new_v), yes(expect));
            if (new_v != expect || old_v != expect_old) {
                printf("  MISMATCH riser %.1f dt %.2f speed %.0f: old %d (expected %d) new %d (expected %d)\n",
                       risers[i], dts[k], speeds[s], old_v, expect_old, new_v, expect);
                failures++;
            }
        }
    }
    /* Ramps. The Quake rules stand on a normal z of 0.69 or more, but a walker that runs into a steeper slope also
     * crawls up it (SV_FlyMove turns its push into the slope into speed along it, faster than gravity takes it back):
     * recorded, not asserted; the step rules lay a too-steep slope flat as a wall, as OpenMW does. */
    for (i = 0; i < (int)(sizeof ramps/sizeof *ramps); i++) {
        float nz = cos(ramps[i]*M_PI/180);
        int expect = nz > AW_OPENMW_WALKABLE_Z, expect_old = nz >= AW_WALKABLE_Z, crawl = 0, first_old = 0, first_new = 0;
        char crawls[128] = "";
        for (k = 0; k < 2; k++) for (s = 0; s < 2; s++) {
            ramp(ramps[i], 128);
            aw_step_rules.value = 0; old_v = climbs(128, speeds[s], dts[k]);
            aw_step_rules.value = 1; new_v = climbs(128, speeds[s], dts[k]);
            if (!k && !s) { first_old = old_v; first_new = new_v; }
            if (old_v && !expect_old) {
                sprintf(crawls + strlen(crawls), "%s%.0f MW/s at %.0f fps", crawl++ ? ", " : "", speeds[s]/MW, 1/dts[k]);
            }
            if (new_v != expect || (expect_old && !old_v)) {
                printf("  MISMATCH ramp %.1f dt %.2f speed %.0f: old %d (expected %d) new %d (expected %d)\n",
                       ramps[i], dts[k], speeds[s], old_v, expect_old, new_v, expect);
                failures++;
            }
        }
        printf("ramp %.1f deg, 128 MW high (normal z %.4f) | %s%s%s%s | %s | %s\n", ramps[i], nz, yes(first_old),
               crawl ? " (crawls up it at " : "", crawls, crawl ? ")" : "", yes(first_new), yes(expect));
    }
    /* A short steep lip: the 55-degree, 27-unit face of ex_hlaalu_dsteps_03 (docs/COLLISION_MESHES.md). OpenMW
     * steps over a too-steep face lower than a step whose run is at most its third try's reach (sMinStep2, 20
     * units); the Quake step reaches only the frame's own move. 34 high runs 23.8 at 55 degrees: no; 40: no. */
    {
        static const float lips[] = { 27, 34, 40 };
        for (i = 0; i < 3; i++) {
            float run = lips[i]/tan(55*M_PI/180), t[8];
            int expect = lips[i] < 35 && run <= 20;
            ground();
            t[0] = 80*MW; t[1] = 0; t[2] = (80 + run)*MW; t[3] = 0; t[4] = (80 + run)*MW; t[5] = lips[i]*MW;
            add_solid(3, t);
            quad((80 + run)*MW, 0, 4000, lips[i]*MW);
            aw_step_rules.value = 0; old_v = climbs(lips[i], 40, .05);
            aw_step_rules.value = 1; new_v = climbs(lips[i], 40, .05);
            printf("lip: 55 deg face %.0f MW high, %.1f MW deep | %s | %s | %s\n", lips[i], run, yes(old_v),
                   yes(new_v), yes(expect));
            if (new_v != expect) { printf("  MISMATCH lip %.0f: new %d expected %d\n", lips[i], new_v, expect); failures++; }
        }
    }
    /* Going down a flight: the walker stays on the ground (no frame in the air) when each drop is within the
     * ground test (Quake 8.75 map units = 35 MW; OpenMW sStepSizeDown 62 + 2). Either way it arrives at the bottom. */
    for (i = 0; i < (int)(sizeof drops/sizeof *drops); i++) {
        walk_t a, b;
        int expect = drops[i] <= 64, expect_old = drops[i]*MW <= 8.75f;
        stairs(drops[i], 4, 48);
        host_frametime = .05;
        aw_step_rules.value = 0; a = walk(400*MW, 4*drops[i]*MW, -40, 120);
        aw_step_rules.value = 1; b = walk(400*MW, 4*drops[i]*MW, -40, 120);
        printf("down a flight of %.0f MW drops | %s (%d frames in the air) | %s (%d frames in the air) | %s\n",
               drops[i], a.airborne ? "falls" : "on the ground", a.airborne, b.airborne ? "falls" : "on the ground",
               b.airborne, expect ? "on the ground" : "falls");
        if (fabs(a.z) > .5f || fabs(b.z) > .5f || (!b.airborne) != expect || (!a.airborne) != expect_old) {
            printf("  MISMATCH drop %.0f: old z %.2f air %d, new z %.2f air %d\n", drops[i], a.z, a.airborne, b.z, b.airborne);
            failures++;
        }
    }
    aw_step_rules.value = 0;
    if (failures) { printf("%d mismatches\n", failures); return 1; }
    puts("step rules: risers, ramps, lips and drops match OpenMW's rules; the Quake rules unchanged");
    return 0;
}
