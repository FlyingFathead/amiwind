/* SPDX-License-Identifier: GPL-2.0-or-later
 * Run the real mixer during a simulated blocking load and DMA ring wraps. */
#include "quakedef.h"
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
extern int sound_started,paintedtime,total_channels,snd_blocked;
static int movie;		/* the intro movie is playing (AW_MovieActive) */
static char report[512];	/* the last "Loading audio:" line */
extern cvar_t _snd_mixahead;
extern channel_t channels[];
client_static_t cls;client_state_t cl;
static double clock_now=1;
static int position,submits,refills,frames,late,loading_updates;
void SCR_LoadingUpdate(void){loading_updates++;}
double Sys_FloatTime(void){return clock_now;}
int SNDDMA_GetDMAPos(void){return position;}
void SNDDMA_Submit(void){submits++;}
void CDAudio_Update(void){refills++;}
void AW_AudioLate(int n){late+=n;}
void AW_SpeechStop(int a,int b){}
void Q_memset(void *p,int value,int n){memset(p,value,n);}
int AW_MovieActive(void){return movie;}
int AW_MovieDebugActive(void){return 0;}
int AW_MovieDebugPending(void){return 0;}
void AW_MoviePaint(portable_samplepair_t *p,int n,int start){assert(movie);}
void AW_MusicPaint(portable_samplepair_t *p,int n){int i;for(i=0;i<n;i++){p[i].left=321;p[i].right=-321;}frames+=n;}
unsigned long AW_MusicSilentSpans(void){return 0;}   /* the load meter's music dry count (snd_dma.c S_Update_) */
static int load_pumps;
void AW_MusicLoadPump(void){load_pumps++;}           /* the music reads go on during a load (AUDIO-LOAD-29) */
sfxcache_t *S_LoadSound(sfx_t *s){assert(0);return NULL;}
void Con_Printf(char *fmt,...){
 char line[512];va_list ap;
 va_start(ap,fmt);vsnprintf(line,sizeof(line),fmt,ap);va_end(ap);
 if(!strncmp(line,"Loading audio:",14))strcpy(report,line);
}
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
 assert(loading_updates==401);
 sound_started=0;S_LoadingUpdate();assert(loading_updates==402 && submits==400);sound_started=1;
 snd_blocked=1;S_LoadingUpdate();assert(loading_updates==403 && submits==400);snd_blocked=0;
 aw_loading_music=false;clock_now+=1;S_LoadingUpdate();assert(submits==400 && loading_updates==403);
 /* AUDIO-LOAD-29: the load meter leaves the intro movie out (the music is paused under it, the mixer plays the
  * movie's own sound): its 530 ms are no gap of the load's music, and the line says what it left out */
 {
  long gap=-1,left=-1;const char *at;
  int pumps;
  aw_loading_music=true;report[0]=0;S_LoadingBegin();
  load_pumps=0;
  for(i=0;i<5;i++){clock_now+=.03;S_LoadingUpdate();}
  assert(load_pumps==5);            /* the music's reads go on through the load, one pump per mixer update */
  pumps=load_pumps;
  movie=1;clock_now+=.03;S_LoadingUpdate();clock_now+=.5;S_LoadingUpdate();
  assert(load_pumps==pumps);        /* not under the movie: the music is paused there */
  movie=0;clock_now+=.03;S_LoadingUpdate();
  for(i=0;i<5;i++){clock_now+=.04;S_LoadingUpdate();}
  assert(load_pumps==pumps+6);
  S_LoadingReport();
  at=strstr(report,"longest gap ");assert(at && sscanf(at,"longest gap %ld ms",&gap)==1);
  assert(gap>=38 && gap<=41);
  at=strstr(report,"(intro movie, ");assert(at && sscanf(at,"(intro movie, %ld ms",&left)==1);
  assert(left>=525 && left<=535);
  /* without a movie the line names none */
  report[0]=0;S_LoadingBegin();
  for(i=0;i<5;i++){clock_now+=.03;S_LoadingUpdate();}
  S_LoadingReport();assert(report[0] && !strstr(report,"intro movie"));
  aw_loading_music=false;
 }
 S_StopAllSounds(true);for(i=0;i<sizeof(buffer);i++)assert(!buffer[i]);
 return 0;
}
