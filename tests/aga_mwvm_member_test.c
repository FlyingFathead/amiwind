/* SPDX-License-Identifier: GPL-2.0-or-later
 * MWSCRIPT-MEMBER-READS-ID-AS-SCRIPT-66: a script reads and writes another object's variables ("heart_test".countHits)
 * through the real interpreter (engine/aga/src/aw_mwvm.c), on a file the builder's own compiler and writer made
 * (tests/test_mwvm_member_native.py). The reader (DagothTest) and the target (HeartTest) run different scripts, and the
 * target's object row has an id that is not its script, so the old read (the script taken from the id's offset) found
 * nothing. Covered: a read (GETM), a whole-number and a fraction write (SETM), a short write (SETMS), a script's own
 * variable by its name ("KeeperTest".level: the script's global instance, row kind 1), and the target parked (its place
 * left) while the reader reads and writes it. Every value is printed; the Python side checks them.
 *
 * Usage: aga_mwvm_member_test FILE.awm HEART_REF DAGOTH_REF KEEPER_SCRIPT PARKNOW_GLOBAL */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_mwvm.h"

static unsigned char buf[1 << 20];
static long nbuf;
static void warn(const char *what, int script) { printf("warn %s %d\n", what, script); }
static aw_mwvm_host_t host;     /* the other calls: none (the scripts read and write locals only) */

/* the BIND row of REFERENCE attached again (all rows when 0), as the engine attaches a map's objects */
static int attach(uint32_t reference) {
    uint32_t off, rows, bytes, r;int i, n = 0;
    if (!AW_MwvmSection("BIND", &off, &rows, &bytes)) return 0;
    for (r = 0; r < rows; r++) {
        const unsigned char *p = buf + off + 24 * r;float o[3];
        uint32_t ref = ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
        if (reference && ref != reference) continue;
        for (i = 0; i < 3; i++)
            o[i] = (float)(int32_t)(((uint32_t)p[12 + 4 * i] << 24) | ((uint32_t)p[13 + 4 * i] << 16) |
                                    ((uint32_t)p[14 + 4 * i] << 8) | p[15 + 4 * i]) * 0.25f;
        if (AW_MwvmAttach(ref, (p[4] << 8) | p[5], (p[6] << 8) | p[7], -1, o) >= 0) n++;
    }
    return n;
}
/* REFERENCE's locals 0..COUNT-1 (attached or parked); a fraction slot printed as one */
static void locals(const char *what, uint32_t reference, int count, int fraction_slot) {
    int slot, script;aw_mwcell_t v;
    printf("%s", what);
    for (slot = 0; slot < count; slot++) {
        if (!AW_MwvmLocalGet(reference, slot, &script, &v)) {printf(" -");continue;}
        if (slot == fraction_slot) printf(" %.2f", v.f);else printf(" %d", (int)v.i);
    }
    printf("\n");
}
static void keeper(int script) {
    int k, found = 0;
    for (k = 0; k < AW_MwvmInstanceCount(); k++) {
        aw_mwvm_instance_t *in = AW_MwvmInstance(k);
        if (in && (in->flags & AWI_GLOBAL) && (int)in->script == script) {
            printf("keeper %d running %d\n", (int)AW_MwvmLocal(k, 0).i, (in->flags & AWI_RUNNING) != 0);found = 1;}
    }
    if (!found) printf("keeper none\n");
}
static void show(const char *when, uint32_t heart, uint32_t dagoth, int keeper_script) {
    printf("== %s\n", when);
    /* HeartTest: countHits total rate started; DagothTest: seen stage totalSeen rateSeen levelSeen hitsSeen */
    locals("heart", heart, 4, 2);
    locals("dagoth", dagoth, 6, 3);
    keeper(keeper_script);
}
int main(int argc, char **argv) {
    FILE *f;uint32_t heart, dagoth;int keeper_script, parknow, tick, k;float player[3] = {0, 0, 0};
    if (argc < 6) {printf("usage: FILE HEART DAGOTH KEEPER PARKNOW\n");return 2;}
    if (!(f = fopen(argv[1], "rb"))) {printf("no file\n");return 2;}
    nbuf = (long)fread(buf, 1, sizeof(buf), f);fclose(f);
    heart = (uint32_t)strtoul(argv[2], NULL, 10);dagoth = (uint32_t)strtoul(argv[3], NULL, 10);
    keeper_script = atoi(argv[4]);parknow = atoi(argv[5]);
    host.warn = warn;
    if (!AW_MwvmLoad(buf, (unsigned long)nbuf, &host)) {printf("load failed\n");return 1;}
    /* the object rows as the interpreter reads them: id and script */
    for (k = 0; k < AW_MwvmObjectCount(); k++)
        printf("row %d reference %u id %d script %d\n", k, (unsigned)AW_MwvmObjectReference(k), AW_MwvmObjectId(k),
               AW_MwvmObjectScript(k));
    AW_MwvmBeginMap();
    printf("attached %d\n", attach(0));
    for (tick = 1; tick <= 6; tick++) AW_MwvmTick(0.25f, player);
    show("attached", heart, dagoth, keeper_script);
    /* the heart's place left: its values parked; the reader reads and writes them there */
    printf("detach %d\n", AW_MwvmDetach(heart));
    AW_MwvmGlobalSetBits(parknow, 1);
    for (tick = 1; tick <= 3; tick++) AW_MwvmTick(0.25f, player);
    show("parked", heart, dagoth, keeper_script);
    printf("back %d\n", attach(heart));
    for (tick = 1; tick <= 2; tick++) AW_MwvmTick(0.25f, player);
    show("back", heart, dagoth, keeper_script);
    {const aw_mwvm_stats_t *s = AW_MwvmStats();
     printf("stats runs %lu quiet %lu aborted %lu\n", s->runs, s->skipped_quiet, s->aborted);}
    return 0;
}
