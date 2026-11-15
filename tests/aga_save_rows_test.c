/* SPDX-License-Identifier: GPL-2.0-or-later
 * SAVE-ACTOR-ROWS-256-66 and MAP-EXPLORED-SAVE-BLOCK-66 through the real writer and loader (aw_save.c): NPCs and
 * creatures changed in two places, both places left, a save in a third, New Game, the load, both places entered
 * again: every actor as it was left (301 rows, past the old 256); the actor window letting an actor go keeps its row;
 * save, load, save gives the same rows; a full 64 KB actor block and a well explored map in one save; a save of the
 * form before v0.0.66 (the 32 KB block, the 48-byte rows) loads; the heap the same to the byte after every save and
 * load. Synthetic actors only; no original game data. Linked with --wrap for malloc, calloc, realloc and free. */
#include <assert.h>
#include <stdarg.h>
#include "aw_save.c"
#include "aw_mapfog.h"
void AW_CombatEquipmentStore(void){}
server_t sv;server_static_t svs;client_state_t cl;
double realtime;char com_gamedir[MAX_OSPATH];int pr_edict_size;
char *pr_strings;vec3_t vec3_origin;keydest_t key_dest;
static char strings[64]="\0aw_npc\0aw_creature\0";   /* 1 aw_npc, 8 aw_creature */
#define EDICTS 512
static edict_t edicts[EDICTS];                         /* 0 the world, 1 the player, then the place's actors */
static eval_t refs[EDICTS],roles[EDICTS],hello[EDICTS],manual[EDICTS],done[EDICTS],hand[5];
static const char *hand_names[]={"aw_hand_goal","aw_hand_state","aw_torch","aw_hand_started","aw_attack_latched"};
static client_t client;
aw_story_t aw_story;
edict_t *EDICT_NUM(int n){assert(n>=0 && n<EDICTS);return &edicts[n];}
eval_t *GetEdictFieldValue(edict_t *e,char *name){
    int i=(int)(e-edicts),k;
    if(i==1){for(k=0;k<5;k++)if(!strcmp(name,hand_names[k]))return &hand[k];return NULL;}
    if(!strcmp(name,"aw_ref"))return &refs[i];
    if(!strcmp(name,"aw_intro_role"))return &roles[i];
    if(!strcmp(name,"aw_hello_count"))return &hello[i];
    if(!strcmp(name,"aw_manual_count"))return &manual[i];
    if(!strcmp(name,"aw_hello_done"))return &done[i];
    return NULL;
}
char *ED_NewString(char *s){int i;for(i=0;i<60;i++)if(!strcmp(pr_strings+i,s))return pr_strings+i;assert(0);return NULL;}
void ED_Free(edict_t *e){e->free=true;}
static int quiet;
void Con_Printf(char *fmt,...){va_list a;if(quiet)return;va_start(a,fmt);vprintf(fmt,a);va_end(a);}
int AW_BarrierLoad(void){return 1;}void AW_OpeningSpawn(void){}
int AW_NPCFloor(edict_t *p){return 1;}int AW_RegionContains(const float *p){return 1;}
void SV_LinkEdict(edict_t *p,qboolean b){}int AW_ReaderActive(void){return 0;}
int COM_FOpenFile(char *name,FILE **f){*f=NULL;return -1;}
float anglemod(float a){return a-360.0f*floorf(a/360.0f);}
int AW_SceneMapSize(const char *name,char *map,int capacity){if(map && capacity>0)snprintf(map,capacity,"maps/%s.bsp",name);return 200;}
int AW_RegionSelect(const char *name,const float *position,int variant){return 1;}
void IN_AWClearButtons(void){}
static char command[64];
void Cbuf_InsertText(char *text){strncpy(command,text,sizeof(command)-1);}
/* every allocation counted to the byte */
static long live;
void *__real_malloc(size_t n);void *__real_realloc(void *p,size_t n);void __real_free(void *p);
void *__wrap_malloc(size_t n){size_t *p=(size_t *)__real_malloc(n+16);if(!p)return NULL;p[0]=n;live+=(long)n;return (char *)p+16;}
void __wrap_free(void *q){size_t *p;if(!q)return;p=(size_t *)(void *)((char *)q-16);live-=(long)p[0];__real_free(p);}
void *__wrap_realloc(void *q,size_t n){
    size_t *p,was;
    if(!q)return __wrap_malloc(n);
    p=(size_t *)(void *)((char *)q-16);was=p[0];p=(size_t *)__real_realloc(p,n+16);
    if(!p)return NULL;
    p[0]=n;live+=(long)n-(long)was;return (char *)p+16;
}
void *__wrap_calloc(size_t c,size_t s){void *q=__wrap_malloc(c*s);if(q)memset(q,0,c*s);return q;}

/* the actor block as aw_mwhost.c's actors_export fills it: here the whole block the setting gives, a known pattern */
static int block_written,block_read;
static int block_export(unsigned char *out,int capacity){int i;for(i=0;i<capacity;i++)out[i]=(unsigned char)(i*31+7);block_written=capacity;return capacity;}
static void block_import(const unsigned char *data,int bytes){
    int i;block_read=bytes;
    for(i=0;i<bytes;i++)assert(data[i]==(unsigned char)(i*31+7));
    AW_MapFogReset();   /* as actors_import does before its blocks */
}
static void explored_import(const unsigned char *p,int bytes){assert(AW_MapFogImport(p,bytes)>0);}
/* the change list's capture at a place's unload (aw_actors.c AW_ActorsCapture): NPCs and creatures alike */
static int left_npcs,left_creatures;
static void leave_capture(edict_t *e){if(e->v.classname==1)left_npcs++;else if(e->v.classname==8)left_creatures++;}
/* a place: NPCS NPCs from FIRST (every GREET-th greeted, hello SAY, manual and done on the greeted), CREATURES
 * creatures, ROLE 1: one builder's role (no game reference) hurt and moved off its spot */
static void place(const char *map,int npcs,uint32_t first,int greet,int say,int creatures,int role){
    int i,n=2;
    strcpy(sv.name,map);
    memset(&edicts[2],0,sizeof(edict_t)*(EDICTS-2));
    memset(refs,0,sizeof refs);memset(roles,0,sizeof roles);memset(hello,0,sizeof hello);
    memset(manual,0,sizeof manual);memset(done,0,sizeof done);
    for(i=0;i<npcs;i++,n++){
        edicts[n].v.classname=1;refs[n]._float=(float)(first+(uint32_t)i);edicts[n].v.health=100;
        edicts[n].v.origin[0]=(float)(10*i);edicts[n].v.origin[1]=-20;
        if(greet && !(i%greet)){hello[n]._float=(float)say;manual[n]._float=1;done[n]._float=1;}
    }
    for(i=0;i<creatures;i++,n++){edicts[n].v.classname=8;refs[n]._float=(float)(first+5000+(uint32_t)i);edicts[n].v.health=30;}
    if(role){edicts[n].v.classname=1;roles[n]._float=3;edicts[n].v.health=12.5f;
             edicts[n].v.origin[0]=321;edicts[n].v.origin[1]=-77;   /* whole units: the packed place's step */edicts[n].v.origin[2]=8;edicts[n].v.angles[1]=135;hello[n]._float=2;n++;}
    sv.num_edicts=n;
}
/* the edict of reference REF in the place (0: none) */
static edict_t *actor(uint32_t ref){int i;for(i=2;i<sv.num_edicts;i++)if(!edicts[i].free && refs[i]._float==(float)ref)return &edicts[i];return NULL;}
static edict_t *role_edict(void){int i;for(i=2;i<sv.num_edicts;i++)if(roles[i]._float==3)return &edicts[i];return NULL;}
static void game(void){
    world.profile=2;
    aw_story.stage=AW_STAGE_RELEASED;aw_story.ship_disabled=1;aw_story.captain=-1;strcpy(aw_story.name,"Synthetic");
    memset(&aw_character,0,sizeof(aw_character));aw_character.level=1;aw_character.hair=1;aw_character.valid=1;
    aw_character.current[0]=aw_character.maximum[0]=50;
    edicts[1].v.health=50;edicts[1].v.movetype=MOVETYPE_WALK;memset(hand,0,sizeof hand);
}
static void load(int slot,const char *at){
    command[0]=0;strcpy(sv.name,at);
    assert(AW_SaveRead(2,slot)==1 && loading);
    sv.num_edicts=2;AW_SaveSpawn();assert(!loading);
}
int main(int argc,char **argv){
    int i,j,n,rows,before_rows,c;long held=0;aw_saved_actor_t *kept;edict_t *e;
    assert(argc==2);strcpy(com_gamedir,argv[1]);setvbuf(stdout,NULL,_IONBF,0);
    aw_race_count=aw_class_count=aw_birth_count=1;aw_part_count=2;
    strcpy(aw_races[0].id,"test_race");strcpy(aw_classes[0].id,"test_class");
    strcpy(aw_births[0].id,"test_sign");strcpy(aw_parts[0].id,"test_head");
    strcpy(aw_parts[1].id,"test_hair");aw_parts[1].kind=1;
    pr_strings=strings;sv.active=1;sv.time=10;svs.maxclients=1;svs.clients=&client;client.edict=&edicts[1];
    content_ready=1;memset(content_id,7,32);key_dest=key_game;
    AW_StateReset();assert(AW_StateSet(&aw_state,AW_GLOBAL,"chargenstate",-1));
    memset(&world,0,sizeof(world));game();
    save_block.value=64;aw_save_actors_export=block_export;aw_save_actors_import=block_import;
    aw_save_explored_encode=AW_MapFogExport;aw_save_explored_import=explored_import;
    /* a well explored map: 600 cells walked over, 120 rooms */
    {int cx,cy,gx,gy;char name[16];static const float mins[2]={0,0},maxs[2]={1600,1600};
     for(cy=0;cy<20;cy++)for(cx=0;cx<30;cx++)for(gy=0;gy<8;gy++)for(gx=0;gx<8;gx++)AW_MapFogReveal(cx*8192.0f+gx*1024+512,cy*8192.0f+gy*1024+512);
     for(i=0;i<120;i++){sprintf(name,"ri%010d",i);AW_MapFogRoomReveal(name,800,800,mins,maxs);}}
    /* place A (Seyda Neen): 200 NPCs, every other one greeted, 50 creatures, the builder's role; left */
    aw_save_actor_leave=leave_capture;
    place("seyda",200,1000,2,1,50,1);assert(AW_SaveLeave());
    assert(world.actor_count==101);                    /* 100 greeted + the role; no creature, no ungreeted NPC */
    assert(left_npcs==201 && left_creatures==50);      /* and every NPC and creature on the change list */
    /* place B (Balmora): 200 NPCs all greeted, 30 creatures; the actor window lets one go before the place is left */
    place("balmora",200,3000,1,2,30,0);
    e=actor(3199);AW_SaveCaptureActor(e);e->free=true;   /* released (aw_actors.c Release) */
    assert(AW_SaveLeave());assert(world.actor_count==301 && left_npcs==201+199 && left_creatures==80);
    /* place C (the census office), nobody: the save holds both places' rows (past the old 256) */
    place("census",0,0,0,0,0,0);
    quiet=1;assert(AW_SaveWrite(0));quiet=0;
    assert(block_written==65536);                      /* the full block the setting gives (aw_save_block_kb 64) */
    kept=(aw_saved_actor_t *)malloc(sizeof(aw_saved_actor_t)*301);memcpy(kept,world.actors,sizeof(aw_saved_actor_t)*301);
    /* New Game: nothing kept */
    AW_SaveReset();AW_MapFogReset();assert(!world.actor_count && !world.actors && !AW_MapFogCells());game();
    /* the load: every row of both places, the block, the explored map */
    block_read=0;load(0,"census");
    assert(world.actor_count==301 && !memcmp(world.actors,kept,sizeof(aw_saved_actor_t)*301));
    assert(block_read==65536 && AW_MapFogCells()==600+2*(30+20) && AW_MapFogRooms()==120);
    /* place A again, as the game data spawns it (counters 0, the role on its spot at full health) */
    place("seyda",200,1000,0,0,50,1);role_edict()->v.health=40;role_edict()->v.origin[0]=0;
    loading=0;AW_SaveSpawn();
    for(i=0;i<200;i++){e=actor(1000+(uint32_t)i);j=(int)(e-edicts);
        assert(hello[j]._float==(i%2?0:1) && manual[j]._float==(i%2?0:1) && done[j]._float==(i%2?0:1) && e->v.health==100);}
    e=role_edict();j=(int)(e-edicts);
    assert(e->v.origin[0]==321 && e->v.origin[1]==-77 && e->v.angles[1]==135 && e->v.health==12.5f && hello[j]._float==2);
    for(i=0;i<50;i++)assert(actor(6000+(uint32_t)i)->v.health==30);   /* creatures: what the change list holds */
    /* place B again: all 200, the one the window let go too */
    place("balmora",200,3000,0,0,30,0);loading=0;AW_SaveSpawn();
    for(i=0;i<200;i++){e=actor(3000+(uint32_t)i);j=(int)(e-edicts);assert(hello[j]._float==2 && done[j]._float==1);}
    /* back to the census: save, load, save gives the same rows */
    place("census",0,0,0,0,0,0);quiet=1;assert(AW_SaveWrite(1));quiet=0;
    rows=world.actor_count;memcpy(kept,world.actors,sizeof(aw_saved_actor_t)*(size_t)rows);
    load(1,"census");assert(world.actor_count==rows && !memcmp(world.actors,kept,sizeof(aw_saved_actor_t)*(size_t)rows));
    /* a greeting changed and put back to nothing: only its latest state, no row once it holds nothing */
    place("balmora",200,3000,0,0,30,0);loading=0;AW_SaveSpawn();
    for(i=0;i<200;i++){j=(int)(actor(3000+(uint32_t)i)-edicts);hello[j]._float=i<100?5:0;manual[j]._float=0;done[j]._float=0;}
    before_rows=world.actor_count;assert(AW_SaveCapture());assert(world.actor_count==before_rows-100);
    for(i=0;i<100;i++)assert(world.actors[AW_SaveActorFind(&world,3000+(uint32_t)i,AW_MapLogicalId("balmora"))].hello_count==5);
    printf("rows: 301 over two places kept through leave, save, New Game and load; %d after 100 went back to the game data\n",
           world.actor_count);
    /* a save of the form before v0.0.66: the 32 KB block, the 48-byte rows (at most 256) */
    save_block.value=32;aw_save_rows_form=1;
    place("seyda",200,1000,2,1,50,1);AW_SaveReset();game();assert(AW_SaveCapture() && world.actor_count==101);
    quiet=1;assert(AW_SaveWrite(2));quiet=0;assert(block_written==32768);
    memcpy(kept,world.actors,sizeof(aw_saved_actor_t)*101);
    save_block.value=64;aw_save_rows_form=0;AW_SaveReset();game();
    block_read=0;load(2,"seyda");
    assert(block_read==32768 && world.actor_count==101);
    for(i=0;i<101;i++){
        assert(world.actors[i].reference==kept[i].reference && world.actors[i].scene==kept[i].scene &&
               world.actors[i].hello_count==kept[i].hello_count && world.actors[i].fields==AW_ROW_ALL);
    }
    printf("old form: a 32 KB block and 101 rows of 48 bytes loaded\n");
    /* the heap: save and load five more times, the same bytes held after each */
    place("balmora",200,3000,1,2,30,0);
    for(c=0;c<6;c++){
        quiet=1;assert(AW_SaveWrite(3));quiet=0;
        load(3,"balmora");
        if(c==1)held=live;
        else if(c>1)assert(live==held);
    }
    printf("heap: %ld bytes held after each save and load, unchanged\n",held);
    free(kept);
    puts("saved actor rows and the explored map: write, leave, New Game, load and the old form passed");
    return 0;
}
