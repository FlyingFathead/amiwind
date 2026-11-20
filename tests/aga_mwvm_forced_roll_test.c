/* SPDX-License-Identifier: GPL-2.0-or-later
 * DBG-DBATTACK-67 and GETPCSLEEP-NOT-CARRIED-OUT-67: a script shaped as Tribunal's dbAttackScript (one roll per sleep,
 * then WakeUpPC, PlaceAtPC of the assassin and DBAttack 1) runs in the real interpreter (engine/aga/src/aw_mwvm.c) on a
 * file the builder's own compiler and writer made (tests/test_mwvm_forced_roll_native.py). The host answers GetPCSleep
 * with a whole number, as aw_mwhost.c does since v0.0.67, 1 while a rest passes. 200 rests with the game's roll, then
 * 200 with the roll made sure for that script (AW_MwvmForceRandom, what dbg dbattack sets for its one rest): the counts
 * of rests, wakes and placements are printed; the Python side checks them.
 *
 * Usage: aga_mwvm_forced_roll_test FILE.awm SCRIPT DBATTACK_GLOBAL */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_mwvm.h"
#include "aw_mwcode.h"

static unsigned char buf[1 << 20];
static int asleep, wakes, places, reads;
static void warn(const char *what, int script) { printf("warn %s %d\n", what, script); }
static int call(int instance, int target, int function, const aw_mwcell_t *numbers, int count,
                const unsigned char *strings, int nstrings, aw_mwcell_t *result) {
    (void)instance; (void)target; (void)numbers; (void)count; (void)strings; (void)nstrings;
    if (function == AWF_GETPCSLEEP) {reads++;result->i = asleep;return AW_MWVM_CALL_READ;}
    if (function == AWF_WAKEUPPC) {wakes++;asleep = 0;return 1;}
    if (function == AWF_PLACEATPC) {places++;return 1;}
    return 0;
}
static aw_mwvm_host_t host;

static void rests(const char *what, int many, int script, int global) {
    float player[3] = {0, 0, 0};int i, tick;
    wakes = places = 0;
    for (i = 0; i < many; i++) {
        asleep = 1;                                   /* a rest's hours pass over three frames */
        for (tick = 0; tick < 3; tick++) AW_MwvmTick(0.1f, player);
        asleep = 0;                                   /* awake again: the script's sleepOnce goes back to 0 */
        for (tick = 0; tick < 2; tick++) AW_MwvmTick(0.1f, player);
    }
    printf("%s rests %d wakes %d places %d dbattack %d forced %d\n", what, many, wakes, places,
           (int)AW_MwvmGlobalInt(global), AW_MwvmForcedRandom() == script);
}
int main(int argc, char **argv) {
    FILE *f;long n;int script, global;
    if (argc < 4) {printf("usage: FILE SCRIPT GLOBAL\n");return 2;}
    if (!(f = fopen(argv[1], "rb"))) {printf("no file\n");return 2;}
    n = (long)fread(buf, 1, sizeof(buf), f);fclose(f);
    script = atoi(argv[2]);global = atoi(argv[3]);
    host.warn = warn;host.call = call;
    if (!AW_MwvmLoad(buf, (unsigned long)n, &host)) {printf("load failed\n");return 1;}
    AW_MwvmBeginMap();
    if (!AW_MwvmGlobalScriptSet(script, 1)) {printf("start failed\n");return 1;}
    rests("game", 200, script, global);
    AW_MwvmGlobalSetBits(global, 0);
    AW_MwvmForceRandom(script);
    rests("sure", 200, script, global);
    AW_MwvmForceRandom(-1);
    printf("reads %d forced_rolls %lu\n", reads, AW_MwvmStats()->forced_rolls);
    return 0;
}
