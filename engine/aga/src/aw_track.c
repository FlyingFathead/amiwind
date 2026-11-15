/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Object tracks: the reader and sampler of the 'AWTK' records (aw_track.h, tools/object_movers.py). */
#include <math.h>
#include <string.h>
#include "aw_track.h"

static unsigned u16(const unsigned char *p) {return (unsigned)p[0]<<8|p[1];}
static int s16(const unsigned char *p) {int v=(int)u16(p);return v>=32768?v-65536:v;}
static float f32(const unsigned char *p) {
    unsigned long v=(unsigned long)p[0]<<24|(unsigned long)p[1]<<16|(unsigned long)p[2]<<8|p[3];float f;
    unsigned int w=(unsigned int)v;
    memcpy(&f,&w,4);
    return f;
}

int AW_TrackParse(const unsigned char *data,int bytes,aw_track_t *t) {
    long need;
    memset(t,0,sizeof(*t));
    if(!data || bytes<AW_TRACK_HEAD || memcmp(data,AW_TRACK_MAGIC,4) || u16(data+4)!=AW_TRACK_VERSION)return 0;
    t->movers=(int)u16(data+6);t->frames=(int)u16(data+8);t->rate=(float)u16(data+10)/16.f;t->unit=f32(data+12);
    t->sounds=(int)u16(data+16);
    if(t->movers<1 || t->movers>AW_TRACK_MAX_MOVERS || t->frames<2 || !(t->rate>0) || !(t->unit>0))return 0;
    t->names_at=AW_TRACK_HEAD;
    t->sounds_at=t->names_at+t->movers*AW_TRACK_MOVER;
    t->frames_at=t->sounds_at+t->sounds*AW_TRACK_SOUND;
    need=(long)t->frames_at+(long)t->movers*t->frames*AW_TRACK_FRAME;
    if(need!=bytes)return 0;
    t->data=data;t->bytes=bytes;
    return 1;
}

float AW_TrackSeconds(const aw_track_t *t) {return t && t->data?(float)(t->frames-1)/t->rate:0.f;}

int AW_TrackMover(const aw_track_t *t,int m,char *name,int size) {
    const unsigned char *p;int k;
    if(!t || !t->data || m<0 || m>=t->movers)return -1;
    p=t->data+t->names_at+m*AW_TRACK_MOVER;
    if(name && size>0){
        for(k=0;k<size-1 && k<AW_TRACK_NAME-1 && p[4+k];k++)name[k]=(char)p[4+k];
        name[k]=0;
    }
    return (int)u16(p);
}

static void frame_of(const aw_track_t *t,int m,int f,float pos[3],float q[4]) {
    const unsigned char *p=t->data+t->frames_at+((long)m*t->frames+f)*AW_TRACK_FRAME;int k;
    for(k=0;k<3;k++)pos[k]=(float)s16(p+2*k)*t->unit;
    for(k=0;k<4;k++)q[k]=(float)s16(p+6+2*k)/32767.f;
}

int AW_TrackSample(const aw_track_t *t,int m,float seconds,float pos[3],float quat[4]) {
    float at,u,p0[3],p1[3],q0[4],q1[4],dot=0,len=0;int f,k;
    if(!t || !t->data || m<0 || m>=t->movers)return 0;
    at=seconds*t->rate;
    if(!(at>0))at=0;                         /* before the start (and NaN): the first frame */
    if(at>=(float)(t->frames-1)){frame_of(t,m,t->frames-1,pos,quat);return 1;}
    f=(int)at;u=at-(float)f;
    frame_of(t,m,f,p0,q0);frame_of(t,m,f+1,p1,q1);
    for(k=0;k<4;k++)dot+=q0[k]*q1[k];
    if(dot<0)for(k=0;k<4;k++)q1[k]=-q1[k];   /* the shorter arc */
    for(k=0;k<3;k++)pos[k]=p0[k]+(p1[k]-p0[k])*u;
    for(k=0;k<4;k++){quat[k]=q0[k]+(q1[k]-q0[k])*u;len+=quat[k]*quat[k];}
    len=(float)sqrt(len);
    if(len>0)for(k=0;k<4;k++)quat[k]/=len;
    return 1;
}

int AW_TrackSoundsBetween(const aw_track_t *t,float from,float to,char (*out)[AW_TRACK_SOUND_NAME],int max) {
    int i,n=0,k;
    if(!t || !t->data)return 0;
    for(i=0;i<t->sounds && n<max;i++){
        const unsigned char *p=t->data+t->sounds_at+i*AW_TRACK_SOUND;
        float s=(float)u16(p)/t->rate;
        if(!(s<=to) || (from>=0 && !(s>from)))continue;
        for(k=0;k<AW_TRACK_SOUND_NAME-1 && p[2+k];k++)out[n][k]=(char)p[2+k];
        out[n][k]=0;n++;
    }
    return n;
}

void AW_TrackMatrix(const float q[4],float m[3][3]) {
    float w=q[0],x=q[1],y=q[2],z=q[3];
    /* the column-form rotation R, written transposed (row vectors: p' = p * R^T) */
    float r[3][3];int i,j;
    r[0][0]=1-2*(y*y+z*z);r[0][1]=2*(x*y-w*z);r[0][2]=2*(x*z+w*y);
    r[1][0]=2*(x*y+w*z);r[1][1]=1-2*(x*x+z*z);r[1][2]=2*(y*z-w*x);
    r[2][0]=2*(x*z-w*y);r[2][1]=2*(y*z+w*x);r[2][2]=1-2*(x*x+y*y);
    for(i=0;i<3;i++)for(j=0;j<3;j++)m[i][j]=r[j][i];
}
