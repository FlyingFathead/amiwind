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
    {int t;
     for(t=0;t<AW_LEDGER_TABLES;t++){
         if(a->value_count[t]!=b->value_count[t])return 0;
         for(i=0;i<a->value_count[t];i++)
             if(a->value[t][i].key!=b->value[t][i].key || a->value[t][i].value!=b->value[t][i].value)return 0;
     }
     if(a->fact_count!=b->fact_count)return 0;
     for(i=0;i<a->fact_count;i++)if(strcmp(a->fact[i].id,b->fact[i].id) || a->fact[i].value!=b->fact[i].value)return 0;}
    if(a->local_count!=b->local_count || a->script_count!=b->script_count)return 0;
    for(i=0;i<a->local_count;i++){
        const aw_ledger_local_t *x=&a->local[i],*y=&b->local[i];
        if(x->global!=y->global || x->key!=y->key || x->script!=y->script || x->hint!=y->hint || x->slot!=y->slot ||
           x->value!=y->value)return 0;
    }
    for(i=0;i<a->script_count;i++)
        if(a->script[i].script!=b->script[i].script || a->script[i].hint!=b->script[i].hint ||
           a->script[i].running!=b->script[i].running)return 0;
    if(a->actor_count!=b->actor_count || a->records_bytes!=b->records_bytes ||
       (a->records_bytes && memcmp(a->records,b->records,(size_t)a->records_bytes)))return 0;
    for(i=0;i<a->actor_count;i++){
        const aw_ledger_actor_t *x=&a->actor[i],*y=&b->actor[i];
        if(x->key!=y->key || x->dead!=y->dead || x->moved!=y->moved || x->fight!=y->fight || x->follow!=y->follow ||
           x->pick!=y->pick || (x->dead && x->died!=y->died))return 0;
        if(x->moved && (memcmp(x->origin,y->origin,sizeof(x->origin)) || x->angles[1]!=y->angles[1] ||
           x->health!=y->health || x->hours!=y->hours || x->room!=y->room))return 0;
    }
    /* slice 7: the content files, the idents and the places' refill times */
    if(a->file_count!=b->file_count || a->ident_count!=b->ident_count || a->stamp_count!=b->stamp_count)return 0;
    for(i=0;i<a->file_count;i++)
        if(a->file[i].index!=b->file[i].index || strcmp(a->file[i].name,b->file[i].name) ||
           a->file[i].references!=b->file[i].references || memcmp(a->file[i].digest,b->file[i].digest,8))return 0;
    for(i=0;i<a->ident_count;i++)if(a->ident[i].key!=b->ident[i].key || a->ident[i].record!=b->ident[i].record)return 0;
    for(i=0;i<a->stamp_count;i++)
        if(a->stamp[i].at!=b->stamp[i].at || a->stamp[i].where!=b->stamp[i].where || a->stamp[i].hours!=b->stamp[i].hours)return 0;
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
static aw_ledger_t *fact_list;
static int test_fact_get(const char *id,int32_t *out){return AW_LedgerFact(fact_list,id,out);}
static int test_fact_set(const char *id,int32_t value){return AW_LedgerFactSet(fact_list,id,value);}
static void refused(aw_ledger_t *l){assert(AW_LedgerEncode(l,NULL,0)==0);assert(AW_LedgerEncode(l,one,sizeof(one))==0);}

/* slice 7: a reference identity table (AWI1, aw_ledger.h) made here, read through the callback */
static unsigned char table[1<<16];
static long table_bytes;
static int table_read(void *context,long at,void *out,long bytes){
    (void)context;
    if(at<0 || bytes<0 || at+bytes>table_bytes)return 1;
    memcpy(out,table+at,(size_t)bytes);return 0;
}
static unsigned char *put_le(unsigned char *p,uint32_t v){p[0]=(unsigned char)v;p[1]=(unsigned char)(v>>8);p[2]=(unsigned char)(v>>16);p[3]=(unsigned char)(v>>24);return p+4;}
/* ROWS keys K*3+1 (K = 0 .. ROWS-1), record hash KEY*7+1, every even K flagged Respawn, every fifth levelled */
static void make_table(int rows,int step){
    unsigned char *p=table;int i;float f;uint32_t u;
    memcpy(p,"AWI1",4);p+=4;*p++=1;*p++=0;*p++=13;memcpy(p,"Morrowind.esm",13);p+=13;p=put_le(p,(uint32_t)rows);
    memcpy(p,"\1\2\3\4\5\6\7\10",8);p+=8;
    p=put_le(p,4);f=72;memcpy(&u,&f,4);p=put_le(p,u);f=72;memcpy(&u,&f,4);p=put_le(p,u);
    p=put_le(p,(uint32_t)rows);p=put_le(p,(uint32_t)step);p=put_le(p,(uint32_t)((rows+step-1)/step));
    for(i=0;i<rows;i+=step)p=put_le(p,(uint32_t)(i*3+1));
    for(i=0;i<rows;i++){uint32_t key=(uint32_t)(i*3+1);
        p=put_le(p,key|(i%2?0:AW_REFS_RESPAWN)|(i%5?0:AW_REFS_LEVELLED));p=put_le(p,key*7+1);}
    table_bytes=p-table;
}
static aw_refs_t test_refs;
static int refs_lookup(void *context,uint32_t key,uint32_t *record){return AW_RefsFind((aw_refs_t *)context,key,record,NULL);}
static int item_known(void *context,const char *id){(void)context;return strncmp(id,"gone_",5)!=0;}
/* host mode (tests/test_world_ledger.py, a changed content list): two tables the builder wrote from two masters */
static FILE *host_file;
static int file_read(void *context,long at,void *out,long bytes){
    FILE *f=(FILE *)context;(void)host_file;
    return fseek(f,at,SEEK_SET) || fread(out,1,(size_t)bytes,f)!=(size_t)bytes;
}
static long awi1_at(FILE *f,long *end){
    static unsigned char buf[1<<22];long n=(long)fread(buf,1,sizeof(buf),f),i;
    *end=n;
    for(i=0;i+4<=n;i++)if(!memcmp(buf+i,"AWI1",4))return i;
    return -1;
}

int main(int argc,char **argv)
{
    int i,n,first,size;unsigned f;aw_ledger_row_t *r;
    o=argc>1?fopen(argv[1],"w"):stdout;assert(o);
    if(argc>=4){
        /* host mode: OLD and NEW focus.awf (tools/prepare_focus.py on two masters: the content list changed). A list
         * made with OLD (every reference taken, a container delta on each, the first ten dead actors) is saved with
         * OLD's idents and files, loaded, and migrated against NEW. */
        FILE *fa=fopen(argv[2],"rb"),*fb=fopen(argv[3],"rb");long ea,eb,aa,ab;aw_refs_t ra,rb;aw_ledger_dropped_t d;
        unsigned long all;uint32_t k,rec,fl;unsigned char row8[8];
        assert(fa && fb);base();
        aw_save_ledger_rows=AW_LedgerRows;aw_save_ledger_encode=AW_LedgerEncode;aw_save_ledger_decode=AW_LedgerDecode;
        aa=awi1_at(fa,&ea);ab=awi1_at(fb,&eb);assert(aa>=0 && ab>=0);
        assert(AW_RefsOpen(&ra,file_read,fa,aa,ea) && AW_RefsOpen(&rb,file_read,fb,ab,eb));
        for(k=0;k<ra.rows;k++){
            assert(!file_read(fa,ra.rows_at+(long)k*8,row8,8));
            {uint32_t key=(uint32_t)row8[0]|((uint32_t)row8[1]<<8)|((uint32_t)row8[2]<<16);
             row(&list,key,AW_LEDGER_TAKEN,AW_AT_ANY,0);
             assert(AW_LedgerContentAdd(&list,key,"misc_com_bottle_01",-1));
             if(k<10){aw_ledger_actor_t *a=AW_LedgerActor(&list,key,1);a->dead=1;a->died=5;}
             assert(AW_RefsFind(&ra,key,&rec,&fl));}
        }
        assert(AW_LedgerIdentRefresh(&list,refs_lookup,&ra) && list.ident_count==(int)ra.rows);
        AW_LedgerFilesSet(&list,ra.file,ra.file_count);
        save_trip(&list);
        all=AW_LedgerMigrate(&got,rb.file,rb.file_count,refs_lookup,&rb,item_known,&d);
        fprintf(o,"host old %lu new %lu: migrated %lu dropped, objects %lu containers %lu actors %lu files %lu; kept %d rows, "
                "%d idents\n",(unsigned long)ra.rows,(unsigned long)rb.rows,all,d.objects,d.containers,d.actors,d.files,
                got.count,got.ident_count);
        /* every kept row names a reference of NEW with the same record */
        for(i=0;i<got.count;i++){
            uint32_t was,now;
            assert(AW_LedgerIdent(&got,got.row[i].key,&now) && AW_RefsFind(&ra,got.row[i].key,&was,NULL) && was==now);
        }
        round_trip(&got);
        AW_RefsClose(&ra);AW_RefsClose(&rb);fclose(fa);fclose(fb);
        AW_LedgerClear(&list);AW_LedgerClear(&got);
        fprintf(o,"done\n");fclose(o);
        return 0;
    }
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
     AW_ItemsFree(&inv);memset(&inv,0,sizeof(inv));AW_LedgerClear(&list);
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
      idx=AW_ItemIndex(&inv,"iron dagger");assert(idx>=0);
      AW_ItemMark(&inv,idx,AW_ITEM_CONDITION,0.5f);
      k=AW_LedgerDrop(&inv,&list,&blade,1,AW_AT_ROOM,203,at,10);assert(k);
      r=&list.row[AW_LedgerFind(&list,k)];
      assert((r->fields&AW_LEDGER_CONDITION) && r->extra->condition==0.5f && !AW_ITEM_HAS(&inv,idx,AW_ITEM_CONDITION));
      assert(AW_LedgerPickup(&inv,&list,k) && AW_ITEM_HAS(&inv,idx,AW_ITEM_CONDITION) && AW_ITEM_ROW(&inv,idx)->condition==0.5f);}
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
     AW_ItemsFree(&inv);memset(&inv,0,sizeof(inv));assert(AW_ItemAdd(&inv,q.id,3));
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

    /* slice 4: the scripts' globals, quest stages, known topics, NPC dispositions and the engine's named facts.
     * The game's full counts (docs/MWSCRIPT_BYTECODE.md and DIALOGUE_DESIGN.md: 143 globals, 318 script journal
     * topics, 632 quests, about 2,400 dialogue topics, 2,673 NPCs): every one of them changed at once, and the
     * interpreter's own ceilings (512 globals) past them; round trip and save; refusals; an older list keeps its form;
     * the 32-slot table's named globals past 32 go to the facts (aw_state.c hooks). */
    {static aw_ledger_t s;int k,t;int32_t v;char id[64];
     assert(AW_LedgerNameHash("Random100")==AW_LedgerNameHash("random100") && AW_LedgerNameHash("")==2166136261u);
     assert(!AW_LedgerValueSet(&s,AW_LEDGER_GLOBALS,0,5) && !AW_LedgerValueSet(&s,9,1,1) &&
            !AW_LedgerValueSet(&s,AW_LEDGER_TOPICS,7,2) && !AW_LedgerValueSet(&s,AW_LEDGER_DISPOSITIONS,AW_LEDGER_PLAYER|3,50) &&
            !AW_LedgerValueSet(&s,AW_LEDGER_DISPOSITIONS,3,40000));
     /* journal: Journal / SetJournalIndex / GetJournalIndex on the table; stage 0 is the data's start: no entry */
     k=(int)AW_LedgerNameHash("A1_1_FindSpymaster");
     assert(AW_LedgerValueSet(&s,AW_LEDGER_QUESTS,(uint32_t)k,10) && AW_LedgerValue(&s,AW_LEDGER_QUESTS,(uint32_t)k,&v) && v==10);
     assert(AW_LedgerValueSet(&s,AW_LEDGER_QUESTS,(uint32_t)k,5) && AW_LedgerValue(&s,AW_LEDGER_QUESTS,(uint32_t)k,&v) && v==5);
     assert(AW_LedgerValueSet(&s,AW_LEDGER_QUESTS,(uint32_t)k,0) && !AW_LedgerValue(&s,AW_LEDGER_QUESTS,(uint32_t)k,&v));
     /* globals Set/Get: a float's bits kept as they are */
     {float f=0.75f;uint32_t bits;memcpy(&bits,&f,4);
      assert(AW_LedgerValueSet(&s,AW_LEDGER_GLOBALS,AW_LedgerNameHash("GameHour"),(int32_t)bits));
      assert(AW_LedgerValue(&s,AW_LEDGER_GLOBALS,AW_LedgerNameHash("gamehour"),&v) && (uint32_t)v==bits);}
     /* AddTopic, ModDisposition / SetDisposition */
     assert(AW_LedgerValueSet(&s,AW_LEDGER_TOPICS,AW_LedgerNameHash("latest rumors"),1));
     assert(AW_LedgerValueSet(&s,AW_LEDGER_DISPOSITIONS,172851,62) && AW_LedgerValueSet(&s,AW_LEDGER_DISPOSITIONS,172851,70));
     assert(AW_LedgerValue(&s,AW_LEDGER_DISPOSITIONS,172851,&v) && v==70 && s.value_count[AW_LEDGER_DISPOSITIONS]==1);
     AW_LedgerValueDrop(&s,AW_LEDGER_DISPOSITIONS,172851);assert(!AW_LedgerValue(&s,AW_LEDGER_DISPOSITIONS,172851,NULL));
     assert(AW_LedgerValueSet(&s,AW_LEDGER_DISPOSITIONS,AW_LEDGER_BUILDER|4,-5));
     /* named facts */
     assert(AW_LedgerFactSet(&s,"amiwind:map:marker:X",120) && AW_LedgerFact(&s,"AMIWIND:MAP:MARKER:x",&v) && v==120);
     assert(!AW_LedgerFactSet(&s,"",1) && !AW_LedgerFactSet(&s,"x234567890123456789012345678901234567890123456789012345678901234",1));
     k=AW_LedgerEncode(&s,one,sizeof(one));assert(k>0 && !memcmp(one,"AWL4",4));
     round_trip(&s);save_trip(&s);
     /* the tables alone are a reason for the fourth form and for a save; a list without them keeps its older form */
     AW_LedgerClear(&other_list);AW_LedgerValueSet(&other_list,AW_LEDGER_TOPICS,9,1);assert(AW_LedgerRows(&other_list)==1);
     k=AW_LedgerEncode(&other_list,one,sizeof(one));assert(k==11*4 && !memcmp(one,"AWL4",4));
     save_trip(&other_list);
     /* reading refusals: an empty fourth form, out of order, a quest at stage 0, cut */
     memcpy(two,"AWL4",4);memset(two+4,0,36);assert(!AW_LedgerDecode(two,40,&got));
     assert(!AW_LedgerDecode(one,k-1,&got) && !AW_LedgerDecode(one,k+1,&got));
     AW_LedgerClear(&other_list);AW_LedgerValueSet(&other_list,AW_LEDGER_QUESTS,20,1);AW_LedgerValueSet(&other_list,AW_LEDGER_QUESTS,30,2);
     k=AW_LedgerEncode(&other_list,one,sizeof(one));assert(k>0);
     /* AWL4, 0 rows, 0 pairs, 0 deltas, 0 ranks, 0 globals, 2 quests: the first key at 28, the second at 36 */
     assert(one[24]==2 && one[28]==20 && one[36]==30);
     memcpy(two,one,(size_t)k);two[36]=20;assert(!AW_LedgerDecode(two,k,&got));     /* not ascending */
     memcpy(two,one,(size_t)k);memset(two+32,0,4);assert(!AW_LedgerDecode(two,k,&got)); /* a quest at stage 0 */
     assert(AW_LedgerDecode(one,k,&got) && same(&other_list,&got));
     /* the game's full counts and past them: 512 globals, 1,024 quests, 3,000 topics, 2,673 dispositions, 64 facts */
     AW_LedgerClear(&other_list);
     for(i=0;i<512;i++){sprintf(id,"global_%d",i);assert(AW_LedgerValueSet(&other_list,AW_LEDGER_GLOBALS,AW_LedgerNameHash(id),i*3+1));}
     for(i=0;i<1024;i++){sprintf(id,"quest_%d",i);assert(AW_LedgerValueSet(&other_list,AW_LEDGER_QUESTS,AW_LedgerNameHash(id),i%200+1));}
     for(i=0;i<3000;i++){sprintf(id,"topic %d",i);assert(AW_LedgerValueSet(&other_list,AW_LEDGER_TOPICS,AW_LedgerNameHash(id),1));}
     for(i=0;i<2673;i++)assert(AW_LedgerValueSet(&other_list,AW_LEDGER_DISPOSITIONS,(uint32_t)(i*37+1),i%100));
     for(i=0;i<64;i++){sprintf(id,"amiwind:fact:%d",i);assert(AW_LedgerFactSet(&other_list,id,i));}
     assert(other_list.value_count[0]==512 && other_list.value_count[1]==1024 && other_list.value_count[2]==3000 &&
            other_list.value_count[3]==2673 && other_list.fact_count==64);   /* no name hash met another */
     n=round_trip(&other_list);size=save_trip(&other_list);
     fprintf(o,"script state %d globals %d quests %d topics %d dispositions %d facts, %d bytes, save %d bytes, %lu resident\n",
             other_list.value_count[0],other_list.value_count[1],other_list.value_count[2],other_list.value_count[3],
             other_list.fact_count,n,size,AW_LedgerResident(&other_list));
     /* with the slices before it in one list */
     row(&s,88,AW_LEDGER_TAKEN,AW_AT_CELL,cell(-2,-9));AW_LedgerContentAdd(&s,1001,"gold_001",-4);AW_LedgerRankSet(&s,5,2);
     AW_LedgerStolenAdd(&s,"misc_quill","arrille",0,1);round_trip(&s);save_trip(&s);
     /* aw_state's named globals past the 32 slots: the facts (the engine binds the hooks in aw_save.c) */
     {static aw_state_t st;
      for(t=0;t<AW_STATE_VALUES;t++){sprintf(id,"amiwind:slot:%d",t);assert(AW_StateSet(&st,AW_GLOBAL,id,t));}
      assert(!AW_StateSet(&st,AW_GLOBAL,"amiwind:map:marker:ready",1));    /* no hooks: refused as before */
      aw_state_fact_get=test_fact_get;aw_state_fact_set=test_fact_set;fact_list=&s;
      assert(AW_StateSet(&st,AW_GLOBAL,"amiwind:map:marker:ready",1) && AW_StateGet(&st,AW_GLOBAL,"AMIWIND:MAP:MARKER:READY")==1);
      assert(AW_StateSet(&st,AW_GLOBAL,"amiwind:map:marker:x",-300) && AW_StateGet(&st,AW_GLOBAL,"amiwind:map:marker:x")==-300);
      assert(st.count[AW_GLOBAL]==AW_STATE_VALUES && AW_StateGet(&st,AW_GLOBAL,"amiwind:slot:31")==31);
      assert(AW_LedgerFact(&s,"amiwind:map:marker:x",&v) && v==-300);
      round_trip(&s);
      aw_state_fact_get=NULL;aw_state_fact_set=NULL;fact_list=NULL;}
     /* an older save (the 32-slot tables and an AWL3 list) loads with empty slice 4 tables: the engine migrates */
     AW_LedgerClear(&other_list);AW_LedgerRankSet(&other_list,5,2);
     k=AW_LedgerEncode(&other_list,one,sizeof(one));assert(!memcmp(one,"AWL3",4));
     assert(AW_LedgerDecode(one,k,&got) && !got.value_count[AW_LEDGER_QUESTS] && !got.fact_count);
     AW_LedgerClear(&s);AW_LedgerClear(&other_list);}

    /* slice 5: the scripts' locals and the running global scripts. The game's counts (v0.0.59-dev5's compiled scripts,
     * read by the worker from the built file): 8,618 scripts, 4 start scripts, 7,339 placed references with a script,
     * 2,115 of them with locals, 7,388 local values in all, at most 37 in one script. Every one of those values changed
     * at once, past them to the list's ceiling, plus global scripts started and stopped; round trip and save;
     * refusals; a value back at 0 goes; an older list keeps its form and loads with no slice 5 entries. */
    {static aw_ledger_t s;int k,v_count=0;int32_t v;uint32_t h=AW_LedgerNameHash("TribunalMain");
     /* refusals: no script, a slot past 255, a hint past 16 bits, a drop's key, a global keyed by another hash */
     assert(!AW_LedgerLocalSet(&s,0,5,0,1,0,7) && !AW_LedgerLocalSet(&s,0,5,h,1,256,7) &&
            !AW_LedgerLocalSet(&s,0,5,h,70000,0,7) && !AW_LedgerLocalSet(&s,0,AW_LEDGER_PLAYER|5,h,1,0,7) &&
            !AW_LedgerLocalSet(&s,1,5,h,1,0,7) && !AW_LedgerLocalSet(&s,2,h,h,1,0,7) && s.local_count==0);
     assert(!AW_LedgerScriptSet(&s,0,1,1) && !AW_LedgerScriptSet(&s,h,1,2) && !AW_LedgerScriptSet(&s,h,-1,1));
     /* an object's local set, changed, read; back at 0 it goes (the start) */
     assert(AW_LedgerLocalSet(&s,0,172851,AW_LedgerNameHash("fargothScript"),402,1,3) &&
            AW_LedgerLocal(&s,0,172851,1,&v) && v==3);
     assert(AW_LedgerLocalSet(&s,0,172851,AW_LedgerNameHash("fargothScript"),402,1,9) && AW_LedgerLocal(&s,0,172851,1,&v) &&
            v==9 && s.local_count==1);
     assert(AW_LedgerLocalSet(&s,0,172851,AW_LedgerNameHash("fargothScript"),402,1,0) && !AW_LedgerLocal(&s,0,172851,1,NULL) &&
            !s.local_count && AW_LedgerLocalSet(&s,0,172851,1,1,0,0) && !s.local_count);
     /* a float's bits as they are; a builder-made object; a global script's locals and its running state */
     {float f=-2.5f;uint32_t bits;memcpy(&bits,&f,4);
      assert(AW_LedgerLocalSet(&s,0,AW_LEDGER_BUILDER|4,AW_LedgerNameHash("timerChime"),12,0,(int32_t)bits));
      assert(AW_LedgerLocal(&s,0,AW_LEDGER_BUILDER|4,0,&v) && (uint32_t)v==bits);}
     assert(AW_LedgerLocalSet(&s,1,h,h,866,1,2) && AW_LedgerScriptSet(&s,h,866,0));
     assert(AW_LedgerScriptSet(&s,AW_LedgerNameHash("FraldCounter"),264,1) && AW_LedgerScriptSet(&s,AW_LedgerNameHash("FraldCounter"),264,1) &&
            s.script_count==2);
     k=AW_LedgerEncode(&s,one,sizeof(one));assert(k>0 && !memcmp(one,"AWL5",4));
     round_trip(&s);save_trip(&s);
     /* the slice 5 tables alone are a reason for the fifth form and a save: 40 bytes of empty earlier parts, then
      * one script (4 + 7) and no locals (4) */
     AW_LedgerClear(&other_list);AW_LedgerScriptSet(&other_list,h,866,0);assert(AW_LedgerRows(&other_list)==1);
     k=AW_LedgerEncode(&other_list,one,sizeof(one));assert(k==40+4+7+4 && !memcmp(one,"AWL5",4));
     save_trip(&other_list);
     /* reading refusals: an empty fifth form, cut, out of order, a value of 0, a running byte of 2 */
     memset(two,0,64);memcpy(two,"AWL5",4);assert(!AW_LedgerDecode(two,48,&got));
     assert(!AW_LedgerDecode(one,k-1,&got) && !AW_LedgerDecode(one,k+1,&got));
     memcpy(two,one,(size_t)k);two[k-5]=2;assert(!AW_LedgerDecode(two,k,&got));
     AW_LedgerClear(&other_list);AW_LedgerLocalSet(&other_list,0,20,h,1,0,5);AW_LedgerLocalSet(&other_list,0,30,h,1,0,6);
     k=AW_LedgerEncode(&other_list,one,sizeof(one));assert(k>0);
     /* AWL5, 0 rows .. 0 facts (40 bytes), 0 scripts (4), 2 locals (4): the first local at 48 (its key at 49, its value
      * at 60), the second at 64 */
     assert(k==48+2*16 && one[44]==2 && one[48]==0 && one[49]==20 && one[60]==5 && one[65]==30);
     memcpy(two,one,(size_t)k);two[65]=20;assert(!AW_LedgerDecode(two,k,&got));          /* not ascending */
     memcpy(two,one,(size_t)k);memset(two+60,0,4);assert(!AW_LedgerDecode(two,k,&got));    /* a value of 0 */
     memcpy(two,one,(size_t)k);two[48]=2;assert(!AW_LedgerDecode(two,k,&got));            /* global 2 */
     assert(AW_LedgerDecode(one,k,&got) && same(&other_list,&got));
     /* the game's counts: 2,115 references with locals, 7,388 values (3 or 4 per reference, all changed), the 4 start
      * scripts stopped and 600 other global scripts started, with 800 global values: 8,188 locals, under the ceiling */
     AW_LedgerClear(&other_list);
     for(i=0;i<2115;i++){int n=i<1043?4:3,slot;
         for(slot=0;slot<n;slot++,v_count++)assert(AW_LedgerLocalSet(&other_list,0,(uint32_t)(i*3+1),AW_LedgerNameHash(i%2?"a":"b"),i%412,slot,i+slot+1));}
     assert(v_count==7388 && other_list.local_count==7388);
     for(i=0;i<604;i++){char id[24];uint32_t sh;sprintf(id,"global_script_%d",i);sh=AW_LedgerNameHash(id);
         assert(AW_LedgerScriptSet(&other_list,sh,i+1000,i>=4));
         if(i<200){int slot;for(slot=0;slot<4;slot++)assert(AW_LedgerLocalSet(&other_list,1,sh,sh,i+1000,slot,-(slot+1)));}}
     assert(other_list.local_count==8188 && other_list.script_count==604);
     n=round_trip(&other_list);size=save_trip(&other_list);
     /* the ceiling: 4 more values fit, the next is refused and counted, nothing else changes */
     for(i=0;i<4;i++)assert(AW_LedgerLocalSet(&other_list,0,0xFFFFF0u+(uint32_t)i,h,1,0,1));
     {unsigned long before=other_list.refused;
      assert(!AW_LedgerLocalSet(&other_list,0,0xFFFFFEu,h,1,0,1) && other_list.refused==before+1 &&
             other_list.local_count==AW_LEDGER_LOCALS_MAX);}
     round_trip(&other_list);
     fprintf(o,"script locals %d values %d scripts, %d bytes, save %d bytes, %lu resident\n",8188,604,n,size,
             AW_LedgerResident(&other_list));
     /* with every slice before it in one list */
     row(&s,88,AW_LEDGER_TAKEN,AW_AT_CELL,cell(-2,-9));AW_LedgerContentAdd(&s,1001,"gold_001",-4);AW_LedgerRankSet(&s,5,2);
     AW_LedgerStolenAdd(&s,"misc_quill","arrille",0,1);AW_LedgerValueSet(&s,AW_LEDGER_QUESTS,77,10);
     AW_LedgerFactSet(&s,"amiwind:x",1);round_trip(&s);save_trip(&s);
     /* an older save (an AWL4 list) loads with no slice 5 entries: the engine sets the scripts at their start */
     AW_LedgerClear(&other_list);AW_LedgerValueSet(&other_list,AW_LEDGER_QUESTS,77,10);
     k=AW_LedgerEncode(&other_list,one,sizeof(one));assert(!memcmp(one,"AWL4",4));
     assert(AW_LedgerDecode(one,k,&got) && !got.local_count && !got.script_count);
     /* clearing slice 5 alone leaves the rest */
     AW_LedgerLocalsClear(&s);assert(!s.local_count && !s.script_count && s.count==1 && s.value_count[AW_LEDGER_QUESTS]==1);
     AW_LedgerClear(&s);AW_LedgerClear(&other_list);}

    /* slice 6: the actors (ACTOR-STATE-POOL-LIMITS-54). The game's counts (v0.0.59-dev5's built actor table, read by the
     * worker: 3,437 actor bases, 3,041 NPC and 396 creature; the original places 2,673 NPCs): every one of 3,437
     * references changed at once (killed, hurt and moved, hostile, a companion, a levelled roll), past the old 2,048
     * entries, up to the ceiling; the actor records' bytes kept as they are; refusals; an older list keeps its form. */
    {static aw_ledger_t s;aw_ledger_actor_t *a;int k;unsigned char rec[64];
     /* refusals: key 0, key bits 24-31 (a drop's or a builder's key stays out) */
     assert(!AW_LedgerActor(&s,0,1) && !AW_LedgerActor(&s,AW_LEDGER_PLAYER|5,1) && !AW_LedgerActor(&s,AW_LEDGER_BUILDER|5,1) &&
            !AW_LedgerActor(&s,0x1000000u,1) && !s.actor_count && s.refused==4);
     assert(!AW_LedgerActor(&s,77,0) && !s.actor_count);
     /* a killed one where it fell (a body left), a hurt one moved in a room, a hostile one, a companion, a roll */
     a=AW_LedgerActor(&s,172851,1);a->dead=1;a->moved=1;a->origin[0]=-12000.5f;a->origin[1]=8000;a->origin[2]=96;
     a->angles[1]=270;a->health=0;a->hours=29.5f;
     a=AW_LedgerActor(&s,4400,1);a->moved=1;a->health=31.5f;a->room=1205;a->origin[2]=-40;a->hours=30;
     a=AW_LedgerActor(&s,9000,1);a->fight=1;
     a=AW_LedgerActor(&s,9001,1);a->follow=1;a->moved=1;a->health=100;a->hours=31;
     a=AW_LedgerActor(&s,9002,1);a->pick=2+17;
     assert(s.actor_count==5 && s.actor[0].key==4400 && AW_LedgerActor(&s,172851,0)->dead==1);
     /* a row with nothing on it is not saved (and alone is no reason for the sixth form) */
     AW_LedgerActor(&s,555,1);
     k=AW_LedgerEncode(&s,one,sizeof(one));assert(k>0 && !memcmp(one,"AWL6",4));
     assert(AW_LedgerDecode(one,k,&got) && got.actor_count==5);
     {aw_ledger_actor_t *gone=AW_LedgerActor(&s,555,0);assert(gone);gone->dead=1;}   /* now it has a field */
     round_trip(&s);save_trip(&s);
     AW_LedgerClear(&other_list);AW_LedgerActor(&other_list,555,1);assert(AW_LedgerRows(&other_list)==0);
     AW_LedgerClear(&other_list);
     /* the records part alone: "AWAR" bytes kept as they are; a block not starting "AWAR" or too short is refused */
     memset(rec,0,sizeof(rec));memcpy(rec,"AWAR\1\0\0\0\0\0\0\1",12);
     assert(!AW_LedgerRecordsSet(&other_list,(const unsigned char *)"AWAS\1\0\0\0",8) && !AW_LedgerRecordsSet(&other_list,rec,4));
     assert(AW_LedgerRecordsSet(&other_list,rec,sizeof(rec)) && AW_LedgerRows(&other_list)==1);
     k=AW_LedgerEncode(&other_list,one,sizeof(one));
     /* AWL6, 0 rows .. 0 locals (48 bytes), 0 actor rows (4), 64 record bytes (4 + 64) */
     assert(k==48+4+4+64 && !memcmp(one,"AWL6",4) && one[52]==64 && !memcmp(one+56,"AWAR",4));
     round_trip(&other_list);save_trip(&other_list);
     /* reading refusals: an empty sixth form, cut, a record part not "AWAR", a field byte past 31, keys out of order */
     memset(two,0,64);memcpy(two,"AWL6",4);assert(!AW_LedgerDecode(two,56,&got));
     assert(!AW_LedgerDecode(one,k-1,&got) && !AW_LedgerDecode(one,k+1,&got));
     memcpy(two,one,(size_t)k);two[59]='S';assert(!AW_LedgerDecode(two,k,&got));
     AW_LedgerClear(&other_list);AW_LedgerActor(&other_list,20,1)->fight=1;AW_LedgerActor(&other_list,30,1)->fight=1;
     k=AW_LedgerEncode(&other_list,one,sizeof(one));
     /* the actor rows at 52: count, then 20 (key at 52, fields at 56), then 30 (key at 57, fields at 61), then 0 bytes */
     assert(k==48+4+5+5+4 && one[48]==2 && one[52]==20 && one[56]==AW_LEDGER_ACTOR_FIGHT && one[57]==30);
     memcpy(two,one,(size_t)k);two[57]=20;assert(!AW_LedgerDecode(two,k,&got));          /* not ascending */
     memcpy(two,one,(size_t)k);two[56]=32;assert(!AW_LedgerDecode(two,k,&got));          /* an unknown field */
     memcpy(two,one,(size_t)k);two[56]=0;assert(!AW_LedgerDecode(two,k,&got));           /* no field */
     memcpy(two,one,(size_t)k);two[55]=1;assert(!AW_LedgerDecode(two,k,&got));           /* key bit 24 */
     assert(AW_LedgerDecode(one,k,&got) && same(&other_list,&got));
     /* a moved row's room past 24 bits and a pick of 0 are refused when writing */
     AW_LedgerActor(&other_list,40,1)->moved=1;AW_LedgerActor(&other_list,40,0)->room=0x1000000;refused(&other_list);
     AW_LedgerActor(&other_list,40,0)->room=0;AW_LedgerActor(&other_list,40,0)->health=1e9f;refused(&other_list);
     AW_LedgerActor(&other_list,40,0)->health=5;round_trip(&other_list);
     /* the game's counts: 3,437 references, all changed (every second killed, every third hurt and moved, the rest
      * hostile), the old list held 2,048 */
     AW_LedgerClear(&other_list);
     for(i=0;i<3437;i++){a=AW_LedgerActor(&other_list,(uint32_t)(3437-i)*7u,1);assert(a);
         if(i%2)a->dead=1;
         if(i%3==0){a->moved=1;a->health=(float)(i%90);a->origin[0]=(float)i;a->hours=(float)i/10;a->room=i%5?0:i;}
         if(!a->dead && !a->moved)a->fight=1;}
     assert(other_list.actor_count==3437);
     n=round_trip(&other_list);size=save_trip(&other_list);
     /* the ceiling: up to 8,192 rows, the next refused and counted, nothing else changes */
     for(i=3437;i<AW_LEDGER_ACTORS_MAX;i++)AW_LedgerActor(&other_list,0xFFFFFFu-(uint32_t)i,1)->follow=1;
     {unsigned long before=other_list.refused;
      assert(other_list.actor_count==AW_LEDGER_ACTORS_MAX && !AW_LedgerActor(&other_list,3,1) &&
             other_list.refused==before+1 && other_list.actor_count==AW_LEDGER_ACTORS_MAX);}
     round_trip(&other_list);
     fprintf(o,"actors 3437 rows, %d bytes, save %d bytes, %lu resident\n",n,size,AW_LedgerResident(&other_list));
     /* with every slice before it in one list */
     row(&s,88,AW_LEDGER_TAKEN,AW_AT_CELL,cell(-2,-9));AW_LedgerContentAdd(&s,1001,"gold_001",-4);AW_LedgerRankSet(&s,5,2);
     AW_LedgerStolenAdd(&s,"misc_quill","arrille",0,1);AW_LedgerValueSet(&s,AW_LEDGER_QUESTS,77,10);
     AW_LedgerFactSet(&s,"amiwind:x",1);AW_LedgerScriptSet(&s,AW_LedgerNameHash("x"),1,1);
     memcpy(rec,"AWAR\1\0\0\0\0\0\0\1",12);AW_LedgerRecordsSet(&s,rec,sizeof(rec));round_trip(&s);save_trip(&s);
     /* an older save (an AWL5 list) loads with no actor rows: the engine migrates the save's own actor entries */
     AW_LedgerClear(&other_list);AW_LedgerScriptSet(&other_list,AW_LedgerNameHash("x"),1,1);
     k=AW_LedgerEncode(&other_list,one,sizeof(one));assert(!memcmp(one,"AWL5",4));
     assert(AW_LedgerDecode(one,k,&got) && !got.actor_count && !got.records_bytes);
     /* clearing slice 6 alone leaves the rest */
     AW_LedgerActorsClear(&s);assert(!s.actor_count && !s.records_bytes && s.count==1 && s.script_count==1);
     AW_LedgerClear(&s);AW_LedgerClear(&other_list);}

    /* slice 7: respawn timing per kind (OpenMW 0.51's rules with Morrowind.esm's GMSTs: 4 months, 72 hours), the
     * places' refill times, the container refill, the seventh form only when needed, the identity table, and the
     * migration of a save of other game data with its counts */
    {static aw_ledger_t s,m;aw_ledger_actor_t *a;aw_ledger_respawn_t rule=AW_LEDGER_RESPAWN_DEFAULT;int k;
     aw_ledger_dropped_t d;aw_ledger_file_t files[2];uint32_t rec,fl;unsigned long all;
     /* a levelled creature (its roll kept) dead at 100 h: not back at 171.9 h, back at 172 h, with or without a flag */
     a=AW_LedgerActor(&s,10,1);a->dead=1;a->pick=5;a->died=100;
     assert(!AW_LedgerActorRespawns(a,0,171.9f,&rule) && AW_LedgerActorRespawns(a,0,172,&rule));
     /* an NPC or creature flagged Respawn: the same; one not flagged never; one alive never */
     a=AW_LedgerActor(&s,11,1);a->dead=1;a->died=100;
     assert(AW_LedgerActorRespawns(a,1,172,&rule) && !AW_LedgerActorRespawns(a,1,171.9f,&rule) &&
            !AW_LedgerActorRespawns(a,0,1000000,&rule));
     a=AW_LedgerActor(&s,12,1);a->fight=1;assert(!AW_LedgerActorRespawns(a,1,1000000,&rule));
     /* the delay is the smaller of fCorpseRespawnDelay and fCorpseClearDelay */
     {aw_ledger_respawn_t r2={4,10.0f,72.0f};a=AW_LedgerActor(&s,11,0);
      assert(AW_LedgerActorRespawns(a,1,110,&r2) && !AW_LedgerActorRespawns(a,1,109.5f,&r2));
      r2.respawn_delay=72;r2.clear_delay=24;assert(AW_LedgerActorRespawns(a,1,124,&r2) && !AW_LedgerActorRespawns(a,1,123.5f,&r2));}
     /* an older row (no death time): its capture time stands for it */
     a=AW_LedgerActor(&s,13,1);a->dead=1;a->moved=1;a->hours=50;
     assert(AW_LedgerActorRespawns(a,1,122,&rule) && !AW_LedgerActorRespawns(a,1,121.5f,&rule));
     /* back: the row is as in the data (a levelled list rolls again), so it is not saved */
     a=AW_LedgerActor(&s,10,0);AW_LedgerActorReset(a);assert(a->key==10 && !a->dead && !a->pick && !a->died && !a->moved);
     a->fight=1;            /* (an empty row is not saved; this one gets a field again for the round trips below) */
     /* containers: a place's first refill comes after 24 x 30 x 4 = 2,880 hours, then 2,880 hours after the last one,
      * counted from the load that refilled (OpenMW: mLastRespawn set at the refill) */
     assert(!AW_LedgerRespawnPlace(&s,AW_AT_ROOM,1205,2880,4) && !s.stamp_count && AW_LedgerRespawnPlace(&s,AW_AT_ROOM,1205,2881,4));
     assert(AW_LedgerPlaceStamp(&s,AW_AT_ROOM,1205)==2881 && !AW_LedgerRespawnPlace(&s,AW_AT_ROOM,1205,5761,4) &&
            AW_LedgerRespawnPlace(&s,AW_AT_ROOM,1205,5762,4) && AW_LedgerPlaceStamp(&s,AW_AT_ROOM,1205)==5762);
     assert(AW_LedgerRespawnPlace(&s,AW_AT_CELL,cell(-2,-9),3000,4) && s.stamp_count==2);
     assert(!AW_LedgerRespawnPlace(&s,AW_AT_ANY,0,99999,4) && !AW_LedgerRespawnPlace(&s,AW_AT_ROOM,7,99999,0));
     /* the refill: every delta of the container goes, the others stay */
     AW_LedgerContentAdd(&s,1001,"misc_com_bottle_01",-2);AW_LedgerContentAdd(&s,1001,"ingred_bread_01",3);
     AW_LedgerContentAdd(&s,1002,"misc_com_bottle_01",1);
     assert(AW_LedgerContentDrop(&s,1001)==2 && s.content_count==1 && !AW_LedgerContentDrop(&s,1001) &&
            AW_LedgerContentDelta(&s,1002,"misc_com_bottle_01")==1);
     /* the seventh form: deaths, refill times, idents and files round trip and survive a save */
     memset(files,0,sizeof(files));files[0].index=0;strcpy(files[0].name,"Morrowind.esm");files[0].references=316116;
     memcpy(files[0].digest,"\x5c\x3c\x8c\x2c\xbd\x20\xe2\x59",8);
     files[1].index=1;strcpy(files[1].name,"Tribunal.esm");files[1].references=15103;
     AW_LedgerFilesSet(&s,files,2);assert(s.file_count==2);
     assert(AW_LedgerIdentSet(&s,11,0x1234u) && AW_LedgerIdentSet(&s,1002,0x99u) && !AW_LedgerIdentSet(&s,AW_LEDGER_PLAYER|3,1) &&
            !AW_LedgerIdentSet(&s,5,0));
     k=AW_LedgerEncode(&s,one,sizeof(one));assert(k>0 && !memcmp(one,"AWL7",4));
     round_trip(&s);save_trip(&s);
     /* only what changes the world makes a save: files and idents alone do not, a refill time does */
     AW_LedgerClear(&m);AW_LedgerFilesSet(&m,files,1);AW_LedgerIdentSet(&m,4,9);assert(AW_LedgerRows(&m)==0);
     AW_LedgerClear(&m);assert(AW_LedgerRespawnPlace(&m,AW_AT_ROOM,3,3000,4) && AW_LedgerRows(&m)==1);round_trip(&m);
     /* the seventh form only when needed: a slice 6 list stays AWL6 (an engine of slice 6 reads it), a death time makes
      * it AWL7 */
     AW_LedgerClear(&m);AW_LedgerActor(&m,20,1)->dead=1;k=AW_LedgerEncode(&m,one,sizeof(one));assert(!memcmp(one,"AWL6",4));
     AW_LedgerActor(&m,20,0)->died=5;k=AW_LedgerEncode(&m,one,sizeof(one));assert(!memcmp(one,"AWL7",4));round_trip(&m);
     /* reading refusals: an empty seventh form; a DIED field in a sixth form; cut */
     memset(two,0,80);memcpy(two,"AWL7",4);assert(!AW_LedgerDecode(two,48+4+4+1+4+4,&got));
     memcpy(two,one,(size_t)k);memcpy(two,"AWL6",4);assert(!AW_LedgerDecode(two,k,&got));
     assert(!AW_LedgerDecode(one,k-1,&got));
     /* the identity table: 1,000 references in blocks of 64, every key found with its hash and flags, others not */
     make_table(1000,64);assert(AW_RefsOpen(&test_refs,table_read,NULL,0,table_bytes));
     assert(test_refs.rows==1000 && test_refs.respawn.months==4 && test_refs.respawn.clear_delay==72 &&
            test_refs.file_count==1 && !strcmp(test_refs.file[0].name,"Morrowind.esm"));
     for(i=0;i<1000;i++){
         uint32_t key=(uint32_t)(i*3+1);
         assert(AW_RefsFind(&test_refs,key,&rec,&fl) && rec==key*7+1 &&
                fl==((i%2?0:AW_REFS_RESPAWN)|(i%5?0:AW_REFS_LEVELLED)));
         assert(!AW_RefsFind(&test_refs,key+1,&rec,&fl));
     }
     assert(!AW_RefsFind(&test_refs,0,&rec,&fl) && !AW_RefsFind(&test_refs,3001,&rec,&fl) && test_refs.reads<=2000);
     {aw_refs_t bad;long keep=table_bytes;table_bytes=keep-1;assert(!AW_RefsOpen(&bad,table_read,NULL,0,table_bytes));
      table[0]='X';table_bytes=keep;assert(!AW_RefsOpen(&bad,table_read,NULL,0,table_bytes));table[0]='A';}
     /* the save's identity: refreshed to exactly the keys the list names, hashes from the table */
     AW_LedgerClear(&m);row(&m,4,AW_LEDGER_TAKEN,AW_AT_ANY,0);row(&m,7,AW_LEDGER_DISABLED,AW_AT_ANY,0);
     row(&m,AW_LEDGER_BUILDER|3,AW_LEDGER_DISABLED,AW_AT_ANY,0);row(&m,AW_LEDGER_PLAYER|1,AW_LEDGER_DROPPED,AW_AT_ROOM,5);
     strcpy(row(&m,AW_LEDGER_PLAYER|2,AW_LEDGER_DROPPED,AW_AT_ROOM,5)->extra->item,"gone_misc");
     row(&m,5,AW_LEDGER_TAKEN,AW_AT_ANY,0);row(&m,(1u<<20)|10,AW_LEDGER_TAKEN,AW_AT_ANY,0);
     AW_LedgerContentAdd(&m,4,"misc_com_bottle_01",-1);AW_LedgerContentAdd(&m,4,"gone_bottle",-1);
     AW_LedgerContentAdd(&m,5,"misc_com_bottle_01",2);AW_LedgerRankSet(&m,5,3);AW_LedgerRankSet(&m,10,1);
     AW_LedgerValueSet(&m,AW_LEDGER_DISPOSITIONS,7,70);AW_LedgerValueSet(&m,AW_LEDGER_GLOBALS,12345,9);
     AW_LedgerLocalSet(&m,0,5,AW_LedgerNameHash("s"),3,0,4);AW_LedgerLocalSet(&m,0,4,AW_LedgerNameHash("s"),3,1,4);
     a=AW_LedgerActor(&m,4,1);a->dead=1;a->pick=9;a->died=3;a=AW_LedgerActor(&m,8,1);a->dead=1;
     AW_LedgerStolenAdd(&m,"gone_ring","arrille",0,1);AW_LedgerStolenAdd(&m,"misc_quill","arrille",0,1);
     assert(AW_LedgerIdentRefresh(&m,refs_lookup,&test_refs));
     /* named: 4, 5, 7, 8, 10 and Tribunal's 1<<20|10; the table (keys K*3+1) has 4, 7 and 10 */
     assert(m.ident_count==3 && AW_LedgerIdent(&m,7,&rec) && rec==50 && !AW_LedgerIdent(&m,8,&rec) &&
            AW_LedgerIdent(&m,10,&rec) && rec==71);
     AW_LedgerFilesSet(&m,files,2);
     /* the save is loaded by a game whose data changed: reference 7 now names another record, 10 and 5 are gone,
      * Tribunal.esm is missing */
     save_trip(&m);
     /* reference 7 (row K=2) now names another record: its hash byte changed in the table */
     assert(table[test_refs.rows_at+2*8]==7 && table[test_refs.rows_at+2*8+4]==50);
     table[test_refs.rows_at+2*8+4]=51;
     AW_RefsClose(&test_refs);assert(AW_RefsOpen(&test_refs,table_read,NULL,0,table_bytes));
     all=AW_LedgerMigrate(&got,files,1,refs_lookup,&test_refs,item_known,&d);
     fprintf(o,"migration: %lu dropped (objects %lu, drops %lu, containers %lu, ranks %lu, dispositions %lu, locals %lu, "
             "actors %lu, rolls %lu, stolen %lu, files %lu), %d rows kept\n",all,d.objects,d.drops,d.containers,d.ranks,
             d.dispositions,d.locals,d.actors,d.picks,d.stolen,d.files,got.count);
     /* objects: 7 (another record), 5 (gone), Tribunal's (its file gone); drops: the gone item; containers: 4's gone
      * item and 5's; ranks: 5; dispositions: 7; locals: 5's; actors: 8 (no reference); 4's roll; the gone ring */
     assert(d.objects==3 && d.drops==1 && d.containers==2 && d.ranks==1 && d.dispositions==1 && d.locals==1 &&
            d.actors==1 && d.picks==1 && d.stolen==1 && d.files==1 && all==12);
     /* what stays: 4 taken, the builder's object, one drop; 4's bottle; rank of 10 (it exists: K=3); the global; the
      * local of 4; 4 dead (no roll); the quill */
     assert(got.count==3 && AW_LedgerFind(&got,4)>=0 && AW_LedgerFind(&got,AW_LEDGER_BUILDER|3)>=0 &&
            AW_LedgerFind(&got,AW_LEDGER_PLAYER|1)>=0 && got.content_count==1 && got.rank_count==1 &&
            got.rank[0].key==10 && got.value_count[AW_LEDGER_GLOBALS]==1 && !got.value_count[AW_LEDGER_DISPOSITIONS] &&
            got.local_count==1 && got.actor_count==1 && got.actor[0].dead && !got.actor[0].pick &&
            got.stolen_count==1 && got.file_count==1 && AW_LedgerIdent(&got,4,&rec) && rec==29);
     round_trip(&got);
     AW_RefsClose(&test_refs);AW_LedgerClear(&s);AW_LedgerClear(&m);}

    AW_LedgerClear(&list);AW_LedgerClear(&got);AW_LedgerClear(&other_list);
    fprintf(o,"done\n");
    if(o!=stdout)fclose(o);
    return 0;
}
