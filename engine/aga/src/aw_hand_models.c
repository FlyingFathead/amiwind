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
static int appearance_count,selected=-2;
static model_t *hand_model,*torch_model;

void AW_HandModelsReset(void)
{
    selected=-2;hand_model=torch_model=NULL;AW_TorchUseHandAssets(0);
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
void AW_HandModelsApply(void)
{
#if !AMIWIND_SPRITE_HANDS
    const char *race="nord";int female=0,index=-1,i;
    AW_TorchUseHandAssets(0);
    if(AW_TorchEquipped())cl.viewent.frame=AW_TorchFrame();
    if(!appearance_count || !cl.viewent.model)return;
    if(aw_character.valid){
        if(aw_character.race<0 || aw_character.race>=aw_race_count ||
           aw_character.female<0 || aw_character.female>1)return;
        race=aw_races[aw_character.race].id;female=aw_character.female;
    }
    for(i=0;i<appearance_count;i++)if(appearances[i].female==female && !strcmp(appearances[i].race,race)){index=i;break;}
    if(index!=selected){
        selected=index;hand_model=torch_model=NULL;
        if(index>=0){
            hand_model=Mod_ForName(appearances[index].hand,false);
            torch_model=Mod_ForName(appearances[index].torch,false);
            if(!hand_model || hand_model->type!=mod_alias || hand_model->numframes!=28 ||
               !torch_model || torch_model->type!=mod_alias || torch_model->numframes!=8){
                hand_model=torch_model=NULL;
                Con_Printf("Incomplete hand appearance for %s; using legacy models.\n",race);
            }
        }
    }
    /* Load the pair atomically: never combine one race's fists with another
     * race's carried-torch arms. Model pointers reset before map memory frees. */
    if(hand_model && torch_model){
        AW_TorchUseHandAssets(1);
        cl.viewent.model=AW_TorchEquipped()?torch_model:hand_model;
        if(AW_TorchEquipped())cl.viewent.frame=AW_TorchFrame();
    }
#endif
}
