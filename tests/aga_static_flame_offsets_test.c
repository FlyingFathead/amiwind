/* SPDX-License-Identifier: GPL-2.0-or-later
 * Static flame emitter offsets (ENGINE-FPU-UNIMPL-31): the precomputed
 * constants equal the per-frame formula they replaced. */
#include "quakedef.h"
#include <assert.h>
#include <math.h>

extern const float aw_static_flame_offsets[6][2];
void Con_Printf(char *fmt,...) {}
void Sys_Error(char *fmt,...) {assert(0);}
int main(void)
{
    int k;float a,r;
    for(k=0;k<6;k++){
        a=k*2.39996f;r=k?0.45f+0.55f*(float)fmod(k*0.618034f,1.0f):0;
        assert(fabs(aw_static_flame_offsets[k][0]-r*cos(a))<1e-6);
        assert(fabs(aw_static_flame_offsets[k][1]-r*sin(a))<1e-6);
    }
    return 0;
}
