/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
int soundtime;client_state_t cl;entity_t cl_entities[MAX_EDICTS];
double S_SceneVoiceRemaining(void){return 0;}
static byte timing[37];static int available=1;
int COM_FOpenFile(char *s,FILE **f){
    if(!available){*f=NULL;return -1;}*f=tmpfile();assert(*f);fwrite(timing,1,sizeof(timing),*f);rewind(*f);return sizeof(timing);
}
extern cvar_t aw_speech_envelope;
void AW_SpeechStartPcm(int,int,const char *,int,int,int,int,const void *,int);
int AW_SpeechEnvelope(const void *,int,int,int,byte *,int);
int AW_SpeechTrack(int,int *,int *,const char **,int *,int *,int *,int *);
static int tracks_of(int entity){
    int k,n=0,e,c,s,count,index,level;const char *sound;
    for(k=0;k<4;k++)if(AW_SpeechTrack(k,&e,&c,&sound,&s,&count,&index,&level) && e==entity)n++;
    return n;
}
static int source_of(int entity){
    int k,e,c,s,count,index,level;const char *sound;
    for(k=0;k<4;k++)if(AW_SpeechTrack(k,&e,&c,&sound,&s,&count,&index,&level) && e==entity)return s;
    return -1;
}
/* 2 s at 11025: 0.4 s each of silence, a quiet line (RMS 20 of 128), a loud one (RMS 100), silence, loud again */
static signed char pcm8[22050];static short pcm16[22050];
static int at_bin(int start,int bin){return start+bin*441+220;}
/* NPC-TALK-MOUTH-STILL-69: a voice line from the media pool (a script's Say, the voice table's lines) on the voice
 * channel of a speaker with the talk poses moves the mouth by its own samples; before, such a line had no track at
 * all and the mouth stayed shut (49449ba84 moved the census clerk's lines onto this route). */
static void pool_voice(void){
    static model_t talk,plain;int i,start;byte levels[64];
    for(i=0;i<22050;i++){int seg=i/4410,amp=seg==1?20:(seg==2 || seg==4)?100:0;
        pcm8[i]=(signed char)(i%2?amp:-amp);pcm16[i]=(short)(pcm8[i]*256);}
    /* the builder's rule (tools/npc_faces.py envelope): peak = the 95th percentile (100), ceil(3 RMS / peak) */
    assert(AW_SpeechEnvelope(pcm8,1,22050,11025,levels,64)==50);
    for(i=0;i<50;i++)assert(levels[i]==(byte)(i<10 || (i>=30 && i<40)?0:i<20?1:3));
    assert(AW_SpeechEnvelope(pcm16,2,22050,11025,levels,64)==50 && levels[15]==1 && levels[25]==3 && levels[45]==3);
    assert(AW_SpeechEnvelope(pcm8,1,22050,11025,levels,20)==20);          /* never past the capacity */
    assert(!AW_SpeechEnvelope(pcm8,1,0,11025,levels,64) && !AW_SpeechEnvelope(NULL,1,100,11025,levels,64));
    strcpy(talk.name,"progs/np_census.mdl");talk.numframes=21;
    strcpy(plain.name,"progs/n_1a41f3de029c64d2.mdl");plain.numframes=1;   /* a skeletal resident: no talk poses */
    cl_entities[7].model=&talk;cl_entities[8].model=&plain;
    aw_speech_envelope.value=1;AW_SpeechStop(-1,-1);
    start=soundtime=50000;
    AW_SpeechStartPcm(7,2,"pool/a0123456789abcdef.wav",start,22050,11025,0,pcm8,1);
    assert(tracks_of(7)==1 && source_of(7)==2);
    soundtime=at_bin(start,5);assert(AW_SpeechPose(7,0,21,"progs/np_census.mdl")==8);
    soundtime=at_bin(start,15);assert(AW_SpeechPose(7,0,21,"progs/np_census.mdl")==9);
    soundtime=at_bin(start,25);assert(AW_SpeechPose(7,0,21,"progs/np_census.mdl")==11);
    soundtime=at_bin(start,35);assert(AW_SpeechPose(7,0,21,"progs/np_census.mdl")==8);
    soundtime=at_bin(start,45);assert(AW_SpeechPose(7,0,21,"progs/np_census.mdl")==11);
    /* the opening's pacing follows its own lines only: a pool line does not hold its next step */
    assert(AW_SpeechRemaining()==0);
    /* a model without the talk poses, or a sound off the voice channel: no track */
    AW_SpeechStartPcm(8,2,"pool/a0123456789abcdef.wav",soundtime,22050,11025,0,pcm8,1);assert(!tracks_of(8));
    AW_SpeechStartPcm(9,2,"pool/a0123456789abcdef.wav",soundtime,22050,11025,0,pcm8,1);assert(!tracks_of(9));
    AW_SpeechStartPcm(7,5,"pool/a0123456789abcdef.wav",soundtime,22050,11025,0,pcm8,1);assert(tracks_of(7)==1);
    /* aw_speech_envelope 0: the previous method, the mouth shut on a pool line */
    aw_speech_envelope.value=0;start=soundtime;
    AW_SpeechStartPcm(7,2,"pool/a0123456789abcdef.wav",start,22050,11025,0,pcm8,1);assert(!tracks_of(7));
    soundtime=at_bin(start,25);assert(AW_SpeechPose(7,3,21,"progs/np_census.mdl")==3);
    /* an npc/ voice without its .lip (a shared voice file): from its samples; 0 keeps the shut mouth of before */
    available=0;aw_speech_envelope.value=1;start=soundtime;
    AW_SpeechStartPcm(7,2,"npc/a_0a963d6561fc.wav",start,22050,11025,0,pcm8,1);assert(source_of(7)==2);
    soundtime=at_bin(start,25);assert(AW_SpeechPose(7,0,21,"progs/np_census.mdl")==11);
    aw_speech_envelope.value=0;start=soundtime;
    AW_SpeechStartPcm(7,2,"npc/a_0a963d6561fc.wav",start,22050,11025,0,pcm8,1);assert(source_of(7)==0);
    soundtime=at_bin(start,25);assert(AW_SpeechPose(7,0,21,"progs/np_census.mdl")==8);
    assert(AW_SpeechRemaining()>0);   /* an npc/ line still paces the opening, as before */
    /* a baked envelope beside the sound wins over the samples */
    available=1;aw_speech_envelope.value=1;start=soundtime;
    AW_SpeechStartPcm(7,2,"intro/test.wav",start,11025,11025,0,pcm8,1);assert(source_of(7)==1);
    soundtime=at_bin(start,1);assert(AW_SpeechPose(7,0,21,"progs/np_census.mdl")==9);
    soundtime=at_bin(start,3);assert(AW_SpeechPose(7,0,21,"progs/np_census.mdl")==11);
    AW_SpeechStop(-1,-1);cl_entities[7].model=cl_entities[8].model=NULL;
}
int main(void){
    int i;memcpy(timing,"AWL1",4);timing[4]=25;timing[6]=25;
    timing[8]=11025&255;timing[9]=11025>>8;
    for(i=12;i<37;i++)timing[i]=(i-12)%4;
    assert(AW_SpeechValidate(timing,37));assert(!AW_SpeechValidate(timing,36));
    timing[36]=4;assert(!AW_SpeechValidate(timing,37));timing[36]=0;
    timing[7]=255;assert(!AW_SpeechValidate(timing,37));timing[7]=0;
    soundtime=0;AW_SpeechStart(5,2,"intro/test.wav",100,11025,11025,0);
    assert(AW_SpeechPose(5,0,21,"progs/np_test.mdl")==8);
    soundtime=100+441;assert(AW_SpeechPose(5,0,21,"progs/np_test.mdl")==9);
    soundtime=100+1323;assert(AW_SpeechPose(5,0,21,"progs/np_test.mdl")==11);
    assert(AW_SpeechPose(6,3,21,"progs/np_test.mdl")==3);
    assert(AW_SpeechPose(5,3,8,"progs/np_test.mdl")==3);
    assert(AW_SpeechPose(5,3,21,"progs/unrelated.mdl")==3);
    soundtime=11125;assert(AW_SpeechRemaining()==0);assert(AW_SpeechPose(5,0,21,"progs/np_test.mdl")==0);
    AW_SpeechStart(5,2,"intro/test.wav",soundtime,11025,11025,0);AW_SpeechStop(5,2);
    assert(AW_SpeechRemaining()==0);
    available=0;AW_SpeechStart(5,2,"intro/missing.wav",soundtime,11025,11025,0);
    soundtime+=1323;assert(AW_SpeechPose(5,0,21,"progs/np_test.mdl")==8);
    /* a sound of no entity (a Quake temporary entity, a magic sound) leaves a speaking voice alone
     * (SPEECH-STOP-ALL-ON-MINUS1-54) */
    available=1;AW_SpeechStart(5,2,"intro/test.wav",soundtime,11025,11025,0);
    AW_SpeechStart(-1,0,"intro/test.wav",soundtime,11025,11025,0);
    assert(AW_SpeechRemaining()>0);
    AW_SpeechStop(-1,-1);assert(AW_SpeechRemaining()==0);
    pool_voice();
    return 0;
}
