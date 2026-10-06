/* SPDX-License-Identifier: GPL-2.0-or-later
 * Real channel mixer and speech lifecycle; synthetic PCM only. */
#include "quakedef.h"
#include <assert.h>
#include <stdarg.h>
extern int sound_started,soundtime;
extern cvar_t _snd_mixahead;
extern void S_StopAllSoundsC(void);
client_static_t cls;client_state_t cl;entity_t cl_entities[MAX_EDICTS];
static dma_t dma;
static short dma_samples[8192],expected[8192];
static sfx_t samples[MAX_DYNAMIC_CHANNELS];
static int cache_reads,allocations,allocation_failure,refusals,movie_debug,movie_pending,dma_position,movie_paints;
static size_t allocated_bytes;
void *__real_malloc(size_t n);
void *__wrap_malloc(size_t n){
    allocations++;allocated_bytes+=n;
    if(allocation_failure)return NULL;
    return __real_malloc(n);
}
void *Cache_Check(cache_user_t *c){cache_reads++;return c->data;}
sfxcache_t *S_LoadSound(sfx_t *s){return Cache_Check(&s->cache);}
void Q_memset(void *p,int value,int n){memset(p,value,n);}
void Con_Printf(char *fmt,...){if(strstr(fmt,"not retained"))refusals++;}
int COM_FOpenFile(char *path,FILE **file){*file=NULL;return -1;}
int AW_MovieActive(void){return movie_debug;}
void AW_MoviePaint(portable_samplepair_t *p,int n,int start){int i;(void)start;movie_paints++;for(i=0;i<n;i++){p[i].left=1234;p[i].right=-1234;}}
int AW_MovieDebugActive(void){return movie_debug||movie_pending;}
int AW_MovieDebugPending(void){return movie_pending;}
int SNDDMA_GetDMAPos(void){return dma_position;}
void SNDDMA_Submit(void){}
void AW_AudioLate(int n){(void)n;}
void AW_MusicPaint(portable_samplepair_t *p,int n){
    int i;for(i=0;i<n;i++){p[i].left=17;p[i].right=-19;}
}
static void discard_sources(void){
    int i;for(i=0;i<MAX_DYNAMIC_CHANNELS;i++){
        free(samples[i].cache.data);memset(&samples[i],0,sizeof(samples[i]));
    }
}
static void reset(void){
    S_CancelSceneVoice();discard_sources();AW_SpeechStop(-1,-1);
    memset(channels,0,sizeof(channel_t)*MAX_CHANNELS);
    memset(dma_samples,0,sizeof(dma_samples));memset(&dma,0,sizeof(dma));
    dma.channels=2;dma.samplebits=16;dma.samples=8192;
    dma.speed=11025;dma.buffer=(byte *)dma_samples;shm=&dma;
    sound_started=1;soundtime=paintedtime=200;dma_position=400;volume.value=1;
    total_channels=NUM_AMBIENTS+MAX_DYNAMIC_CHANNELS;aw_loading_music=false;
    cache_reads=allocations=allocation_failure=refusals=0;allocated_bytes=0;
}
static channel_t *source(int id,int n,int width,const char *name,int pos){
    int i;sfxcache_t *sc;channel_t *ch=&channels[NUM_AMBIENTS+id];
    sc=(sfxcache_t *)__real_malloc(sizeof(*sc)+(size_t)n*width);assert(sc);
    memset(sc,0,sizeof(*sc));sc->length=n;sc->loopstart=-1;
    sc->width=width;sc->speed=dma.speed;strcpy(samples[id].name,name);samples[id].cache.data=sc;
    for(i=0;i<n;i++)if(width==1)((signed char *)sc->data)[i]=(i%64)-32;
        else ((short *)sc->data)[i]=((i%128)-64)*127;
    memset(ch,0,sizeof(*ch));ch->sfx=&samples[id];ch->pos=pos;
    ch->end=paintedtime+n-pos;ch->leftvol=128;ch->rightvol=64;
    ch->entnum=10+id;ch->entchannel=2;
    return ch;
}
static void continuity(int width){
    channel_t *ch;int before;
    reset();source(0,1300,width,"npc/test.wav",100);
    S_PaintChannels(1400);memcpy(expected,dma_samples,sizeof(expected));
    reset();ch=source(0,1300,width,"npc/test.wav",100);
    AW_SpeechStart(10,2,"npc/test.wav",paintedtime,1300,dma.speed,100);
    assert(AW_SpeechPose(10,3,21,"progs/np_test.mdl")==8);
    S_PaintChannels(600);S_BeginSceneVoice();
    assert(!ch->sfx && allocations==1 && AW_SpeechRemaining()>0);
    assert(AW_SpeechPose(10,3,21,"progs/np_test.mdl")==3);
    discard_sources();before=cache_reads;
    aw_loading_music=true;S_StopAllSounds(true);S_StopAllSounds(true);
    S_PaintChannels(1000);
    /* A second crossing carries the existing detached tail without duplicating. */
    S_BeginSceneVoice();assert(allocations==1);S_StopAllSounds(true);
    S_EndSceneVoice();aw_loading_music=false;S_PaintChannels(1400);
    assert(cache_reads==before && !memcmp(expected,dma_samples,sizeof(expected)));
    assert(AW_SpeechRemaining()>0); /* Queued samples are still audible. */
    soundtime=1400;assert(AW_SpeechRemaining()==0);
    S_PaintChannels(1500);assert(dma_samples[2800]==17 && dma_samples[2801]==-19);
}
static void cancellation(void){
    int i;reset();source(0,1000,1,"intro/test.wav",0);S_BeginSceneVoice();
    aw_loading_music=true;S_StopAllSoundsC();assert(!S_PreserveSceneVoice());
    S_PaintChannels(300);for(i=400;i<600;i+=2)assert(dma_samples[i]==17 && dma_samples[i+1]==-19);
    assert(AW_SpeechRemaining()==0);
    reset();source(0,1000,1,"npc/test.wav",0);S_BeginSceneVoice();
    S_EndSceneVoice();S_StopAllSounds(true);assert(AW_SpeechRemaining()==0);
    reset();source(0,1000,1,"npc/test.wav",0);S_BeginSceneVoice();
    S_CancelSceneVoice();assert(AW_SpeechRemaining()==0); /* Failed map/disconnect. */
}
static void limits(void){
    int i;channel_t *ch;sfxcache_t *sc;
    reset();ch=source(0,140000,1,"npc/long.wav",0);S_BeginSceneVoice();
    assert(ch->sfx && refusals==1 && allocations==0);
    reset();for(i=0;i<4;i++)source(i,32000,1,"npc/test.wav",0);
    S_BeginSceneVoice();assert(allocations==4 && allocated_bytes<=128*1024);
    source(4,1000,1,"npc/fifth.wav",0);S_BeginSceneVoice();
    assert(channels[NUM_AMBIENTS+4].sfx && allocations==4 && refusals==1);
    reset();source(0,110000,1,"intro/long.wav",0);source(1,30000,1,"npc/test.wav",0);
    S_BeginSceneVoice();assert(allocations==1 && refusals==1 && allocated_bytes<=128*1024);
    reset();ch=source(0,1000,1,"npc/test.wav",0);allocation_failure=1;
    S_BeginSceneVoice();assert(ch->sfx && refusals==1 && AW_SpeechRemaining()==0);
    reset();ch=source(0,1000,1,"npc/test.wav",0);sc=(sfxcache_t *)samples[0].cache.data;
    sc->loopstart=0;S_BeginSceneVoice();assert(ch->sfx && refusals==1 && allocations==0);
    sc->loopstart=-1;sc->stereo=1;S_BeginSceneVoice();assert(refusals==2 && allocations==0);
    sc->stereo=0;sc->speed++;S_BeginSceneVoice();assert(refusals==3 && allocations==0);
    reset();ch=source(0,1000,1,"npc/test.wav",0);discard_sources();strcpy(samples[0].name,"npc/test.wav");
    S_BeginSceneVoice();assert(ch->sfx && refusals==1 && allocations==0);
    reset();ch=source(0,1000,1,"env/test.wav",0);S_BeginSceneVoice();assert(ch->sfx && !allocations && !refusals);
}
static void movie_isolation(void){
    channel_t *npc,*ordinary;int i,before_cache,before_ordinary,remaining,resume_start,saved_left,saved_right;
    vec3_t saved_listener;
    short expected[200];
    reset();_snd_mixahead.value=0.05f;npc=source(0,1300,2,"npc/movie.wav",100);
    ordinary=source(1,700,2,"env/loop.wav",50);
    AW_SpeechStart(10,2,"npc/movie.wav",paintedtime,1300,dma.speed,100);
    AW_SpeechStart(99,7,"npc/ghost.wav",paintedtime,2200,dma.speed,0);
    S_PaintChannels(300);S_BeginSceneVoice();assert(!npc->sfx);S_PaintChannels(400);
    for(i=0;i<200;i++)expected[i]=dma_samples[((300&4095)*2+i)&8191];

    reset();_snd_mixahead.value=0.05f;npc=source(0,1300,2,"npc/movie.wav",100);
    ordinary=source(1,700,2,"env/loop.wav",50);
    AW_SpeechStart(10,2,"npc/movie.wav",paintedtime,1300,dma.speed,100);
    AW_SpeechStart(99,7,"npc/ghost.wav",paintedtime,2200,dma.speed,0);
    S_PaintChannels(300);S_BeginSceneVoice();assert(!npc->sfx);
    soundtime=paintedtime=300;dma_position=600;
    remaining=(int)(S_SceneVoiceRemaining()*dma.speed);assert(remaining>0);
    before_cache=cache_reads;before_ordinary=ordinary->pos;
    listener_origin[0]=77;listener_origin[1]=88;listener_origin[2]=99;
    VectorCopy(listener_origin,saved_listener);saved_left=ordinary->leftvol;saved_right=ordinary->rightvol;
    assert(AW_SpeechPose(99,3,21,"progs/np_test.mdl")==8);
    S_MovieAudioBegin();movie_debug=1;
    S_Update(vec3_origin,vec3_origin,vec3_origin,vec3_origin);
    assert(movie_paints>0 && cache_reads==before_cache && ordinary->pos==before_ordinary);
    assert(!memcmp(saved_listener,listener_origin,sizeof(saved_listener)) && ordinary->leftvol==saved_left && ordinary->rightvol==saved_right);
    for(i=400;i<=1300;i+=100){dma_position=i*2;S_Update(vec3_origin,vec3_origin,vec3_origin,vec3_origin);}
    assert(ordinary->pos==before_ordinary && cache_reads==before_cache);
    movie_debug=0;S_MovieAudioEnd();
    assert((int)(S_SceneVoiceRemaining()*dma.speed)==remaining);
    assert(AW_SpeechRemaining()>0 && AW_SpeechPose(99,3,21,"progs/np_test.mdl")==8);
    resume_start=paintedtime;S_PaintChannels(resume_start+100);
    assert(ordinary->pos==before_ordinary+100);
    for(i=0;i<200;i++)assert(dma_samples[((resume_start&4095)*2+i)&8191]==expected[i]);

    /* During queue drain, S_Update polls DMA but paints nothing or spatializes. */
    movie_pending=1;before_cache=cache_reads;before_ordinary=ordinary->pos;
    paintedtime=soundtime+100;dma_position=soundtime*2;resume_start=paintedtime;
    S_Update(vec3_origin,vec3_origin,vec3_origin,vec3_origin);
    assert(ordinary->pos==before_ordinary && cache_reads==before_cache && paintedtime==resume_start);
    assert(!memcmp(saved_listener,listener_origin,sizeof(saved_listener)) && ordinary->leftvol==saved_left && ordinary->rightvol==saved_right);
    movie_pending=0;S_CancelSceneVoice();discard_sources();
}
static void late_clock(void){
    int before;reset();source(0,1000,2,"npc/test.wav",0);S_PaintChannels(1200);
    memcpy(expected,dma_samples,sizeof(expected));
    reset();source(0,1000,2,"npc/test.wav",0);S_BeginSceneVoice();discard_sources();
    aw_loading_music=true;S_StopAllSounds(true);before=cache_reads;
    paintedtime=350;S_PaintChannels(1200);
    assert(!memcmp(expected+700,dma_samples+700,1700*sizeof(short)) && cache_reads==before);
    reset();source(0,1000,1,"npc/test.wav",0);S_BeginSceneVoice();aw_loading_music=true;S_StopAllSounds(true);
    paintedtime=1500;S_PaintChannels(1600);soundtime=1500;assert(AW_SpeechRemaining()==0);
}
int main(void){
    SND_InitScaletable();continuity(1);continuity(2);cancellation();limits();late_clock();movie_isolation();
    reset();discard_sources();S_CancelSceneVoice();return 0;
}
