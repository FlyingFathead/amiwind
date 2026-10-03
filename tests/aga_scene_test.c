/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
#include "aw_story.h"
#include "aw_character.h"
#include "aw_region.h"
aw_character_t aw_character;
void AW_HeapAuditReport(const char *scene){}
qboolean noclip_anglehack;
static float door_duration;static int audio_open,audio_close;
float AW_DoorSound(unsigned ref,int close){if(close)audio_close++;else audio_open++;return door_duration;}
int AW_CharacterHors(void){aw_character.valid=1;strcpy(aw_story.name,"Hors");return 1;}
keydest_t key_dest=key_game;double realtime;
char *pr_strings="\0aw_npc\0Fargoth\0worldspawn\0Darvame Hleran\0Selvil Sareloth";
static cvar_t *names_option;
static edict_t target;static int target_trace;
static int voice_aim,prompt,travel_trace;
static char drawn[2048];
static char hint[80];
static eval_t role,voice;
static ddef_t deadline_global;
static float globals[1];float *pr_globals=globals;
viddef_t vid;refdef_t r_refdef;int scr_copyeverything;
edict_t *EDICT_NUM(int n){return &target;}
ddef_t *ED_FindGlobal(char *name){return &deadline_global;}
int AW_UISpeakerAtRight(void){return 0;}
void AW_UIObjectName(const char *name,int style){}
int AW_IntroUse(void){return 0;}
int AW_OpeningHint(const char **name,const char **action){return 0;}
int AW_ConsoleCharHeight(void){return 8;}
int AW_ConsoleCharWidth(void){return 8;}
void AW_ConsoleCharacter(int x,int y,int c){int n=strlen(hint);assert(n<79);hint[n]=c;hint[n+1]=0;}
void AW_UIBox(int a,int b,int c,int d){}
void AW_UISmallBegin(void){}
void AW_UISmallEnd(void){}
void AW_UITextBox(int a,int b,int c,int d,const char *s,int e){strcat(drawn,s);strcat(drawn,"|");}
int AW_IntroPromptActive(void){return prompt;}
int AW_UIVoiceAimOnly(void){return voice_aim;}
int AW_CharacterActive(void){return 0;}
void AW_GallerySpawn(edict_t *p){AW_RegionWorldModel(sv.name,0);}
void AW_StreamTick(const char *path){}
float AW_StreamLookahead(void){return 1.5f;}
int AW_CellChangeMethod(void){return 1;}
void AW_StreamTransitionBegin(void){}
void AW_StreamTransitionReady(void){}
int AW_CharacterLoad(void){return 0;}
float AW_CharacterEyeHeight(void){return 0;}
int AW_ReaderActive(void){return 0;}
int AW_RegionLoadingFrozen(void){return 1;}
void AW_SetNextLoadingStyle(aw_loading_style_t style){}
static int requested_loading_delays;
void AW_SetNextLoadingDelay(void){requested_loading_delays++;}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void Cvar_SetValue(char *s,float v){if(names_option && !strcmp(s,names_option->name))names_option->value=v;}
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;
static char queued[64];static eval_t goal,torch;static int clear_buttons,events,occluded;
static void (*start_demo)(void),(*teleport)(void),(*scene)(void);static cvar_t *demo_option;
static int command_argc;static char *command_args[3];
static int opening_track=-1,ship_available=1,narrow_room;
static char notice[96];
void AW_UISubtitle(const char *name,const char *text,double duration){strcpy(notice,text);}
void Cvar_RegisterVariable(cvar_t *c){if(!strcmp(c->name,"aw_target_names"))names_option=c;else demo_option=c;c->value=atof(c->string);}
void Cmd_AddCommand(char *name,void(*fn)(void)){if(!strcmp(name,"aw_demo_start"))start_demo=fn;else if(!strcmp(name,"aw_teleport"))teleport=fn;else if(!strcmp(name,"aw_scene"))scene=fn;}
int Cmd_Argc(void){return command_argc;}
char *Cmd_Argv(int i){return i<command_argc?command_args[i]:"";}
int AW_MusicStartTrack(int id){opening_track=id;return 1;}
int COM_FOpenFile(char *name,FILE **f){
 const char *s="AWD3\nprison seyda 1 -5 35 25 5 45 35 0 0 77 90\tSeyda Neen\nprison evil;quit 2 -5 35 25 5 45 35 0 0 77 90\tInvalid\nprison seyda 3 nan 35 25 5 45 35 0 0 77 90\tInvalid\nseyda - 4 -5 35 25 5 45 35 0 0 0 90\tCensus and Excise Office\nseyda census 474482 -5 235 25 5 245 35 0 0 77 90\tOther doorway\nseyda census 113893 -5 235 25 5 245 35 12 34 77 90\tRegistration entrance\n";
 if(!strcmp(name,"seyda-regions.txt"))s="AWBR1 2 96 540 0 0 77 90 0 0 77 90\nsn000 -1024 -1024 1024 1024 -2048 -2048 2048 2048\nsn001 1024 -1024 2048 1024 128 -2048 2944 2048\n";
 if(!strcmp(name,"doors-balmora.txt") || !strcmp(name,"scene-doors-balmora.txt"))s="AWD3\nbalmora bmcaius 42 -5 35 25 5 45 35 22 44 77 90\tCaius Cosades House\n";
 if(!strcmp(name,"maps/prison.bsp") && !ship_available){*f=NULL;return -1;}
#ifdef BALMORA_AVAILABLE
 if(!strcmp(name,"balmora-regions.txt"))s="AWBR1 1 96 540 0 0 77 90 0 0 77 90\nbm000 -1024 -1024 1024 1024 -2048 -2048 2048 2048\n";
#endif
 *f=tmpfile();assert(*f);fputs(s,*f);rewind(*f);return strlen(s);
}
void Con_Printf(char *fmt,...){}
void Sys_Error(char *fmt,...){abort();}
void Cbuf_AddText(char *s){strcpy(queued,s);}
void Cbuf_InsertText(char *s){strcpy(queued,s);}
void IN_AWClearButtons(void){clear_buttons++;}
void AW_MusicSceneEvent(const char *s){events++;}
double Sys_FloatTime(void){return 1;}
int Hunk_LowMark(void){return 1000;}
int Hunk_HighMark(void){return 0;}
eval_t *GetEdictFieldValue(edict_t *p,char *name){
 if(!strcmp(name,"aw_torch"))return &torch;
 if(!strcmp(name,"aw_intro_role"))return &role;
 if(!strcmp(name,"aw_voice"))return &voice;
 return &goal;
}
qboolean AW_PlacePlayer(edict_t *p,vec3_t v){return false;}
void SV_LinkEdict(edict_t *p,qboolean touch){}
trace_t SV_Move(vec3_t a,vec3_t mins,vec3_t maxs,vec3_t b,int type,edict_t *p){
 trace_t t;memset(&t,0,sizeof(t));t.fraction=1;VectorCopy(b,t.endpos);
 if(travel_trace){t.fraction=.5;t.ent=occluded?NULL:&target;return t;}
 if(target_trace){assert(type==MOVE_NORMAL);assert(fabs((b[0]-a[0])*(b[0]-a[0])+(b[1]-a[1])*(b[1]-a[1])+(b[2]-a[2])*(b[2]-a[2])-72*72)<.1);t.fraction=.5;t.ent=occluded?NULL:&target;return t;}
 if(type==MOVE_NOMONSTERS){if(occluded)t.fraction=.3f;return t;}
 if(narrow_room){
  if(a[2]>88 || a[2]<66){t.startsolid=t.allsolid=true;t.fraction=0;return t;}
  if(b[2]<66){t.fraction=(a[2]-66)/(a[2]-b[2]);t.endpos[2]=66;t.plane.normal[2]=1;}
  return t;
 }
 if(a[2]>80){t.startsolid=t.allsolid=true;t.fraction=0;return t;}
 if(b[2]<50 && a[2]>=50){t.fraction=(a[2]-50)/(a[2]-b[2]);t.endpos[2]=50;t.plane.normal[2]=1;}
 return t;
}
int main(void){
 edict_t p;client_t client;vec3_t arrival={0,0,77};memset(&p,0,sizeof(p));memset(&client,0,sizeof(client));
 sv.active=true;svs.maxclients=1;svs.clients=&client;client.edict=&p;strcpy(sv.name,"prison");
 cls.state=ca_connected;p.v.movetype=MOVETYPE_WALK;p.v.health=100;p.v.view_ofs[2]=30;goal._float=1;cl.viewangles[1]=90;
 torch._float=1;assert(AW_Interior());
 cl.viewangles[1]=0;assert(!AW_SceneUse());cl.viewangles[1]=90;
 p.v.origin[1]=-100;assert(!AW_SceneUse());p.v.origin[1]=0;
 occluded=1;assert(!AW_SceneUse());occluded=0;
 door_duration=.4f;realtime=10;
 assert(AW_SceneUse());assert(!queued[0] && !clear_buttons && audio_open==1);
 assert(AW_SceneUse());assert(audio_open==1); /* held use during opening */
 realtime=10.39;AW_SceneTick();assert(!queued[0]);
 realtime=10.41;AW_SceneTick();assert(!strcmp(queued,"map seyda\n") && clear_buttons==1);
 door_duration=0;
 assert(AW_SceneUse());assert(clear_buttons==1); /* held use cannot queue twice */
 strcpy(sv.name,"seyda");p.v.health=0;goal._float=0;torch._float=0;AW_SceneSpawn(&p);
 assert(torch._float==1); /* Equipped torch follows the raised hands through a door. */
 cls.signon=SIGNONS;AW_SceneTick();assert(audio_close==1);AW_SceneTick();assert(audio_close==1);
 assert(p.v.health==100 && goal._float==1 && events==2);assert(p.v.origin[2]>50 && p.v.origin[2]<51);
 assert(p.v.angles[1]==90 && p.v.fixangle);assert(!AW_Interior());
 assert(AW_InteriorPlace(&p,arrival));assert(p.v.origin[2]>50 && p.v.origin[2]<51);
 p.v.origin[0]=p.v.origin[1]=p.v.origin[2]=0;queued[0]=0;
 assert(AW_SceneUse());assert(!strcmp(notice,"Interior not found."));
 assert(!queued[0] && clear_buttons==1 && p.v.health==100); /* no transition or state loss */
 occluded=1;assert(!AW_SceneUse());occluded=0;
 p.v.movetype=MOVETYPE_NOCLIP;assert(!AW_SceneUse());
 AW_SceneInit();assert(start_demo && demo_option && demo_option->value==1);
 assert(!strcmp(demo_option->name,"early_game_demo_start_1"));
 start_demo();assert(!strcmp(queued,"map seyda\n"));assert(opening_track==4);
 demo_option->value=0;opening_track=-1;start_demo();
 assert(!strcmp(queued,"map prison\n"));assert(opening_track==-1);
 ship_available=0;start_demo();assert(!strcmp(queued,"map seyda\n"));
 target_trace=1;target.v.classname=1;target.v.netname=8;target.v.modelindex=1;
 p.v.movetype=MOVETYPE_WALK;voice.string=8;
 assert(names_option->value==1);names_option->value=0;assert(!AW_SceneTargetName());names_option->value=1;
 names_option->value=0;voice_aim=1;assert(!AW_SceneTargetName());
 names_option->value=1;voice_aim=0;
 aw_story.stage=AW_STAGE_SHIP;assert(!AW_SceneTargetName());aw_story.stage=AW_STAGE_REVIEW;assert(!AW_SceneTargetName());
 voice_aim=1;assert(!AW_SceneTargetName());
 prompt=1;assert(!AW_SceneTargetName());prompt=0;voice_aim=0;
 aw_story.stage=AW_STAGE_PAPERS;assert(!strcmp(AW_SceneTargetName(),"Fargoth"));
 occluded=1;assert(!AW_SceneTargetName());occluded=0;
 target.free=1;assert(!AW_SceneTargetName());target.free=0;
 target.v.classname=16;assert(!AW_SceneTargetName());target.v.classname=1;
 key_dest=key_menu;assert(!AW_SceneTargetName());key_dest=key_game;
 names_option->value=0;assert(!AW_SceneTargetName());target_trace=0;
 narrow_room=1;arrival[2]=84;
 assert(AW_InteriorPlace(&p,arrival));assert(p.v.origin[2]>66 && p.v.origin[2]<67);
 travel_trace=1;narrow_room=0;target.v.netname=27;
 p.v.movetype=MOVETYPE_WALK;key_dest=key_game;aw_story.stage=AW_STAGE_RELEASED;
 AW_StateSet(&aw_state,AW_GLOBAL,"CharGenState",-1);
 AW_StateSet(&aw_state,AW_ITEM,"gold_001",87);
 vid.width=320;vid.height=200;r_refdef.vrect.height=152;
 globals[0]=100;sv.time=0;hint[0]=0;AW_SceneDraw();
 assert(!strcmp(hint,"(E: Talk)")); /* Service survives greeting cooldown. */
 hint[0]=0;occluded=1;AW_SceneDraw();assert(!hint[0]);occluded=0;
 /* A nearby facing actor without a direct hit must not produce a prompt.
  * The name and Talk action become available together on a clear hit. */
 travel_trace=0;target.v.netname=8;voice.string=8;role._float=0;
 target.v.origin[0]=40;target.v.origin[1]=0;p.v.origin[0]=p.v.origin[1]=p.v.origin[2]=0;
 cl.viewangles[1]=0;sv.num_edicts=2;globals[0]=0;
 hint[0]=0;AW_SceneDraw();assert(!hint[0] && !AW_SceneTargetName());
 target_trace=1;names_option->value=1;
 hint[0]=0;AW_SceneDraw();assert(!strcmp(hint,"(E: Talk)") && !strcmp(AW_SceneTargetName(),"Fargoth"));
 role._float=1;hint[0]=0;AW_SceneDraw();assert(!hint[0]);role._float=0;
 globals[0]=100;hint[0]=0;AW_SceneDraw();assert(!strcmp(hint,"(E: Talk)") && !strcmp(AW_SceneTargetName(),"Fargoth"));globals[0]=0;
 occluded=1;hint[0]=0;AW_SceneDraw();assert(!hint[0]);occluded=0;
 target_trace=0;travel_trace=1;target.v.netname=27;
 occluded=1;assert(!AW_SceneUse());occluded=0;
 assert(AW_SceneUse() && key_dest==key_menu);
 drawn[0]=0;assert(AW_TravelDraw());assert(strstr(drawn,"Balmora") && strstr(drawn,"Gnisis") && strstr(drawn,"Suran") && strstr(drawn,"Vivec") && strstr(drawn,"Cancel"));
#ifdef BALMORA_AVAILABLE
 assert(AW_TravelKey(K_ENTER));assert(!strcmp(queued,"map balmora\n"));
 assert(key_dest==key_game && AW_StateGet(&aw_state,AW_ITEM,"gold_001")==87);
 strcpy(notice,"Old room greeting");
 strcpy(sv.name,"balmora");AW_SceneSpawn(&p);assert(!AW_Interior());assert(!notice[0]);
 target.v.netname=27+strlen(pr_strings+27)+1;
 assert(AW_SceneUse());drawn[0]=0;assert(AW_TravelDraw());assert(strstr(drawn,"Seyda Neen"));
 assert(AW_TravelKey(K_ENTER));assert(!strcmp(queued,"map seyda\n"));
 assert(AW_StateGet(&aw_state,AW_ITEM,"gold_001")==87);
#else
 {int i;for(i=0;i<4;i++){
   queued[0]=0;assert(AW_TravelKey(K_ENTER));drawn[0]=0;assert(AW_TravelDraw());
   assert(strstr(drawn,"Destination not found."));assert(!queued[0]);
   assert(AW_StateGet(&aw_state,AW_ITEM,"gold_001")==87);AW_TravelKey(K_DOWNARROW);
 }}
 assert(AW_TravelKey(K_ENTER) && key_dest==key_game);
 assert(!AW_TravelDraw());assert(AW_SceneUse());AW_TravelKey(K_ESCAPE);assert(key_dest==key_game);
#endif
 /* Teleport aliases share the checked scene path; no New Game/state reset. */
 travel_trace=target_trace=occluded=0;
 assert(teleport && scene);strcpy(sv.name,"seyda");AW_SceneSpawn(&p);ship_available=1;
 command_args[0]="aw_teleport";command_argc=1;queued[0]=0;teleport();
 assert(!strcmp(queued,"aw_scene_menu\n"));
 sv.active=false;queued[0]=0;teleport();assert(!queued[0]);sv.active=true;
 command_argc=2;command_args[1]="SeYdAnEeN";p.v.health=73;goal._float=1;teleport();
 assert(!strcmp(queued,"map seyda\n"));p.v.health=0;AW_SceneSpawn(&p);assert(p.v.health==73);
 assert(AW_StateGet(&aw_state,AW_ITEM,"gold_001")==87);
 command_args[1]="prisonship";teleport();assert(!strcmp(queued,"map prison\n"));
 strcpy(sv.name,"prison");AW_SceneSpawn(&p);
 queued[0]=0;ship_available=0;teleport();assert(!queued[0]);ship_available=1;
 command_args[1]="balmora;quit";teleport();assert(!queued[0]);
 command_args[1]="missing";teleport();assert(!queued[0]);
 command_argc=3;command_args[1]="seydaneen";command_args[2]="extra";teleport();assert(!queued[0]);
 command_argc=2;command_args[1]="census";strcpy(sv.name,"balmora");
 scene();assert(!strcmp(queued,"map census\n")); /* Destination catalogue, not Balmora's empty links. */
 strcpy(sv.name,"census");AW_SceneSpawn(&p);assert(p.v.origin[0]==12 && p.v.origin[1]==34);
 command_args[1]="bmcaius";scene();assert(!strcmp(queued,"map bmcaius\n"));
 strcpy(sv.name,"bmcaius");AW_SceneSpawn(&p);assert(p.v.origin[0]==22 && p.v.origin[1]==44);
#ifdef BALMORA_AVAILABLE
 command_args[1]="BaLmOrA";teleport();assert(!strcmp(queued,"map balmora\n"));
 strcpy(sv.name,"balmora");AW_SceneSpawn(&p);
#endif
 assert(requested_loading_delays==0); /* Explicit travel stays immediate. */
 /* An automatic sub-cell transition preserves held input and player goals.
  * Ordinary doors/teleports above must still clear input deliberately. */
 strcpy(sv.name,"seyda");p.v.movetype=MOVETYPE_NOCLIP;p.v.health=73;
 goal._float=1;torch._float=1;key_dest=key_game;cls.signon=SIGNONS;
 aw_character.current[1]=33;aw_character.current[2]=44;aw_character.level=7;
 aw_story.stage=AW_STAGE_RELEASED;p.v.origin[0]=0;p.v.origin[1]=300;
 assert(AW_RegionSelect("seyda",p.v.origin,0));AW_RegionWorldModel("seyda",0);
 p.v.origin[0]=1200;p.v.velocity[0]=42;p.v.v_angle[0]=12;p.v.v_angle[1]=34;
 queued[0]=0;
 {int before=clear_buttons;AW_SceneTick();
  assert(!strcmp(queued,"map seyda\n") && clear_buttons==before);
  assert(requested_loading_delays==1);
  p.v.health=100;goal._float=0;torch._float=0;p.v.movetype=MOVETYPE_WALK;
  AW_SceneSpawn(&p);
  assert(p.v.health==73 && goal._float==1 && torch._float==1);
  assert(aw_character.current[1]==33 && aw_character.current[2]==44 && aw_character.level==7);
  assert(AW_StateGet(&aw_state,AW_ITEM,"gold_001")==87);
  assert(p.v.movetype==MOVETYPE_NOCLIP && p.v.velocity[0]==42);
  assert(p.v.origin[0]==1200 && p.v.angles[0]==12 && p.v.angles[1]==34);
 }
 return 0;
}

void AW_IntroSpawn(void){}

void AW_OpeningSpawn(void){}
void AW_SaveCapture(void){}
void AW_SaveSpawn(void){}
void AW_SaveReset(void){}

qboolean AW_MapPlace(edict_t *p,const float *xy){return false;}
