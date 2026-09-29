/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
client_state_t cl;
static int interior=1;
static sfxcache_t sample;
int AW_Interior(void){return interior;}
sfxcache_t *S_LoadSound(sfx_t *s){return &sample;}
void Con_Printf(char *fmt,...){}
void AW_SpeechStart(int a,int b,const char *c,int d,int e,int f,int g){}
void AW_SpeechStop(int a,int b){}
extern int sound_started;
extern volatile dma_t *shm;
int main(void){
    sfx_t hull,other;vec3_t position={0,0,0};dma_t dma;
    int i,first=NUM_AMBIENTS+MAX_DYNAMIC_CHANNELS;
    sfxcache_t original;
    memset(&hull,0,sizeof(hull));memset(&other,0,sizeof(other));
    memset(&dma,0,sizeof(dma));dma.channels=2;dma.speed=11025;shm=&dma;
    strcpy(hull.name,"env/boat_hull.wav");strcpy(other.name,"env/other.wav");
    sample.length=11025;sample.loopstart=0;sample.speed=11025;
    sample.width=1;sample.data[0]=73;original=sample;
    cl.viewentity=1;total_channels=first;
    /* Both placed hull instances retain authored gain before spatialization. */
    for(i=0;i<2;i++)S_StaticSound(&hull,position,102,128);
    for(i=first;i<first+2;i++){
        assert(channels[i].master_vol==102);
        assert(channels[i].leftvol==102 && channels[i].rightvol==102);
        assert(channels[i].sfx==&hull);
    }
    S_StaticSound(&other,position,102,128);
    assert(channels[first+2].master_vol==102);
    /* The same cached sample outside prison retains its ordinary gain. */
    interior=0;S_StaticSound(&hull,position,102,128);
    assert(channels[first+3].master_vol==102);
    interior=1;S_StaticSound(&hull,position,102,128);
    assert(channels[first+4].master_vol==102);
    /* Dynamic use (including dialogue) bypasses the static emitter path. */
    sound_started=1;S_StartSound(1,2,&hull,position,.4f,0);
    assert(channels[NUM_AMBIENTS].master_vol==102);
    assert(channels[NUM_AMBIENTS].leftvol==102);
    S_StartSound(1,3,&other,position,.9f,0);
    assert(channels[NUM_AMBIENTS+1].master_vol==229);
    assert(!memcmp(&sample,&original,sizeof(sample)));
    return 0;
}
