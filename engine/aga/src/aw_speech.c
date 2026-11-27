/* SPDX-License-Identifier: GPL-2.0-or-later
 * Speech poses follow the audio playback clock, not the rendering clock.
 * Four bounded tracks; original morph poses and envelopes are external data.
 * NPC-TALK-MOUTH-STILL-69: a voice line without an envelope beside it (the media pool's shared voice files: a script's
 * Say, the voice table's greetings, idle, combat and dialogue lines) gets one from its own loaded samples, by the same
 * rule the builder writes the .lip files with (tools/npc_faces.py envelope), when its speaker's model carries the talk
 * poses. The original's rule (OpenMW 0.53 apps/openmw/mwrender/npcanimation.cpp 162-195 HeadAnimationTime::update:
 * while the actor says anything, sayActive, the head's talk morph follows the loudness of the line playing,
 * SoundManager::getSaySoundLoudness, soundmanagerimp.cpp 381-391; the loudness is the RMS of each window of the voice's
 * samples, mwsound/loudness.cpp 11-66, 20 windows a second, openaloutput.cpp 38 and 517): every voice line of any
 * route, in the world as in a conversation, for every speaking NPC. aw_speech_envelope 0 keeps the previous method
 * (only a baked .lip beside an npc/ or intro/ sound), for an A/B.
 */
#include "quakedef.h"
extern int soundtime;
/* NPC-TALK-MOUTH-STILL-69: declared here, used through local declarations in snd_dma.c and aw_debug.c (quakedef.h is
 * read by builder checks whose stage keys must not move for an engine-only change) */
int AW_SpeechEnvelope(const void *pcm,int width,int length,int speed,byte *levels,int capacity);
void AW_SpeechStartPcm(int entity,int channel,const char *sound,int start,int length,int speed,int skip,
                       const void *pcm,int width);
int AW_SpeechTrack(int k,int *entity,int *channel,const char **sound,int *source,int *count,int *index,int *level);
void AW_SpeechCounts(unsigned long *baked,unsigned long *computed,unsigned long *bins,double *ms_last,double *ms_max);
int AW_SpeechLevel(int entity,int *head);
#define AW_SPEECH_BINS 3000                 /* 120 s at 25 a second, the .lip files' own limit (AW_SpeechValidate) */
#define AW_SPEECH_VOICE_CHANNEL 2           /* the voice channel: aw_anim.c AW_VoicePlay, aw_mwhost.c host_say */
/* head: the speaker's head in the talk pack when its model is skeletal (aw_talkpack.c), -1 otherwise */
typedef struct {int entity,channel,start,end,speed,count,source,head;char sound[64];byte levels[AW_SPEECH_BINS];} aw_voice_t;
/* aw_talkpack.c AW_TalkTalker (set in aw_debug.c; NULL in fixtures): 1 and the head when the entity is an NPC with a
 * skeletal model whose head has the Talk morph (NPC-TALK-MOUTH-STILL-69) */
int (*aw_speech_talker)(int entity,int *head);
static aw_voice_t voices[4];
static int latest=-1;
/* 1 (the default): a voice line without a .lip gets an envelope from its samples; 0: the baked .lip files only */
cvar_t aw_speech_envelope={"aw_speech_envelope","1",false,false,1};   /* registered in aw_debug.c, not saved */
static unsigned long envelopes_baked,envelopes_computed,envelope_bins;
/* the time an envelope from samples took (the budget sheet's CPU line, dbg speech): aw_debug.c sets the clock
 * (Sys_FloatTime), NULL in fixtures */
double (*aw_speech_clock)(void);
static double envelope_ms_last,envelope_ms_max;
/* the integer square root (the largest r with r*r <= x), bit by bit */
static unsigned long isqrt(unsigned long x){
    unsigned long r=0,bit=1UL<<30;
    while(bit>x)bit>>=2;
    while(bit){if(x>=r+bit){x-=r+bit;r=(r>>1)+bit;}else r>>=1;bit>>=2;}
    return r;
}
static unsigned get16(const byte *p){return p[0]+(p[1]<<8);}
static unsigned get32(const byte *p){return get16(p)+(get16(p+2)<<16);}
/* The 21-frame actor's talk poses (idle 0..7, talk 8..11, blink 12, walk 13..20; tools/actor_frames.py ACTOR_GROUPS):
 * an np_ model only, never an unrelated alias or a legacy actor. */
static int talk_model(int frames,const char *model){return frames==21 && model && !strncmp(model,"progs/np_",9);}
static int talker(int entity){
    const entity_t *e;
    if(entity<=0 || entity>=MAX_EDICTS)return 0;
    e=&cl_entities[entity];
    return e->model && talk_model(e->model->numframes,e->model->name);
}
int AW_SpeechValidate(const byte *p,int n) {
    unsigned count,samples;int i;
    if(n<13 || memcmp(p,"AWL1",4) || get16(p+4)!=25)return 0;
    count=get16(p+6);samples=get32(p+8);
    if(!count || count>3000 || n!=12+(int)count || !samples || samples>1323000 ||
       count!=(samples*25+11024)/11025)return 0;
    for(i=12;i<n;i++)if(p[i]>3)return 0;
    return 1;
}
/* NPC-TALK-MOUTH-STILL-69: the four mouth levels at 25 a second of PCM (LENGTH samples at SPEED, WIDTH 1: signed 8-bit,
 * 2: 16-bit, as S_LoadSound keeps them), the builder's rule in integers (tools/npc_faces.py envelope): each bin's RMS
 * (at most 128 samples of it read, evenly spaced), the 95th percentile of the bins as the peak (at least 4 of 128),
 * level = ceil(3 RMS / peak) up to 3, and 0 below max(1.5, 0.08 peak). Returns the bins written (at most CAPACITY), 0
 * when there is nothing to read. */
int AW_SpeechEnvelope(const void *pcm,int width,int length,int speed,byte *levels,int capacity) {
    static unsigned short square[256],rms[AW_SPEECH_BINS],histogram[2048/4+1];static int ready;
    int bins,i,k,step,n,rank,seen,peak,floor_;unsigned long sum,a,b;
    if(!pcm || (width!=1 && width!=2) || length<=0 || speed<=0 || !levels || capacity<=0)return 0;
    if(!ready){for(i=0;i<256;i++)square[i]=(unsigned short)((i-128)*(i-128));ready=1;}
    bins=(int)(((unsigned long)length*25+(unsigned long)speed-1)/(unsigned long)speed);
    if(bins>capacity)bins=capacity;
    if(bins>AW_SPEECH_BINS)bins=AW_SPEECH_BINS;
    memset(histogram,0,sizeof(histogram));
    for(i=0;i<bins;i++){
        a=(unsigned long)i*(unsigned long)speed/25;b=(unsigned long)(i+1)*(unsigned long)speed/25;
        if(b>(unsigned long)length)b=(unsigned long)length;
        step=b-a>128?(int)((b-a+127)/128):1;sum=0;n=0;
        if(width==1){const signed char *p=(const signed char *)pcm;
            for(k=(int)a;k<(int)b;k+=step){sum+=square[(unsigned char)(p[k]+128)];n++;}}
        else{const short *p=(const short *)pcm;
            for(k=(int)a;k<(int)b;k+=step){sum+=square[((p[k]>>8)+128)&255];n++;}}
        /* RMS in sixteenths (0..2048): the root of the mean square times 256 (at most 128 x 16384 x 256 < 2^32) */
        rms[i]=n?(unsigned short)isqrt(sum*256/(unsigned long)n):0;
        histogram[rms[i]>>2]++;
    }
    if(bins<=0)return 0;
    /* the 95th percentile (numpy's index 0.95 (n-1), the lower neighbour) from the histogram, in sixteenths */
    rank=(int)((95L*(bins-1))/100);seen=0;peak=0;
    for(i=0;i<(int)(sizeof(histogram)/sizeof(histogram[0]));i++){seen+=histogram[i];if(seen>rank){peak=i*4+2;break;}}
    if(peak<4*16)peak=4*16;
    floor_=peak*8/100;if(floor_<24)floor_=24;
    for(i=0;i<bins;i++){
        int level=rms[i]<floor_?0:(int)((3L*rms[i]+peak-1)/peak);
        levels[i]=(byte)(level>3?3:level);
    }
    envelope_bins+=bins;
    return bins;
}
void AW_SpeechStop(int entity,int channel) {
    int i;for(i=0;i<4;i++)if(entity<0 || (voices[i].entity==entity && (channel<0 || voices[i].channel==channel)))voices[i].end=0;
}
/* A sound starts on ENTITY's CHANNEL (snd_dma.c S_StartSound): its track. PCM / WIDTH: the sound's loaded samples
 * (NULL: none to read), for a line without an envelope beside it (NPC-TALK-MOUTH-STILL-69). */
void AW_SpeechStartPcm(int entity,int channel,const char *sound,int start,int length,int speed,int skip,
                       const void *pcm,int width) {
    FILE *f;byte data[3013];int n,i,slot=0,baked,computed,head=-1;char path[128];aw_voice_t *v;
    /* entity -1 (a sound of no entity: Quake's temporary-entity sounds, cl_tent.c) never speaks; AW_SpeechStop(-1)
     * means "every voice" (S_StopAllSounds), so it must not be passed on here (SPEECH-STOP-ALL-ON-MINUS1-54) */
    if(entity<0)return;
    AW_SpeechStop(entity,channel);
    if(!sound || strlen(sound)>100 || strstr(sound,"..") || length<=0 || speed<=0)return;
    /* the opening's lines and the town actors' own voices: an envelope beside the sound (sound/<name>.lip) */
    baked=!strncmp(sound,"npc/",4) || !strncmp(sound,"intro/",6);
    /* NPC-TALK-MOUTH-STILL-69: any other voice line on the voice channel of a speaker with the talk poses: the opening's
     * 21-frame actors, or an NPC with a skeletal model whose head has the Talk morph (aw_talkpack.c) */
    computed=aw_speech_envelope.value!=0 && pcm && channel==AW_SPEECH_VOICE_CHANNEL &&
             (talker(entity) || (aw_speech_talker && aw_speech_talker(entity,&head)));
    if(!baked && !computed)return;
    for(i=0;i<4;i++)if(voices[i].end<=soundtime){slot=i;break;}else if(voices[i].end<voices[slot].end)slot=i;
    v=&voices[slot];memset(v,0,sizeof(*v));
    v->entity=entity;v->channel=channel;v->start=start-skip;v->end=start+length-skip;v->speed=speed;v->head=head;
    strncpy(v->sound,sound,sizeof(v->sound)-1);
    if(baked){
        sprintf(path,"sound/%s",sound);strcpy(path+strlen(path)-4,".lip");
        f=NULL;n=COM_FOpenFile(path,&f);
        if(f){
            if(n>=13 && n<=3012 && fread(data,1,n,f)==(size_t)n && AW_SpeechValidate(data,n)) {
                v->count=get16(data+6);memcpy(v->levels,data+12,v->count);v->source=1;envelopes_baked++;
            }
            fclose(f);
        }
    }
    if(!v->count && computed){
        double t0=aw_speech_clock?aw_speech_clock():0;
        if((v->count=AW_SpeechEnvelope(pcm,width,length,speed,v->levels,AW_SPEECH_BINS))>0){v->source=2;envelopes_computed++;}
        if(aw_speech_clock){
            envelope_ms_last=(aw_speech_clock()-t0)*1000.0;
            if(envelope_ms_last>envelope_ms_max)envelope_ms_max=envelope_ms_last;
        }
    }
    /* the opening's pacing (AW_SpeechRemaining) follows its own lines as before: the npc/ and intro/ sounds */
    if(baked)latest=slot;
    else if(latest==slot)latest=-1;
}
void AW_SpeechStart(int entity,int channel,const char *sound,int start,int length,int speed,int skip) {
    AW_SpeechStartPcm(entity,channel,sound,start,length,speed,skip,NULL,0);
}
void AW_SpeechShiftTiming(int elapsed,int start_time) {
    int i;if(elapsed<=0)return;
    for(i=0;i<4;i++)if(voices[i].end>start_time){voices[i].start+=elapsed;voices[i].end+=elapsed;}
}
double AW_SpeechRemaining(void) {
    aw_voice_t *v;double remaining=S_SceneVoiceRemaining(),live;
    if(latest<0)return remaining;
    v=&voices[latest];
    live=v->end>soundtime && v->speed>0?(double)(v->end-soundtime)/v->speed:0;
    return live>remaining?live:remaining;
}
int AW_SpeechPose(int entity,int current,int frames,const char *model) {
    int i,index,phase;aw_voice_t *v;
    /* Explicit converter ABI. Never animate unrelated aliases or legacy actors. */
    if(!talk_model(frames,model))return current;
    for(i=0;i<4;i++) {
        v=&voices[i];if(v->entity!=entity || v->end<=soundtime)continue;
        if(soundtime<v->start)return 8;
        index=(int)((double)(soundtime-v->start)*25/v->speed);
        if(v->count && index>=0 && index<v->count)return 8+v->levels[index];
        return 8; /* Missing/corrupt timing closes the mouth, never fakes speech. */
    }
    phase=((int)(cl.time*100)+entity*83)%457;
    if(current<8 && phase>=440)return 12;
    return current;
}
/* NPC-TALK-MOUTH-STILL-69: a speaking skeletal NPC's mouth level now (aw_talkpack.c, the renderer): 0..3 and its HEAD
 * in the talk pack while a line plays, -1 when it says nothing (the shut mouth before a line's first bin, and a line
 * without timing, give 0, as the 21-frame actors' AW_SpeechPose gives its shut talk frame) */
int AW_SpeechLevel(int entity,int *head) {
    int i,index;aw_voice_t *v;
    for(i=0;i<4;i++){
        v=&voices[i];if(v->entity!=entity || v->end<=soundtime || v->head<0)continue;
        *head=v->head;
        if(soundtime<v->start || v->speed<=0)return 0;
        index=(int)((double)(soundtime-v->start)*25/v->speed);
        return v->count && index>=0 && index<v->count?v->levels[index]:0;
    }
    return -1;
}
void AW_SpeechRelink(void) {
    int i;entity_t *e;
    for(i=1;i<cl.num_entities;i++) {
        e=&cl_entities[i];if(!e->model)continue;
        e->frame=AW_SpeechPose(i,e->frame,e->model->numframes,e->model->name);
    }
}
/* aw_speech_status (aw_debug.c, dbg speech): track K of 4 while it plays: 1 and its fields (SOURCE 0 no envelope, 1 the
 * baked .lip, 2 from its samples; INDEX the bin now, LEVEL its mouth level); 0 when the track is silent. */
int AW_SpeechTrack(int k,int *entity,int *channel,const char **sound,int *source,int *count,int *index,int *level) {
    aw_voice_t *v;
    if(k<0 || k>=4)return 0;
    v=&voices[k];
    if(v->end<=soundtime || v->speed<=0)return 0;
    *entity=v->entity;*channel=v->channel;*sound=v->sound;*source=v->source;*count=v->count;
    *index=soundtime<v->start?-1:(int)((double)(soundtime-v->start)*25/v->speed);
    *level=v->count && *index>=0 && *index<v->count?v->levels[*index]:0;
    return 1;
}
void AW_SpeechCounts(unsigned long *baked,unsigned long *computed,unsigned long *bins,double *ms_last,double *ms_max) {
    *baked=envelopes_baked;*computed=envelopes_computed;*bins=envelope_bins;*ms_last=envelope_ms_last;*ms_max=envelope_ms_max;
}
