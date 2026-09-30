/* SPDX-License-Identifier: GPL-2.0-or-later
 * Converted DOOR SNAM/ANAM -> SOUN files; no per-frame file reads. */
#include "quakedef.h"
typedef struct {unsigned ref;char path[2][32];float volume[2],seconds[2];} door_audio_t;
static door_audio_t entries[256];static int loaded,count;
static cvar_t enabled={"aw_door_sounds","1",true};
void AW_DoorAudioInit(void){Cvar_RegisterVariable(&enabled);}
static int valid_path(const char *s){
    int i;if(!strcmp(s,"-"))return 1;
    if(strncmp(s,"doors/d",7) || strlen(s)!=27 || strcmp(s+23,".wav"))return 0;
    for(i=7;i<23;i++)if(!((s[i]>='0' && s[i]<='9') || (s[i]>='a' && s[i]<='f')))return 0;
    return 1;
}
static void load(void){
    FILE *f=NULL;char line[192],extra;door_audio_t e;int i;
    if(loaded)return;
    loaded=1;
    if(COM_FOpenFile("door-sounds.txt",&f)<0 || !f)return;
    if(!fgets(line,sizeof(line),f) || strcmp(line,"AWSFX1\n")){fclose(f);return;}
    while(count<256 && fgets(line,sizeof(line),f)){
        if(sscanf(line,"%u %31s %31s %f %f %f %f %c",&e.ref,e.path[0],e.path[1],
           &e.volume[0],&e.volume[1],&e.seconds[0],&e.seconds[1],&extra)!=7)continue;
        for(i=0;i<2;i++)if(!valid_path(e.path[i]) || !(e.volume[i]>=0 && e.volume[i]<=1) ||
            !(e.seconds[i]>=0 && e.seconds[i]<=30))break;
        if(i==2)entries[count++]=e;
    }
    fclose(f);
}
float AW_DoorSound(unsigned reference,int closing){
    int i;sfx_t *s;
    if(!enabled.value || closing<0 || closing>1)return 0;
    load();
    for(i=0;i<count;i++)if(entries[i].ref==reference){
        if(entries[i].path[closing][0]=='-')return 0;
        s=S_PrecacheSound(entries[i].path[closing]);if(!s)return 0;
        S_StartSound(cl.viewentity,4,s,cl_entities[cl.viewentity].origin,entries[i].volume[closing],0);
        return entries[i].seconds[closing];
    }
    return 0;
}
