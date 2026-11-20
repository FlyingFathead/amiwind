/* SPDX-License-Identifier: GPL-2.0-or-later
 * Game rolls (REST-CUT-TOO-OFTEN-67, docs/RESTING.md "The roll"): every random number that decides a game outcome (the
 * rest interruption, alchemy, casting, persuasion, the dialogue's Random100, voice and idle picks, spell magnitudes,
 * QuakeC random(), monster moves) comes from AW_Roll, never from rand()%N or rand()&M.
 *
 * AW_Roll(N): a whole number 0..N-1 from ONE draw of the C library's generator, taken from the draw's TOP bits
 * (multiply by N, divide by RAND_MAX+1). A remainder rand()%N keeps the LOW bits, which a plain 32-bit generator (the
 * ANSI example, libnix) repeats with a period of 2^k for the k-th bit. The engine's own C library (newlib in the
 * AmigaPorts SDK: a 64-bit state, next*0x5851F42D4C957F2D+1, the top 31 bits returned) is good in every bit, so for it
 * the two give the same 1 in N; the top bits keep the rolls right whatever C library a build links. Exactly one draw,
 * as rand()%N was: the gameplay recorder's per-frame seeding (aw_recorder.c frame_seed) replays the same rolls.
 *
 * The generator is seeded once at boot from the machine's clock (sys_amiga.c boot_seed, after Host_Init; the console's
 * "Random: boot seed N" line), so a fresh session is not a replay of the last one; aw_seed N sets it for a test, and a
 * recording or its replay sets it every frame from the recording's seed. */
#ifndef AW_ROLL_H
#define AW_ROLL_H
#include <stdlib.h>

static inline int AW_Roll(int n)
{
    unsigned long long draw=(unsigned long long)(unsigned)rand();
    if(n<2)return 0;
    return (int)(draw*(unsigned long long)(unsigned)n/((unsigned long long)RAND_MAX+1ULL));
}

#endif
