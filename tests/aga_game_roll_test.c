/* SPDX-License-Identifier: GPL-2.0-or-later
 * Game rolls (REST-CUT-TOO-OFTEN-67, aw_roll.h, docs/RESTING.md "The roll"): the engine's AW_Roll and the rest rule
 * (aw_rest_rules.c AW_RestInterruptAt) on the C library the engine links, modelled here from its own code: newlib in
 * the AmigaPorts SDK v16.2-rc11, libm020/libm881/libc.a lib_a-rand.o, disassembled: a 64-bit state, lazily 1,
 * next = next*0x5851F42D4C957F2D + 1, the top 31 bits returned (next>>32 & 0x7fffffff); srand(s) sets the state to s.
 * This file's rand and srand stand in for the C library's in this program (the engine's code calls them by name).
 *
 * 1. AW_Roll(N) is 0..N-1 and takes exactly one draw for every N (0 and 1 too), as rand()%N did, so the gameplay
 *    recorder's per-frame seeding replays the same rolls.
 * 2. Over many boots (boot seeds) and many boot paths (different numbers of draws before and between the rests, as
 *    different frame counts give), a 12-hour wilderness rest is cut close to one time in four (3 of 12 values), cut
 *    after 9 hours. The old roll rand()%12 on newlib is fair as well: the rate alone never failed on this library.
 * 3. The boot seed matters: with the generator unseeded (state 1 at every boot, the old engine), two boots that draw
 *    the same numbers before each rest roll the same eight rests; seeded from different boot seeds they do not.
 * 4. A recording's per-frame seed wins over the boot seed: after srand(frame seed) the rolls are the same whatever
 *    the boot seeded.
 * 5. On a C library whose rand keeps a plain 32-bit generator's LOW bits (a remainder keeps bits with periods of 2,
 *    4, 8 ...), rests a multiple of 4 draws apart roll rand()%4 the same every time, so rand()%12 < 3 is stuck; AW_Roll
 *    takes the top bits and stays near one in four. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_rest.h"
#include "aw_roll.h"

static int lowbit_library;                      /* 0: newlib (the engine's), 1: a low-bit 32-bit generator */
static unsigned long long newlib_state=1;       /* newlib: lazily 1 */
static unsigned long lowbit_state=1;
static unsigned long draws;
int rand(void)
{
    draws++;
    if(lowbit_library){
        lowbit_state=(lowbit_state*1103515245UL+12345UL)&0xffffffffUL;
        return (int)(lowbit_state&0x7fffffffUL);
    }
    newlib_state=newlib_state*0x5851F42D4C957F2DULL+1ULL;
    return (int)((newlib_state>>32)&0x7fffffffULL);
}
void srand(unsigned seed){newlib_state=seed;lowbit_state=seed;}

/* a small independent generator for the boot paths' draw counts (not the one under test) */
static unsigned long path_state=0x9e3779b9UL;
static unsigned long path_next(unsigned long n)
{
    path_state^=path_state<<13;path_state&=0xffffffffUL;path_state^=path_state>>17;path_state^=path_state<<5;
    path_state&=0xffffffffUL;
    return path_state%n;
}
static void skip(unsigned long n){while(n--)(void)rand();}

static aw_rest_settings_t settings(void)
{
    aw_rest_settings_t s;memset(&s,0,sizeof(s));
    assert(AW_RestSettingSet(&s,"fSleepRandMod",0.25f) && AW_RestSettingSet(&s,"fSleepRestMod",0.3f));
    return s;
}

static void one_draw_each(void)
{
    static const int sizes[]={0,1,2,3,4,5,12,24,100,101,256,10000,10001,32768};
    unsigned i,k;
    lowbit_library=0;srand(7);
    for(i=0;i<sizeof(sizes)/sizeof(sizes[0]);i++)
        for(k=0;k<20000;k++){
            unsigned long before=draws;int r=AW_Roll(sizes[i]);
            assert(draws==before+1);
            assert(r>=0 && (sizes[i]<2?r==0:r<sizes[i]));
        }
    /* the first draw from newlib's lazy state is 0x5851F42D (the constant its first-call path loads) */
    newlib_state=1;assert(rand()==1481765933);
}

/* 8 rests of 12 hours per boot; before the first and between rests a number of other draws (frame counts) */
static double rest_rate(int seeded,int old_remainder,int boots,int *cut_hour_ok)
{
    aw_rest_settings_t s=settings();long cut=0,rests=0;int b,r;
    *cut_hour_ok=1;
    for(b=0;b<boots;b++){
        if(seeded)srand((unsigned)(0x2545F491UL^((unsigned long)b*2654435761UL)));else{newlib_state=1;lowbit_state=1;}
        skip(200+path_next(5000));
        for(r=0;r<8;r++){
            int roll=old_remainder?rand()%12:AW_Roll(12),at=AW_RestInterruptAt(&s,12,roll);
            rests++;
            if(at){cut++;if(at!=9)*cut_hour_ok=0;}
            skip(50+path_next(3000));
        }
    }
    return (double)cut/(double)rests;
}

static void rate_near_one_in_four(void)
{
    int ok;double rate;
    lowbit_library=0;
    rate=rest_rate(1,0,4000,&ok);
    printf("newlib, AW_Roll, seeded boots: %.4f of 32000 rests cut\n",rate);
    assert(ok && rate>0.235 && rate<0.265);
    rate=rest_rate(1,1,4000,&ok);
    printf("newlib, rand()%%12 (the old roll), seeded boots: %.4f\n",rate);
    assert(ok && rate>0.235 && rate<0.265);
    rate=rest_rate(0,0,4000,&ok);
    printf("newlib, AW_Roll, unseeded boots (different paths): %.4f\n",rate);
    assert(ok && rate>0.235 && rate<0.265);
}

static void boot_seed_matters(void)
{
    int a[8],b[8],c[8],i;aw_rest_settings_t s=settings();
    lowbit_library=0;
    /* the same draws before each rest (the same frame counts) on two boots */
    newlib_state=1;for(i=0;i<8;i++){skip(1000+(unsigned long)i*37);a[i]=AW_RestInterruptAt(&s,12,AW_Roll(12));}
    newlib_state=1;for(i=0;i<8;i++){skip(1000+(unsigned long)i*37);b[i]=AW_RestInterruptAt(&s,12,AW_Roll(12));}
    assert(!memcmp(a,b,sizeof(a)));             /* unseeded (the old engine): the same eight rests every boot */
    {int differs=0;unsigned seed;
     for(seed=1;seed<=16;seed++){
         srand(seed*0x9E3779B9u);for(i=0;i<8;i++){skip(1000+(unsigned long)i*37);c[i]=AW_RestInterruptAt(&s,12,AW_Roll(12));}
         if(memcmp(a,c,sizeof(a)))differs++;
     }
     printf("boot seeds giving other rests than the unseeded boot: %d of 16\n",differs);
     assert(differs>=12);}
}

static void recording_seed_wins(void)
{
    int a[16],b[16],i;
    lowbit_library=0;
    srand(11111u);skip(123);srand(0xC0DE0042u);for(i=0;i<16;i++)a[i]=AW_Roll(12);
    srand(99999u);skip(4567);srand(0xC0DE0042u);for(i=0;i<16;i++)b[i]=AW_Roll(12);
    assert(!memcmp(a,b,sizeof(a)));
}

static void low_bit_library(void)
{
    aw_rest_settings_t s=settings();long old_cut=0,new_cut=0,n=0;int k;
    lowbit_library=1;srand(1);
    for(k=0;k<4000;k++){
        /* the old rolls are 8 draws apart: the generator's low two bits repeat every 4 draws, so rand()%4 is the
         * same at every one of them (2 from seed 1): rolls 2, 6 or 10 only, a cut one time in three */
        if(AW_RestInterruptAt(&s,12,rand()%12))old_cut++;
        skip(3);
        if(AW_RestInterruptAt(&s,12,AW_Roll(12)))new_cut++;
        skip(3);
        n++;
    }
    printf("low-bit library, rests 4 draws apart: rand()%%12 cut %.4f, AW_Roll cut %.4f\n",(double)old_cut/n,(double)new_cut/n);
    assert(new_cut>0.2*n && new_cut<0.3*n);
    assert(old_cut<0.2*n || old_cut>0.3*n);    /* the remainder keeps a 4-periodic bit pattern: not one in four */
    lowbit_library=0;
}

int main(void)
{
    one_draw_each();
    rate_near_one_in_four();
    boot_seed_matters();
    recording_seed_wins();
    low_bit_library();
    puts("game rolls: ok");
    return 0;
}
