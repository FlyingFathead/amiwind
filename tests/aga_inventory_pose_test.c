/* SPDX-License-Identifier: GPL-2.0-or-later
 * Real preview routing with controlled alias/cache/equipment services. */
#include "../engine/aga/src/aw_view.c"
#include <assert.h>
#include <strings.h>
server_t sv;server_static_t svs;client_static_t cls;
aw_character_t aw_character;aw_race_t aw_races[16];int aw_race_count;
int hunk_size=8*1024*1024,hunk_low_used,hunk_high_used,com_filesize;
static model_t world,portrait,gear;
static int right_type=-1,shield=1,loads,frees,tag_frame=-1,wrong_frames,missing,torch;
int AW_TorchEquipped(void){return torch;}
int Hunk_LowMark(void){return 0;}
void Hunk_FreeToLowMark(int n){(void)n;}
byte *COM_LoadHunkFile(char *path){(void)path;return NULL;}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void Con_Printf(char *format,...){(void)format;}
void *Cache_Check(cache_user_t *c){return c->data;}
void Cache_Free(cache_user_t *c){assert(c->data);c->data=NULL;frees++;}
model_t *Mod_ForName(char *path,qboolean crash){
    model_t *m;(void)crash;
    if(strstr(path,"_i.mdl")){
        loads++;if(missing)return NULL;m=&portrait;m->numframes=wrong_frames?9:10;
    }else if(strstr(path,"items/")){m=&gear;m->numframes=1;}
    else {m=&world;m->numframes=24;}
    strcpy(m->name,path);m->type=mod_alias;m->cache.data=m;return m;
}
void AW_ItemsAliasClear(void){}
int AW_ItemsAliasTag(model_t *m,int frame,int kind,float tag[6]){
    int i;(void)kind;assert(m==&portrait || m==&world);
    if(frame<0)return 1;tag_frame=frame;
    for(i=0;i<6;i++)tag[i]=(float)(frame*10+i);return 1;
}
int AW_InventoryEquippedItem(int slot,aw_inventory_item_t *out){
    memset(out,0,sizeof(*out));
    if(slot==AW_SLOT_RIGHT && right_type>=0){out->category=AW_INV_WEAPON;out->subtype=right_type;strcpy(out->model,"items/weapon.mdl");return 1;}
    if(slot==AW_SLOT_LEFT && shield){out->category=AW_INV_ARMOUR;out->subtype=8;strcpy(out->model,"items/shield.mdl");return 1;}
    return 0;
}
int main(void){
    model_t *m,*equipment[2];int frame,i,n,oldloads;float origins[2][3],angles[2][3];
    static const int left[]={1,1,0,1,0,0,0,1,0};
    body_cvar.value=1;body_count=1;body_race=-1;body_female=0;strcpy(bodies[0].race,"dark elf");
    strcpy(bodies[0].path,"progs/body/dark_elf_m.mdl");bodies[0].female=0;
    body.model=&world;body.frame=7;body_play.phase=3.25f;
    assert(AW_ViewInventoryBody(&m,&frame) && m!=&world && frame==0);
    assert(body.frame==7 && body_play.phase==3.25f);
    oldloads=loads;body.frame=19;
    assert(AW_ViewInventoryBody(&m,&frame) && frame==0 && loads==oldloads);
    for(i=0;i<9;i++){
        right_type=i;assert(AW_ViewInventoryBody(&m,&frame) && frame==i+1);
        n=AW_ViewInventoryEquipment(equipment,origins,angles);
        assert(n==1+left[i] && tag_frame==frame && origins[0][0]==frame*10);
        assert(body.frame==19 && body_play.phase==3.25f && loads==oldloads);
    }
    right_type=9;assert(!AW_ViewInventoryBody(&m,&frame)); /* no fabricated ranged pose */
    right_type=-1;AW_ViewInventoryClear();assert(!portrait.cache.data && world.cache.data);
    hunk_size=1024*1024;oldloads=loads;
    assert(!AW_ViewInventoryBody(&m,&frame) && loads==oldloads);
    hunk_size=8*1024*1024;AW_ViewInventoryClear();wrong_frames=1;
    assert(!AW_ViewInventoryBody(&m,&frame));oldloads=loads;
    assert(!AW_ViewInventoryBody(&m,&frame) && loads==oldloads);
    wrong_frames=0;AW_ViewInventoryClear();missing=1;
    assert(!AW_ViewInventoryBody(&m,&frame));missing=0;AW_ViewInventoryClear();
    assert(AW_ViewInventoryBody(&m,&frame));portrait.cache.data=NULL;oldloads=loads;
    assert(AW_ViewInventoryBody(&m,&frame) && loads==oldloads+1);
    /* Appearance catalogue change obtains the corresponding companion. */
    strcpy(bodies[0].path,"progs/body/dark_elf_f.mdl");
    assert(AW_ViewInventoryBody(&m,&frame) && strstr(m->name,"_f_i.mdl"));
    assert(world.cache.data && body.frame==19);
    AW_ViewInventoryClear();AW_ViewInventoryClear();assert(frees>0);return 0;
}
