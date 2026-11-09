/* SPDX-License-Identifier: GPL-2.0-or-later
 * The saved block of a script's ForceSneak and screen fade (aw_forced_rules.h). */
#include <string.h>
#include "aw_forced_rules.h"

int AW_ForcedPack(unsigned char *out,int capacity,int player,const uint32_t *refs,int count,float fade){
    int i,k;unsigned char *p;unsigned int v;
    if(count<0 || count>255 || 11+4*count>capacity)return -1;
    memcpy(out,"AWFS",4);out[4]=1;out[5]=(unsigned char)(player!=0);out[6]=(unsigned char)count;p=out+7;
    for(i=0;i<count;i++)for(k=3;k>=0;k--)*p++=(unsigned char)(refs[i]>>(8*k));
    memcpy(&v,&fade,4);
    for(k=3;k>=0;k--)*p++=(unsigned char)(v>>(8*k));
    return 11+4*count;
}
int AW_ForcedUnpack(const unsigned char *p,int bytes,int *player,uint32_t *refs,int max,int *count,float *fade){
    int i,k,n;unsigned int v=0;float f;
    if(bytes<11 || memcmp(p,"AWFS",4) || p[4]!=1 || (n=p[6])>max || bytes<11+4*n)return -1;
    for(k=0;k<4;k++)v=(v<<8)|p[7+4*n+k];
    memcpy(&f,&v,4);
    if(!(f>=0 && f<=1))return -1;
    for(i=0;i<n;i++){
        uint32_t r=0;
        for(k=0;k<4;k++)r=(r<<8)|p[7+4*i+k];
        refs[i]=r;
    }
    *player=p[5]!=0;*count=n;*fade=f;
    return 11+4*n;
}
