/* SPDX-License-Identifier: GPL-3.0-only
 * The save's budget (SAVE-STATE-FIXED-CAPS-66; tests/test_save_contract.py): a synthetic 100-hour game's change list,
 * sized from a late original save (about 7,700 changed references, 800 of them drops, 242 containers, 3,000 changed
 * actors with their records, 2,800 script locals, every global, quest and topic, 1,400 refilled places, the dated
 * journal with the master's 2,489 entries), encoded as one saved game. Writes (to argv[1]) the measured numbers, one
 * "key value" a line: the file's bytes and each part's, the encode and decode times, the list's resident bytes; and
 * checks the contract: every part kept through a load, a second encode of the loaded game gives the same bytes (no
 * growth without a change), and the file stays under 1 MiB.
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include "aw_story.h"
#include "aw_save.h"
#include "aw_maps.h"
#include "aw_ledger.h"
#include "aw_jhist.h"
aw_race_t aw_races[16];aw_class_t aw_classes[32];aw_birth_t aw_births[16];aw_part_t aw_parts[384];
int aw_race_count=1,aw_class_count=1,aw_birth_count=1,aw_part_count=2;
static aw_save_t save,loaded;
static aw_changes_t changes,back;
static aw_ledger_t list,got;
static aw_jhist_t hist,hist_back;
static unsigned char one[AW_SAVE_MAX_BYTES],two[AW_SAVE_MAX_BYTES];
static FILE *o;

#define OBJECTS 7700
#define DROPS 800
#define CONTAINERS 242
#define DELTAS_PER_CONTAINER 3
#define ACTORS 3000
#define RECORD_BYTES 182
#define LOCALS 2800
#define GLOBAL_SCRIPTS 100
#define GLOBALS 143
#define QUESTS 632
#define TOPICS 2400
#define DISPOSITIONS 500
#define STOLEN 143
#define RANKS 40
#define PLACES 1400
#define JOURNAL 2489

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
static void line(const char *key,long value){fprintf(o,"%s %ld\n",key,value);printf("%s %ld\n",key,value);}
static long ms(clock_t from,clock_t to){return (long)((to-from)*1000L/CLOCKS_PER_SEC);}
/* the list of a long game */
static void fill(aw_ledger_t *l)
{
    int i,k;char id[48];uint32_t key;aw_ledger_row_t *r;aw_ledger_extra_t *x;aw_ledger_actor_t *a;
    static unsigned char records[12+ACTORS*RECORD_BYTES];
    static aw_ledger_file_t files[3];
    /* placed objects: taken, disabled, locked, open doors, moved (a fifth of them), in 400 cells */
    for(i=0;i<OBJECTS-DROPS;i++){
        key=(uint32_t)(1000+i*37);
        r=AW_LedgerPut(l,key);assert(r);
        r->fields=(uint8_t)(i%5==0?AW_LEDGER_MOVED:i%5==1?AW_LEDGER_TAKEN:i%5==2?AW_LEDGER_DISABLED:i%5==3?AW_LEDGER_LOCK:AW_LEDGER_OPEN);
        if(r->fields&AW_LEDGER_LOCK){r->lock=(uint8_t)(i%101);r->last_lock=r->lock;}
        if(i%7==0 && (r->fields&AW_LEDGER_TAKEN))r->fields|=AW_LEDGER_STOLEN;
        AW_LedgerSetPlace(l,r,AW_AT_CELL,cell(i%20-10,(i/20)%20-10));
        if(r->fields&AW_LEDGER_MOVED){x=AW_LedgerExtra(l,r);assert(x);x->position[0]=(float)i;x->position[1]=-(float)i;x->position[2]=100;x->yaw=(float)(i%360);}
        assert(AW_LedgerIdentSet(l,key,(uint32_t)(0x9e3779b9U*(key+1))|1U));
    }
    /* the player's drops (key bit 30, by serial), with their item and some with a condition */
    for(i=0;i<DROPS;i++){
        key=AW_LEDGER_PLAYER|(uint32_t)(i+1);
        r=AW_LedgerPut(l,key);assert(r);
        r->fields=(uint8_t)(AW_LEDGER_DROPPED|(i%3?0:AW_LEDGER_CONDITION));
        AW_LedgerSetPlace(l,r,AW_AT_CELL,cell(i%20-10,(i/20)%20-10));
        x=AW_LedgerExtra(l,r);assert(x);x->position[0]=(float)i;x->position[2]=50;x->count=(int32_t)(i%5+1);
        sprintf(x->item,"misc_de_drop_%03d",i%100);if(r->fields&AW_LEDGER_CONDITION)x->condition=0.5f;
    }
    /* stolen pairs, container deltas, ranks */
    for(i=0;i<STOLEN;i++){sprintf(id,"stolen_item_%03d",i);assert(AW_LedgerStolenAdd(l,id,i%2?"owner_npc":"owner_faction",i%2?0:1,i%3+1)>0);}
    for(i=0;i<CONTAINERS;i++)for(k=0;k<DELTAS_PER_CONTAINER;k++){
        sprintf(id,"ingred_%02d",k);
        assert(AW_LedgerContentAdd(l,(uint32_t)(500000+i*11),id,k==0?-2:k==1?3:-1)!=0);
    }
    for(i=0;i<RANKS;i++)assert(AW_LedgerRankSet(l,(uint32_t)(700000+i*13),i%10));
    /* every global, quest and topic of the game, the dispositions changed, the engine's facts */
    for(i=0;i<GLOBALS;i++){sprintf(id,"global_%03d",i);assert(AW_LedgerValueSet(l,AW_LEDGER_GLOBALS,AW_LedgerNameHash(id),i*7+1));}
    for(i=0;i<QUESTS;i++){sprintf(id,"quest_%03d",i);assert(AW_LedgerValueSet(l,AW_LEDGER_QUESTS,AW_LedgerNameHash(id),(i%10+1)*10));}
    for(i=0;i<TOPICS;i++){sprintf(id,"topic_%04d",i);assert(AW_LedgerValueSet(l,AW_LEDGER_TOPICS,AW_LedgerNameHash(id),1));}
    for(i=0;i<DISPOSITIONS;i++)assert(AW_LedgerValueSet(l,AW_LEDGER_DISPOSITIONS,(uint32_t)(800000+i*3),i%100));
    for(i=0;i<40;i++){sprintf(id,"amiwind:fact:%02d",i);assert(AW_LedgerFactSet(l,id,i+1));}
    /* the scripts: locals of 2,800 objects, 100 global scripts and their state */
    for(i=0;i<LOCALS;i++)assert(AW_LedgerLocalSet(l,0,(uint32_t)(1000+i*37),(uint32_t)(0x1000+i%300),i%300,i%4,i+1));
    for(i=0;i<GLOBAL_SCRIPTS;i++){
        assert(AW_LedgerScriptSet(l,(uint32_t)(0x5000+i),i,i%2));
        assert(AW_LedgerLocalSet(l,1,(uint32_t)(0x5000+i),(uint32_t)(0x5000+i),i,0,i+100));
    }
    /* the actors: dead, moved or hostile, their deaths timed; and their changed records */
    for(i=0;i<ACTORS;i++){
        key=(uint32_t)(300000+i*5);
        a=AW_LedgerActor(l,key,1);assert(a);
        if(i%3==0){a->dead=1;a->died=100.0f+(float)i;if(i%6==0)a->cleared=1;}
        else{a->moved=1;a->origin[0]=(float)i;a->origin[1]=1;a->origin[2]=2;a->angles[1]=(float)(i%360);a->health=30+(float)(i%40);a->hours=200.0f+(float)i;a->room=i%2?0:(int32_t)(i%500+1);}
        if(i%4==1)a->fight=1;
        if(i%50==2)a->pick=(uint16_t)(2+i%100);
        assert(AW_LedgerIdentSet(l,key,(uint32_t)(0x85ebca6bU*(key+1))|1U));
    }
    memset(records,0,sizeof(records));memcpy(records,"AWAR",4);records[4]=1;
    records[8]=(unsigned char)(ACTORS>>24);records[9]=(unsigned char)(ACTORS>>16);records[10]=(unsigned char)(ACTORS>>8);records[11]=(unsigned char)ACTORS;
    assert(AW_LedgerRecordsSet(l,records,(int)sizeof(records)));
    /* the refilled places and the content files */
    for(i=0;i<PLACES;i++)assert(AW_LedgerRespawnPlace(l,i%2?AW_AT_CELL:AW_AT_ROOM,i%2?cell(i%40-20,(i/40)%40-20):(int32_t)(i+1),3000.0f,4)==1);
    memset(files,0,sizeof(files));
    for(i=0;i<3;i++){files[i].index=(uint8_t)i;files[i].references=100000U*(uint32_t)(i+1);memset(files[i].digest,0x11*(i+1),8);
        strcpy(files[i].name,i==0?"Morrowind.esm":i==1?"Tribunal.esm":"Bloodmoon.esm");}
    AW_LedgerFilesSet(l,files,3);
}
static void counts(const aw_ledger_t *l,const char *tag)
{
    char key[64];
    sprintf(key,"%s_rows",tag);line(key,l->count);
    sprintf(key,"%s_actors",tag);line(key,l->actor_count);
    sprintf(key,"%s_locals",tag);line(key,l->local_count);
    sprintf(key,"%s_scripts",tag);line(key,l->script_count);
    sprintf(key,"%s_contents",tag);line(key,l->content_count);
    sprintf(key,"%s_stolen",tag);line(key,l->stolen_count);
    sprintf(key,"%s_values",tag);line(key,l->value_count[0]+l->value_count[1]+l->value_count[2]+l->value_count[3]);
    sprintf(key,"%s_stamps",tag);line(key,l->stamp_count);
    sprintf(key,"%s_idents",tag);line(key,l->ident_count);
    sprintf(key,"%s_records",tag);line(key,l->records_bytes);
    sprintf(key,"%s_refused",tag);line(key,(long)l->refused);
}
int main(int argc,char **argv)
{
    int n,m,i,ledger_bytes,journal_bytes,plain;clock_t t0,t1;
    assert(argc>1);o=fopen(argv[1],"w");assert(o);
    base();
    aw_save_ledger_rows=AW_LedgerRows;aw_save_ledger_encode=AW_LedgerEncode;aw_save_ledger_decode=AW_LedgerDecode;
    aw_save_journal_encode=AW_JHistEncode;aw_save_journal_decode=AW_JHistDecode;
    /* the game's state without a change: the fixed part of every save */
    plain=AW_SaveEncode(one,AW_SAVE_BYTES,&save);assert(plain>0);line("plain_bytes",plain);
    t0=clock();fill(&list);t1=clock();line("fill_ms",ms(t0,t1));
    for(i=0;i<JOURNAL;i++)assert(AW_JHistAdd(&hist,(uint32_t)(0x7000+i/4),(i%4+1)*10,i/25,1000*(i%86))==2);
    assert(list.refused==0);counts(&list,"made");
    line("resident_bytes",(long)AW_LedgerResident(&list));
    ledger_bytes=AW_LedgerEncode(&list,NULL,0);assert(ledger_bytes>0);line("ledger_bytes",ledger_bytes);
    line("ledger_without_records_bytes",ledger_bytes-list.records_bytes);
    journal_bytes=AW_JHistEncode(&hist,NULL,0);assert(journal_bytes>0);line("journal_bytes",journal_bytes);
    /* one saved game */
    memset(&changes,0,sizeof(changes));changes.ledger=&list;changes.journal=&hist;
    t0=clock();n=AW_SaveEncodeChanges(one,sizeof(one),&save,&changes);t1=clock();
    assert(n>0);line("file_bytes",n);line("encode_ms",ms(t0,t1));
    assert(n<1048576);   /* the contract: well under 1 MiB in a 100-hour game */
    /* loaded: every part back */
    memset(&back,0,sizeof(back));back.ledger=&got;back.journal=&hist_back;
    t0=clock();assert(AW_SaveDecodeChanges(one,n,&loaded,&back));t1=clock();line("decode_ms",ms(t0,t1));
    counts(&got,"loaded");
    assert(got.count==list.count && got.actor_count==list.actor_count && got.local_count==list.local_count &&
           got.script_count==list.script_count && got.content_count==list.content_count && got.stolen_count==list.stolen_count &&
           got.stamp_count==list.stamp_count && got.ident_count==list.ident_count && got.records_bytes==list.records_bytes &&
           got.file_count==3 && hist_back.count==JOURNAL);
    for(i=0;i<AW_LEDGER_TABLES;i++)assert(got.value_count[i]==list.value_count[i]);
    /* the loaded game saved again, unchanged: the same bytes (no duplicate, nothing grown) */
    memset(&changes,0,sizeof(changes));changes.ledger=&got;changes.journal=&hist_back;
    m=AW_SaveEncodeChanges(two,sizeof(two),&loaded,&changes);
    assert(m==n && !memcmp(one,two,(size_t)n));line("second_encode_same",1);
    AW_SaveRelease(&loaded);AW_LedgerClear(&list);AW_LedgerClear(&got);AW_JHistClear(&hist);AW_JHistClear(&hist_back);
    fclose(o);puts("aga_save_budget_test ok");
    return 0;
}
