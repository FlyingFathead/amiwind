/* SPDX-License-Identifier: GPL-2.0-or-later
 * Optional owned race/sex viewmodels. Keep the server's animation/frame
 * contract and legacy Nord payload; only the local appearance is selected. */
#include "quakedef.h"
#include "aw_character.h"
#include "aw_hand_models.h"
#include "aw_torch.h"

#define MAX_HAND_APPEARANCES 32
#define HAND_RECORD_BYTES 196
typedef struct {char race[64],hand[64],torch[64];int female;} hand_appearance_t;
static hand_appearance_t appearances[MAX_HAND_APPEARANCES];
static int appearance_count,selected=-2,pair_valid;
static model_t *hand_model,*torch_model;

void AW_HandModelsReset(void)
{
    selected=-2;pair_valid=0;hand_model=torch_model=NULL;AW_TorchUseHandAssets(0);
}
static int string_field(char *out,const byte *raw,int path)
{
    int i,end=-1;
    for(i=0;i<64;i++){
        unsigned char c=raw[i];
        if(!c){if(end<0)end=i;continue;}
        if(end>=0)return 0;
        if(!((c>='a' && c<='z') || (c>='0' && c<='9') || c=='_' ||
             (!path && c==' ') || (path && (c=='/' || c=='.'))))return 0;
    }
    if(end<=0)return 0;
    memcpy(out,raw,64);
    if(path && (strncmp(out,"progs/hands/",12) || strstr(out,"..") ||
                end<16 || strcmp(out+end-4,".mdl")))return 0;
    return 1;
}
int AW_HandModelsDecode(const unsigned char *data,int size)
{
    int count,i,j;const byte *p;hand_appearance_t *a;
    appearance_count=0;AW_HandModelsReset();
    if(!data || size<8 || memcmp(data,"AWH1",4) || data[4] || data[6] || data[7]!=HAND_RECORD_BYTES)return 0;
    count=data[5];if(count<1 || count>MAX_HAND_APPEARANCES || size!=8+count*HAND_RECORD_BYTES)return 0;
    for(i=0;i<count;i++){
        p=data+8+i*HAND_RECORD_BYTES;a=&appearances[i];
        if(p[64]>1 || p[65] || p[66] || p[67] ||
           !string_field(a->race,p,0) || !string_field(a->hand,p+68,1) ||
           !string_field(a->torch,p+132,1) || !strcmp(a->hand,a->torch))return 0;
        a->female=p[64];
        for(j=0;j<i;j++)if(a->female==appearances[j].female && !strcmp(a->race,appearances[j].race))return 0;
    }
    appearance_count=count;return 1;
}
void AW_HandModelsLoad(void)
{
    byte *raw;extern int com_filesize;
    raw=COM_LoadHunkFile("gfx/hand-models.awh");
    if(!AW_HandModelsDecode(raw,com_filesize)){
        if(raw)Con_Printf("Invalid hand appearance catalogue; using legacy models.\n");
        return;
    }
    if(!AW_TorchLoadHandAssets()){
        appearance_count=0;
        Con_Printf("Hand torch metadata unavailable; using legacy models.\n");
    }
}
static void release_owned(model_t *model,const char *name)
{
    /* Mod_FindName can recycle unreferenced model_t slots after a map change.
     * Name/type are part of ownership, not just the retained pointer. */
    if(model && model!=cl.viewent.model && model->type==mod_alias &&
       !strcmp(model->name,name) && model->cache.data)Cache_Free(&model->cache);
}
static unsigned int little32(const byte *p)
{
    return (unsigned int)p[0]|((unsigned int)p[1]<<8)|
           ((unsigned int)p[2]<<16)|((unsigned int)p[3]<<24);
}
static int probe_frames(const char *name,int frames)
{
    FILE *file=NULL;byte header[84];int size,ok;
    /* Verify both advertised members without retaining either alias. Respect
     * PAK member length and initial file offset; never read another member. */
    size=COM_FOpenFile((char *)name,&file);
    if(!file)return 0;
    ok=size>=(int)sizeof(header) &&
       fread(header,1,sizeof(header),file)==sizeof(header) &&
       !memcmp(header,"IDPO",4) && little32(header+4)==6 &&
       little32(header+68)==(unsigned int)frames;
    fclose(file);return ok;
}
int AW_HandModelsApply(void)
{
#if !AMIWIND_SPRITE_HANDS
    const char *race="nord",*path;int female=0,index=-1,i,equipped,frames;
    model_t **wanted,*base=cl.viewent.model;
    AW_TorchUseHandAssets(0);
    if(!appearance_count || !base)return 0;
    /* Do not replace an actual weapon or other custom viewmodel. */
    if(strcmp(base->name,"progs/v_nord.mdl") && strcmp(base->name,"progs/v_torch.mdl"))return 0;
    if(aw_character.valid){
        if(aw_character.race<0 || aw_character.race>=aw_race_count ||
           aw_character.female<0 || aw_character.female>1)return 0;
        race=aw_races[aw_character.race].id;female=aw_character.female;
    }
    for(i=0;i<appearance_count;i++)if(appearances[i].female==female && !strcmp(appearances[i].race,race)){index=i;break;}
    if(index!=selected){
        if(selected>=0 && selected<appearance_count){
            release_owned(hand_model,appearances[selected].hand);
            release_owned(torch_model,appearances[selected].torch);
        }
        selected=index;hand_model=torch_model=NULL;pair_valid=0;
        if(index>=0){
            pair_valid=probe_frames(appearances[index].hand,28) &&
                       probe_frames(appearances[index].torch,8);
            if(!pair_valid)
                Con_Printf("Incomplete hand appearance for %s; using legacy models.\n",race);
        }
    }
    if(!pair_valid || index<0)return 0;
    equipped=AW_TorchEquipped();frames=equipped?8:28;
    path=equipped?appearances[index].torch:appearances[index].hand;
    wanted=equipped?&torch_model:&hand_model;
    if(*wanted && (strcmp((*wanted)->name,path) || (*wanted)->type!=mod_alias ||
                   (*wanted)->numframes!=frames))*wanted=NULL;
    if(!*wanted){
        if(!Mod_CanFindName(path)){
            pair_valid=0;Con_Printf("Hand model slots unavailable; using legacy models.\n");return 0;
        }
        *wanted=Mod_ForName((char *)path,false);
        if(!*wanted || strcmp((*wanted)->name,path) || (*wanted)->type!=mod_alias ||
           (*wanted)->numframes!=frames){
            *wanted=NULL;pair_valid=0;
            Con_Printf("Invalid hand appearance for %s; using legacy models.\n",race);return 0;
        }
    }
    /* Only the selected mode loads. A previously used mode stays ordinary
     * LRU-evictable cache, avoiding forced reloads on repeated equip toggles.
     * Mod_Extradata reloads the active payload if cache pressure evicts it. */
    cl.viewent.model=*wanted;AW_TorchUseHandAssets(1);
    if(equipped)cl.viewent.frame=AW_TorchFrame();
    release_owned(base,"progs/v_nord.mdl");
    AW_TorchReleaseLegacyCache();
    return 1;
#else
    return 0;
#endif
}
