/* SPDX-License-Identifier: GPL-2.0-or-later
 * snd_dma.c S_FindName past MAX_SFX names (AUDIO-SFX-NAME-TABLE-FULL-58): the name table is never emptied in a
 * session, so a slot whose cached data was freed and that nothing plays or holds is given to the new name; slots a
 * channel plays, a level precache names, a holder keeps (S_KeepSound) or whose data is still cached stay. */
#include "quakedef.h"
#include <assert.h>
client_state_t cl;
static sfxcache_t sample;
static int printed;
int AW_Interior(void){return 0;}
sfxcache_t *S_LoadSound(sfx_t *s){(void)s;return &sample;}
void Con_Printf(char *fmt,...){(void)fmt;printed++;}
void AW_SpeechStart(int a,int b,const char *c,int d,int e,int f,int g){}
static int stopped_all;   /* AW_SpeechStop(-1): every voice (only S_StopAllSounds may) */
void AW_SpeechStop(int a,int b){(void)b;if(a<0)stopped_all++;}
void *Cache_Check(cache_user_t *c){return c->data;}
int Q_strlen(char *s){return (int)strlen(s);}
int Q_strcmp(char *a,char *b){return strcmp(a,b);}
sfx_t *S_FindName(char *name);
extern sfx_t *known_sfx;
extern int num_sfx;
int main(void){
    static sfx_t table[512];static char held;char name[MAX_QPATH];int i;sfx_t *s,*first;
    known_sfx=table;num_sfx=0;total_channels=NUM_AMBIENTS+MAX_DYNAMIC_CHANNELS;
    /* 512 different names fill the table; each one's data is "cached" while it plays, then freed */
    for(i=0;i<512;i++){sprintf(name,"vo/n%03d.wav",i);s=S_FindName(name);assert(s && s==&table[i]);}
    assert(num_sfx==512);
    table[0].cache.data=&held;                       /* still cached */
    channels[NUM_AMBIENTS].sfx=&table[1];            /* still playing */
    cl.sound_precache[1]=&table[2];                  /* the level's precache names it */
    S_KeepSound(&table[3]);                          /* a long-lived holder keeps it */
    /* the 513th name takes the oldest free slot (4), and the same name is found again there */
    first=S_FindName("vo/new513.wav");
    assert(first==&table[4] && !strcmp(first->name,"vo/new513.wav") && !first->keep && !first->cache.data);
    assert(S_FindName("vo/new513.wav")==first);
    assert(!strcmp(table[0].name,"vo/n000.wav") && !strcmp(table[1].name,"vo/n001.wav"));
    assert(!strcmp(table[2].name,"vo/n002.wav") && !strcmp(table[3].name,"vo/n003.wav"));
    /* many more different names than the table holds: the newest is always found, nothing printed */
    for(i=0;i<2000;i++){sprintf(name,"vo/more%04d.wav",i);s=S_FindName(name);assert(s && !strcmp(s->name,name));
        assert(s!=&table[0] && s!=&table[1] && s!=&table[2] && s!=&table[3]);}
    assert(!printed);
    /* nothing free at all: refused with one console line, never a stop */
    for(i=0;i<512;i++)table[i].keep=1;
    assert(!S_FindName("vo/none.wav") && printed==1);
    /* AUDIO-LOCAL-SOUND-CUTS-58: one blow's three local sounds all play side by side; a fourth S_LocalSound
       (entity channel -1) still replaces one of the view entity's sounds, as Quake's menus expect */
    {extern int sound_started;extern volatile dma_t *shm;static dma_t dma;int playing=0;
     for(i=0;i<512;i++)table[i].keep=0;
     memset(channels,0,sizeof(channels));dma.channels=2;dma.speed=11025;shm=&dma;sound_started=1;cl.viewentity=1;
     sample.length=11025;sample.speed=11025;sample.width=1;
     S_LocalSoundBeside("fx/swish.wav");S_LocalSoundBeside("fx/armor.wav");S_LocalSoundBeside("fx/health.wav");
     for(i=NUM_AMBIENTS;i<NUM_AMBIENTS+MAX_DYNAMIC_CHANNELS;i++)if(channels[i].sfx)playing++;
     assert(playing==3);
     S_LocalSound("misc/menu1.wav");playing=0;
     for(i=NUM_AMBIENTS;i<NUM_AMBIENTS+MAX_DYNAMIC_CHANNELS;i++)if(channels[i].sfx)playing++;
     assert(playing==3);
     /* AUDIO-MAGIC-STOPS-SPEECH-54: a sound of no entity (-1: temporary entities, spells) never ends the voices */
     {vec3_t at={0,0,0};sfx_t *s=S_FindName("fx/magic.wav");int k;
      for(k=0;k<MAX_DYNAMIC_CHANNELS+2;k++)S_StartSound(-1,0,s,at,1,1);
      S_StopSound(-1,0);assert(!stopped_all);}}
    printf("sfx names ok\n");
    return 0;
}
