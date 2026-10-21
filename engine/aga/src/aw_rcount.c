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
 * console notify text over the measured view); 3 adds the brush-model profile
 * line "rprof" (below), also for the state file only; 4 prints both. Integer
 * output only.
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
#include "aw_links.h"
#include "aw_rcount.h"
#include <devices/timer.h>
#include <proto/timer.h>

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
static void format_line(double seconds);
const char *AW_RCountLine(void) {return line;}
static void timedemo_done(const char *demo, int frames_counted, double seconds);
extern void (*aw_timedemo_done)(const char *demo, int frames, double seconds);
void AW_RCountInit(void) {Cvar_RegisterVariable(&aw_rcount_cvar);aw_timedemo_done=timedemo_done;}

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

/* ------------------------------------------------------------ dbg rprof
 * dbg rcount 3 (4: also printed): the rcount line for the remote state file as
 * with 2, plus once a second this brush-model profile, per-frame averages (no
 * console variable of its own: ENGINE-RESIDENT-REGISTRY-GROWTH-36):
 *   rprof N frames | r  the measured cost of one clock read (us, 2 decimals)
 *   walk/emit/oneleaf/setup  the brush-model slot (R_DrawBEntitiesOnList) split:
 *        walk    R_RecursiveClipBPoly without the fragments it emits, nodes = calls
 *        emit    R_RenderBmodelFace calls on the clipped path, frag = calls
 *        oneleaf R_DrawSubmodelPolygons (backface test + R_RenderFace), lf = faces
 *        setup   the rest of an in-view pass (rotation, lights, box split,
 *                backface tests on the clipped path), passes = in-view passes
 *        added   what the timers themselves added to the slot
 *   (corrected for the clock reads: a timer's own reads cost r, every timer
 *   nested inside it 2r; EClock ticks, about 1.4 us each; emulator-relative)
 *   so/eo  frames with surfaces / edges past r_maxsurfs / r_maxedges and the
 *          average shortage per frame (faces dropped from the drawn view)
 *   hp/hf/hs  in-view passes, front faces and sent faces (fragments + one-leaf
 *          faces) per distance band (rows: 0-25/25-50/50-75/75-100 % of the
 *          draw distance, beyond; model centre depth along the view) x size
 *          class (columns: model radius <32, 32-128, 128-512, >=512 units)
 *   lv     in-view passes by the world leaves their box touches (1, 2, 3-4,
 *          5-8, 9-16, 17-32, 33-64, 65+), the mean, and the mean of those
 *          leaves in the current PVS (vis).
 * Nothing is timed or binned while aw_rcount is below 3: every site tests aw_rprof_on. */
extern struct Device *TimerBase;
extern ULONG eclocks_per_second;
extern int r_outofsurfaces, r_outofedges;
int AW_DrawDistance(void);
int aw_rprof_on;
unsigned long aw_rprof_ticks[RP_TIMERS];
long aw_rprof_pairs[RP_TIMERS];
#define RP_LEAF_BUCKETS 8
#define RP_CAL_READS 32
static double rp_ticks[RP_TIMERS], rp_pairs[RP_TIMERS], rp_cal_ticks, rp_cal_reads;
static double rp_passes[RP_BANDS][RP_SIZES], rp_front[RP_BANDS][RP_SIZES], rp_sent[RP_BANDS][RP_SIZES];
static double rp_leafhist[RP_LEAF_BUCKETS], rp_leaves, rp_visleaves, rp_models;
static double rp_nodes, rp_frags, rp_leaffaces, rp_so_frames, rp_so, rp_eo_frames, rp_eo, rp_start;
static long rp_frames;
static int rp_distance_frame = -1;
static float rp_distance = 540;
static char rp_line[1400];

unsigned long AW_RProfTicks(void)
{
    struct EClockVal e;

    if (!TimerBase)
        return 0;
    ReadEClock(&e);
    return e.ev_lo;
}

const char *AW_RProfLine(void) {return rp_line;}

void AW_RProfModel(const float *origin, float radius, long front, long sent, int leaves, int visible_leaves)
{
    int band, size, bucket;
    float depth;

    if (rp_distance_frame != r_framecount) {
        rp_distance_frame = r_framecount;
        rp_distance = AW_DrawDistance();
        if (rp_distance < 1)
            rp_distance = 1;
    }
    depth = DotProduct(origin, vpn) - DotProduct(r_origin, vpn);
    band = depth < rp_distance * .25f ? 0 : depth < rp_distance * .5f ? 1 :
        depth < rp_distance * .75f ? 2 : depth < rp_distance ? 3 : 4;
    size = radius < 32 ? 0 : radius < 128 ? 1 : radius < 512 ? 2 : 3;
    rp_passes[band][size] += 1;
    rp_front[band][size] += front;
    rp_sent[band][size] += sent;
    for (bucket = 0; bucket < RP_LEAF_BUCKETS - 1 && leaves > (1 << bucket); bucket++)
        ;
    rp_leafhist[bucket] += 1;
    rp_leaves += leaves;
    rp_visleaves += visible_leaves;
    rp_models += 1;
}

static void rprof_clear(void)
{
    memset(rp_ticks, 0, sizeof rp_ticks);
    memset(rp_pairs, 0, sizeof rp_pairs);
    memset(rp_passes, 0, sizeof rp_passes);
    memset(rp_front, 0, sizeof rp_front);
    memset(rp_sent, 0, sizeof rp_sent);
    memset(rp_leafhist, 0, sizeof rp_leafhist);
    rp_cal_ticks = rp_cal_reads = rp_leaves = rp_visleaves = rp_models = 0;
    rp_nodes = rp_frags = rp_leaffaces = rp_so_frames = rp_so = rp_eo_frames = rp_eo = 0;
    rp_frames = 0;
}

/* Per frame, one decimal: " name a,b,c,d/..." rows of the band x size table. */
static int rprof_table(char *out, int size, const char *name, double table[RP_BANDS][RP_SIZES])
{
    int b, s, used;
    long v;

    if (size <= 1)
        return 0;
    used = snprintf(out, size, " %s ", name);
    for (b = 0; b < RP_BANDS && used < size; b++)
        for (s = 0; s < RP_SIZES && used < size; s++) {
            v = (long)(table[b][s] * 10 / rp_frames + .5);
            used += snprintf(out + used, size - used, "%ld.%ld%s", v / 10, v % 10,
                s < RP_SIZES - 1 ? "," : b < RP_BANDS - 1 ? "/" : "");
        }
    return used < size ? used : size - 1;
}

static long rprof_us(double ticks)
{
    return rp_frames ? (long)(ticks * 1e6 / eclocks_per_second / rp_frames + (ticks < 0 ? -.5 : .5)) : 0;
}

static void rprof_frame(double now)
{
    int i, used;
    unsigned long t, u;
    double r, emit, walk, oneleaf, clip, pass, nested;
    long cal, v, mean, vis;
    int on = aw_rcount_cvar.value >= 3 && cls.state == ca_connected && TimerBase && eclocks_per_second;

    if (!on || !aw_rprof_on || !rp_start) {   /* off, or the first frame on: start clean */
        memset(aw_rprof_ticks, 0, sizeof aw_rprof_ticks);
        memset(aw_rprof_pairs, 0, sizeof aw_rprof_pairs);
        rprof_clear();
        aw_rprof_on = on;
        rp_start = on ? now : 0;
        if (!on)
            rp_line[0] = 0;
        return;
    }
    for (i = 0; i < RP_TIMERS; i++) {
        rp_ticks[i] += aw_rprof_ticks[i];
        rp_pairs[i] += aw_rprof_pairs[i];
    }
    memset(aw_rprof_ticks, 0, sizeof aw_rprof_ticks);
    memset(aw_rprof_pairs, 0, sizeof aw_rprof_pairs);
    rp_nodes += aw_rcount[RC_CLIP_NODES];
    rp_frags += aw_rcount[RC_FRAGMENTS];
    rp_leaffaces += aw_rcount[RC_LEAF_FACES];
    if (r_outofsurfaces) {rp_so_frames++; rp_so += r_outofsurfaces;}
    if (r_outofedges) {rp_eo_frames++; rp_eo += r_outofedges * 2 / 3;}
    /* the clock's own cost, measured every frame: consecutive reads */
    t = AW_RProfTicks();
    for (cal = 0; cal < RP_CAL_READS; cal++) {
        u = AW_RProfTicks();
        rp_cal_ticks += u - t;
        t = u;
    }
    rp_cal_reads += RP_CAL_READS;
    rp_frames++;
    if (now - rp_start < 1.0)
        return;
    r = rp_cal_ticks / rp_cal_reads;
    emit = rp_ticks[RP_EMIT] - r * rp_pairs[RP_EMIT];
    clip = rp_ticks[RP_CLIP] - r * rp_pairs[RP_CLIP] - 2 * r * rp_pairs[RP_EMIT];
    walk = clip - emit;
    oneleaf = rp_ticks[RP_ONELEAF] - r * rp_pairs[RP_ONELEAF];
    nested = rp_pairs[RP_CLIP] + rp_pairs[RP_EMIT] + rp_pairs[RP_ONELEAF];
    pass = rp_ticks[RP_PASS] - r * rp_pairs[RP_PASS] - 2 * r * nested;
    v = (long)(r * 1e8 / eclocks_per_second + .5);
    used = snprintf(rp_line, sizeof rp_line,
        "%ld frames | r %ld.%02ld us | walk %ld us nodes %ld | emit %ld us frag %ld | oneleaf %ld us lf %ld"
        " | setup %ld us passes %ld | added %ld us | so %ld/%ld eo %ld/%ld |",
        rp_frames, v / 100, v % 100,
        rprof_us(walk), (long)(rp_nodes / rp_frames + .5), rprof_us(emit), (long)(rp_frags / rp_frames + .5),
        rprof_us(oneleaf), (long)(rp_leaffaces / rp_frames + .5),
        rprof_us(pass - clip - oneleaf), (long)(rp_pairs[RP_PASS] / rp_frames + .5),
        rprof_us(2 * r * (rp_pairs[RP_PASS] + nested)),
        (long)rp_so_frames, (long)(rp_so / rp_frames + .5), (long)rp_eo_frames, (long)(rp_eo / rp_frames + .5));
    if (used >= (int)sizeof rp_line)
        used = (int)sizeof rp_line - 1;
    used += rprof_table(rp_line + used, (int)sizeof rp_line - used, "hp", rp_passes);
    used += rprof_table(rp_line + used, (int)sizeof rp_line - used, "hf", rp_front);
    used += rprof_table(rp_line + used, (int)sizeof rp_line - used, "hs", rp_sent);
    for (i = 0; i < RP_LEAF_BUCKETS && used < (int)sizeof rp_line - 1; i++) {
        v = (long)(rp_leafhist[i] * 10 / rp_frames + .5);
        used += snprintf(rp_line + used, sizeof rp_line - used, "%s%ld.%ld", i ? "/" : " | lv ", v / 10, v % 10);
    }
    mean = rp_models ? (long)(rp_leaves * 10 / rp_models + .5) : 0;
    vis = rp_models ? (long)(rp_visleaves * 10 / rp_models + .5) : 0;
    if (used < (int)sizeof rp_line - 1)
        snprintf(rp_line + used, sizeof rp_line - used, " mean %ld.%ld vis %ld.%ld", mean / 10, mean % 10, vis / 10, vis % 10);
    if (aw_rcount_cvar.value >= 4)
        Con_Printf("rprof %s\n", rp_line);
    rp_start = now;
    rprof_clear();
}

void AW_RCountFrame(void)
{
    int i;
    double now, dt;
    /* A timedemo counts on its own (dbg rcount off too) and keeps one window for the whole
     * demo: CL_FinishTimeDemo hands it to timedemo_done (below). */
    int on = (aw_rcount_cvar.value > 0 || cls.timedemo) && cls.state == ca_connected;

    rprof_frame(Sys_FloatTime());

    if (!on) {
        memset(aw_rcount, 0, sizeof aw_rcount);
        memset(aw_rtime, 0, sizeof aw_rtime);
        aw_rcount_timing = 0;
        start = previous = 0;
        clear();
        return;
    }
    now = Sys_FloatTime();
    /* a timedemo counts the frames Quake times: from the second frame of the demo
     * (cl_demo.c td_starttime), not its loading */
    if (!aw_rcount_timing || !start || (cls.timedemo && host_framecount <= cls.td_startframe + 1)) {     /* first frame: start clean */
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
    if (now - start < 1.0 || cls.timedemo)
        return;
    format_line(now - start);
    if (aw_rcount_cvar.value < 2 || aw_rcount_cvar.value >= 4)  /* 2, 3: state file only */
        Con_Printf("rcount %s\n", line);
    start = now;
    clear();
}

/* The rcount line of the frames summed so far (SECONDS: their span, for fps10). */
static void format_line(double seconds)
{
    snprintf(line, sizeof line,
        "%ld frames fps10 %ld | bm %ld/%ld/%ld/%ld/%ld bf %ld/%ld cf %ld frag %ld/%ld lf %ld wf %ld"
        " | q %ld/%ld/%ld e %ld/%ld/%ld s %ld sp %ld | sc %ld/%ld scb %ld/%ld al %ld"
        " | us %ld/%ld/%ld/%ld/%ld/%ld/%ld pk %ld | vd %ld ne %ld/%ld | at %ld ln %ld/%ld/%ld"
        " | ft %ld/%ld/%ld %ld/%ld/%ld/%ld sk %ld/%ld",
        frames, seconds > 0 ? (long)(frames * 10.0 / seconds) : 0L,
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
        avg(sum[RQ_VISEDICTS_DROPPED]), avg(sum[RC_ENTITIES]), avg(sum[RC_SPRITES]),
        avg(sum[RC_ALIAS_TRIS]), avg(sum[RC_LOD_NEAR]), avg(sum[RC_LOD_COARSE]), avg(sum[RC_LOD_SLOTS]),
        avg(sum[RC_FAR_FOG_ON]), avg(sum[RC_FAR_FOG_DEPTH]), avg(sum[RC_FAR_FOG_WHY]), avg(sum[RC_FAR_FOG_MODELS]), avg(sum[RC_FAR_FOG_FACES]), avg(sum[RC_FAR_SIZE]), avg(sum[RC_FAR_DETAIL]),
        us(time_sum[RT_SKY]), us(time_sum[RT_FOG]));
    if (aw_chim_rcount) {
        int used = (int)strlen(line);
        aw_chim_rcount(line + used, (int)sizeof line - used, frames);
    }
}

/* timedemo DEMO (cl_demo.c): Quake's frames/seconds/fps, and the renderer counters averaged
 * over every frame of the demo (the rcount line's fields). The counts are the comparable part
 * (the same demo draws the same frames); the times are this machine's. One line per run is
 * appended to saves/timedemo-results.txt: AWTD1|demo|frames|centiseconds|fps10|rcount line. */
int AW_CamSavesFolder(char *out, int size);
static void timedemo_done(const char *demo, int frames_counted, double seconds)
{
    char path[256];
    FILE *f;
    long fps10 = seconds > 0 ? (long)(frames_counted * 10.0 / seconds + .5) : 0;
    if (!frames) {
        Con_Printf("timedemo %s: no frames counted\n", demo);
        return;
    }
    format_line(frame_sum);
    Con_Printf("timedemo rcount %s\n", line);
    if (AW_CamSavesFolder(path, (int)sizeof path) &&
        (int)strlen(path) + 24 < (int)sizeof path) {
        strcat(path, "/timedemo-results.txt");
        f = fopen(path, "a");
        if (f) {
            fprintf(f, "AWTD1|%s|%d|%ld|%ld|%s\n", demo, frames_counted, (long)(seconds * 100 + .5), fps10, line);
            fclose(f);
            Con_Printf("timedemo results appended to saves/timedemo-results.txt\n");
        } else
            Con_Printf("timedemo results: cannot write saves/timedemo-results.txt\n");
    }
    start = 0;
    clear();
}
