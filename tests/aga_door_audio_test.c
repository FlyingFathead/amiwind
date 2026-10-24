/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
client_state_t cl;entity_t cl_entities[MAX_EDICTS];
static cvar_t *enabled;static int opens,played;static sfx_t sample;static float low=.39f,high=.71f;
static const char *catalogue;
/* AWSFX1 (earlier images): one row per door reference. */
static const char *v1="AWSFX1\n172860 doors/d0123456789abcdef.wav doors/dfedcba9876543210.wav 0.7 0.4 1.2 0.8\n1 ../evil.wav - 1 0 1 0\n2 doors/d0123456789abcdef.wav - nan 0 1 0\n";
/* AWSFX2 (AW-20260928-10): the door sound pairs, then every load door's reference and pair, ascending. A bad
   reference row, a pair index past the table and a reference out of order are skipped. */
static const char *v2="AWSFX2\n"
 "p doors/d0123456789abcdef.wav doors/dfedcba9876543210.wav 0.7 0.4 1.2 0.8\n"
 "p doors/d1111111111111111.wav - 0.5 0 2.0 0\n"
 "32928 1\n41172 0\n41175 0\n99999 7\n50000 x\n172860 0\n100 0\n315559 1\n";
/* A bad pair row: every pair index after it would be wrong, so no door plays. */
static const char *v2bad="AWSFX2\np ../evil.wav - 1 0 1 0\np doors/d0123456789abcdef.wav - 0.5 0 1 0\n172860 0\n";
void Cvar_RegisterVariable(cvar_t *c){enabled=c;c->value=atof(c->string);}
int COM_FOpenFile(char *path,FILE **f){assert(!strcmp(path,"door-sounds.txt"));opens++;*f=tmpfile();fputs(catalogue,*f);rewind(*f);return strlen(catalogue);}
sfx_t *S_PrecacheSound(char *s){assert(!strncmp(s,"doors/d",7));return &sample;}
void S_StartSound(int ent,int channel,sfx_t *s,vec3_t origin,float volume,float attenuation){
 assert(ent==1 && channel==4 && s==&sample && !attenuation);
 assert(volume>low && volume<high);played++;
}
int main(int argc,char **argv){
 const char *mode=argc>1?argv[1]:"v1";
 AW_DoorAudioInit();assert(enabled->value==1);cl.viewentity=1;
 if(!strcmp(mode,"v1")){
  catalogue=v1;
  assert(AW_DoorSound(172860,0)>1.19 && played==1 && opens==1);
  assert(AW_DoorSound(172860,1)>.79 && played==2 && opens==1);
  assert(!AW_DoorSound(172860,2) && !AW_DoorSound(1,0) && !AW_DoorSound(2,0));
  enabled->value=0;assert(!AW_DoorSound(172860,0) && played==2 && opens==1);
 }else if(!strcmp(mode,"v2")){
  catalogue=v2;
  assert(AW_DoorSound(172860,0)>1.19 && played==1 && opens==1);
  assert(AW_DoorSound(41172,1)>.79 && AW_DoorSound(41175,0)>1.19 && played==3);
  low=.49f;high=.51f;
  assert(AW_DoorSound(32928,0)>1.99 && AW_DoorSound(315559,0)>1.99 && played==5);
  assert(!AW_DoorSound(32928,1) && played==5);          /* "-": the door has no closing sound */
  assert(!AW_DoorSound(99999,0) && !AW_DoorSound(50000,0) && !AW_DoorSound(100,0) && !AW_DoorSound(7,0));
  assert(played==5 && opens==1);
 }else{
  catalogue=v2bad;
  assert(!AW_DoorSound(172860,0) && played==0 && opens==1);
 }
 return 0;
}
