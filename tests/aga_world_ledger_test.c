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
    if(a->count!=b->count || a->stolen_count!=b->stolen_count || a->content_count!=b->content_count ||
       a->rank_count!=b->rank_count)return 0;
    for(i=0;i<a->content_count;i++)
        if(a->content[i].key!=b->content[i].key || strcmp(a->content[i].item,b->content[i].item) ||
           a->content[i].count!=b->content[i].count)return 0;
    for(i=0;i<a->rank_count;i++)if(a->rank[i].key!=b->rank[i].key || a->rank[i].rank!=b->rank[i].rank)return 0;
    for(i=0;i<a->stolen_count;i++){
        const aw_ledger_stolen_t *x=&a->stolen[i],*y=&b->stolen[i];
        if(strcmp(x->item,y->item) || strcmp(x->owner,y->owner) || x->faction!=y->faction || x->count!=y->count)return 0;
    }
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
        {5,AW_LEDGER_CONDITION|AW_LEDGER_TAKEN,AW_AT_ROOM,3},
        {AW_LEDGER_PLAYER|5,AW_LEDGER_DROPPED|AW_LEDGER_OPEN,AW_AT_ROOM,3},      /* a drop is never an open door */
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

    /* 9. slice 2: doors, locks, the stolen mark. OPEN alone and with a lock survives a save and a load; a list without
     * OPEN or a stolen pair keeps the first form (an engine of slice 1 reads it), one with them takes the second, which
     * the first never carried; the stolen pairs: added, folded, counted, given back, never gold, kept across a drop, a
     * pickup and a save, alone a reason to save; refused when broken */
    {static aw_ledger_t s;int k;aw_inventory_item_t q;float at[3]={1,2,3};uint32_t key;
     AW_LedgerClear(&other_list);r=row(&other_list,51,AW_LEDGER_LOCK,AW_AT_ROOM,3);
     k=AW_LedgerEncode(&other_list,one,sizeof(one));assert(k>0 && !memcmp(one,"AWL1",4));
     r->fields|=AW_LEDGER_OPEN;row(&other_list,52,AW_LEDGER_OPEN,AW_AT_CELL,cell(-2,-9));
     k=AW_LedgerEncode(&other_list,one,sizeof(one));assert(k>0 && !memcmp(one,"AWL2",4));
     one[3]='1';assert(!AW_LedgerDecode(one,k,&got));one[3]='2';          /* the first form never had OPEN */
     round_trip(&other_list);save_trip(&other_list);
     assert(got.count==2 && got.row[0].fields==(AW_LEDGER_LOCK|AW_LEDGER_OPEN) && got.row[0].lock==51 &&
            got.row[1].fields==AW_LEDGER_OPEN && !got.stolen_count);
     /* a lock alone: a script's Lock, a key's Unlock (level 0, the last level kept) */
     AW_LedgerClear(&other_list);r=row(&other_list,53,AW_LEDGER_LOCK,AW_AT_ANY,0);r->lock=0;r->last_lock=40;
     save_trip(&other_list);assert(got.row[0].lock==0 && got.row[0].last_lock==40);
     fprintf(o,"doors and locks ok\n");
     /* the stolen pairs */
     assert(AW_LedgerStolenAdd(&s,"Misc_Quill","Fargoth",0,1)==1);
     assert(AW_LedgerStolenAdd(&s,"misc_quill","fargoth",0,2)==3);          /* folded: the same pair */
     assert(AW_LedgerStolenAdd(&s,"misc_quill","Hlaalu",1,1)==1);           /* a faction: a pair of its own */
     assert(AW_LedgerStolenAdd(&s,"misc_quill","hlaalu",0,1)==1);           /* an owner of that name: another */
     assert(AW_LedgerStolenAdd(&s,"iron dagger","fargoth",0,1)==1);
     assert(!AW_LedgerStolenAdd(&s,"Gold_001","fargoth",0,5) && !AW_LedgerStolenAdd(&s,"","fargoth",0,1) &&
            !AW_LedgerStolenAdd(&s,"misc_quill","",0,1) && !AW_LedgerStolenAdd(&s,"misc_quill",NULL,0,1) &&
            !AW_LedgerStolenAdd(&s,"x23456789012345678901234567890123","fargoth",0,1) &&
            !AW_LedgerStolenAdd(&s,"misc_quill","fargoth",0,0) && !AW_LedgerStolenAdd(&s,"misc_cup","fargoth",0,-1));
     assert(s.stolen_count==4 && AW_LedgerStolenCount(&s,"MISC_QUILL",NULL,0)==5 &&
            AW_LedgerStolenCount(&s,"misc_quill","fargoth",0)==3 && AW_LedgerStolenCount(&s,"misc_quill","hlaalu",1)==1 &&
            AW_LedgerStolenCount(&s,"misc_cup",NULL,0)==0 && !s.count && AW_LedgerRows(&s)==4);
     for(i=1;i<s.stolen_count;i++)assert(strcmp(s.stolen[i-1].item,s.stolen[i].item)<=0);
     k=AW_LedgerEncode(&s,one,sizeof(one));assert(k>0 && !memcmp(one,"AWL2",4));
     round_trip(&s);
     n=save_trip(&s);assert(!got.count && got.stolen_count==4 && AW_LedgerStolenCount(&got,"misc_quill","fargoth",0)==3);
     /* the mark goes with the item: dropped (a row of the list), saved, picked up, the pairs never change */
     memset(&q,0,sizeof(q));strcpy(q.id,"misc_quill");strcpy(q.model,"progs/items/x.mdl");q.flags=AW_INV_DROP;
     memset(&inv,0,sizeof(inv));assert(AW_ItemAdd(&inv,q.id,3));
     key=AW_LedgerDrop(&inv,&s,&q,1,AW_AT_CELL,cell(-2,-9),at,0);assert(key && s.count==1);
     save_trip(&s);assert(got.count==1 && AW_LedgerStolenCount(&got,"misc_quill","fargoth",0)==3);
     assert(AW_LedgerPickup(&inv,&s,key) && !s.count && AW_LedgerStolenCount(&s,"misc_quill",NULL,0)==5);
     /* given back (CRIME-59 later: returned or confiscated): the count falls, a pair at 0 goes, never below */
     assert(AW_LedgerStolenAdd(&s,"misc_quill","fargoth",0,-2)==1);
     assert(AW_LedgerStolenAdd(&s,"misc_quill","hlaalu",1,-5)==0 && s.stolen_count==3);
     assert(AW_LedgerStolenCount(&s,"misc_quill",NULL,0)==2);
     /* refused on reading: a pair not folded, out of order, a faction flag past 1, a count of 0, cut bytes, nothing
      * at all; a refused read leaves the list it was to fill as it was */
     k=AW_LedgerEncode(&s,one,sizeof(one));assert(k>0);
     AW_LedgerClear(&got);assert(AW_LedgerDecode(one,k,&got) && got.stolen_count==3);
     assert(one[12]==11 && one[13]=='i');                                   /* "iron dagger" comes first */
     one[13]='I';assert(!AW_LedgerDecode(one,k,&got) && got.stolen_count==3);one[13]='i';
     one[13]='z';assert(!AW_LedgerDecode(one,k,&got));one[13]='i';        /* after the quills: out of order */
     assert(one[12+1+11]==7 && one[12+1+11+1+7]==0);                        /* "fargoth", a person */
     one[12+1+11+1+7]=2;assert(!AW_LedgerDecode(one,k,&got));one[12+1+11+1+7]=0;
     assert(one[12+1+11+1+7+1]==1);
     one[12+1+11+1+7+1]=0;assert(!AW_LedgerDecode(one,k,&got));one[12+1+11+1+7+1]=1;
     assert(!AW_LedgerDecode(one,k-1,&got) && !AW_LedgerDecode(one,k+1,&got));
     memcpy(two,"AWL2\0\0\0\0\0\0\0\0",12);assert(!AW_LedgerDecode(two,12,&got));
     assert(AW_LedgerDecode(one,k,&got) && same(&s,&got));
     fprintf(o,"stolen %d pairs, save %d bytes\n",s.stolen_count,n);
     AW_LedgerClear(&s);}

    /* 10. slice 3: container deltas and NPC ranks. Deltas against the data: taken out (< 0), put in (> 0), folded,
     * summed, an entry back at 0 goes; kept per container; the third form only when there is one, and an older list
     * keeps its form; 3,000 deltas past any small table; the stolen mark of slice 2 with them; ranks set, kept, saved;
     * refusals on writing and reading */
    {static aw_ledger_t c;int k,first,m;
     assert(AW_LedgerContentAdd(&c,1001,"Potion_Restore_Health",-2)==-2);
     assert(AW_LedgerContentAdd(&c,1001,"potion_restore_health",-1)==-3);   /* folded: the same entry */
     assert(AW_LedgerContentAdd(&c,1001,"gold_001",-25)==-25);             /* a container's gold is an item */
     assert(AW_LedgerContentAdd(&c,1001,"misc_quill",1)==1);               /* put in: the data had none */
     assert(AW_LedgerContentAdd(&c,1000,"misc_quill",4)==4);
     assert(AW_LedgerContentAdd(&c,1001,"misc_quill",-1)==0 && c.content_count==3);   /* back as in the data */
     assert(!AW_LedgerContentAdd(&c,AW_LEDGER_PLAYER|5,"misc_quill",1) && !AW_LedgerContentAdd(&c,0x01000005,"misc_quill",1) &&
            !AW_LedgerContentAdd(&c,0,"misc_quill",1) && !AW_LedgerContentAdd(&c,7,"",1) && !AW_LedgerContentAdd(&c,7,"misc",0) &&
            !AW_LedgerContentAdd(&c,7,"x23456789012345678901234567890123",1));
     assert(AW_LedgerContentDelta(&c,1001,"POTION_RESTORE_HEALTH")==-3 && AW_LedgerContentDelta(&c,1002,"misc_quill")==0);
     assert(AW_LedgerContentOf(&c,1001,&first)==2 && c.content[first].key==1001 && AW_LedgerContentOf(&c,999,&first)==0);
     k=AW_LedgerEncode(&c,one,sizeof(one));assert(k>0 && !memcmp(one,"AWL3",4));
     round_trip(&c);save_trip(&c);assert(AW_LedgerContentDelta(&got,1000,"misc_quill")==4);
     /* with rows, stolen pairs, a builder-made container */
     row(&c,77,AW_LEDGER_TAKEN|AW_LEDGER_OPEN,AW_AT_ROOM,3);AW_LedgerStolenAdd(&c,"potion_restore_health","arrille",0,3);
     assert(AW_LedgerContentAdd(&c,AW_LEDGER_BUILDER|9,"iron dagger",-1)==-1);
     /* NPC ranks */
     assert(AW_LedgerRank(&c,4242)==-1 && AW_LedgerRankSet(&c,4242,3) && AW_LedgerRank(&c,4242)==3);
     assert(AW_LedgerRankSet(&c,4242,4) && AW_LedgerRank(&c,4242)==4 && c.rank_count==1);
     assert(AW_LedgerRankSet(&c,17,0) && c.rank[0].key==17 && !AW_LedgerRankSet(&c,18,-1) &&
            !AW_LedgerRankSet(&c,18,AW_LEDGER_RANK_TOP+1) && !AW_LedgerRankSet(&c,AW_LEDGER_PLAYER|1,1));
     round_trip(&c);m=save_trip(&c);
     assert(got.count==1 && got.stolen_count==1 && AW_LedgerRank(&got,4242)==4 && AW_LedgerRank(&got,17)==0 &&
            AW_LedgerContentDelta(&got,AW_LEDGER_BUILDER|9,"iron dagger")==-1);
     /* ranks alone are a reason for the third form and for a save */
     AW_LedgerClear(&other_list);AW_LedgerRankSet(&other_list,5,2);assert(AW_LedgerRows(&other_list)==1);
     k=AW_LedgerEncode(&other_list,one,sizeof(one));assert(k==4+4+4+4+4+5 && !memcmp(one,"AWL3",4));
     save_trip(&other_list);
     /* an older list keeps its form: no delta, no rank, no "AWL3" */
     AW_LedgerClear(&other_list);row(&other_list,51,AW_LEDGER_TAKEN,AW_AT_ROOM,3);
     assert(AW_LedgerEncode(&other_list,one,sizeof(one))>0 && !memcmp(one,"AWL1",4));
     /* reading refusals: the second form has no deltas, an empty third form, a count of 0, out of order, not folded,
      * a key with bit 30, cut bytes */
     AW_LedgerClear(&other_list);AW_LedgerContentAdd(&other_list,300,"misc_quill",-1);AW_LedgerContentAdd(&other_list,301,"misc_cup",2);
     k=AW_LedgerEncode(&other_list,one,sizeof(one));assert(k>0);
     /* AWL3, 0 rows, 0 pairs, 2 deltas: the first at 16: key, len, id, count */
     assert(one[16]==44 && one[20]==10 && one[21]=='m');
     one[3]='2';assert(!AW_LedgerDecode(one,k,&got));one[3]='3';
     one[21]='M';assert(!AW_LedgerDecode(one,k,&got));one[21]='m';
     memcpy(two,one,(size_t)k);two[16]=46;assert(!AW_LedgerDecode(two,k,&got));                /* 302 after 301 */
     memcpy(two,one,(size_t)k);two[19]=0x40;assert(!AW_LedgerDecode(two,k,&got));             /* key bit 30 */
     memcpy(two,one,(size_t)k);memset(two+31,0,4);assert(!AW_LedgerDecode(two,k,&got));        /* a count of 0 */
     assert(!AW_LedgerDecode(one,k-1,&got) && !AW_LedgerDecode(one,k+1,&got));
     memcpy(two,"AWL3\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0",20);assert(!AW_LedgerDecode(two,20,&got));
     assert(AW_LedgerDecode(one,k,&got) && same(&other_list,&got));
     /* 3,000 deltas over 1,000 containers: no small ceiling */
     AW_LedgerClear(&other_list);
     for(i=0;i<3000;i++){char id[16];sprintf(id,"item_%d",i%3);assert(AW_LedgerContentAdd(&other_list,(uint32_t)(i/3+1),id,i%2?2:-1));}
     assert(other_list.content_count==3000);n=round_trip(&other_list);save_trip(&other_list);
     fprintf(o,"containers %d deltas %d bytes, ranks %d, save %d bytes\n",other_list.content_count,n,c.rank_count,m);
     AW_LedgerClear(&c);AW_LedgerClear(&other_list);}

    AW_LedgerClear(&list);AW_LedgerClear(&got);AW_LedgerClear(&other_list);
    fprintf(o,"done\n");
    if(o!=stdout)fclose(o);
    return 0;
}
