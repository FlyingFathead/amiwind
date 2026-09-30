/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
client_state_t cl;entity_t cl_entities[MAX_EDICTS];
static cvar_t *enabled;static int opens,played;static sfx_t sample;
static const char *catalogue="AWSFX1\n172860 doors/d0123456789abcdef.wav doors/dfedcba9876543210.wav 0.7 0.4 1.2 0.8\n1 ../evil.wav - 1 0 1 0\n2 doors/d0123456789abcdef.wav - nan 0 1 0\n";
void Cvar_RegisterVariable(cvar_t *c){enabled=c;c->value=atof(c->string);}
int COM_FOpenFile(char *path,FILE **f){assert(!strcmp(path,"door-sounds.txt"));opens++;*f=tmpfile();fputs(catalogue,*f);rewind(*f);return strlen(catalogue);}
sfx_t *S_PrecacheSound(char *s){assert(!strncmp(s,"doors/d",7));return &sample;}
void S_StartSound(int ent,int channel,sfx_t *s,vec3_t origin,float volume,float attenuation){
 assert(ent==1 && channel==4 && s==&sample && !attenuation);
 assert(volume>.39 && volume<.71);played++;
}
int main(void){
 AW_DoorAudioInit();assert(enabled->value==1);cl.viewentity=1;
 assert(AW_DoorSound(172860,0)>1.19 && played==1 && opens==1);
 assert(AW_DoorSound(172860,1)>.79 && played==2 && opens==1);
 assert(!AW_DoorSound(172860,2) && !AW_DoorSound(1,0) && !AW_DoorSound(2,0));
 enabled->value=0;assert(!AW_DoorSound(172860,0) && played==2 && opens==1);
 return 0;
}
