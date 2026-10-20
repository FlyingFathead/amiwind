/* SPDX-License-Identifier: GPL-2.0-or-later
 * Real preview routing with controlled alias/cache/equipment services. */
#include "../engine/aga/src/aw_view.c"
#include <assert.h>
#include <strings.h>
server_t sv;server_static_t svs;client_static_t cls;
aw_character_t aw_character;aw_race_t aw_races[16];int aw_race_count;
int hunk_size=8*1024*1024,hunk_low_used,hunk_high_used,com_filesize;double realtime;
static model_t world,portrait,gear,held_torch;static int held_loads;
static int right_type=-1,shield=1,loads,frees,tag_frame=-1,wrong_frames,missing,torch;
int AW_TorchEquipped(void){return torch;}
int Hunk_LowMark(void){return 0;}
void Hunk_FreeToLowMark(int n){(void)n;}
byte *COM_LoadHunkFile(char *path){(void)path;return NULL;}
static int pose_file=128*1024,pose_absent;
int COM_FOpenFile(char *path,FILE **f){
    (void)path;*f=NULL;if(pose_absent)return -1;
    *f=tmpfile();assert(*f);return pose_file;
}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void Con_Printf(char *format,...){(void)format;}
void *Cache_Check(cache_user_t *c){return c->data;}
void Cache_Free(cache_user_t *c){assert(c->data);c->data=NULL;frees++;}
model_t *Mod_ForName(char *path,qboolean crash){
    model_t *m;(void)crash;
    if(strstr(path,"_i.mdl")){
        loads++;if(missing)return NULL;m=&portrait;m->numframes=wrong_frames?9:10;
    }else if(strstr(path,"items/")){m=&gear;m->numframes=1;}
    else if(strstr(path,"_h.mdl")){m=&held_torch;m->numframes=24;held_loads++;}
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
    /* UI-INVENTORY-PREVIEW-GAP-41: admitted by the model's real need (3 x file + 256 KiB),
     * not a blanket 2 MiB: the Seyda Neen CHIM gap (2,056,656 bytes) shows the preview;
     * a gap below the need, a missing file and the old rule (reserve 2) refuse without a load. */
    hunk_size=2056656;oldloads=loads;
    assert(AW_ViewInventoryBody(&m,&frame) && loads==oldloads+1);
    AW_ViewInventoryClear();hunk_size=600*1024;oldloads=loads;
    assert(!AW_ViewInventoryBody(&m,&frame) && loads==oldloads);
    AW_ViewInventoryClear();hunk_size=2056656;aw_inventory_preview_reserve.value=2;oldloads=loads;
    assert(!AW_ViewInventoryBody(&m,&frame) && loads==oldloads);
    AW_ViewInventoryClear();aw_inventory_preview_reserve.value=0;pose_absent=1;hunk_size=8*1024*1024;
    assert(!AW_ViewInventoryBody(&m,&frame) && loads==oldloads);pose_absent=0;
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
    /* PLAYER-TORCH-THIRDPERSON-38: the held torch evicted from the cache under a torch
     * body is loaded again (same slot, same frame count), at most once a second and only
     * with its first admission's free memory; before, it was never drawn again. */
    {int before;
     body_model=&world;world.numframes=24;body_torch=1;held_model=Mod_ForName("progs/body/dark_elf_m_h.mdl",false);
     strcpy(held_path,"progs/body/dark_elf_m_h.mdl");held_next=0;realtime=10;before=held_loads;
     assert(held_ready() && held_loads==before);
     held_torch.cache.data=NULL;assert(held_ready() && held_loads==before+1 && held_torch.cache.data);
     held_torch.cache.data=NULL;realtime=10.5;assert(!held_ready() && held_loads==before+1);
     realtime=11;assert(held_ready() && held_loads==before+2);
     held_torch.cache.data=NULL;hunk_size=1024*1024;realtime=13;assert(!held_ready() && held_loads==before+2);
     hunk_size=8*1024*1024;realtime=14;assert(held_ready() && held_loads==before+3);
     held_torch.cache.data=NULL;world.numframes=23;realtime=16;assert(!held_ready());   /* wrong alias refused */
     world.numframes=24;body_torch=0;assert(!held_ready());
     held_model=NULL;held_path[0]=0;body_model=NULL;}
    AW_ViewInventoryClear();AW_ViewInventoryClear();assert(frees>0);return 0;
}
