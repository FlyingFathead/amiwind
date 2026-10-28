/* SPDX-License-Identifier: GPL-2.0-or-later
 * The first-person hand clip table (aw_hand_models.c AW_HandTableParse, AW_HandClipFrame; FIRST-PERSON-HANDS-IN-C-54):
 * the text tools/hand_metadata.py hand_table writes, and the frames the old QuakeC gave. */
#include <assert.h>
#include <string.h>
#include "aw_hand_models.h"

int main(void) {
    aw_hand_table_t t;
    const char *good="AWHA1\nclip idle 0 8 2.700000\nclip draw 8 6 0.470000\nclip lower 14 4 0.270000\nclip punch 18 10 1.070000\n";
    assert(AW_HandTableParse(good,&t));
    assert(t.first[AW_HAND_PUNCH]==18 && t.count[AW_HAND_PUNCH]==10 && t.duration[AW_HAND_PUNCH]>1.06f && t.duration[AW_HAND_PUNCH]<1.08f);
    /* world.qc's weaponframe = first + floor(elapsed * count / duration) */
    assert(AW_HandClipFrame(&t,AW_HAND_IDLE,0)==0);
    assert(AW_HandClipFrame(&t,AW_HAND_DRAW,.25f)==8+3);
    assert(AW_HandClipFrame(&t,AW_HAND_PUNCH,1.069f)==27);
    assert(AW_HandClipFrame(&t,AW_HAND_PUNCH,5)==27);        /* held on its last frame */
    assert(AW_HandClipFrame(&t,AW_HAND_LOWER,-1)==14);
    /* a later stance line is skipped (the stances to come) */
    assert(AW_HandTableParse("AWHA1\nstance 1h progs/hands/x.mdl\nclip idle 0 8 1\nclip draw 8 6 1\nclip lower 14 4 1\nclip punch 18 10 1\n",&t));
    /* refused: no magic, a missing or repeated clip, bad numbers */
    assert(!AW_HandTableParse("clip idle 0 8 1\n",&t));
    assert(!AW_HandTableParse("AWHA1\nclip idle 0 8 1\nclip draw 8 6 1\nclip lower 14 4 1\n",&t));
    assert(!AW_HandTableParse("AWHA1\nclip idle 0 8 1\nclip idle 0 8 1\nclip draw 8 6 1\nclip lower 14 4 1\nclip punch 18 10 1\n",&t));
    assert(!AW_HandTableParse("AWHA1\nclip idle 0 8 0\nclip draw 8 6 1\nclip lower 14 4 1\nclip punch 18 10 1\n",&t));
    assert(!AW_HandTableParse("AWHA1\nclip idle 0 8 61\nclip draw 8 6 1\nclip lower 14 4 1\nclip punch 18 10 1\n",&t));
    assert(!AW_HandTableParse("AWHA1\nclip idle 0 8 1e-1\nclip draw 8 6 1\nclip lower 14 4 1\nclip punch 18 10 1\n",&t));
    assert(!AW_HandTableParse("AWHA1\nclip kick 0 8 1\nclip draw 8 6 1\nclip lower 14 4 1\nclip punch 18 10 1\n",&t));
    assert(!AW_HandTableParse(NULL,&t));
    return 0;
}
