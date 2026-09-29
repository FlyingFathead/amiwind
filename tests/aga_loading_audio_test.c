/* SPDX-License-Identifier: GPL-2.0-or-later
 * Run the real mixer during a simulated blocking load and DMA ring wraps. */
#include "quakedef.h"
#include <assert.h>
extern int sound_started,paintedtime,total_channels;
extern cvar_t _snd_mixahead;
extern channel_t channels[];
client_static_t cls;client_state_t cl;
static double clock_now=1;
static int position,submits,refills,frames,late;
double Sys_FloatTime(void){return clock_now;}
int SNDDMA_GetDMAPos(void){return position;}
void SNDDMA_Submit(void){submits++;}
void CDAudio_Update(void){refills++;}
void AW_AudioLate(int n){late+=n;}
void AW_SpeechStop(int a,int b){}
void Q_memset(void *p,int value,int n){memset(p,value,n);}
int AW_MovieActive(void){return 0;}
void AW_MoviePaint(portable_samplepair_t *p,int n,int start){assert(0);}
void AW_MusicPaint(portable_samplepair_t *p,int n){int i;for(i=0;i<n;i++){p[i].left=321;p[i].right=-321;}frames+=n;}
sfxcache_t *S_LoadSound(sfx_t *s){assert(0);return NULL;}
void Con_Printf(char *fmt,...){}
int main(void){
 dma_t dma;byte buffer[65536];sfx_t sound;int i,was;
 memset(&dma,0,sizeof(dma));dma.channels=2;dma.samplebits=16;dma.samples=32768;dma.speed=11015;dma.buffer=buffer;
 shm=&dma;sound_started=1;volume.value=1;_snd_mixahead.value=.1;
 memset(buffer,0x57,sizeof(buffer));channels[0].sfx=&sound;total_channels=1;
 aw_loading_music=true;S_StopAllSounds(true);
 for(i=0;i<sizeof(buffer);i++)assert(buffer[i]==0x57);
 assert(!channels[0].sfx);
 /* A new map may already have precached static effects: loading never tries
  * to resolve their cache while model temporary storage is live. */
 channels[0].sfx=&sound;channels[0].leftvol=channels[0].rightvol=100;
 for(i=0;i<400;i++){
  clock_now+=.03;position=(i*330*2)&32767;S_LoadingUpdate();
  assert(((short *)buffer)[(position/2*2)&32767]==321);
  assert(((short *)buffer)[(position/2*2+1)&32767]==-321);
 }
 assert(refills==400 && submits==400 && frames>120000 && !late);
 was=paintedtime;S_LoadingUpdate();assert(paintedtime==was && submits==400);
 aw_loading_music=false;clock_now+=1;S_LoadingUpdate();assert(submits==400);
 S_StopAllSounds(true);for(i=0;i<sizeof(buffer);i++)assert(!buffer[i]);
 return 0;
}
