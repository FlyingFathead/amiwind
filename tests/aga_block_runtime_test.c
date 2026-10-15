/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_character.h"
#include "aw_hand_models.h"
#include <assert.h>
#include <stdarg.h>
client_state_t cl;server_t sv;aw_character_t aw_character;aw_race_t aw_races[16];int aw_race_count;
double host_frametime=.05;
int com_filesize;
static unsigned char metadata[372];
static model_t arms,shield,base;
static int owned=1,guarding=1,warnings,loads,probes,reads,badframes,missing,slots=1,torch;
static int slot_budget=-1;
int AW_CombatGuarding(void){return guarding;}
float AW_CombatBlockShown(void){return 0;}
int AW_TorchEquipped(void){return torch;}
void AW_TorchUseHandAssets(int value){(void)value;}
int AW_ModalWorldFrozen(void){return 0;}
void Con_Printf(char *fmt,...){(void)fmt;warnings++;}
int Hunk_LowMark(void){return 0;}
void Hunk_FreeToLowMark(int mark){assert(!mark);}
byte *COM_LoadHunkFile(char *name){
    assert(!strcmp(name,"gfx/block-models.awb"));reads++;com_filesize=missing?0:sizeof(metadata);
    return missing?NULL:metadata;
}
static void be32(unsigned char *p,unsigned long n){p[0]=n>>24;p[1]=n>>16;p[2]=n>>8;p[3]=n;}
static int equipment(char id[64],char path[64]){
    if(!owned)return 0;strcpy(id,"steel_shield");strcpy(path,"progs/inv/steel_shield.mdl");return 1;
}
int COM_FOpenFile(char *name,FILE **file){
    byte header[84];int frames=!strcmp(name,"progs/hands/nord_m_b.mdl")?8:1;
    assert(frames==8 || !strcmp(name,"progs/inv/steel_shield.mdl"));
    probes++;memset(header,0,sizeof(header));memcpy(header,"IDPO",4);header[4]=6;header[68]=badframes?2:frames;
    *file=tmpfile();assert(*file);fwrite("PAK OFFSET",1,10,*file);fwrite(header,1,84,*file);fseek(*file,10,SEEK_SET);return 84;
}
qboolean Mod_CanFindName(const char *name){(void)name;return slots && slot_budget!=0;}
model_t *Mod_ForName(char *name,qboolean crash){
    model_t *m;assert(!crash);loads++;m=strstr(name,"nord_m_b")?&arms:&shield;
    if(slot_budget>=0){assert(slot_budget>0);slot_budget--;}
    strcpy(m->name,name);m->type=mod_alias;m->numframes=m==&arms?8:1;return m;
}
static int apply(void){cl.viewent.model=&base;cl.viewent.frame=18;return AW_HandBlockApply();}
static void setup(void){
    static const unsigned long times[8]={0,167,333,533,733,933,1133,1333};int i;
    memset(metadata,0,sizeof(metadata));memcpy(metadata,"AWB1",4);metadata[5]=1;metadata[7]=132;
    be32(metadata+8,1333);be32(metadata+12,333);
    for(i=0;i<8;i++)be32(metadata+16+28*i,times[i]);
    strcpy((char *)metadata+240,"nord");strcpy((char *)metadata+308,"progs/hands/nord_m_b.mdl");
    strcpy(base.name,"progs/v_nord.mdl");base.type=mod_alias;base.numframes=28;
}
int main(void){
    int i,before,probe_before;
    setup();AW_HandModelsReset();assert(!apply() && !loads && !reads);
    aw_hand_block_item=equipment;owned=0;assert(!apply() && !reads);
    owned=1;guarding=0;assert(!apply() && !reads);
    guarding=1;assert(apply() && cl.viewent.model==&arms && loads==2 && reads==1 && probes==2);
    before=loads;probe_before=probes;
    for(i=0;i<50;i++)assert(apply());
    assert(cl.viewent.frame==2 && loads==before && probes==probe_before && reads==1);
    assert(AW_HandBlockItemApply() && cl.viewent.model==&shield && cl.viewent.frame==0);
    owned=0;assert(!apply() && !AW_HandBlockItemApply());owned=1;
    torch=1;assert(!apply());torch=0;
    AW_HandModelsReset();badframes=1;before=warnings;assert(!apply());
    for(i=0;i<30;i++)assert(!apply());assert(warnings==before+1);badframes=0;
    AW_HandModelsReset();missing=1;before=warnings;assert(!apply());
    for(i=0;i<30;i++)assert(!apply());assert(warnings==before+1);missing=0;
    AW_HandModelsReset();slots=0;before=warnings;assert(!apply());
    for(i=0;i<30;i++)assert(!apply());assert(warnings==before+1);slots=1;
    AW_HandModelsReset();slot_budget=1;before=loads;assert(!apply());
    assert(loads==before+1); /* Arms consume the last slot; no shield load is attempted. */
    slot_budget=-1;
    AW_HandModelsReset();assert(apply());cl.paused=1;
    for(i=0;i<30;i++)assert(apply());assert(cl.viewent.frame==0);cl.paused=0;
    puts("Actual equipment gating, lazy block probes, torch/ownership fallback and once-only failures passed.");return 0;
}
