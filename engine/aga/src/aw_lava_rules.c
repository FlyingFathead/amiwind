/* SPDX-License-Identifier: GPL-2.0-or-later
 * Lava rules as pure functions (aw_lava.h, docs/LAVA.md). No engine state:
 * the host test runs them as they are. */
#include "aw_lava.h"

int AW_LavaIn(int watertype, int waterlevel) {
    return watertype==AW_LAVA_CONTENTS && waterlevel>=1;
}
static int clamp255(int v) {return v<0?0:v>255?255:v;}
int AW_LavaTintPercent(float seconds, int low, int high, float ramp) {
    float t;
    low=clamp255(low);high=clamp255(high);
    if(high<low)high=low;
    if(ramp<=0 || seconds>=ramp)return high;
    if(seconds<=0)return low;
    t=seconds/ramp;
    return low+(int)((float)(high-low)*t);
}
int AW_LavaParseTint(const char *text, int rgb[3]) {
    int v[3]={0,0,0},n=0;
    const char *p=text;
    while(p && n<3){
        int value=0,digits=0;
        while(*p==' ' || *p=='\t')p++;
        while(*p>='0' && *p<='9'){if(value<1000)value=value*10+(*p-'0');p++;digits++;}
        if(!digits)break;
        v[n++]=clamp255(value);
    }
    if(p)while(*p==' ' || *p=='\t')p++;
    if(n!=3 || !p || *p){rgb[0]=128;rgb[1]=4;rgb[2]=4;return 0;}
    rgb[0]=v[0];rgb[1]=v[1];rgb[2]=v[2];
    return 1;
}
float AW_LavaDamage(float dps, float seconds) {
    float d=dps*seconds;
    return d>0?d:0;
}
