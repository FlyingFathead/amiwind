/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_character.h"
#include "aw_hand_models.h"
#include <assert.h>
#include <stdarg.h>
client_state_t cl;aw_character_t aw_character;aw_race_t aw_races[16];int aw_race_count;
int com_filesize;
static byte raw[8+3*196],broken[sizeof(raw)],cache_tokens[7];
static model_t legacy,models[6];
static int torch,loads,warnings,missing,probes,frees,slots=1,bad_frame;
static int metadata_valid=1,metadata_active,torch_releases;
int AW_TorchLoadHandAssets(void){return metadata_valid;}
void AW_TorchUseHandAssets(int enabled){metadata_active=enabled && metadata_valid;}
void AW_TorchReleaseLegacyCache(void){torch_releases++;}
int AW_TorchFrame(void){return metadata_active?6:2;}
int AW_TorchEquipped(void){return torch;}
void Con_Printf(char *fmt,...){warnings++;}
static const char *names[]={"nord_m","nord_f","khajiit_m"};
byte *COM_LoadHunkFile(char *name){assert(!strcmp(name,"gfx/hand-models.awh"));com_filesize=sizeof(raw);return raw;}
qboolean Mod_CanFindName(const char *name){return slots;}
static int index_for(const char *name){
    int i;char path[64];
    for(i=0;i<6;i++){
        sprintf(path,"progs/hands/%s%s.mdl",names[i/2],i%2?"_t":"");
        if(!strcmp(path,name))return i;
    }
    assert(0);return -1;
}
int COM_FOpenFile(char *name,FILE **file){
    byte header[84];int i=index_for(name);probes++;*file=NULL;
    if(missing && i%2)return -1;
    memset(header,0,sizeof(header));memcpy(header,"IDPO",4);header[4]=6;
    header[68]=i%2?(bad_frame?7:8):28;
    *file=tmpfile();assert(*file);fwrite("PAK-PREFIX",1,10,*file);
    assert(fwrite(header,1,sizeof(header),*file)==sizeof(header));
    fwrite("TRAILING-MEMBER",1,15,*file);fseek(*file,10,SEEK_SET);
    return sizeof(header);
}
model_t *Mod_ForName(char *name,qboolean crash){
    int i=index_for(name);assert(!crash && slots);loads++;
    strcpy(models[i].name,name);models[i].type=mod_alias;models[i].numframes=i%2?8:28;
    models[i].cache.data=&cache_tokens[i];return &models[i];
}
void Cache_Free(cache_user_t *cache){
    assert(cache->data && (!cl.viewent.model || cache!=&cl.viewent.model->cache));
    cache->data=NULL;frees++;
}
static void build(void){
    int i;byte *p;memset(raw,0,sizeof(raw));memcpy(raw,"AWH1",4);raw[5]=3;raw[7]=196;
    for(i=0;i<3;i++){
        p=raw+8+i*196;strcpy((char *)p,i==2?"khajiit":"nord");p[64]=i==1;
        sprintf((char *)p+68,"progs/hands/%s.mdl",names[i]);sprintf((char *)p+132,"progs/hands/%s_t.mdl",names[i]);
    }
    strcpy(legacy.name,"progs/v_nord.mdl");legacy.type=mod_alias;
    legacy.cache.data=&cache_tokens[6];
    aw_race_count=2;strcpy(aw_races[0].id,"nord");strcpy(aw_races[1].id,"khajiit");
}
static int apply(int frame){
    int selected;cl.viewent.model=&legacy;cl.viewent.frame=frame;selected=AW_HandModelsApply();
    if(!selected && torch)cl.viewent.frame=AW_TorchFrame();
    assert(cl.viewent.frame==(torch?(metadata_active?6:2):frame));return selected;
}
int main(void){
    int i,before,probe_before,free_before;build();AW_HandModelsLoad();
    for(i=0;i<28;i++){assert(apply(i));assert(cl.viewent.model==&models[0]);}
    assert(loads==1 && probes==2 && frees==1 && !legacy.cache.data);
    assert(!models[1].cache.data);
    torch=1;assert(apply(6));assert(cl.viewent.model==&models[1] && loads==2 && metadata_active);
    before=loads;probe_before=probes;free_before=frees;
    for(i=0;i<64;i++){torch=i%2;assert(apply(i%8));}
    assert(loads==before && probes==probe_before && frees==free_before);
    /* Normal eviction leaves metadata valid; actual drawing will reload via
     * Mod_Extradata, not a fresh per-frame selection probe. */
    models[1].cache.data=NULL;torch=1;assert(apply(1));
    assert(cl.viewent.model==&models[1] && loads==before);
    models[1].cache.data=&cache_tokens[1];
    aw_character.valid=1;aw_character.race=1;torch=0;assert(apply(18));
    assert(cl.viewent.model==&models[4] && loads==3 && frees==free_before+2);
    assert(!models[0].cache.data && !models[1].cache.data && !models[5].cache.data);
    torch=1;assert(apply(7));assert(cl.viewent.model==&models[5] && loads==4);
    /* A reused slot belongs to the new name; never evict another actor. */
    strcpy(models[4].name,"progs/other_actor.mdl");free_before=frees;
    aw_character.race=0;aw_character.female=1;torch=0;assert(apply(27));
    assert(models[4].cache.data && frees==free_before+1 && loads==5);
    AW_HandModelsReset();assert(apply(2));assert(loads==6);
    missing=1;AW_HandModelsReset();before=loads;probe_before=probes;
    assert(!apply(2) && cl.viewent.model==&legacy && !metadata_active && loads==before);
    assert(probes==probe_before+2);probe_before=probes;assert(!apply(3) && probes==probe_before);
    missing=0;bad_frame=1;AW_HandModelsReset();assert(!apply(4));bad_frame=0;
    slots=0;AW_HandModelsReset();before=loads;assert(!apply(4) && loads==before);
    slots=1;AW_HandModelsReset();assert(apply(4));
    strcpy(legacy.name,"progs/v_sword.mdl");cl.viewent.model=&legacy;before=loads;
    assert(!AW_HandModelsApply() && cl.viewent.model==&legacy && loads==before);
    strcpy(legacy.name,"progs/v_nord.mdl");
    aw_character.race=1;aw_character.female=1;before=loads;assert(!apply(0) && loads==before);
    aw_character.race=-1;assert(!apply(0) && loads==before);
    metadata_valid=0;aw_character.valid=0;torch=1;AW_HandModelsLoad();before=loads;
    assert(!apply(7) && cl.viewent.model==&legacy && loads==before && !metadata_active);
    metadata_valid=1;AW_HandModelsLoad();assert(apply(7) && cl.viewent.model==&models[1]);
    AW_HandModelsReset();assert(!metadata_active);
    assert(!AW_HandModelsDecode(NULL,0));aw_character.valid=0;assert(!apply(0));
    memcpy(broken,raw,sizeof(raw));broken[8+65]=1;assert(!AW_HandModelsDecode(broken,sizeof(raw)));
    memcpy(broken,raw,sizeof(raw));memcpy(broken+8+68,"../",3);assert(!AW_HandModelsDecode(broken,sizeof(raw)));
    memcpy(broken,raw,sizeof(raw));broken[8+196+64]=0;assert(!AW_HandModelsDecode(broken,sizeof(raw)));
    memcpy(broken,raw,sizeof(raw));memset(broken+8,'n',64);assert(!AW_HandModelsDecode(broken,sizeof(raw)));
    assert(!AW_HandModelsDecode(raw,sizeof(raw)-1));assert(AW_HandModelsDecode(raw,sizeof(raw)));
    assert(torch_releases>0);
    puts("Lazy hand residency, paired probes, toggle reuse, owned eviction, reused slots/admission, weapon protection and fallback passed.");return 0;
}
