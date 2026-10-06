/* SPDX-License-Identifier: GPL-2.0-or-later
 * Real intro/opening scene lifecycle; synthetic local map, assets and UI. */
#include "aw_intro.c"
#include <assert.h>

server_t sv;server_static_t svs;client_static_t cls;client_state_t cl;
aw_character_t aw_character;
cmd_source_t cmd_source=src_command;
keydest_t key_dest=key_console;double host_frametime=.02;
char *pr_strings="";
static client_t client;static edict_t entities[3];static eval_t role;
static int argc=2,maps,save_resets,cancels,opened,done,character;
static int map_present=1,catalogue=1,preview=1,guard_present=1,placement=1,barriers=1;
static int movie,reader,gallery,map_failure;
static char *args[]={"aw_tpscene","headselection","extra"};
static char last_map[48];
int Cmd_Argc(void){return argc;}char *Cmd_Argv(int n){return n<argc?args[n]:"";}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void Con_Printf(char *s,...){}
void IN_AWClearButtons(void){}
void AW_SaveReset(void){save_resets++;}
void AW_SceneCancelTransition(void){cancels++;}
void AW_EndLoadingStyle(void){}void AW_SetNextLoadingStyle(aw_loading_style_t n){}void AW_BeginLoadingStyle(void){}
int AW_RegionSelect(const char *name,const float *point,int intro){assert(!strcmp(name,"seyda") && intro==1);return 1;}
int AW_CharacterLoad(void){return catalogue;}
void AW_CharacterReset(void){character=done=0;}
int AW_CharacterActive(void){return character;}
int AW_CharacterOpen(int kind){assert(kind==1);opened++;character=preview;return preview;}
int AW_CharacterDone(void){int n=done;done=0;return n;}
int AW_MovieActive(void){return movie;}int AW_ReaderActive(void){return reader;}
int AW_GalleryModal(void){return gallery;}int AW_ReaderResult(void){return 0;}
int AW_ReaderOpen(const char *s,int n){return 0;}
int COM_FOpenFile(char *path,FILE **f){
    assert(!strcmp(path,"maps/seyda.bsp"));*f=map_present?tmpfile():NULL;
    return *f?124:-1;
}
edict_t *EDICT_NUM(int n){assert(n>=0 && n<3);return &entities[n];}
int NUM_FOR_EDICT(edict_t *e){return (int)(e-entities);}
eval_t *GetEdictFieldValue(edict_t *e,char *name){
    role._float=0;if(!strcmp(name,"aw_intro_role") && e==&entities[2] && guard_present)role._float=5;
    return &role;
}
int AW_BarrierLoad(void){return barriers;}
int AW_NavLoad(const char *map){return 1;}
int AW_NavStart(edict_t *e,vec3_t p){return 1;}
int AW_NavStep(double dt,int follow){return 0;}
int AW_InteriorPlace(edict_t *e,vec3_t at){
    if(placement)VectorCopy(at,e->v.origin);return placement;
}
void SV_LinkEdict(edict_t *e,qboolean triggers){}
int SV_ModelIndex(char *name){return 0;}
double AW_SpeechRemaining(void){return 0;}
sfx_t *S_PrecacheSound(char *name){assert(0);return NULL;}
void S_StartSound(int e,int channel,sfx_t *s,vec3_t p,float volume,float attenuation){assert(0);}
void AW_UIVoiceSubtitle(const char *who,const char *text,double duration){assert(0);}
void AW_UISubtitle(const char *who,const char *text,double duration){}
void Cmd_ExecuteString(char *text,cmd_source_t source){
    assert(source==src_command);maps++;strcpy(last_map,text);
    assert(!strcmp(text,"map seyda"));assert(!character);
    sv.active=!map_failure;cls.signon=0;
    if(map_failure)return;
    strcpy(sv.name,"seyda");sv.num_edicts=3;
    memset(entities,0,sizeof(entities));entities[1].v.mins[2]=-24;
    entities[2].v.origin[0]=100;entities[2].v.origin[2]=8;
    AW_IntroSpawn();AW_OpeningSpawn();
}
static void ready(void){cls.state=ca_connected;cls.signon=SIGNONS;AW_IntroTick();}
static void request(void){key_dest=key_console;debug_scene_command();}
static void untouched(void){int before=maps,reset=save_resets;request();assert(maps==before && save_resets==reset);}
int main(void){
    svs.maxclients=1;svs.clients=&client;client.edict=&entities[1];
    argc=1;untouched();argc=2;args[1]="list";untouched();
    args[1]="missing";untouched();args[1]="headselection;quit";untouched();
    args[1]="headselection";argc=3;untouched();argc=2;
    cmd_source=src_client;untouched();cmd_source=src_command;
    movie=1;untouched();movie=0;reader=1;untouched();reader=0;gallery=1;untouched();gallery=0;
    svs.maxclients=2;untouched();svs.maxclients=1;
    cls.state=ca_connected;sv.active=0;untouched();cls.state=ca_disconnected;
    map_present=0;untouched();map_present=1;catalogue=0;untouched();catalogue=1;
    request();assert(maps==1 && save_resets==1 && cancels==1 && debug_scene_ready);
    assert(!active && !pending && !prompt && !opened && key_dest==key_game);
    assert(!strcmp(player_name,"Scene Tester") && aw_story.stage==AW_STAGE_DOCK && aw_story.dock==30);
    assert(entities[1].v.origin[0]==132 && entities[1].v.origin[2]==32);
    AW_IntroTick();assert(!opened); /* Wait for client sign-on, not a frame count. */
    ready();assert(opened==1 && character && !debug_scene && aw_story.stage==AW_STAGE_RACE && aw_story.dock==40);
    AW_IntroTick();assert(opened==1); /* No duplicate open while modal owns input. */
    character=0;done=1;AW_IntroTick();assert(aw_story.stage==AW_STAGE_OFFICE);
    assert(aw_story.dock==40 && aw_story.dock_timer>0 && !aw_story.ship_disabled);
    /* Case-insensitive repeat performs a fresh scene reset, not a second movie. */
    args[1]="HeAdSeLeCtIoN";request();ready();assert(opened==2 && aw_story.stage==AW_STAGE_RACE);
    preview=0;request();ready();assert(failed && !character && !debug_scene && aw_story.dock==-1);preview=1;
    guard_present=0;request();assert(!debug_scene && failed && opened==3);guard_present=1;
    placement=0;request();assert(!debug_scene && failed);placement=1;
    barriers=0;request();assert(!debug_scene && failed);barriers=1;
    map_failure=1;request();assert(!debug_scene && !debug_scene_ready && aw_story.dock==-1);map_failure=0;
    /* A superseding load cancels the pending scene, including actor pointers. */
    request();strcpy(sv.name,"prison");AW_IntroSpawn();assert(!debug_scene);
    return 0;
}
