/* SPDX-License-Identifier: GPL-3.0-only
 * The world change list (CELL-CHANGES-59; engine aw_ledger.h, aw_ledger.c, aw_ledger_drops.c, the save codec's
 * feature 32; tests/test_world_ledger.py). Writes (to argv[1]) one line per part, then checks: rows kept sorted and
 * found by key, a row with no field left goes, the place order finds exactly a place's rows (and follows a moved
 * place); the saved form encodes, decodes and encodes again to the same bytes with every field combination and every
 * kind of place, also with 20,000 rows (no 2,048 ceiling); each field alone survives a save and a load; TAKEN and
 * DISABLED stay apart; a broken row is refused on writing and on reading; a save with the list does not load without
 * the list's reader; an older save keeps loading; the drops: 40 drops (past the old 32) and a pickup, a refused drop
 * changes nothing, condition kept both ways, an older save's dropped items move onto the list.
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "aw_story.h"
#include "aw_save.h"
#include "aw_maps.h"
#include "aw_ledger.h"
#include "aw_inventory.h"
aw_race_t aw_races[16];aw_class_t aw_classes[32];aw_birth_t aw_births[16];aw_part_t aw_parts[384];
int aw_race_count=1,aw_class_count=1,aw_birth_count=1,aw_part_count=2;
static aw_save_t save,decoded;
static aw_changes_t changes,back;
static aw_ledger_t list,got,other_list;
static aw_state_t inv;
static unsigned char one[AW_SAVE_MAX_BYTES],two[AW_SAVE_MAX_BYTES];
static FILE *o;

static void base(void)
{
    strcpy(aw_races[0].id,"race");strcpy(aw_classes[0].id,"class");strcpy(aw_births[0].id,"birth");
    strcpy(aw_parts[0].id,"head");strcpy(aw_parts[1].id,"hair");aw_parts[1].kind=1;
    memset(&save,0,sizeof(save));
    save.sequence=save.profile=1;strcpy(save.scene,"seyda");strcpy(save.story.name,"Player");
    save.story.stage=AW_STAGE_RELEASED;save.story.ship_disabled=1;save.story.captain=-1;
    save.character.valid=1;save.character.level=1;save.character.hair=1;
    assert(AW_StateSet(&save.state,AW_GLOBAL,"CharGenState",-1));
}
static int32_t cell(int x,int y){return (int32_t)(((uint32_t)(x&0xffff)<<16)|(uint32_t)(y&0xffff));}
/* a row with FIELDS at a place; moved and dropped rows get a position (and a drop its item) */
static aw_ledger_row_t *row(aw_ledger_t *l,uint32_t key,unsigned fields,int at,int32_t where)
{
    aw_ledger_row_t *r=AW_LedgerPut(l,key);aw_ledger_extra_t *x;
    assert(r);r->fields=(uint8_t)fields;AW_LedgerSetPlace(l,r,at,where);
    if(fields&AW_LEDGER_LOCK){r->lock=(uint8_t)(key%101);r->last_lock=(uint8_t)((key/3)%101);}
    if(fields&(AW_LEDGER_MOVED|AW_LEDGER_DROPPED)){
        x=AW_LedgerExtra(l,r);assert(x);
        x->position[0]=(float)(key&AW_LEDGER_ID)*0.5f;x->position[1]=-(float)(key%977);x->position[2]=12.25f;x->yaw=(float)(key%360);
        if(fields&AW_LEDGER_DROPPED){x->count=(int32_t)(key%7)+1;sprintf(x->item,"misc_item_%u",(unsigned)((key&AW_LEDGER_ID)%100));}
        if(fields&AW_LEDGER_CONDITION)x->condition=0.25f;
    }
    return r;
}
static int same(const aw_ledger_t *a,const aw_ledger_t *b)
{
    int i;
    if(a->count!=b->count)return 0;
    for(i=0;i<a->count;i++){
        const aw_ledger_row_t *x=&a->row[i],*y=&b->row[i];
        if(x->key!=y->key || x->fields!=y->fields || x->at!=y->at || x->where!=y->where || x->lock!=y->lock ||
           x->last_lock!=y->last_lock || !x->extra!=!y->extra)return 0;
        if(x->extra && (memcmp(x->extra->position,y->extra->position,sizeof(x->extra->position)) ||
           x->extra->yaw!=y->extra->yaw || ((x->fields&AW_LEDGER_DROPPED) &&
           (x->extra->count!=y->extra->count || strcmp(x->extra->item,y->extra->item))) ||
           ((x->fields&AW_LEDGER_CONDITION) && x->extra->condition!=y->extra->condition)))return 0;
    }
    return 1;
}
/* encode, decode, encode: the same bytes; returns the size */
static int round_trip(aw_ledger_t *l)
{
    int n=AW_LedgerEncode(l,NULL,0),m;
    assert(n>0 && n<=(int)sizeof(one));
    assert(AW_LedgerEncode(l,one,n)==n);
    assert(AW_LedgerDecode(one,n,&got));
    assert(same(l,&got));
    m=AW_LedgerEncode(&got,two,sizeof(two));assert(m==n && !memcmp(one,two,n));
    assert(AW_LedgerDecode(one,n,NULL));               /* checked, not kept */
    return n;
}
/* a save with list L, loaded back into READ; returns the save's size */
static int save_trip(aw_ledger_t *l)
{
    int n;
    changes.count=0;changes.ledger=l;
    n=AW_SaveEncodeChanges(one,sizeof(one),&save,&changes);assert(n>AW_SAVE_BYTES/1000);
    AW_LedgerClear(&got);back.ledger=&got;
    assert(AW_SaveDecodeChanges(one,n,&decoded,&back));
    assert(same(l,&got));
    return n;
}
static void refused(aw_ledger_t *l){assert(AW_LedgerEncode(l,NULL,0)==0);assert(AW_LedgerEncode(l,one,sizeof(one))==0);}

int main(int argc,char **argv)
{
    int i,n,first,size;unsigned f;aw_ledger_row_t *r;
    o=argc>1?fopen(argv[1],"w"):stdout;assert(o);
    aw_save_ledger_rows=AW_LedgerRows;aw_save_ledger_encode=AW_LedgerEncode;aw_save_ledger_decode=AW_LedgerDecode;
    base();

    /* 1. sorted, found by key, the same row twice, a row with no field left goes */
    for(i=0;i<500;i++)assert(AW_LedgerPut(&list,(uint32_t)((i*7919)%500+1)));
    assert(list.count==500);
    for(i=1;i<list.count;i++)assert(list.row[i-1].key<list.row[i].key);
    for(i=1;i<=500;i++)assert(AW_LedgerFind(&list,(uint32_t)i)==i-1);
    assert(AW_LedgerFind(&list,501)<0 && AW_LedgerPut(&list,7)==&list.row[6] && list.count==500);
    AW_LedgerTidy(&list,7);assert(list.count==499 && AW_LedgerFind(&list,7)<0);
    list.row[AW_LedgerFind(&list,8)].fields=AW_LEDGER_TAKEN;AW_LedgerTidy(&list,8);assert(AW_LedgerFind(&list,8)>=0);
    assert(AW_LedgerFrom(&list,AW_LEDGER_PLAYER)==list.count);
    AW_LedgerClear(&list);assert(!list.count && !list.row);
    fprintf(o,"rows ok\n");

    /* 2. the place order: a room's, a cell's, a scene's and the unknown place's rows, and a row moved to another */
    row(&list,10,AW_LEDGER_TAKEN,AW_AT_ROOM,203);row(&list,11,AW_LEDGER_DISABLED,AW_AT_ROOM,203);
    row(&list,12,AW_LEDGER_TAKEN,AW_AT_ROOM,204);row(&list,13,AW_LEDGER_TAKEN,AW_AT_CELL,cell(-2,-9));
    row(&list,14,AW_LEDGER_TAKEN,AW_AT_CELL,cell(-2,-9));row(&list,15,AW_LEDGER_DISABLED,AW_AT_ANY,0);
    row(&list,16,AW_LEDGER_TAKEN,AW_AT_SCENE,AW_MapId("census"));
    assert(AW_LedgerPlace(&list,AW_AT_ROOM,203,&first)==2);
    assert(AW_LedgerPlaceRow(&list,first)->key==10 && AW_LedgerPlaceRow(&list,first+1)->key==11);
    assert(AW_LedgerPlace(&list,AW_AT_ROOM,204,&first)==1 && AW_LedgerPlaceRow(&list,first)->key==12);
    assert(AW_LedgerPlace(&list,AW_AT_CELL,cell(-2,-9),&first)==2);
    assert(AW_LedgerPlace(&list,AW_AT_CELL,cell(-2,-8),&first)==0);
    assert(AW_LedgerPlace(&list,AW_AT_ANY,0,&first)==1 && AW_LedgerPlaceRow(&list,first)->key==15);
    assert(AW_LedgerPlace(&list,AW_AT_SCENE,AW_MapId("census"),&first)==1);
    AW_LedgerSetPlace(&list,&list.row[AW_LedgerFind(&list,12)],AW_AT_ROOM,203);
    assert(AW_LedgerPlace(&list,AW_AT_ROOM,203,&first)==3 && AW_LedgerPlace(&list,AW_AT_ROOM,204,&first)==0);
    AW_LedgerClear(&list);
    fprintf(o,"places ok\n");

    /* 3. every field combination at every kind of place: encode, decode, encode the same bytes */
    {uint32_t key=100;
     for(f=1;f<=AW_LEDGER_FIELDS;f++){
         int at;int32_t where;
         if(f&(AW_LEDGER_DROPPED|AW_LEDGER_CONDITION))continue;      /* drops: below, under key bit 30 */
         for(at=AW_AT_ANY;at<=AW_AT_SCENE;at++){
             where=at==AW_AT_ANY?0:at==AW_AT_CELL?cell(-3,(int)(key%20)-10):at==AW_AT_ROOM?(int32_t)key:AW_MapId("seyda");
             row(&list,key,f,at,where);key++;
         }
     }
     for(i=1;i<=6;i++){
         unsigned fields=AW_LEDGER_DROPPED|(i&1?AW_LEDGER_CONDITION:0)|(i&2?AW_LEDGER_MOVED:0)|(i&4?AW_LEDGER_STOLEN:0);
         row(&list,AW_LEDGER_PLAYER|(uint32_t)i,fields,i%2?AW_AT_CELL:AW_AT_ROOM,i%2?cell(1,-7):55);
     }
     row(&list,AW_LEDGER_BUILDER|3,AW_LEDGER_DISABLED,AW_AT_ANY,0);}
    size=round_trip(&list);
    fprintf(o,"combinations %d rows %d bytes\n",list.count,size);
    size=save_trip(&list);
    fprintf(o,"save %d bytes\n",size);

    /* 4. each field alone survives a save and a load; TAKEN and DISABLED stay apart */
    {static const unsigned alone[]={AW_LEDGER_TAKEN,AW_LEDGER_DISABLED,AW_LEDGER_LOCK,AW_LEDGER_STOLEN,AW_LEDGER_MOVED};
     for(i=0;i<5;i++){
         AW_LedgerClear(&other_list);row(&other_list,484475,alone[i],AW_AT_CELL,cell(-2,-9));save_trip(&other_list);
         assert(got.count==1 && got.row[0].fields==alone[i]);
     }
     AW_LedgerClear(&other_list);
     row(&other_list,AW_LEDGER_PLAYER|9,AW_LEDGER_DROPPED|AW_LEDGER_CONDITION,AW_AT_ROOM,203);save_trip(&other_list);
     assert(got.row[0].extra && got.row[0].extra->count==other_list.row[0].extra->count &&
            !strcmp(got.row[0].extra->item,"misc_item_9") && got.row[0].extra->condition==0.25f);
     AW_LedgerClear(&other_list);
     r=row(&other_list,172851,AW_LEDGER_TAKEN,AW_AT_ROOM,7);row(&other_list,172852,AW_LEDGER_DISABLED,AW_AT_ROOM,7);
     save_trip(&other_list);
     assert(got.row[0].fields==AW_LEDGER_TAKEN && got.row[1].fields==AW_LEDGER_DISABLED);
     (void)r;}
    fprintf(o,"fields ok\n");

    /* 5. 20,000 rows: no 2,048 ceiling, in the saved form and in a save */
    AW_LedgerClear(&list);
    for(i=0;i<20000;i++)row(&list,(uint32_t)(i*3+1),i%5==0?AW_LEDGER_MOVED|AW_LEDGER_TAKEN:AW_LEDGER_TAKEN,AW_AT_CELL,cell(i%40-20,i%30-15));
    size=round_trip(&list);
    n=save_trip(&list);assert(n>AW_SAVE_BYTES/4);
    fprintf(o,"big %d rows %d bytes, save %d bytes, %lu bytes resident\n",list.count,size,n,AW_LedgerResident(&list));

    /* 6. refused on writing: bits 24-29, a drop without key bit 30 and key bit 30 without a drop, condition
     * without a drop, an unknown field, a lock past 100 (and a lock level without its field), places of the wrong
     * kind, a position that is not a number, a drop with no item or count; and on reading: a stray bit, a key out of
     * order, cut bytes, a byte too many, another magic */
    {static const struct {uint32_t key;unsigned fields;int at;int32_t where;} bad[]={
        {0x01000005,AW_LEDGER_TAKEN,AW_AT_ANY,0},{0x20000005,AW_LEDGER_TAKEN,AW_AT_ANY,0},
        {5,AW_LEDGER_DROPPED,AW_AT_ROOM,3},{AW_LEDGER_PLAYER|5,AW_LEDGER_TAKEN,AW_AT_ROOM,3},
        {AW_LEDGER_PLAYER|AW_LEDGER_BUILDER|5,AW_LEDGER_DROPPED,AW_AT_ROOM,3},
        {5,AW_LEDGER_CONDITION|AW_LEDGER_TAKEN,AW_AT_ROOM,3},{5,0x80,AW_AT_ROOM,3},
        {5,AW_LEDGER_TAKEN,AW_AT_ROOM,0},{5,AW_LEDGER_TAKEN,AW_AT_ANY,4},{5,AW_LEDGER_TAKEN,AW_AT_CELL,0x7fff0000},
        {5,AW_LEDGER_TAKEN,AW_AT_SCENE,0x10000},{5,AW_LEDGER_TAKEN,9,0}};
     for(i=0;i<(int)(sizeof(bad)/sizeof(bad[0]));i++){
         AW_LedgerClear(&other_list);r=AW_LedgerPut(&other_list,bad[i].key);
         r->fields=(uint8_t)bad[i].fields;r->at=(uint8_t)bad[i].at;r->where=bad[i].where;
         if(bad[i].fields&(AW_LEDGER_DROPPED|AW_LEDGER_MOVED|AW_LEDGER_CONDITION)){
             aw_ledger_extra_t *x=AW_LedgerExtra(&other_list,r);x->count=1;strcpy(x->item,"gold_001");}
         refused(&other_list);
     }
     AW_LedgerClear(&other_list);r=row(&other_list,5,AW_LEDGER_LOCK,AW_AT_ROOM,3);r->lock=101;refused(&other_list);
     r->lock=50;r->fields=AW_LEDGER_TAKEN;refused(&other_list);
     AW_LedgerClear(&other_list);r=row(&other_list,5,AW_LEDGER_MOVED,AW_AT_ROOM,3);r->extra->position[1]=NAN;refused(&other_list);
     r->extra->position[1]=0;r->extra->yaw=1000;refused(&other_list);
     AW_LedgerClear(&other_list);r=AW_LedgerPut(&other_list,5);r->fields=AW_LEDGER_MOVED;r->at=AW_AT_ROOM;r->where=3;
     refused(&other_list);                                          /* a position without its block */
     AW_LedgerClear(&other_list);r=row(&other_list,AW_LEDGER_PLAYER|5,AW_LEDGER_DROPPED,AW_AT_ROOM,3);
     r->extra->item[0]=0;refused(&other_list);strcpy(r->extra->item,"gold_001");r->extra->count=0;refused(&other_list);
     r->extra->count=3;assert(AW_LedgerEncode(&other_list,NULL,0)>0);
     /* reading */
     AW_LedgerClear(&other_list);row(&other_list,5,AW_LEDGER_TAKEN,AW_AT_ROOM,3);row(&other_list,6,AW_LEDGER_TAKEN,AW_AT_ROOM,3);
     n=AW_LedgerEncode(&other_list,one,sizeof(one));assert(n==8+2*12);
     one[8+3]|=0x01;assert(!AW_LedgerDecode(one,n,&got));one[8+3]&=~0x01;     /* bit 24 */
     one[8+4]|=0x80;assert(!AW_LedgerDecode(one,n,&got));one[8+4]&=~0x80;     /* an unknown field */
     one[8]=7;assert(!AW_LedgerDecode(one,n,&got));one[8]=5;                  /* 7 then 6: out of order */
     assert(!AW_LedgerDecode(one,n-1,&got) && !AW_LedgerDecode(one,n+1,&got));
     one[0]='X';assert(!AW_LedgerDecode(one,n,&got));one[0]='A';
     assert(AW_LedgerDecode(one,n,&got) && got.count==2);
     /* a refused read leaves the list it was to fill as it was, never half filled */
     one[8+12+4]=0x80;assert(!AW_LedgerDecode(one,n,&got) && got.count==2);}
    fprintf(o,"refusals ok\n");

    /* 7. a save with the list does not load without the list's reader (an older engine refuses feature 32 the
     * same way); a save without a list loads and leaves the list alone; a list with no row writes no section */
    {int k;
     AW_LedgerClear(&other_list);row(&other_list,77,AW_LEDGER_TAKEN,AW_AT_ROOM,3);
     changes.count=0;changes.ledger=&other_list;
     k=AW_SaveEncodeChanges(one,sizeof(one),&save,&changes);assert(k>0);
     aw_save_ledger_decode=NULL;assert(!AW_SaveDecodeChanges(one,k,&decoded,NULL));
     aw_save_ledger_decode=AW_LedgerDecode;assert(AW_SaveDecodeChanges(one,k,&decoded,NULL));
     AW_LedgerClear(&other_list);changes.ledger=&other_list;
     n=AW_SaveEncodeChanges(two,sizeof(two),&save,&changes);
     assert(n>0 && n==AW_SaveEncodeChanges(one,sizeof(one),&save,NULL) && !memcmp(one,two,n));
     AW_LedgerClear(&got);row(&got,99,AW_LEDGER_TAKEN,AW_AT_ROOM,3);back.ledger=&got;
     assert(AW_SaveDecodeChanges(two,n,&decoded,&back) && got.count==1);
     /* the buffer the save needs: a save over AW_SAVE_BYTES is written when given the room */
     changes.ledger=&list;
     assert(!AW_SaveEncodeChanges(one,AW_SAVE_BYTES/64,&save,&changes));}
    fprintf(o,"versions ok\n");

    /* 8. the drops: 40 of them (the old table held 32), a pickup, a refused drop changes nothing, condition both
     * ways, an older save's dropped items move onto the list */
    {aw_inventory_item_t item;uint32_t keys[40];int32_t before;
     memset(&item,0,sizeof(item));strcpy(item.id,"misc_com_bottle_01");strcpy(item.model,"progs/items/x.mdl");
     item.flags=AW_INV_DROP;
     memset(&inv,0,sizeof(inv));AW_LedgerClear(&list);
     assert(AW_ItemAdd(&inv,item.id,45));
     for(i=0;i<40;i++){
         float at[3];at[0]=(float)i*16;at[1]=-74000;at[2]=120;
         keys[i]=AW_LedgerDrop(&inv,&list,&item,1,AW_AT_CELL,cell(-2,-10),at,90);
         assert(keys[i]==(AW_LEDGER_PLAYER|(uint32_t)(i+1)));
     }
     assert(list.count==40 && AW_StateGet(&inv,AW_ITEM,item.id)==5 && inv.inventory.next_serial==40);
     assert(AW_LedgerPlace(&list,AW_AT_CELL,cell(-2,-10),&first)==40);
     size=save_trip(&list);
     assert(AW_LedgerPickup(&inv,&list,keys[3]) && list.count==39 && AW_StateGet(&inv,AW_ITEM,item.id)==6);
     assert(!AW_LedgerPickup(&inv,&list,keys[3]));                 /* gone */
     before=AW_StateGet(&inv,AW_ITEM,item.id);
     {float at[3]={0,0,0};
      assert(!AW_LedgerDrop(&inv,&list,&item,before+1,AW_AT_CELL,cell(0,0),at,0));       /* more than held */
      assert(!AW_LedgerDrop(&inv,&list,&item,1,AW_AT_ANY,0,at,0));                        /* no place */
      at[0]=NAN;assert(!AW_LedgerDrop(&inv,&list,&item,1,AW_AT_CELL,cell(0,0),at,0));
      item.flags=0;at[0]=0;assert(!AW_LedgerDrop(&inv,&list,&item,1,AW_AT_CELL,cell(0,0),at,0));item.flags=AW_INV_DROP;}
     assert(list.count==39 && AW_StateGet(&inv,AW_ITEM,item.id)==before && inv.inventory.next_serial==40);
     /* condition: the last one, worn, dropped and taken back */
     {aw_inventory_item_t blade=item;float at[3]={5,5,5};uint32_t k;int idx;
      strcpy(blade.id,"iron dagger");assert(AW_ItemAdd(&inv,blade.id,1));
      for(idx=0;strcmp(inv.values[AW_ITEM][idx].id,"iron dagger");idx++);
      inv.inventory.condition_known|=1U<<idx;inv.inventory.condition[idx]=0.5f;
      k=AW_LedgerDrop(&inv,&list,&blade,1,AW_AT_ROOM,203,at,10);assert(k);
      r=&list.row[AW_LedgerFind(&list,k)];
      assert((r->fields&AW_LEDGER_CONDITION) && r->extra->condition==0.5f && !(inv.inventory.condition_known&(1U<<idx)));
      assert(AW_LedgerPickup(&inv,&list,k) && (inv.inventory.condition_known&(1U<<idx)) && inv.inventory.condition[idx]==0.5f);}
     /* an older save's drops (keyed by the map's name) */
     memset(&inv.inventory.dropped,0,sizeof(inv.inventory.dropped));
     strcpy(inv.inventory.dropped[0].id,"gold_001");strcpy(inv.inventory.dropped[0].scene,"seyda");
     inv.inventory.dropped[0].count=12;inv.inventory.dropped[0].serial=41;inv.inventory.dropped[0].position[0]=33;
     strcpy(inv.inventory.dropped[5].id,"iron dagger");strcpy(inv.inventory.dropped[5].scene,"census");
     inv.inventory.dropped[5].count=1;inv.inventory.dropped[5].serial=42;
     inv.inventory.dropped[5].condition_known=1;inv.inventory.dropped[5].condition=0.75f;
     inv.inventory.next_serial=42;
     assert(AW_LedgerAdoptDrops(&inv,&list)==2 && !inv.inventory.dropped[0].count && !inv.inventory.dropped[5].count);
     r=&list.row[AW_LedgerFind(&list,AW_LEDGER_PLAYER|41)];
     assert(r->at==AW_AT_SCENE && r->where==AW_MapId("seyda") && r->extra->count==12 && r->extra->position[0]==33);
     r=&list.row[AW_LedgerFind(&list,AW_LEDGER_PLAYER|42)];
     assert(r->where==AW_MapId("census") && (r->fields&AW_LEDGER_CONDITION) && r->extra->condition==0.75f);
     assert(AW_LedgerAdoptDrops(&inv,&list)==0);
     save_trip(&list);
     fprintf(o,"drops %d rows, save %d bytes\n",list.count,size);}

    AW_LedgerClear(&list);AW_LedgerClear(&got);AW_LedgerClear(&other_list);
    fprintf(o,"done\n");
    if(o!=stdout)fclose(o);
    return 0;
}
