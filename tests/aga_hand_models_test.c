/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_character.h"
#include "aw_hand_models.h"
#include <assert.h>
#include <stdarg.h>
client_state_t cl;aw_character_t aw_character;aw_race_t aw_races[16];int aw_race_count;
int com_filesize;
static byte raw[8+3*196],broken[sizeof(raw)];
static model_t legacy,models[6];static int torch,loads,warnings,missing;
static int metadata_valid=1,metadata_active;
int AW_TorchLoadHandAssets(void){return metadata_valid;}
void AW_TorchUseHandAssets(int enabled){metadata_active=enabled && metadata_valid;}
int AW_TorchFrame(void){return metadata_active?6:2;}
static const char *names[]={"nord_m","nord_f","khajiit_m"};
int AW_TorchEquipped(void){return torch;}
void Con_Printf(char *fmt,...){warnings++;}
byte *COM_LoadHunkFile(char *name){assert(!strcmp(name,"gfx/hand-models.awh"));com_filesize=sizeof(raw);return raw;}
model_t *Mod_ForName(char *name,qboolean crash){
    int i;char path[64];assert(!crash);loads++;
    for(i=0;i<6;i++){
        sprintf(path,"progs/hands/%s%s.mdl",names[i/2],i%2?"_t":"");
        if(!strcmp(path,name))return missing && i%2?NULL:&models[i];
    }
    assert(0);return NULL;
}
static void build(void){
    int i;byte *p;memset(raw,0,sizeof(raw));memcpy(raw,"AWH1",4);raw[5]=3;raw[7]=196;
    for(i=0;i<3;i++){
        p=raw+8+i*196;strcpy((char *)p,i==2?"khajiit":"nord");p[64]=i==1;
        sprintf((char *)p+68,"progs/hands/%s.mdl",names[i]);sprintf((char *)p+132,"progs/hands/%s_t.mdl",names[i]);
    }
    for(i=0;i<6;i++){models[i].type=mod_alias;models[i].numframes=i%2?8:28;}
    aw_race_count=2;strcpy(aw_races[0].id,"nord");strcpy(aw_races[1].id,"khajiit");
}
static void apply(int frame){cl.viewent.model=&legacy;cl.viewent.frame=frame;AW_HandModelsApply();assert(cl.viewent.frame==(torch?(metadata_active?6:2):frame));}
int main(void){
    int i,before;build();AW_HandModelsLoad();
    for(i=0;i<28;i++){apply(i);assert(cl.viewent.model==&models[0]);}assert(loads==2);
    torch=1;apply(6);assert(cl.viewent.model==&models[1] && loads==2 && metadata_active);
    aw_character.valid=1;aw_character.race=1;torch=0;apply(18);assert(cl.viewent.model==&models[4] && loads==4);
    torch=1;apply(7);assert(cl.viewent.model==&models[5] && loads==4);
    aw_character.race=0;aw_character.female=1;torch=0;apply(27);assert(cl.viewent.model==&models[2] && loads==6);
    AW_HandModelsReset();apply(2);assert(cl.viewent.model==&models[2] && loads==8);
    /* A missing paired torch cannot silently leave mismatched race arms. */
    missing=1;AW_HandModelsReset();apply(2);assert(cl.viewent.model==&legacy && warnings==1 && !metadata_active);
    before=loads;apply(3);assert(cl.viewent.model==&legacy && loads==before);
    missing=0;models[3].numframes=7;AW_HandModelsReset();apply(4);assert(cl.viewent.model==&legacy);models[3].numframes=8;
    /* Unknown/invalid selections retain the ordinary model without file probes. */
    aw_character.race=1;aw_character.female=1;before=loads;apply(0);assert(cl.viewent.model==&legacy && loads==before);
    aw_character.race=-1;apply(0);assert(cl.viewent.model==&legacy && loads==before);
    /* Missing metadata rejects even a syntactically valid paired catalogue. */
    metadata_valid=0;aw_character.valid=0;torch=1;AW_HandModelsLoad();before=loads;
    apply(7);assert(cl.viewent.model==&legacy && loads==before && !metadata_active);
    metadata_valid=1;AW_HandModelsLoad();apply(7);assert(cl.viewent.model==&models[1] && metadata_active);
    AW_HandModelsReset();assert(!metadata_active);
    assert(!AW_HandModelsDecode(NULL,0));aw_character.valid=0;apply(0);assert(cl.viewent.model==&legacy);
    memcpy(broken,raw,sizeof(raw));broken[8+65]=1;assert(!AW_HandModelsDecode(broken,sizeof(raw)));
    memcpy(broken,raw,sizeof(raw));memcpy(broken+8+68,"../",3);assert(!AW_HandModelsDecode(broken,sizeof(raw)));
    memcpy(broken,raw,sizeof(raw));broken[8+196+64]=0;assert(!AW_HandModelsDecode(broken,sizeof(raw)));
    memcpy(broken,raw,sizeof(raw));memset(broken+8,'n',64);assert(!AW_HandModelsDecode(broken,sizeof(raw)));
    assert(!AW_HandModelsDecode(raw,sizeof(raw)-1));assert(AW_HandModelsDecode(raw,sizeof(raw)));
    puts("Race/sex paired hand models, frame preservation, cache reuse/reset, malformed catalogue and legacy fallback passed.");return 0;
}
