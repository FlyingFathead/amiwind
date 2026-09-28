/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
int soundtime;client_state_t cl;entity_t cl_entities[MAX_EDICTS];
static byte timing[37];static int available=1;
int COM_FOpenFile(char *s,FILE **f){
    if(!available){*f=NULL;return -1;}*f=tmpfile();assert(*f);fwrite(timing,1,sizeof(timing),*f);rewind(*f);return sizeof(timing);
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
    AW_SpeechStop(-1,-1);assert(AW_SpeechRemaining()==0);
    return 0;
}
