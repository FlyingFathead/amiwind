/* SPDX-License-Identifier: GPL-2.0-or-later
 * dbg rcount (aw_rcount 1): once a second, per-frame averages of what the
 * renderer did, printed to the console and kept for the remote state file
 * (aw_remote.c "rcount" line). Counts are the main currency for comparing
 * builds; emulator frame times are relative only (BENCH-JIT-PROFILE-32).
 *
 * Quake's own r_speeds counters are reused (c_faceclip: faces clipped,
 * r_polycount: faces that reached the edge list, r_drawnpolycount: surfaces
 * drawn, r_amodels_drawn: alias models) and extended for brush models
 * (RENDER-BMODEL-FRAGMENTS-32: faces submitted on the clipped path against
 * fragments emitted, and the one-leaf path), edges, spans and the surface
 * cache. The timing split mirrors r_dspeeds: R_RenderWorld, brush models
 * (R_DrawBEntitiesOnList), R_ScanEdges including D_DrawSurfaces, then
 * D_DrawSurfaces alone, alias models (R_DrawEntitiesOnList), the whole
 * R_RenderView, and the host frame (wall clock between frames, unclamped).
 * aw_rcount 2 keeps the line for the state file without printing it (no
 * console notify text over the measured view). Integer output only.
 *
 * Line fields (averages per frame; times in microseconds):
 *   bm  passes/visible/inview/clipped/oneleaf   brush model passes
 *   bf  tested/front                            brush model faces, backface test
 *   cf/frag/lf/wf  clipped-path faces, fragments/BSP nodes visited clipping
 *                  them, one-leaf faces, world faces
 *   q   faceclip/poly/drawn                     Quake's r_speeds counts
 *   e   new/cached/used, s surfaces, sp spans
 *   sc  allocs/bytes, scb blocks/texels drawn
 *   al  alias models
 *   us  world/bmodels/scan/draw/alias/view/frame, pk frame peak
 *   vd  entities refused for a full cl_visedicts (MAX_VISEDICTS)
 *   ne  entities in cl_visedicts / sprites drawn (render cost per entity)
 *   chim ... the CHIM world streamer's fields, on a CHIM map only
 */
#include "quakedef.h"
#include "aw_rcount.h"

long aw_rcount[RC_COUNTERS];
int aw_rcount_timing;
double aw_rtime[RT_TIMERS];
extern int c_faceclip, r_polycount, r_drawnpolycount, r_amodels_drawn;
int (*aw_chim_rcount)(char *out, int size, long frames);

static cvar_t aw_rcount_cvar = {"aw_rcount", "0"};
enum { RQ_FACECLIP = RC_COUNTERS, RQ_POLY, RQ_DRAWN, RQ_ALIAS, RQ_VISEDICTS_DROPPED, RQ_TOTAL };
static double sum[RQ_TOTAL], time_sum[RT_TIMERS], frame_sum, frame_peak, start, previous;
static long frames;
static char line[896];

double AW_RCountClock(void) {return Sys_FloatTime();}
const char *AW_RCountLine(void) {return line;}
void AW_RCountInit(void) {Cvar_RegisterVariable(&aw_rcount_cvar);}

static void clear(void)
{
    memset(sum, 0, sizeof sum);
    memset(time_sum, 0, sizeof time_sum);
    frame_sum = frame_peak = 0;
    frames = 0;
}

static long avg(double total)
{
    return frames ? (long)(total / frames + .5) : 0;
}

static long us(double seconds)
{
    return frames ? (long)(seconds * 1e6 / frames + .5) : 0;
}

void AW_RCountFrame(void)
{
    int i;
    double now, dt;
    int on = aw_rcount_cvar.value > 0 && cls.state == ca_connected;

    if (!on) {
        memset(aw_rcount, 0, sizeof aw_rcount);
        memset(aw_rtime, 0, sizeof aw_rtime);
        aw_rcount_timing = 0;
        start = previous = 0;
        clear();
        return;
    }
    now = Sys_FloatTime();
    if (!aw_rcount_timing || !start) {     /* first frame: start clean */
        aw_rcount_timing = 1;
        memset(aw_rcount, 0, sizeof aw_rcount);
        memset(aw_rtime, 0, sizeof aw_rtime);
        start = previous = now;
        clear();
        return;
    }
    for (i = 0; i < RC_COUNTERS; i++)
        sum[i] += aw_rcount[i];
    sum[RQ_FACECLIP] += c_faceclip;
    sum[RQ_POLY] += r_polycount;
    sum[RQ_DRAWN] += r_drawnpolycount;
    sum[RQ_ALIAS] += r_amodels_drawn;
    sum[RQ_VISEDICTS_DROPPED] += aw_visedicts_dropped_frame;
    for (i = 0; i < RT_TIMERS; i++)
        time_sum[i] += aw_rtime[i];
    dt = now - previous;
    previous = now;
    frame_sum += dt;
    if (dt > frame_peak)
        frame_peak = dt;
    frames++;
    memset(aw_rcount, 0, sizeof aw_rcount);
    memset(aw_rtime, 0, sizeof aw_rtime);
    if (now - start < 1.0)
        return;
    snprintf(line, sizeof line,
        "%ld frames fps10 %ld | bm %ld/%ld/%ld/%ld/%ld bf %ld/%ld cf %ld frag %ld/%ld lf %ld wf %ld"
        " | q %ld/%ld/%ld e %ld/%ld/%ld s %ld sp %ld | sc %ld/%ld scb %ld/%ld al %ld"
        " | us %ld/%ld/%ld/%ld/%ld/%ld/%ld pk %ld | vd %ld ne %ld/%ld",
        frames, (long)(frames * 10.0 / (now - start)),
        avg(sum[RC_BM_PASSES]), avg(sum[RC_BM_VISIBLE]), avg(sum[RC_BM_INVIEW]),
        avg(sum[RC_BM_CLIPPED]), avg(sum[RC_BM_ONELEAF]),
        avg(sum[RC_BF_TESTED]), avg(sum[RC_BF_FRONT]),
        avg(sum[RC_CLIP_FACES]), avg(sum[RC_FRAGMENTS]), avg(sum[RC_CLIP_NODES]), avg(sum[RC_LEAF_FACES]), avg(sum[RC_WORLD_FACES]),
        avg(sum[RQ_FACECLIP]), avg(sum[RQ_POLY]), avg(sum[RQ_DRAWN]),
        avg(sum[RC_EDGES_NEW]), avg(sum[RC_EDGES_CACHED]), avg(sum[RC_EDGES_USED]),
        avg(sum[RC_SURFS]), avg(sum[RC_SPANS]),
        avg(sum[RC_SC_ALLOC]), avg(sum[RC_SC_ALLOC_BYTES]), avg(sum[RC_SC_BUILD]), avg(sum[RC_SC_BUILD_BYTES]),
        avg(sum[RQ_ALIAS]),
        us(time_sum[RT_WORLD]), us(time_sum[RT_BMODELS]), us(time_sum[RT_SCAN]), us(time_sum[RT_DRAW]),
        us(time_sum[RT_ALIAS]), us(time_sum[RT_VIEW]), us(frame_sum), (long)(frame_peak * 1e6 + .5),
        avg(sum[RQ_VISEDICTS_DROPPED]), avg(sum[RC_ENTITIES]), avg(sum[RC_SPRITES]));
    if (aw_chim_rcount) {
        int used = (int)strlen(line);
        aw_chim_rcount(line + used, (int)sizeof line - used, frames);
    }
    if (aw_rcount_cvar.value < 2)       /* 2: state file only, nothing on screen */
        Con_Printf("rcount %s\n", line);
    start = now;
    clear();
}
