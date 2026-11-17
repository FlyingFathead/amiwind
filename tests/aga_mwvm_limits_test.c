/* SPDX-License-Identifier: GPL-2.0-or-later
 * EXPANSION-SCRIPT-LIMITS-66 (MWVM-INSTANCES-256-66, MWVM-PARKING-STORE-SMALL-66, MWSCRIPT-MEMBER-QUIET-READER-66): the
 * script engine's tables sized by the build, through the real interpreter (engine/aga/src/aw_mwvm.c) on files the
 * builder's own compiler, planner and writer made (tests/test_mwvm_limits_native.py). Modes:
 *   attach    a map with more scripted placements than the old 256 attaches every one and every script runs (Count)
 *   park      the placements attached in chunks (map changes) past the old 2,816 objects and 9,216 values keep their
 *             values, read back parked and attached again
 *   roundtrip the values a save keeps (AW_MwvmLocalsEach) put back after a reset (AW_MwvmLocalSet): all intact
 *   shared    a quiet reader of another object's variable runs again when that object's own script changes it
 *   full      a file whose plan is too small: the host's full() is told, the stats count, nothing crashes
 *   forget    a forgotten reference's values are gone; a new object under it starts clean
 *   plan      the plan the file carries (an older 8-byte CONF: the earlier constants)
 * Usage: aga_mwvm_limits_test FILE.awm MODE [SEED_GLOBAL GO_GLOBAL COUNT_GLOBAL CHUNK] */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_mwvm.h"

static unsigned char *buf;
static long nbuf;
static int full_calls;
static char full_table[64];
static void warn(const char *what, int script) { printf("warn %s %d\n", what, script); }
static void full(const char *table, int planned, int used) {
    full_calls++;
    if (full_calls == 1) { strncpy(full_table, table, sizeof(full_table) - 1); printf("full %s planned %d used %d\n", table, planned, used); }
}
static aw_mwvm_host_t host;

static uint32_t be32(const unsigned char *p) { return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3]; }
static int bind_rows(uint32_t *off) {
    uint32_t rows, bytes;
    if (!AW_MwvmSection("BIND", off, &rows, &bytes)) return 0;
    return (int)rows;
}
/* the BIND row R: its reference, script, flags and position (engine units) */
static void bind_row(uint32_t off, int r, uint32_t *ref, int *script, int *flags, float o[3]) {
    const unsigned char *p = buf + off + 24 * r;int i;
    *ref = be32(p);*script = (p[4] << 8) | p[5];*flags = (p[6] << 8) | p[7];
    for (i = 0; i < 3; i++) o[i] = (float)(int32_t)be32(p + 12 + 4 * i) * 0.25f;
}
/* the rows FIRST .. LAST-1 attached, as the engine attaches a map's objects; how many were */
static int attach_rows(int first, int last) {
    uint32_t off, ref;int r, n = 0, rows = bind_rows(&off), script, flags;float o[3];
    for (r = first; r < last && r < rows; r++) {
        bind_row(off, r, &ref, &script, &flags, o);
        if (AW_MwvmAttach(ref, script, flags, -1, o) >= 0) n++;
    }
    return n;
}
static void stats(void) {
    const aw_mwvm_stats_t *s = AW_MwvmStats();int pi, pc, pp, ppc, ui, uc, up, upc;
    AW_MwvmPlan(&pi, &pc, &pp, &ppc);AW_MwvmUsage(&ui, &uc, &up, &upc);
    printf("plan %d %d %d %d\n", pi, pc, pp, ppc);
    printf("usage %d %d %d %d\n", ui, uc, up, upc);
    printf("refused %lu %lu %lu %lu\n", s->full_instances, s->full_cells, s->full_parked, s->full_park_cells);
    printf("stats runs %lu quiet %lu aborted %lu bytes %lu\n", s->runs, s->skipped_quiet, s->aborted, AW_MwvmTableBytes());
}
/* every row's values 0 and 1 (short a, long b: the Keeper script's first two) against CHUNK's seed */
static int check_rows(int rows, int chunk_size, int only_chunk) {
    uint32_t off, ref;int r, script, flags, bad = 0, s;float o[3];aw_mwcell_t a, b;
    bind_rows(&off);
    for (r = 0; r < rows; r++) {
        int chunk = r / chunk_size, want = chunk + 1;
        if (only_chunk >= 0 && chunk != only_chunk) continue;
        bind_row(off, r, &ref, &script, &flags, o);
        if (!AW_MwvmLocalGet(ref, 0, &s, &a) || !AW_MwvmLocalGet(ref, 1, &s, &b) || a.i != want || b.i != want * 1000) {
            if (bad < 5) printf("mismatch row %d ref %u a %d b %d want %d\n", r, (unsigned)ref, (int)a.i, (int)b.i, want);
            bad++;
        }
    }
    return bad;
}
typedef struct {uint32_t ref;int script, slot;uint32_t bits;} kept_t;
static kept_t *kept;static int nkept, kept_max;
static void keep(void *user, uint32_t reference, int script, int global, int running, const aw_mwcell_t *cells, int count) {
    int i;(void)user;(void)running;
    if (global) return;
    for (i = 0; i < count; i++) {
        if (!cells[i].i || nkept >= kept_max) continue;
        kept[nkept].ref = reference;kept[nkept].script = script;kept[nkept].slot = i;kept[nkept].bits = (uint32_t)cells[i].i;nkept++;
    }
}
int main(int argc, char **argv) {
    FILE *f;const char *mode;int seed_g = -1, go_g = -1, count_g = -1, chunk = 100, rows, tick, chunks, c;uint32_t off;
    float player[3] = {0, 0, 0};
    if (argc < 3) {printf("usage: FILE MODE [SEED GO COUNT CHUNK]\n");return 2;}
    if (!(f = fopen(argv[1], "rb"))) {printf("no file\n");return 2;}
    fseek(f, 0, SEEK_END);nbuf = ftell(f);fseek(f, 0, SEEK_SET);
    buf = (unsigned char *)malloc((size_t)nbuf + 1);
    if (!buf || (long)fread(buf, 1, (size_t)nbuf, f) != nbuf) {printf("read failed\n");return 2;}
    fclose(f);
    mode = argv[2];
    if (argc > 3) seed_g = atoi(argv[3]);
    if (argc > 4) go_g = atoi(argv[4]);
    if (argc > 5) count_g = atoi(argv[5]);
    if (argc > 6) chunk = atoi(argv[6]);
    host.warn = warn;host.full = full;
    if (!AW_MwvmLoad(buf, (unsigned long)nbuf, &host)) {printf("load failed\n");stats();return 1;}
    rows = bind_rows(&off);
    printf("rows %d\n", rows);
    if (!strcmp(mode, "plan")) {stats();return 0;}
    if (!strcmp(mode, "attach") || !strcmp(mode, "full")) {
        /* one map with every placement: more than the old 256 */
        AW_MwvmBeginMap();
        printf("attached %d\n", attach_rows(0, rows));
        for (tick = 1; tick <= 4; tick++) AW_MwvmTick(0.25f, player);
        if (count_g >= 0) printf("count %d\n", (int)AW_MwvmGlobalInt(count_g));
        printf("full calls %d\n", full_calls);
        stats();
        return 0;
    }
    if (!strcmp(mode, "park") || !strcmp(mode, "roundtrip") || !strcmp(mode, "forget")) {
        chunks = (rows + chunk - 1) / chunk;
        /* each chunk a map: attached, its scripts run with Seed = chunk + 1, then the next map parks them */
        for (c = 0; c < chunks; c++) {
            AW_MwvmBeginMap();
            if (seed_g >= 0) AW_MwvmGlobalSetBits(seed_g, (uint32_t)(c + 1));
            attach_rows(c * chunk, (c + 1) * chunk);
            for (tick = 1; tick <= 2; tick++) AW_MwvmTick(0.25f, player);
        }
        AW_MwvmBeginMap();   /* everything parked */
        printf("parked-check mismatches %d\n", check_rows(rows, chunk, -1));
        if (!strcmp(mode, "roundtrip")) {
            /* what a save keeps, then back after a reset (a load) */
            int i, put = 0;
            kept_max = rows * 4 + 16;kept = (kept_t *)calloc((size_t)kept_max, sizeof(kept_t));nkept = 0;
            AW_MwvmLocalsEach(keep, NULL);
            printf("kept %d values\n", nkept);
            AW_MwvmLocalsReset();
            printf("reset-check mismatches %d\n", check_rows(rows, chunk, -1));
            for (i = 0; i < nkept; i++) put += AW_MwvmLocalSet(kept[i].ref, kept[i].script, kept[i].slot, kept[i].bits);
            printf("put %d\n", put);
            printf("loaded-check mismatches %d\n", check_rows(rows, chunk, -1));
        }
        if (!strcmp(mode, "forget")) {
            uint32_t ref;int script, flags, s;float o[3];aw_mwcell_t v;
            bind_row(off, 0, &ref, &script, &flags, o);
            printf("forget %d\n", AW_MwvmForget(ref));
            printf("after-forget found %d\n", AW_MwvmLocalGet(ref, 0, &s, &v));
            printf("forget-again %d\n", AW_MwvmForget(ref));
            /* a new object under the reference starts clean: attached in chunk 0's map, its script runs with Seed 77 */
            AW_MwvmBeginMap();
            if (seed_g >= 0) AW_MwvmGlobalSetBits(seed_g, 77);
            attach_rows(0, 1);
            printf("fresh a %d\n", AW_MwvmLocalGet(ref, 0, &s, &v) ? (int)v.i : -1);
            for (tick = 1; tick <= 2; tick++) AW_MwvmTick(0.25f, player);
            printf("ran a %d\n", AW_MwvmLocalGet(ref, 0, &s, &v) ? (int)v.i : -1);
        }
        /* chunk 0 back in place: the values come with it */
        AW_MwvmBeginMap();
        attach_rows(0, chunk);
        if (strcmp(mode, "forget")) printf("back-check mismatches %d\n", check_rows(rows, chunk, 0));
        stats();
        return 0;
    }
    if (!strcmp(mode, "shared")) {
        /* MWSCRIPT-MEMBER-QUIET-READER-66: the reader (row 0) attached before the target (row 1); both go quiet; the
         * global Go wakes both, the target changes its variable: the reader sees it on the next frame */
        uint32_t ref;int script, flags, s;float o[3];aw_mwcell_t v;
        AW_MwvmBeginMap();
        printf("attached %d\n", attach_rows(0, rows));
        for (tick = 1; tick <= 3; tick++) AW_MwvmTick(0.25f, player);
        bind_row(off, 0, &ref, &script, &flags, o);
        printf("seen-before %d\n", AW_MwvmLocalGet(ref, 0, &s, &v) ? (int)v.i : -1);
        if (go_g >= 0) AW_MwvmGlobalSetBits(go_g, 1);
        AW_MwvmTick(0.25f, player);
        printf("seen-first-frame %d\n", AW_MwvmLocalGet(ref, 0, &s, &v) ? (int)v.i : -1);
        AW_MwvmTick(0.25f, player);
        printf("seen-second-frame %d\n", AW_MwvmLocalGet(ref, 0, &s, &v) ? (int)v.i : -1);
        for (tick = 1; tick <= 3; tick++) AW_MwvmTick(0.25f, player);
        printf("seen-later %d\n", AW_MwvmLocalGet(ref, 0, &s, &v) ? (int)v.i : -1);
        stats();
        return 0;
    }
    printf("unknown mode\n");
    return 2;
}
