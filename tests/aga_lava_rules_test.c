/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_lava_rules.c alone: who is in lava, the damage of Morrowind's pool
 * script (20 health a second), the blood-red tint and its ramp. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include "aw_lava.h"

static int near(float a, float b) {return fabsf(a-b)<.001f;}

int main(void) {
    int rgb[3];
    /* In lava from the feet up; water and slime are not lava. */
    assert(AW_LavaIn(-5,1) && AW_LavaIn(-5,2) && AW_LavaIn(-5,3));
    assert(!AW_LavaIn(-5,0) && !AW_LavaIn(-3,1) && !AW_LavaIn(-4,3) && !AW_LavaIn(-1,0));
    /* Damage: dps x frame time, never negative. One second of 50 Hz frames = 20. */
    {
        float total=0;int i;
        for(i=0;i<50;i++)total+=AW_LavaDamage(AW_LAVA_DEFAULT_DPS,.02f);
        assert(near(total,20.f));
    }
    assert(AW_LavaDamage(20,0)==0 && AW_LavaDamage(20,-1)==0 && AW_LavaDamage(-5,1)==0);
    assert(near(AW_LavaDamage(20,.5f),10.f));
    /* Tint ramp: low on stepping in, rising to high after the ramp; clamped. */
    assert(AW_LavaTintPercent(0,110,230,3)==110);
    assert(AW_LavaTintPercent(1.5f,110,230,3)==170);
    assert(AW_LavaTintPercent(3,110,230,3)==230 && AW_LavaTintPercent(99,110,230,3)==230);
    assert(AW_LavaTintPercent(1,110,230,0)==230);           /* no ramp: full at once */
    assert(AW_LavaTintPercent(1,300,400,3)==255);           /* clamped to 255 */
    assert(AW_LavaTintPercent(1,200,100,3)==200);           /* high below low: low */
    {   /* the ramp never goes down while the player stays in */
        int last=0;float t;
        for(t=0;t<4;t+=.05f){int p=AW_LavaTintPercent(t,110,230,3);assert(p>=last);last=p;}
    }
    /* Tint colour: "R G B", clamped; anything else gives the default blood red. */
    assert(AW_LavaParseTint("128 4 4",rgb) && rgb[0]==128 && rgb[1]==4 && rgb[2]==4);
    assert(AW_LavaParseTint("  90 0 10 ",rgb) && rgb[0]==90 && rgb[1]==0 && rgb[2]==10);
    assert(AW_LavaParseTint("999 0 0",rgb) && rgb[0]==255);
    assert(!AW_LavaParseTint("red",rgb) && rgb[0]==128 && rgb[1]==4 && rgb[2]==4);
    assert(!AW_LavaParseTint("1 2",rgb) && rgb[0]==128);
    assert(!AW_LavaParseTint("1 2 3 4",rgb) && rgb[0]==128);
    assert(!AW_LavaParseTint("",rgb) && !AW_LavaParseTint(0,rgb));
    /* The default is a blood red: red dominant, green and blue near zero, darker
     * than the damage flash (190, 20, 20) and id's orange preset (255, 80, 0). */
    AW_LavaParseTint(AW_LAVA_DEFAULT_TINT,rgb);
    assert(rgb[0]>=100 && rgb[0]<190 && rgb[1]<16 && rgb[2]<16);
    puts("lava rules ok");
    return 0;
}
