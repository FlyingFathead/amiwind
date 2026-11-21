/* SPDX-License-Identifier: GPL-2.0-or-later
 * A room's water level as the scripts read it, pure functions (aw_water.h, GETWATERLEVEL-COLUMN-NOT-ROOM-67). No
 * engine state: the host test runs them as they are (tests/aga_water_rules_test.c). */
#include <float.h>
#include <string.h>
#include "aw_water.h"

static unsigned long be16(const unsigned char *p) {
    return ((unsigned long)p[0]<<8)|p[1];
}
static float be32f(const unsigned char *p) {
    unsigned long u=((unsigned long)p[0]<<24)|((unsigned long)p[1]<<16)|((unsigned long)p[2]<<8)|p[3];
    unsigned int bits=(unsigned int)u;float f;
    memcpy(&f,&bits,4);
    return f;
}
int AW_WaterRow(const unsigned char *rows, unsigned long count, unsigned long number, float *level) {
    unsigned long low=0,high=count;
    if(!rows || !count)return 0;
    while(low<high){
        unsigned long mid=low+(high-low)/2,n=be16(rows+AW_WATER_ROW_BYTES*mid);
        if(n==number){
            const unsigned char *r=rows+AW_WATER_ROW_BYTES*mid;
            float f;
            if(!(r[2]&AW_WATER_FLAG))return 0;
            f=be32f(r+4);
            if(!(f==f) || f>FLT_MAX || f<-FLT_MAX)return 0;    /* a level that is not a number: not listed */
            if(level)*level=f;
            return 1;
        }
        if(n<number)low=mid+1;else high=mid;
    }
    return 0;
}
float AW_WaterNone(void) {
    return -FLT_MAX;
}
float AW_WaterReading(int where, int found, float level) {
    if(where!=AW_WATER_ROOM)return 0.0f;         /* outdoors 0, the original's oddity; no player: 0 */
    return found?level:AW_WaterNone();
}
float AW_WaterLevelAfter(int mod, float now, float value) {
    return mod?now+value:value;
}
int AW_WaterCallChanges(int where, int found) {
    return where==AW_WATER_ROOM && found;
}
void AW_WaterFactId(char out[32], unsigned long number) {
    static const char head[]="amiwind:water:";
    char digits[12];int n=0,i;
    memcpy(out,head,sizeof(head)-1);
    do{digits[n++]=(char)('0'+number%10);number/=10;}while(number && n<10);
    for(i=0;i<n;i++)out[sizeof(head)-1+i]=digits[n-1-i];
    out[sizeof(head)-1+n]=0;
}
long AW_WaterFactValue(float level) {
    unsigned int bits;
    memcpy(&bits,&level,4);
    return (long)(int)bits;
}
float AW_WaterFactLevel(long value) {
    unsigned int bits=(unsigned int)value;float f;
    memcpy(&f,&bits,4);
    return f;
}
