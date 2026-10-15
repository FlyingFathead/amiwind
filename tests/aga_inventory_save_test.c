/* SPDX-License-Identifier: GPL-3.0-only */
#include <assert.h>
#include <string.h>
#include "aw_story.h"
#include "aw_save.h"
#include "aw_inventory.h"
aw_race_t aw_races[16];aw_class_t aw_classes[32];aw_birth_t aw_births[16];aw_part_t aw_parts[384];
int aw_race_count=1,aw_class_count=1,aw_birth_count=1,aw_part_count=2;
static aw_save_t save,decoded,prior;
static unsigned char bytes[AW_SAVE_BYTES],legacy[AW_SAVE_BYTES];
int main(void){
    int size,oldsize,index;float pos[3]={10,20,30};aw_inventory_item_t ring;
    strcpy(aw_races[0].id,"race");strcpy(aw_classes[0].id,"class");strcpy(aw_births[0].id,"birth");
    strcpy(aw_parts[0].id,"head");strcpy(aw_parts[1].id,"hair");aw_parts[1].kind=1;
    save.sequence=save.profile=1;strcpy(save.scene,"seyda");strcpy(save.story.name,"Player");
    save.story.stage=AW_STAGE_RELEASED;save.story.ship_disabled=1;save.story.captain=-1;
    save.character.valid=1;save.character.level=1;save.character.hair=1;
    assert(AW_StateSet(&save.state,AW_GLOBAL,"CharGenState",-1));
    /* The added activation fact uses the existing table encoding; supported
     * released-game saves retain it without opening a new save version. */
    aw_story.stage=AW_STAGE_PAPERS;
    assert(AW_StateSet(&aw_state,AW_GLOBAL,"CharGenState",1));
    assert(AW_StoryPapersRead());save.state=aw_state;
    assert(AW_StateSet(&save.state,AW_GLOBAL,"CharGenState",-1));
    oldsize=AW_SaveEncode(legacy,sizeof(legacy),&save);assert(oldsize>0);
    assert(AW_SaveDecode(legacy,oldsize,&decoded));assert(!decoded.state.inventory.next_serial);
    assert(AW_StateGet(&decoded.state,AW_GLOBAL,"amiwind:opening:papers_read")==1);
    memset(&ring,0,sizeof(ring));strcpy(ring.id,"synthetic_ring");strcpy(ring.model,"progs/inv/test.mdl");
    ring.slots=(1U<<AW_SLOT_LRING)|(1U<<AW_SLOT_RRING);ring.flags=AW_INV_EQUIP|AW_INV_EQUIP_SUPPORTED|AW_INV_DROP;
    assert(AW_ItemAdd(&save.state,ring.id,3));assert(AW_InventoryEquip(&save.state,&ring));
    save.state.inventory.condition_known=1;save.state.inventory.condition[0]=.375f;
    index=AW_InventoryDrop(&save.state,&ring,2,"seyda",pos,90);assert(index>=0);
    size=AW_SaveEncode(bytes,sizeof(bytes),&save);assert(size>oldsize);
    assert(AW_SaveDecode(bytes,size,&decoded));assert(!memcmp(&save.state,&decoded.state,sizeof(save.state)));
    assert(decoded.state.inventory.dropped[index].condition_known);
    assert(decoded.state.inventory.dropped[index].condition==.375f);
    decoded.state.inventory.condition[0]=.5f;prior=decoded;
    assert(!AW_InventoryPickup(&decoded.state,index));assert(!memcmp(&prior,&decoded,sizeof(prior)));
    decoded.state.inventory.condition[0]=.375f;
    assert(AW_InventoryPickup(&decoded.state,index));assert(AW_StateGet(&decoded.state,AW_ITEM,ring.id)==3);
    assert(AW_InventoryEquipped(&decoded.state,ring.id)==1);
    prior=decoded;bytes[size-1]^=1;assert(!AW_SaveDecode(bytes,size,&decoded));assert(!memcmp(&prior,&decoded,sizeof(prior)));
    save.state.inventory.dropped[index].count=-1;assert(!AW_SaveEncode(bytes,sizeof(bytes),&save));
    save.state.inventory.dropped[index].count=2;save.state.inventory.dropped[index].serial=0;assert(!AW_SaveEncode(bytes,sizeof(bytes),&save));
    return 0;
}
