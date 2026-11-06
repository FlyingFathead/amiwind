/* SPDX-License-Identifier: GPL-3.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_story.h"
#include "aw_save.h"
#include "aw_inventory.h"
aw_race_t aw_races[16];aw_class_t aw_classes[32];aw_birth_t aw_births[16];aw_part_t aw_parts[384];
int aw_race_count=1,aw_class_count=1,aw_birth_count=1,aw_part_count=2;
static aw_save_t save,decoded,prior;
static unsigned char bytes[AW_SAVE_BYTES],legacy[AW_SAVE_BYTES];
/* INVENTORY-ORIGINAL-LIMITS-61: two states are the same when their item rows are (id, count, marks and their values)
 * and everything else is byte for byte (a decoded save owns a table of its own, aw_state.h OWNERSHIP) */
static int same_state(const aw_state_t *x,const aw_state_t *y){
    aw_state_t a=*x,b=*y;int i;
    if(a.items.count!=b.items.count)return 0;
    for(i=0;i<a.items.count;i++){
        const aw_item_row_t *r=AW_ITEM_ROW(&a,i),*s=AW_ITEM_ROW(&b,i);unsigned f=AW_ITEM_FLAGS(r);
        if(strcmp(AW_ITEM_ID(&a,i),AW_ITEM_ID(&b,i)) || r->value!=s->value ||
           (f&(AW_ITEM_CONDITION|AW_ITEM_CHARGE))!=(AW_ITEM_FLAGS(s)&(AW_ITEM_CONDITION|AW_ITEM_CHARGE)) ||
           ((f&AW_ITEM_CONDITION) && r->condition!=s->condition) || ((f&AW_ITEM_CHARGE) && r->charge!=s->charge))return 0;
    }
    memset(&a.items,0,sizeof(a.items));memset(&b.items,0,sizeof(b.items));
    return !memcmp(&a,&b,sizeof(a));
}
/* a copy of SRC with an item table of its own */
static void copy_save(aw_save_t *out,const aw_save_t *src){*out=*src;assert(AW_ItemsClone(&out->state.items,&src->state.items));}
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
    assert(AW_StoryPapersRead());save.state=aw_state;memset(&aw_state.items,0,sizeof(aw_state.items));
    assert(AW_StateSet(&save.state,AW_GLOBAL,"CharGenState",-1));
    oldsize=AW_SaveEncode(legacy,sizeof(legacy),&save);assert(oldsize>0);
    assert(AW_SaveDecode(legacy,oldsize,&decoded));assert(!decoded.state.inventory.next_serial);
    assert(AW_StateGet(&decoded.state,AW_GLOBAL,"amiwind:opening:papers_read")==1);
    AW_SaveRelease(&decoded);
    memset(&ring,0,sizeof(ring));strcpy(ring.id,"synthetic_ring");strcpy(ring.model,"progs/inv/test.mdl");
    ring.slots=(1U<<AW_SLOT_LRING)|(1U<<AW_SLOT_RRING);ring.flags=AW_INV_EQUIP|AW_INV_EQUIP_SUPPORTED|AW_INV_DROP;
    assert(AW_ItemAdd(&save.state,ring.id,3));assert(AW_InventoryEquip(&save.state,&ring));
    index=AW_ItemIndex(&save.state,ring.id);AW_ItemMark(&save.state,index,AW_ITEM_CONDITION,.375f);
    index=AW_InventoryDrop(&save.state,&ring,2,"seyda",pos,90);assert(index>=0);
    size=AW_SaveEncode(bytes,sizeof(bytes),&save);assert(size>oldsize);
    assert(AW_SaveDecode(bytes,size,&decoded));assert(same_state(&save.state,&decoded.state));
    assert(decoded.state.inventory.dropped[index].condition_known);
    assert(decoded.state.inventory.dropped[index].condition==.375f);
    AW_ITEM_ROW(&decoded.state,AW_ItemIndex(&decoded.state,ring.id))->condition=.5f;prior=decoded;
    assert(!AW_InventoryPickup(&decoded.state,index));assert(!memcmp(&prior,&decoded,sizeof(prior)));
    AW_ITEM_ROW(&decoded.state,AW_ItemIndex(&decoded.state,ring.id))->condition=.375f;
    assert(AW_InventoryPickup(&decoded.state,index));assert(AW_StateGet(&decoded.state,AW_ITEM,ring.id)==3);
    assert(AW_InventoryEquipped(&decoded.state,ring.id)==1);
    AW_SaveRelease(&decoded);
    /* Feature bit 4: the selected magic item and a recorded charge round-trip;
     * a selection of an item not owned is refused. */
    {
        static aw_save_t magic;int msize;static unsigned char mbytes[AW_SAVE_BYTES];
        copy_save(&magic,&save);
        strcpy(magic.state.magic.selected,"synthetic_ring");AW_ItemMark(&magic.state,0,AW_ITEM_CHARGE,7.5f);
        msize=AW_SaveEncode(mbytes,sizeof(mbytes),&magic);assert(msize>size);
        memset(&decoded,0,sizeof(decoded));assert(AW_SaveDecode(mbytes,msize,&decoded));
        assert(!strcmp(decoded.state.magic.selected,"synthetic_ring") && AW_ITEM_ROW(&decoded.state,0)->charge==7.5f);
        assert(AW_ITEM_HAS(&decoded.state,0,AW_ITEM_CHARGE));AW_SaveRelease(&decoded);
        strcpy(magic.state.magic.selected,"not_owned");assert(!AW_SaveEncode(mbytes,sizeof(mbytes),&magic));
        assert(AW_SaveDecode(bytes,size,&decoded) && !decoded.state.magic.selected[0]);AW_SaveRelease(&decoded);
        AW_SaveRelease(&magic);
    }
    /* INVENTORY-ORIGINAL-LIMITS-61: up to 32 kinds the save is as before (no feature bit); past 32 it is feature 512
     * with ceil(kinds / 32) mark words: 400 kinds, every kind, condition and charge round-trip, the last row's marks
     * included; a feature 256 save (the 128-kind table of the v0.0.61 line, 4 mark words) still loads; a bit that
     * does not match the kinds, or both bits, is refused. */
    {
        static aw_save_t wide,back;static unsigned char wbytes[AW_SAVE_MAX_BYTES/4];int wsize,i,at;char id[32];uint32_t f;
        copy_save(&wide,&save);
        for(i=AW_ItemCount(&wide.state);i<32;i++){sprintf(id,"kind_%d",i);assert(AW_ItemAdd(&wide.state,id,1));}
        wsize=AW_SaveEncode(wbytes,sizeof(wbytes),&wide);assert(wsize>0);
        assert(AW_SaveDecode(wbytes,wsize,&back) && same_state(&back.state,&wide.state));AW_SaveRelease(&back);
        for(i=32;i<400;i++){sprintf(id,"kind_%d",i);assert(AW_ItemAdd(&wide.state,id,2));}
        assert(AW_ItemCount(&wide.state)==400 && AW_ItemRoom(&wide.state)>0);
        AW_ItemMark(&wide.state,399,AW_ITEM_CONDITION,.25f);AW_ItemMark(&wide.state,40,AW_ITEM_CONDITION,.75f);
        AW_ItemMark(&wide.state,270,AW_ITEM_CHARGE,3.5f);AW_ItemMark(&wide.state,399,AW_ITEM_CHARGE,9);
        wsize=AW_SaveEncode(wbytes,sizeof(wbytes),&wide);assert(wsize>0);
        memset(&back,0,sizeof(back));
        assert(AW_SaveDecode(wbytes,wsize,&back) && same_state(&back.state,&wide.state));
        assert(AW_ITEM_ROW(&back.state,399)->condition==.25f && AW_ITEM_ROW(&back.state,270)->charge==3.5f);
        assert(!strcmp(AW_ITEM_ID(&back.state,399),"kind_399") && AW_StateGet(&back.state,AW_ITEM,"kind_200")==2);
        AW_SaveRelease(&back);
        /* the features word sits after the journal; find it by its value (512 | 2 | 4 here) and break it */
        for(at=12;at+4<=wsize;at++){f=wbytes[at]|(wbytes[at+1]<<8)|(wbytes[at+2]<<16)|((uint32_t)wbytes[at+3]<<24);if(f==(512U|2U|4U))break;}
        assert(at+4<=wsize);
        wbytes[at+1]^=3;   /* 512 -> 256: a 128-kind feature with 400 kinds, refused (the CRC is fixed below) */
        {   /* recompute the CRC so only the features word is wrong */
            uint32_t crc=0xffffffffU;int n,k;
            for(n=12;n<wsize;n++){crc^=wbytes[n];for(k=0;k<8;k++)crc=(crc>>1)^((crc&1)?0xedb88320U:0);}
            crc^=0xffffffffU;wbytes[8]=crc;wbytes[9]=crc>>8;wbytes[10]=crc>>16;wbytes[11]=crc>>24;
        }
        memset(&back,0,sizeof(back));assert(!AW_SaveDecode(wbytes,wsize,&back) && !back.state.items.block);
        /* a 128-kind save of the v0.0.61 line: feature 256 and 4 mark words */
        {
            static aw_save_t old;copy_save(&old,&save);
            for(i=AW_ItemCount(&old.state);i<128;i++){sprintf(id,"kind_%d",i);assert(AW_ItemAdd(&old.state,id,1));}
            AW_ItemMark(&old.state,127,AW_ITEM_CONDITION,.5f);
            wsize=AW_SaveEncode(wbytes,sizeof(wbytes),&old);assert(wsize>0);   /* feature 512, 4 words for 128 kinds */
            for(at=12;at+4<=wsize;at++){f=wbytes[at]|(wbytes[at+1]<<8)|(wbytes[at+2]<<16)|((uint32_t)wbytes[at+3]<<24);if(f==(512U|2U))break;}
            assert(at+4<=wsize);wbytes[at+1]=1;   /* 512 -> 256: the same bytes as the 128-kind table wrote */
            {uint32_t crc=0xffffffffU;int n,k;
             for(n=12;n<wsize;n++){crc^=wbytes[n];for(k=0;k<8;k++)crc=(crc>>1)^((crc&1)?0xedb88320U:0);}
             crc^=0xffffffffU;wbytes[8]=crc;wbytes[9]=crc>>8;wbytes[10]=crc>>16;wbytes[11]=crc>>24;}
            assert(AW_SaveDecode(wbytes,wsize,&back) && same_state(&back.state,&old.state));
            assert(AW_ITEM_ROW(&back.state,127)->condition==.5f);AW_SaveRelease(&back);AW_SaveRelease(&old);
        }
        AW_SaveRelease(&wide);
    }
    assert(AW_SaveDecode(bytes,size,&decoded));
    prior=decoded;bytes[size-1]^=1;assert(!AW_SaveDecode(bytes,size,&decoded));assert(!memcmp(&prior,&decoded,sizeof(prior)));
    AW_SaveRelease(&decoded);
    save.state.inventory.dropped[index].count=-1;assert(!AW_SaveEncode(bytes,sizeof(bytes),&save));
    save.state.inventory.dropped[index].count=2;save.state.inventory.dropped[index].serial=0;assert(!AW_SaveEncode(bytes,sizeof(bytes),&save));
    AW_SaveRelease(&save);
    return 0;
}
