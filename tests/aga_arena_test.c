/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_arena.c (the Vivec Arena debug minigame) with the gallery session and
 * the combat layer stubbed: the commands and aliases (dbgmode, testarena),
 * the opponent choice (default fighter, by name, record ID, gallery number,
 * stand-in, refusals, list, next/prev), the map choice (pit, gallery floor,
 * here), spectators leaving and the opponent arriving with the residents'
 * box, both fighters placed on the pit floor facing each other at full
 * health, the title card -> fight -> result flow, the result keys (rematch,
 * same seed, next, pick, leave) and the setup hook. */
#include "quakedef.h"
#include "aw_combat.h"
#include "aw_character.h"
#include <assert.h>

server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;static int loading;int AW_LoadingScreen(void){return loading;}
keydest_t key_dest;viddef_t vid;
char *pr_strings;double realtime;aw_character_t aw_character;
static char strings[2048];static int string_at=1;
static edict_t edicts[16];static client_t client;static model_t fighter_model,gallery_model;
static eval_t source_id[16];
static int have_pit,have_floor,enters,reloads,leaves,engages,clears,toggles,box_sets,frees,model_loads;
static char entered_map[32],queued[128],last_layout[160],printed[4096];
static float box_low[3],box_high[3],seed_cvar,seed_at_engage;
static aw_combat_stats_t stats;static aw_fighter_t engaged;

char *ED_NewString(char *s){int at=string_at;strcpy(strings+at,s);string_at+=strlen(s)+1;return strings+at;}
edict_t *EDICT_NUM(int n){return &edicts[n];}
edict_t *ED_Alloc(void){edict_t *e=&edicts[sv.num_edicts++];memset(e,0,sizeof(*e));return e;}
void ED_Free(edict_t *e){e->free=1;frees++;}
eval_t *GetEdictFieldValue(edict_t *e,char *name){return strcmp(name,"aw_source_id")?NULL:&source_id[e-edicts];}
void SetMinMaxSize(edict_t *e,float *lo,float *hi,qboolean rotate){(void)rotate;VectorCopy(lo,e->v.mins);VectorCopy(hi,e->v.maxs);
    VectorCopy(lo,box_low);VectorCopy(hi,box_high);box_sets++;}
void SV_LinkEdict(edict_t *e,qboolean touch){(void)e;(void)touch;}
/* The pit floor: z -116 (original -464 x 0.25). */
trace_t SV_Move(vec3_t a,vec3_t mi,vec3_t ma,vec3_t b,int type,edict_t *e){
    trace_t t;float floor_z=-116-mi[2];(void)ma;(void)type;(void)e;
    memset(&t,0,sizeof(t));t.fraction=1;VectorCopy(b,t.endpos);
    if(b[2]<floor_z && a[2]>=floor_z){t.fraction=(a[2]-floor_z)/(a[2]-b[2]);t.endpos[2]=floor_z;t.plane.normal[2]=1;}
    return t;
}
model_t *Mod_ForName(char *name,qboolean crash){(void)crash;model_loads++;return !strncmp(name,"gallery/",8)?&gallery_model:&fighter_model;}
static const char *fighters="AWAF1 2\n"
    "mevil molor\tarena/f1.mdl\tMevil Molor\tidle:0:4:0.6667 run:4:6:0.1556 attack:10:8:0.1500:0.667 hit:18:3:0.3333 knock:21:4:0.6667 death:25:6:0.3333\n"
    "ultis salam\tarena/f2.mdl\tUltis Salam\tidle:0:4:0.6667 run:4:6:0.1556 attack:10:8:0.1500:0.667 hit:18:3:0.3333 knock:21:4:0.6667 death:25:6:0.3333\n";
int COM_FOpenFile(char *name,FILE **file){
    *file=NULL;
    if(!strcmp(name,"arena/fighters.txt")){*file=fmemopen((void *)fighters,strlen(fighters),"r");return (int)strlen(fighters);}
    if(!strcmp(name,"maps/vai000.bsp"))return have_pit?1000:-1;
    if(!strcmp(name,"maps/charplane.bsp"))return have_floor?1000:-1;
    if(!strncmp(name,"arena/f",7) || !strncmp(name,"gallery/",8))return 5000;
    return -1;
}
int AW_CombatSettingsLoad(void){return 1;}
int AW_CombatActorLoad(const char *id,aw_fighter_t *out){
    memset(out,0,sizeof(*out));
    if(strcmp(id,"mevil molor") && strcmp(id,"ultis salam") && strcmp(id,"fargoth") && strcmp(id,"caius cosades"))return 0;
    strcpy(out->id,id);strcpy(out->name,!strcmp(id,"fargoth")?"Fargoth":"Someone");out->level=9;out->health=out->health_max=94;return 1;
}
void (*aw_combat_result)(int won);
int AW_CombatEngage(struct edict_s *e,const aw_fighter_t *f,const char *layout){
    (void)e;engages++;engaged=*f;strcpy(last_layout,layout?layout:"(own frames)");seed_at_engage=seed_cvar;return 1;
}
void AW_CombatClear(void){clears++;}
const aw_combat_stats_t *AW_CombatStats(void){return &stats;}
const aw_fighter_t *AW_CombatFighter(struct edict_s *e){(void)e;return &engaged;}
int AW_GalleryArenaEnter(const char *map){enters++;strcpy(entered_map,map);return 1;}
void AW_GalleryArenaReload(void){reloads++;}
void AW_GalleryArenaLeave(void){leaves++;}
int AW_GalleryArenaBack(vec3_t o,vec3_t a){o[0]=500;o[1]=0;o[2]=40;a[0]=a[1]=a[2]=0;return 1;}
void AW_GalleryHandsDrawn(edict_t *p){(void)p;}
/* Gallery: #5 is "Caius Cosades" (an NPC), #6 a creature (refused). */
int AW_GalleryFind(const char *search,int index,char *id,char *name,char *model,int *total){
    *total=3;
    if(search && strcmp(search,"5") && strcasecmp(search,"caius cosades"))return 0;
    if(!search && index!=0)return 0;
    strcpy(id,"caius cosades");strcpy(name,"Caius Cosades");strcpy(model,"gallery/m0123456789abcdef.mdl");return 1;
}
void Con_Printf(char *f,...){va_list ap;int n=strlen(printed);va_start(ap,f);if(n<3800)vsnprintf(printed+n,sizeof(printed)-n,f,ap);va_end(ap);}
void Con_ToggleConsole_f(void){toggles++;}
void Sys_Error(char *f,...){(void)f;abort();}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
float Q_atof(char *s){return (float)atof(s);}
float Cvar_VariableValue(char *name){assert(!strcmp(name,"aw_combat_seed"));return seed_cvar;}
void Cvar_SetValue(char *name,float v){assert(!strcmp(name,"aw_combat_seed"));seed_cvar=v;}
void Cbuf_InsertText(char *s){strcpy(queued,s);}
int AW_ConsoleCharWidth(void){return 8;}
int AW_ConsoleCharHeight(void){return 8;}
static char drawn[4096];
void AW_ConsoleCharacter(int x,int y,int c){int n=strlen(drawn);(void)x;(void)y;if(n<4000){drawn[n]=(char)c;drawn[n+1]=0;}}
void AW_UIBox(int x,int y,int w,int h){(void)x;(void)y;(void)w;(void)h;}
int scr_copyeverything;
static struct {char *name;xcommand_t f;} commands[8];static int command_count;
void Cmd_AddCommand(char *name,xcommand_t f){commands[command_count].name=name;commands[command_count++].f=f;}
static char *argv[8];static int argc;
int Cmd_Argc(void){return argc;}
char *Cmd_Argv(int i){return i<argc?argv[i]:"";}
static void run(const char *line){
    static char buffer[160];char *p;int i;
    strcpy(buffer,line);argc=0;printed[0]=0;
    for(p=strtok(buffer," ");p && argc<8;p=strtok(NULL," "))argv[argc++]=p;
    for(i=0;i<command_count;i++)if(!strcmp(commands[i].name,argv[0])){commands[i].f();return;}
    assert(!"command not registered");
}
extern void AW_ArenaInit(void);extern void AW_ArenaEnd(void);
extern int (*aw_arena_setup)(void (*done)(void));
static void (*setup_continue)(void);static int setup_calls;
static int setup(void (*done)(void)){setup_calls++;setup_continue=done;return 1;}
static void draw(void){drawn[0]=0;AW_ArenaDraw();}
static void spawn_scene(const char *map){
    edict_t *e;int i;
    strcpy(sv.name,map);sv.num_edicts=2;memset(edicts+2,0,sizeof(edict_t)*14);
    for(i=0;i<3;i++){
        e=ED_Alloc();e->v.classname=ED_NewString(i==2?"aw_corpse":"aw_npc")-pr_strings;e->v.modelindex=3+i;
    }
    sv.model_precache[1]="maps/x.bsp";sv.model_precache[2]=NULL;
    AW_ArenaEntities();
}
int main(void){
    edict_t *p=&edicts[1],*foe;int i;
    cls.signon=SIGNONS;pr_strings=strings;vid.width=320;vid.height=200;key_dest=key_game;
    sv.active=1;sv.edicts=edicts;svs.maxclients=1;svs.clients=&client;client.edict=p;
    fighter_model.numframes=31;gallery_model.numframes=1;
    p->v.mins[2]=-16.625f;p->v.maxs[2]=16.625f;
    aw_character.valid=1;aw_character.maximum[0]=80;aw_character.current[0]=10;aw_character.maximum[2]=300;aw_character.current[2]=5;
    AW_ArenaInit();assert(command_count==3 && aw_combat_result);
    assert(!AW_ArenaActive());

    /* list: the fighters, the gallery and any record */
    run("aw_arenapit list");assert(strstr(printed,"Mevil Molor (mevil molor)") && strstr(printed,"Ultis Salam") && strstr(printed,"3 humanoid NPCs"));

    /* the map: the pit when built, else the gallery floor, else here */
    have_pit=0;have_floor=0;run("aw_arenapit");assert(enters==1 && !strcmp(entered_map,"") && engaged.id[0]==0);
    have_floor=1;run("aw_arenapit");assert(enters==2 && !strcmp(entered_map,"charplane"));
    have_pit=1;run("aw_arenapit");assert(enters==3 && !strcmp(entered_map,"vai000"));
    run("aw_arenapit floor");assert(enters==4 && !strcmp(entered_map,"charplane"));
    run("aw_arenapit pit");assert(enters==5 && !strcmp(entered_map,"vai000"));

    /* opponents: by name, gallery number, record ID; refusals enter nothing */
    run("aw_arenapit Ultis Salam");assert(enters==6);
    run("aw_arenapit #5");assert(enters==7);
    run("aw_arenapit fargoth");assert(enters==8);                     /* record only: stand-in */
    run("aw_arenapit nobody at all");assert(enters==8 && strstr(printed,"No fighter"));
    run("aw_arenapit seed 4242");assert(seed_cvar==4242);
    run("aw_arenapit setup");assert(strstr(printed,"quick character"));

    /* back to the default fighter; the arena map spawns */
    run("aw_arenapit mevil molor");assert(enters==9);
    have_pit=1;spawn_scene("vai000");
    assert(frees==3 && sv.num_edicts==6);                             /* spectators gone, the opponent in */
    foe=&edicts[5];
    assert(!strcmp(pr_strings+foe->v.classname,"aw_npc") && !strcmp(sv.model_precache[(int)foe->v.modelindex],"arena/f1.mdl"));
    assert(box_sets==1 && box_low[0]==-7.32f && box_high[2]==33.25f && foe->v.solid==SOLID_BBOX);
    assert(!strcmp(pr_strings+source_id[5].string,"mevil molor"));
    realtime=10;AW_ArenaSpawn(p);
    assert(AW_ArenaActive());
    assert(p->v.origin[0]==0 && p->v.origin[1]==-150 && fabs(p->v.origin[2]-(-116+16.625f))<.01f);
    assert(foe->v.origin[1]==150 && fabs(foe->v.origin[2]-(-116))<.01f);
    assert(fabs(p->v.angles[1]-90)<.01f && fabs(foe->v.angles[1]-(-90-90))<.01f);   /* face each other */
    assert(p->v.health==80 && aw_character.current[0]==80 && aw_character.current[2]==300);

    /* title card, then the fight with the fighter's frames */
    loading=1;draw();realtime+=30;draw();loading=0;                    /* a slow load: the card still shows */
    draw();assert(strstr(drawn,"VIVEC ARENA") && strstr(drawn,"Mevil Molor, level 9") && !engages);
    realtime+=2.5;draw();assert(strstr(drawn,"FIGHT!") && !engages);
    realtime+=1;draw();assert(engages==1 && strstr(last_layout,"attack:10:8") && seed_at_engage==4242);
    draw();assert(strstr(drawn,"Vivec Arena: Mevil Molor"));
    assert(!AW_ArenaKey('n',1));                                       /* the fight: keys are the game's */
    assert(AW_ArenaKey(K_F1,1));draw();assert(strstr(drawn,"dbgmode arenapit list"));AW_ArenaKey(K_ESCAPE,1);

    /* the result: totals, keys */
    stats.started=20;stats.ended=31.5;stats.seed=4242;stats.player_hits=7;stats.player_misses=3;stats.dealt_health=94;
    aw_combat_result(1);draw();
    assert(strstr(drawn,"VICTORY") && strstr(drawn,"11.5 s") && strstr(drawn,"7 hits, 3 misses") && strstr(drawn,"Enter: rematch"));
    assert(AW_ArenaKey(K_ENTER,1) && reloads==1);
    assert(AW_ArenaKey('s',1) && reloads==2);                          /* same seed: replayed at the next engage */
    seed_cvar=0;spawn_scene("vai000");AW_ArenaSpawn(p);draw();realtime+=4;draw();draw();
    assert(engages==2 && seed_at_engage==4242 && seed_cvar==0);
    aw_combat_result(0);
    assert(p->v.movetype==MOVETYPE_NONE);                              /* the fallen stay down */
    draw();assert(strstr(drawn,"DEFEAT"));
    assert(AW_ArenaKey('n',1) && reloads==3);                          /* next: Ultis Salam */
    spawn_scene("vai000");foe=&edicts[5];assert(!strcmp(sv.model_precache[(int)foe->v.modelindex],"arena/f2.mdl"));
    AW_ArenaSpawn(p);draw();realtime+=4;draw();draw();assert(engages==3);aw_combat_result(1);
    assert(AW_ArenaKey('p',1) && toggles==1);
    assert(AW_ArenaKey(K_ESCAPE,1) && leaves==1);
    AW_ArenaEnd();assert(!AW_ArenaActive() && clears>=1);

    /* a gallery opponent (one pose: its own frames) */
    run("aw_arenapit caius cosades");
    spawn_scene("vai000");foe=&edicts[5];assert(!strncmp(sv.model_precache[(int)foe->v.modelindex],"gallery/",8));
    AW_ArenaSpawn(p);draw();realtime+=4;draw();draw();assert(!strcmp(last_layout,"(own frames)"));
    AW_ArenaEnd();
    /* the stand-in: a resident's model of the scene */
    run("aw_arenapit fargoth");
    spawn_scene("vai000");foe=&edicts[5];assert(foe->v.modelindex==3 && !strcmp(pr_strings+foe->v.netname,"Fargoth"));
    /* here: the captured spot, the opponent ahead */
    spawn_scene("balmora");AW_ArenaSpawn(p);foe=&edicts[5];
    assert(p->v.origin[0]==500 && foe->v.origin[0]>600);
    AW_ArenaEnd();

    /* the setup hook runs before the title card */
    aw_arena_setup=setup;run("aw_arenapit mevil molor");spawn_scene("vai000");AW_ArenaSpawn(p);
    realtime+=10;draw();assert(setup_calls==1 && strstr(drawn,"Set up your fighter") && engages==4-0);
    setup_continue();realtime+=.01;draw();assert(strstr(drawn,"VIVEC ARENA"));
    aw_arena_setup=NULL;AW_ArenaEnd();

    /* dbgmode and testarena */
    run("dbgmode");assert(strstr(printed,"dbgmode arenapit") && strstr(printed,"dbg combattest gallery"));
    run("dbgmode arenapit ultis salam");assert(!strcmp(queued,"aw_arenapit ultis salam\n"));
    run("dbgmode combattest");assert(!strcmp(queued,"aw_combattest gallery\n"));
    run("dbgmode nonsense");assert(strstr(printed,"Unknown debug mode"));
    {int before=enters;run("testarena");assert(enters==before+1);}
    for(i=0;i<3;i++)assert(strcmp(commands[i].name,""));
    printf("arena ok\n");
    return 0;
}
