/* SPDX-License-Identifier: GPL-2.0-or-later
 * Converted DOOR SNAM/ANAM -> SOUN files; no per-frame file reads.
 *
 * door-sounds.txt (tools/prepare_door_audio.py), read once at the first door:
 *   AWSFX2: "p <open> <close> <open volume> <close volume> <open s> <close s>" rows (the door sound pairs, in
 *           order: pair 0, 1, ...), then "<reference> <pair>" rows in ascending reference order: every load door
 *           of the game data, so every converted door plays its DOOR record's sounds, whatever map form it has
 *           (AW-20260928-10: the 256-row AWSFX1 table held only the opening scene's doors).
 *   AWSFX1: "<reference> <open> <close> <volumes> <seconds>" rows (earlier images), at most 256. */
#include "quakedef.h"
#define AW_DOOR_PAIRS 64
#define AW_DOOR_REFS 8192
typedef struct {char path[2][32];float volume[2],seconds[2];} door_pair_t;
static door_pair_t pairs[AW_DOOR_PAIRS];
static unsigned refs[AW_DOOR_REFS];static unsigned char ref_pair[AW_DOOR_REFS];
static int loaded,pair_count,count;
static cvar_t enabled={"aw_door_sounds","1",true};
void AW_DoorAudioInit(void){Cvar_RegisterVariable(&enabled);}
static int valid_path(const char *s){
    int i;if(!strcmp(s,"-"))return 1;
    if(strncmp(s,"doors/d",7) || strlen(s)!=27 || strcmp(s+23,".wav"))return 0;
    for(i=7;i<23;i++)if(!((s[i]>='0' && s[i]<='9') || (s[i]>='a' && s[i]<='f')))return 0;
    return 1;
}
static int valid_pair(const door_pair_t *p){
    int i;
    for(i=0;i<2;i++)if(!valid_path(p->path[i]) || !(p->volume[i]>=0 && p->volume[i]<=1) ||
        !(p->seconds[i]>=0 && p->seconds[i]<=30))return 0;
    return 1;
}
/* An AWSFX1 row: its sounds as a pair (equal pairs shared), its reference kept in order (the first row wins). */
static void add_v1(unsigned ref,const door_pair_t *p){
    int i,at;
    for(at=0;at<count && refs[at]<ref;at++);
    if(at<count && refs[at]==ref)return;
    for(i=0;i<pair_count;i++)if(!memcmp(&pairs[i],p,sizeof(*p)))break;
    if(i==pair_count){if(pair_count>=AW_DOOR_PAIRS)return;pairs[pair_count++]=*p;}
    memmove(refs+at+1,refs+at,(count-at)*sizeof(refs[0]));
    memmove(ref_pair+at+1,ref_pair+at,(count-at)*sizeof(ref_pair[0]));
    refs[at]=ref;ref_pair[at]=(unsigned char)i;count++;
}
static void load(void){
    FILE *f=NULL;char line[192],extra;door_pair_t p;unsigned ref,index;int v2;
    if(loaded)return;
    loaded=1;
    if(COM_FOpenFile("door-sounds.txt",&f)<0 || !f)return;
    if(!fgets(line,sizeof(line),f) || (strcmp(line,"AWSFX1\n") && strcmp(line,"AWSFX2\n"))){fclose(f);return;}
    v2=line[5]=='2';
    while(fgets(line,sizeof(line),f)){
        memset(&p,0,sizeof(p));
        if(v2 && line[0]=='p'){
            if(pair_count>=AW_DOOR_PAIRS || count)continue;   /* pairs come first; a late pair row is refused */
            if(Q_sscanf(line+1,"%31s %31s %f %f %f %f %c",p.path[0],p.path[1],&p.volume[0],&p.volume[1],
                &p.seconds[0],&p.seconds[1],&extra)!=6 || !valid_pair(&p)){
                pair_count=AW_DOOR_PAIRS+1;continue;          /* pair indexes after a bad row would be wrong */
            }
            pairs[pair_count++]=p;
        }else if(v2){
            if(count>=AW_DOOR_REFS || pair_count>AW_DOOR_PAIRS)continue;
            if(Q_sscanf(line,"%u %u %c",&ref,&index,&extra)!=2 || (int)index>=pair_count)continue;
            if(count && ref<=refs[count-1])continue;          /* ascending, as the lookup needs */
            refs[count]=ref;ref_pair[count++]=(unsigned char)index;
        }else{
            if(count>=256)continue;
            if(Q_sscanf(line,"%u %31s %31s %f %f %f %f %c",&ref,p.path[0],p.path[1],
               &p.volume[0],&p.volume[1],&p.seconds[0],&p.seconds[1],&extra)!=7 || !valid_pair(&p))continue;
            add_v1(ref,&p);
        }
    }
    fclose(f);
}
float AW_DoorSound(unsigned reference,int closing){
    int low,high,mid;sfx_t *s;door_pair_t *p;
    if(!enabled.value || closing<0 || closing>1)return 0;
    load();
    low=0;high=count-1;
    while(low<=high){
        mid=(low+high)/2;
        if(refs[mid]<reference)low=mid+1;
        else if(refs[mid]>reference)high=mid-1;
        else{
            p=&pairs[ref_pair[mid]];
            if(p->path[closing][0]=='-')return 0;
            s=S_PrecacheSound(p->path[closing]);if(!s)return 0;
            S_StartSound(cl.viewentity,4,s,cl_entities[cl.viewentity].origin,p->volume[closing],0);
            return p->seconds[closing];
        }
    }
    return 0;
}
