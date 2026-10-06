/* SPDX-License-Identifier: GPL-2.0-or-later
 * Speech poses follow the audio playback clock, not the rendering clock.
 * Four bounded tracks; original morph poses and envelopes are external data.
 */
#include "quakedef.h"
extern int soundtime;
typedef struct {int entity,channel,start,end,speed,count;byte levels[3000];} aw_voice_t;
static aw_voice_t voices[4];
static int latest=-1;
static unsigned get16(const byte *p){return p[0]+(p[1]<<8);}
static unsigned get32(const byte *p){return get16(p)+(get16(p+2)<<16);}
int AW_SpeechValidate(const byte *p,int n) {
    unsigned count,samples;int i;
    if(n<13 || memcmp(p,"AWL1",4) || get16(p+4)!=25)return 0;
    count=get16(p+6);samples=get32(p+8);
    if(!count || count>3000 || n!=12+count || !samples || samples>1323000 ||
       count!=(samples*25+11024)/11025)return 0;
    for(i=12;i<n;i++)if(p[i]>3)return 0;
    return 1;
}
void AW_SpeechStop(int entity,int channel) {
    int i;for(i=0;i<4;i++)if(entity<0 || (voices[i].entity==entity && (channel<0 || voices[i].channel==channel)))voices[i].end=0;
}
void AW_SpeechStart(int entity,int channel,const char *sound,int start,int length,int speed,int skip) {
    FILE *f;byte data[3013];int n,i,slot=0;char path[128];aw_voice_t *v;
    AW_SpeechStop(entity,channel);
    if((strncmp(sound,"npc/",4) && strncmp(sound,"intro/",6)) || strlen(sound)>100 ||
       strstr(sound,"..") || length<=0 || speed<=0)return;
    for(i=0;i<4;i++)if(voices[i].end<=soundtime){slot=i;break;}else if(voices[i].end<voices[slot].end)slot=i;
    v=&voices[slot];memset(v,0,sizeof(*v));
    v->entity=entity;v->channel=channel;v->start=start-skip;v->end=start+length-skip;v->speed=speed;
    sprintf(path,"sound/%s",sound);strcpy(path+strlen(path)-4,".lip");
    f=NULL;n=COM_FOpenFile(path,&f);
    if(f){
        if(n>=13 && n<=3012 && fread(data,1,n,f)==n && AW_SpeechValidate(data,n)) {
            v->count=get16(data+6);memcpy(v->levels,data+12,v->count);
        }
        fclose(f);
    }
    latest=slot;
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
    if(frames!=21 || strncmp(model,"progs/np_",9))return current;
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
void AW_SpeechRelink(void) {
    int i;entity_t *e;
    for(i=1;i<cl.num_entities;i++) {
        e=&cl_entities[i];if(!e->model)continue;
        e->frame=AW_SpeechPose(i,e->frame,e->model->numframes,e->model->name);
    }
}
