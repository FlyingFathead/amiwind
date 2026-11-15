/* SPDX-License-Identifier: GPL-2.0-or-later
 * SAVE-EXPORT-FAILURE-ACCEPTED-65 (the save contract's rule 4, all or nothing): the real save path (aw_save.c
 * AW_SaveWrite -> encode_world) with every export forced to fail in turn, and with rows the world change list refused
 * while an export reported success. Each time: the save is refused, the previous generation stays byte for byte, no
 * other generation is written, the generation number is as before, the actor records' copy is given back, and the
 * one console line names the part. Then a good save still works. Synthetic state only (tests/test_save_refusal_native.py). */
#include <assert.h>
#include <stdarg.h>
#include "aw_save.c"
void AW_CombatEquipmentStore(void){}
server_t sv;server_static_t svs;client_state_t cl;
double realtime;char com_gamedir[MAX_OSPATH];int pr_edict_size;
char *pr_strings;vec3_t vec3_origin;
static char strings_a[128]="\0progs/v_nord.mdl\0progs/future_weapon.mdl\0aw_npc";
static eval_t field_values[5];
static const char *field_names[]={"aw_hand_goal","aw_hand_state","aw_torch","aw_hand_started","aw_attack_latched"};
static edict_t player;static client_t client;
edict_t *EDICT_NUM(int n){assert(n==1);return &player;}
aw_story_t aw_story;
eval_t *GetEdictFieldValue(edict_t *p,char *name){int i;assert(p==&player);for(i=0;i<5;i++)if(!strcmp(name,field_names[i]))return &field_values[i];return NULL;}
char *ED_NewString(char *s){int i;for(i=0;i<120;i++)if(!strcmp(pr_strings+i,s))return pr_strings+i;assert(0);return NULL;}
static char line[512];
void Con_Printf(char *fmt,...){va_list a;va_start(a,fmt);vsnprintf(line,sizeof(line),fmt,a);va_end(a);}
int AW_BarrierLoad(void){return 1;}void AW_OpeningSpawn(void){}
int AW_NPCFloor(edict_t *p){return 1;}int AW_RegionContains(const float *p){return 1;}
void SV_LinkEdict(edict_t *p,qboolean b){}int AW_ReaderActive(void){return 0;}
int COM_FOpenFile(char *name,FILE **f){*f=NULL;return -1;}
float anglemod(float a){return a;}
/* AW_SaveTick's game around it (the autosave's rules are not exercised here: no autosave slots) */
client_static_t cls;keydest_t key_dest=key_game;
void AW_UISubtitle(const char *a,const char *b,double t){(void)a;(void)b;(void)t;}
int AW_ModalWorldFrozen(void){return 0;}int AW_LoadingScreen(void){return 0;}int AW_PhotoModeActive(void){return 0;}
int AW_PlayerInCombat(void){return 0;}double AW_SpeechRemaining(void){return 0;}int AW_RecorderActive(void){return 0;}
static void hand(void){memset(field_values,0,sizeof(field_values));field_values[0]._float=1;field_values[1]._float=2;
    field_values[2]._float=1;field_values[3]._float=sv.time-.2;field_values[4]._float=1;player.v.weaponframe=2;player.v.weaponmodel=1;}

/* the exports, each forced to fail when FAIL names it; NAMED: it names its part first (AW_SaveRefusePart) */
enum {NONE,SCRIPT,SCRIPT_NAMED,SCRIPT_ROW,IDENT,CHANGES,CHANGES_ROW,OBJECTS,ACTORS,ACTORS_NAMED,ACTORS_GROWN_ROW,JOURNAL,SEQUENCE};
static int fail,block_tries;
static int step_busy;static int busy_hook(void){return step_busy;}   /* SAVE-INSIDE-SCRIPT-STEP-66: the host's script step */
static int script_export(struct aw_ledger_s *l){
    aw_ledger_t *x=(aw_ledger_t *)l;
    /* a kept value, and the actor records' copy the real export makes (given back by a refused save) */
    assert(AW_LedgerLocalSet(x,0,5,AW_LedgerNameHash("guardScript"),1,0,3));
    assert(AW_LedgerRecordsSet(x,(const unsigned char *)"AWAR\1\0\0\0\0\0\0\0",12));
    if(fail==SCRIPT)return 0;
    if(fail==SCRIPT_NAMED){AW_SaveRefusePart("the quest stages");return 0;}
    /* a row the list refuses (a drop's key for an object's local) while the export says all went well */
    if(fail==SCRIPT_ROW)assert(!AW_LedgerLocalSet(x,0,AW_LEDGER_PLAYER|5,AW_LedgerNameHash("guardScript"),1,0,3));
    return 1;
}
static int ident_refresh(struct aw_ledger_s *l){(void)l;return fail!=IDENT;}
static int changes_export(aw_changes_t *c){
    if(fail==CHANGES)return -1;
    if(fail==CHANGES_ROW)assert(!AW_LedgerItemLocalSet(&aw_ledger,0,0,0,1,0,0,0,1));   /* no item: refused */
    return c->count;
}
static int objects_export(aw_changes_t *c){return fail==OBJECTS?-1:c->count;}
static int actors_export(unsigned char *out,int capacity){
    (void)out;(void)capacity;
    if(fail==ACTORS)return -1;
    /* a part of the block names itself (aw_mwhost.c actors_export's ACTOR_PART): the line says which part */
    if(fail==ACTORS_NAMED){AW_SaveRefusePart("the filled soul gems");return -1;}
    /* a part short of room names itself, the block is grown and the part fits: its name must not outlive the retry;
     * the save is then refused for a row the list refused, and the line must name the row, not the gems */
    if(fail==ACTORS_GROWN_ROW){
        if(++block_tries==1){AW_SaveRefusePart("the filled soul gems");return -1;}
        assert(!AW_LedgerLocalSet(&aw_ledger,0,AW_LEDGER_PLAYER|5,AW_LedgerNameHash("guardScript"),1,0,3));
    }
    return 0;
}

static unsigned char before[AW_SAVE_MAX_BYTES],now[AW_SAVE_MAX_BYTES];
static int file_bytes(int generation,unsigned char *out){
    char filename[512];FILE *f;int n;
    assert(path(filename,sizeof(filename),world.profile,1,generation));
    if(!(f=fopen(filename,"rb")))return -1;
    n=(int)fread(out,1,AW_SAVE_MAX_BYTES,f);fclose(f);return n;
}
static void refused_with(int how,const char *part){
    int n,m;uint32_t sequence=world.sequence;
    fail=how;line[0]=0;
    n=file_bytes(0,before);assert(n>0);
    assert(!AW_SaveWrite(1));
    m=file_bytes(0,now);
    assert(m==n && !memcmp(before,now,(size_t)n));          /* the previous generation stays, byte for byte */
    assert(file_bytes(1,now)<0);                             /* and no other generation is written */
    assert(world.sequence==sequence);                        /* the generation number as before */
    assert(!aw_ledger.records_bytes && !aw_ledger.records);  /* the actor records' copy given back */
    assert(!world.state.items.block);                        /* the game's item table is the game's alone */
    if(!strstr(line,part) || !strstr(line,"previous saves retained")){fprintf(stderr,"%d: %s\n",how,line);assert(0);}
    printf("refused %d: %s",how,line);
    fail=NONE;
}
int main(int argc,char **argv){
    assert(argc==2);
    aw_race_count=aw_class_count=aw_birth_count=1;aw_part_count=2;
    strcpy(aw_races[0].id,"test_race");strcpy(aw_classes[0].id,"test_class");
    strcpy(aw_births[0].id,"test_sign");strcpy(aw_parts[0].id,"test_head");
    strcpy(aw_parts[1].id,"test_hair");aw_parts[1].kind=1;
    world.sequence=1;world.profile=2;strcpy(world.scene,"seyda");
    strcpy(aw_story.name,"Synthetic");aw_story.stage=AW_STAGE_RELEASED;aw_story.ship_disabled=1;aw_story.captain=-1;
    aw_character.level=1;aw_character.hair=1;aw_character.valid=1;aw_character.current[0]=aw_character.maximum[0]=50;
    assert(AW_StateSet(&aw_state,AW_GLOBAL,"chargenstate",-1));
    assert(AW_ItemAdd(&aw_state,"ingredient_test",1));
    strcpy(com_gamedir,argv[1]);pr_strings=strings_a;sv.active=1;sv.num_edicts=1;sv.time=10;strcpy(sv.name,"seyda");
    sv.model_precache[1]="progs/v_nord.mdl";svs.maxclients=1;svs.clients=&client;client.edict=&player;
    player.v.health=50;player.v.movetype=MOVETYPE_WALK;content_ready=1;hand();
    aw_save_script_export=script_export;aw_save_ident_refresh=ident_refresh;aw_save_changes_export=changes_export;
    aw_save_objects_export=objects_export;aw_save_actors_export=actors_export;
    aw_save_ledger_rows=AW_LedgerRows;aw_save_ledger_encode=AW_LedgerEncode;aw_save_ledger_decode=AW_LedgerDecode;
    aw_save_journal_encode=AW_JHistEncode;aw_save_journal_decode=AW_JHistDecode;
    /* the previous generation: a good save (generation a) */
    assert(AW_SaveWrite(1) && world.sequence==2);
    refused_with(SCRIPT,"the scripts' state");
    refused_with(SCRIPT_NAMED,"the quest stages");
    refused_with(SCRIPT_ROW,"a row of the world change list");
    refused_with(IDENT,"the references' identities");
    refused_with(CHANGES,"the actors' changes");
    refused_with(CHANGES_ROW,"a row of the world change list");
    refused_with(OBJECTS,"the objects' changes");
    refused_with(ACTORS,"the actor block");
    refused_with(ACTORS_NAMED,"the filled soul gems");
    block_tries=0;refused_with(ACTORS_GROWN_ROW,"a row of the world change list");
    assert(block_tries==2 && !strstr(line,"soul gems"));   /* grown once; the stale name gone */
    /* the dated journal with entries it cannot write (past its bound) is refused, never left out */
    {int keep=aw_jhist.count;aw_jhist.count=AW_JHIST_MAX+1;refused_with(JOURNAL,"the dated journal");aw_jhist.count=keep;}
    /* every generation number used */
    {uint32_t keep=world.sequence;world.sequence=0xffffffffU;refused_with(SEQUENCE,"the generation number");world.sequence=keep;}
    /* after them all, a good save writes the other generation with the next number */
    assert(AW_SaveWrite(1) && world.sequence==3 && file_bytes(1,now)>0 && strstr(line,"Saved Manual 1"));
    /* SAVE-INSIDE-SCRIPT-STEP-66 (the save contract, rule 6): a save asked for inside a script step is queued, not
     * taken: nothing is written and the generation number stays; the step's second half (a second ingredient, the other
     * half of a scripted transfer) happens; the settled frame's tick writes it, and the save holds the item once, with
     * the count the whole step left (2), under the next generation */
    {int n_before=file_bytes(0,before),m_before=file_bytes(1,now),n;uint32_t sequence=world.sequence;aw_save_t got;
     step_busy=1;aw_save_busy=busy_hook;line[0]=0;
     assert(AW_SaveWrite(1)==2 && AW_SaveQueued()==1 && strstr(line,"Save queued: Manual 1"));
     assert(world.sequence==sequence && file_bytes(0,now)==n_before && file_bytes(1,now)==m_before);
     AW_SaveTick();assert(AW_SaveQueued()==1 && world.sequence==sequence);          /* still busy: still waiting */
     assert(AW_ItemAdd(&aw_state,"ingredient_test",1) && AW_StateGet(&aw_state,AW_ITEM,"ingredient_test")==2);
     step_busy=0;line[0]=0;AW_SaveTick();
     assert(AW_SaveQueued()==-1 && world.sequence==sequence+1 && strstr(line,"Saved Manual 1"));
     n=file_bytes(0,now);assert(n>0 && AW_SaveDecodeChanges(now,n,&got,NULL) && got.sequence==sequence+1 &&
                                AW_StateGet(&got.state,AW_ITEM,"ingredient_test")==2);
     AW_SaveRelease(&got);
     /* the recorder's starting save and the debug snapshot refuse while busy */
     step_busy=1;{int size;uint32_t pr,sq;assert(!AW_SaveEncodeNow(&size,&pr,&sq) && strstr(line,"inside a script step"));}
     step_busy=0;aw_save_busy=NULL;}
    puts("Every export refused in turn: no generation written, the previous kept, the part named; then saved; a save inside a script step waits for the settled frame.");
    return 0;
}
