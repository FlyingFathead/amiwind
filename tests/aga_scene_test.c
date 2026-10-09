/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
#include "aw_story.h"
#include "aw_character.h"
#include "aw_region.h"
#include "aw_harvest_runtime.h"
aw_character_t aw_character;
void AW_HeapAuditReport(const char *scene){}
qboolean noclip_anglehack;
kbutton_t in_mlook;
static float door_duration;static int audio_open,audio_close;
float AW_DoorSound(unsigned ref,int close){if(close)audio_close++;else audio_open++;return door_duration;}
int AW_CharacterHors(void){aw_character.valid=1;strcpy(aw_story.name,"Hors");return 1;}
keydest_t key_dest=key_game;double realtime;
#define ORIGINAL_STRINGS "\0aw_npc\0Fargoth\0worldspawn\0Darvame Hleran\0Selvil Sareloth\0progs/v_nord.mdl"
char *pr_strings=ORIGINAL_STRINGS "\0func_wall\0*1";
static int harvest_fixture,section_doors;
static eval_t harvest_reference;
static model_t harvest_world,harvest_model;
static char object_name[80];
static cvar_t *names_option;
static edict_t target;static int target_trace;
static int voice_aim,prompt,travel_trace;
static char drawn[2048];
static char hint[80];
static eval_t role,voice;
static ddef_t deadline_global;
static float globals[1];float *pr_globals=globals;
viddef_t vid;refdef_t r_refdef;int scr_copyeverything;
/* This fixture's harvest representation is inline brush only. */
qboolean Mod_CanFindName(const char *name){(void)name;assert(0);return false;}
model_t *Mod_ForName(char *name,qboolean crash){(void)name;(void)crash;assert(0);return NULL;}
edict_t *EDICT_NUM(int n){return &target;}
ddef_t *ED_FindGlobal(char *name){return &deadline_global;}
int host_framecount; /* npc_target caches its result per frame: each call below is a new frame */
#define AW_SceneTargetName() (host_framecount++,AW_SceneTargetName())
#define AW_SceneDraw() (host_framecount++,AW_SceneDraw())
#define AW_SceneUse() (host_framecount++,AW_SceneUse())
int AW_UISpeakerAtRight(void){return 0;}
void AW_UIObjectName(const char *name,int style){if(name)strcpy(object_name,name);}
void S_LocalSound(char *name){}
int AW_IntroUse(void){return 0;}
int AW_OpeningHint(const char **name,const char **action){return 0;}
int AW_ConsoleCharHeight(void){return 8;}
int AW_ConsoleCharWidth(void){return 8;}
void AW_ConsoleCharacter(int x,int y,int c){int n=strlen(hint);assert(n<79);hint[n]=c;hint[n+1]=0;}
int AW_UIMode(void){return 2;}
int AW_UIColor(int r,int g,int b){return (r+g+b)%256;}
void AW_UIFill(int x,int y,int w,int h,int c){assert(x>=0 && y>=0 && x+w<=320 && y+h<=200);}
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
server_t sv;server_static_t svs;
/* Use the real client reset, final signon and pitch-drift routines. */
entity_t cl_temp_entities[MAX_TEMP_ENTITIES];beam_t cl_beams[MAX_BEAMS];
double host_frametime=.02;
cvar_t cl_forwardspeed={"cl_forwardspeed","200",false,false,200};
extern cvar_t v_centermove,v_centerspeed;
extern void V_DriftPitch(void);
static int signon_finished;
static int scene_voice_begins,scene_voice_ends,scene_voice_cancels,scene_voice_armed;
void S_BeginSceneVoice(void){scene_voice_begins++;scene_voice_armed=1;}
void S_EndSceneVoice(void){assert(scene_voice_armed);scene_voice_ends++;scene_voice_armed=0;}
void S_CancelSceneVoice(void){scene_voice_cancels++;scene_voice_armed=0;}
void Host_ClearMemory(void){}
void R_ClearEfrags(qboolean preserve){}
void SZ_Clear(sizebuf_t *buf){buf->cursize=0;}
void MSG_WriteByte(sizebuf_t *buf,int value){}
void MSG_WriteString(sizebuf_t *buf,char *value){}
void Cache_Report(void){}
void SCR_EndLoadingPlaque(void){signon_finished++;}
void Con_DPrintf(char *fmt,...){}
char *va(char *fmt,...){return "";}
/* Legacy spawn angle packets arrive before final signon. Model their actual
 * integer/byte round trip, including signed yaw, then call real client signon. */
static void finish_signon(edict_t *p){
 int i;
 for(i=0;i<3;i++)cl.viewangles[i]=(signed char)(((int)p->v.angles[i]*256/360)&255)*(360.0f/256);
 cls.signon=3;CL_SignonReply();
 cls.signon=SIGNONS;CL_SignonReply();
}
static char queued[64];static eval_t goal,torch,hand_state,hand_started,attack_latched;static int clear_buttons,events,occluded;
static void (*start_demo)(void),(*teleport)(void),(*scene)(void),(*shroompicker)(void);static cvar_t *demo_option;
static int command_argc;static char *command_args[4];
static int opening_track=-1,ship_available=1,narrow_room;
static int world_map_unavailable,map_place_calls,map_place_blocked;static vec3_t last_map_arrival;
static int picker_file_mode,picker_file_reads,picker_list_rows;
static char notice[96];
/* A partial-area build's notice file (aw_miniwind.c) and its missing rooms. */
#include "aw_miniwind.h"
static int miniwind_fixture,miniwind_rooms_missing,miniwind_pure_exterior;static void (*quick)(void);
extern const char *(*aw_chim_town_map)(const char *town);
static const char *balmora_frame(const char *town){return strcmp(town,"balmora")?NULL:"maps/balmora-chim.bsp";}
void AW_UISubtitle(const char *name,const char *text,double duration){strcpy(notice,text);}
void AW_UIPickupNotice(const char *text,double duration){AW_UISubtitle("",text,duration);}
void Cvar_RegisterVariable(cvar_t *c){if(!strcmp(c->name,"aw_target_names"))names_option=c;else demo_option=c;c->value=atof(c->string);}
void Cmd_AddCommand(char *name,void(*fn)(void)){if(!strcmp(name,"aw_demo_start"))start_demo=fn;else if(!strcmp(name,"aw_teleport"))teleport=fn;else if(!strcmp(name,"aw_scene"))scene=fn;else if(!strcmp(name,"aw_shroompicker"))shroompicker=fn;else if(!strcmp(name,"aw_quick_start"))quick=fn;}
int Cmd_Argc(void){return command_argc;}
char *Cmd_Argv(int i){return i<command_argc?command_args[i]:"";}
int AW_MusicStartTrack(int id){opening_track=id;return 1;}
static int excluded_interiors;
int COM_FOpenFile(char *name,FILE **f){
 if(!strcmp(name,"miniwind.txt")){
  const char *s="AWMW1\ntown balmora\ntitle ATTENTION: THIS IS A MINIWIND PLAYTEST BUILD\n"
   "features FEATURES ONLY: Balmora exterior (CHIM)\n";
  if(!miniwind_fixture){*f=NULL;return -1;}
  *f=tmpfile();assert(*f);fputs(s,*f);rewind(*f);return strlen(s);
 }
 if(miniwind_rooms_missing && !strcmp(name,"maps/bmcaius.bsp")){*f=NULL;return -1;}
 /* The exterior scope on a pure CHIM image: no Balmora legacy maps, no rooms; only the frame map. */
 if(miniwind_pure_exterior && (!strncmp(name,"maps/bm",7) || !strcmp(name,"maps/balmora.bsp"))){*f=NULL;return -1;}
 if(!strcmp(name,"shroompicker.txt")){
  int i,size;long start;picker_file_reads++;
  if(picker_file_mode==1){*f=NULL;return -1;}
  *f=tmpfile();assert(*f);
  if(picker_file_mode==6)fputs("PAK prefix and another member\n",*f);
  start=ftell(*f);fputs("AWSP1\n",*f);
  for(i=1;i<=10;i++)fprintf(*f,"%d %d %d %s %s %d %.2f %.2f Test mushroom %d\n",
   picker_file_mode==2 && i==2?1:i,i==1,i==1?0:42,
   picker_file_mode==5?"vf0000":"seyda",picker_file_mode==3?"nan":"-10920",
   i==2?-75080:-75120,i==2?17.25:4.,i==2?60.5:64.,i);
  size=ftell(*f)-start;
  if(picker_file_mode==6)fputs("Following PAK member must not be read\n1 1 0 seyda 0 0 0 0 invalid duplicate\n",*f);
  if(picker_file_mode==7)size-=4; /* Member ends within label despite trailing file bytes. */
  if(picker_file_mode==8)size+=40; /* Advertised member extends beyond actual EOF. */
  assert(!fseek(*f,start,SEEK_SET));return picker_file_mode==4?5000:size;
 }
 if(section_doors && (!strcmp(name,"doors-vf0000.txt") || !strcmp(name,"doors-mi5b8154939f7aa.txt"))){
  const char *s=!strcmp(name,"doors-vf0000.txt")?
   "AWD3\nvf0000 mi5b8154939f7aa 222000 -5 35 25 5 45 35 -380 758 77 90\tMine entrance\n":
   "AWD3\nmi5b8154939f7aa vf0000 221950 -5 35 25 5 45 35 12 34 77 180\tOriginal exterior exit\n";
  *f=tmpfile();assert(*f);fputs(s,*f);rewind(*f);return strlen(s);
 }
 if(!strcmp(name,"interior-sections.txt")){
  const char *s="AWIS1 2 1\nmi5b8154939f7aa -600 600 -600 320 1600 300\n"
   "mi5b8154939f7ab -300 600 -600 1000 1600 300\n"
   "mi5b8154939f7aa mi5b8154939f7ab 0 -128 16 -192 960 -256 -64 1216 -128\n";
  *f=tmpfile();assert(*f);fputs(s,*f);rewind(*f);return strlen(s);
 }
 if(!strcmp(name,"harvest-vf0000.txt") && harvest_fixture){
  const char *s="AWH2 1 1 1\n0 0 0 0 0 original_item\tOriginal item name\n0 0 2\n"
    "aw:h:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 42 *1 11 0 1 40 0 30 0 0 0 Luminous Russula\n";
  *f=tmpfile();assert(*f);fputs(s,*f);rewind(*f);return strlen(s);
 }
 if(!strcmp(name,"world/regions.awr")) {
  unsigned count=1;float town0[7]={-2816,-17920,0,-1024,-1024,1024,1024};
  float town1[7]={-5120,-3072,0,-1024,-1024,1024,1024};
  float region[11]={-512,-17920,0,-256,-1024,1024,1024,-1920,-1920,1920,1920};
  *f=tmpfile();assert(*f);fwrite("AWR2",1,4,*f);fwrite(&count,4,1,*f);
  fwrite(town0,sizeof(town0),1,*f);fwrite(town1,sizeof(town1),1,*f);
  fwrite("vf0000\0\0",1,8,*f);fwrite(region,sizeof(region),1,*f);rewind(*f);return 116;
 }
 if(!strcmp(name,"maps/seyda.bsp") && world_map_unavailable){*f=NULL;return -1;}
 if(!strcmp(name,"excluded-content.txt")){
  /* A quick test build without interiors (tools/build_exclusions.py marker). */
  const char *s="AWX1\ninteriors the interiors\n";
  if(!excluded_interiors){*f=NULL;return -1;}
  *f=tmpfile();assert(*f);fputs(s,*f);rewind(*f);return strlen(s);
 }

 const char *s="AWD3\nprison seyda 1 -5 35 25 5 45 35 0 0 77 90\tSeyda Neen\nprison evil;quit 2 -5 35 25 5 45 35 0 0 77 90\tInvalid\nprison seyda 3 nan 35 25 5 45 35 0 0 77 90\tInvalid\nseyda - 4 -5 35 25 5 45 35 0 0 0 90\tCensus and Excise Office\nseyda census 474482 -5 235 25 5 245 35 0 0 77 90\tOther doorway\nseyda census 113893 -5 235 25 5 245 35 12 34 77 90\tRegistration entrance\n";
 if(!strcmp(name,"seyda-regions.txt"))s="AWBR1 2 96 540 0 0 77 90 0 0 77 90\nsn000 -1024 -1024 1024 1024 -2048 -2048 2048 2048\nsn001 1024 -1024 2048 1024 128 -2048 2944 2048\n";
 if(!strcmp(name,"doors-balmora.txt") || !strcmp(name,"scene-doors-balmora.txt"))s="AWD3\nbalmora bmcaius 42 -5 35 25 5 45 35 22 44 77 90\tCaius Cosades House\n";
 if(!strcmp(name,"maps/prison.bsp") && !ship_available){*f=NULL;return -1;}
#ifdef BALMORA_AVAILABLE
 if(!strcmp(name,"balmora-regions.txt"))s="AWBR1 1 96 540 0 0 77 90 0 0 77 90\nbm000 -1024 -1024 1024 1024 -2048 -2048 2048 2048\n";
#endif
 *f=tmpfile();assert(*f);fputs(s,*f);rewind(*f);return strlen(s);
}
void Con_Printf(char *fmt,...){if(!strcmp(fmt,"%ld: %s [%s]\n"))picker_list_rows++;}
void Sys_Error(char *fmt,...){abort();}
void Cbuf_AddText(char *s){strcpy(queued,s);}
void Cbuf_InsertText(char *s){strcpy(queued,s);}
void IN_AWClearButtons(void){clear_buttons++;}
void AW_MusicSceneEvent(const char *s){events++;}
double Sys_FloatTime(void){return 1;}
int Hunk_LowMark(void){return 1000;}
int Hunk_HighMark(void){return 0;}
static double torch_offset;
static int torch_restores;
double AW_TorchAnimationTime(void){return cl.time+torch_offset;}
void AW_TorchRestoreAnimation(double time){torch_offset=time-cl.time;torch_restores++;}
void AW_TorchResetAnimation(void){torch_offset=0;}
char *ED_NewString(char *text){
 const char *hands="progs/v_nord.mdl";char *at=pr_strings+1;
 assert(!strcmp(text,hands));
 while(strcmp(at,hands))at+=strlen(at)+1;
 return at;
}
eval_t *GetEdictFieldValue(edict_t *p,char *name){
 if(!strcmp(name,"aw_ref") && harvest_fixture){harvest_reference._float=42;return &harvest_reference;}
 if(!strcmp(name,"aw_hand_goal"))return &goal;
 if(!strcmp(name,"aw_hand_state"))return &hand_state;
 if(!strcmp(name,"aw_hand_started"))return &hand_started;
 if(!strcmp(name,"aw_attack_latched"))return &attack_latched;
 if(!strcmp(name,"aw_torch"))return &torch;
 if(!strcmp(name,"aw_intro_role"))return &role;
 if(!strcmp(name,"aw_voice"))return &voice;
 return NULL;
}
qboolean AW_PlacePlayer(edict_t *p,vec3_t v){return false;}
void SV_LinkEdict(edict_t *p,qboolean touch){}
static int all_solid,water_feet,calls_mark;
int SV_PointContents(vec3_t p){return water_feet?CONTENTS_WATER:CONTENTS_EMPTY;}
trace_t SV_Move(vec3_t a,vec3_t mins,vec3_t maxs,vec3_t b,int type,edict_t *p){
 trace_t t;memset(&t,0,sizeof(t));t.fraction=1;VectorCopy(b,t.endpos);
 if(all_solid==1 || (all_solid==2 && fabs(a[0])<100 && fabs(a[1])<100)){t.startsolid=t.allsolid=true;t.fraction=0;return t;}
 if(travel_trace){t.fraction=.5;t.ent=occluded?NULL:&target;return t;}
 if(target_trace){assert(type==MOVE_NORMAL);assert(fabs((b[0]-a[0])*(b[0]-a[0])+(b[1]-a[1])*(b[1]-a[1])+(b[2]-a[2])*(b[2]-a[2])-72*72)<.1);t.fraction=.5;t.ent=occluded?NULL:&target;return t;}
 if(harvest_fixture && occluded){t.fraction=.1f;return t;}
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
 int i;edict_t p;client_t client;vec3_t arrival={0,0,77};memset(&p,0,sizeof(p));memset(&client,0,sizeof(client));
 sv.active=true;svs.maxclients=1;svs.clients=&client;client.edict=&p;strcpy(sv.name,"prison");
 sv.model_precache[1]="progs/v_nord.mdl";
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
 finish_signon(&p);assert(cl.viewangles[0]==0 && cl.viewangles[1]==90);
 assert(!cl.nodrift); /* A door keeps the authored arrival policy. */
 assert(AW_InteriorPlace(&p,arrival));assert(p.v.origin[2]>50 && p.v.origin[2]<51);
 p.v.origin[0]=p.v.origin[1]=p.v.origin[2]=0;queued[0]=0;
 assert(AW_SceneUse());assert(!strcmp(notice,"Interior not found."));
 assert(!queued[0] && clear_buttons==1 && p.v.health==100); /* no transition or state loss */
 /* Quick test build without interiors: a friendly line instead of the repair message. */
 excluded_interiors=1;AW_ExcludedReset();
 assert(AW_SceneUse());assert(!strcmp(notice,"Area unavailable in this quick test build."));
 assert(!queued[0] && p.v.health==100);
 excluded_interiors=0;AW_ExcludedReset();
 assert(AW_SceneUse());assert(!strcmp(notice,"Interior not found."));
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
 /* Coordinate arguments use the same checked transition and preserve state. */
 command_argc=3;command_args[0]="aw_teleport";command_args[1]="-11264";command_args[2]="-71680";
 /* The optional Hors fixture has no populated current-health preset. Check
  * the real dead-player rejection, then establish an alive gameplay request. */
 p.v.health=0;queued[0]=0;teleport();assert(!queued[0]);p.v.health=73;
 queued[0]=0;teleport();assert(!strcmp(queued,"map seyda\n"));
 calls_mark=map_place_calls;strcpy(sv.name,"seyda");AW_SceneSpawn(&p);assert(map_place_calls==calls_mark+1 && last_map_arrival[0]==0 && last_map_arrival[1]==0);
 assert(p.v.health==73 && AW_StateGet(&aw_state,AW_ITEM,"gold_001")==87);
 {const char *badcoords[]={"nan","inf","1junk","0x10","1e9999","1e-9999","2000001","--1","1 2",""};unsigned i;
 for(i=0;i<sizeof(badcoords)/sizeof(badcoords[0]);i++) {
  command_args[1]=(char *)badcoords[i];queued[0]=0;teleport();
  assert(!queued[0] && p.v.health==73);
 }
 command_args[1]="-11264";command_args[2]="-71680";world_map_unavailable=1;
 queued[0]=0;teleport();assert(!queued[0] && p.v.health==73);
 world_map_unavailable=0;command_argc=4;command_args[3]="extra";
 queued[0]=0;teleport();assert(!queued[0] && p.v.health==73);
 }
 assert(requested_loading_delays==0); /* Explicit travel stays immediate. */
 assert(!scene_voice_begins && !scene_voice_ends && !scene_voice_cancels);
 /* An automatic sub-cell transition preserves held input and player goals.
  * Ordinary doors/teleports above must still clear input deliberately. */
 strcpy(sv.name,"seyda");p.v.movetype=MOVETYPE_NOCLIP;p.v.health=73;
 goal._float=1;torch._float=1;key_dest=key_game;cls.signon=SIGNONS;
 hand_state._float=2;hand_started._float=.25f;attack_latched._float=1;sv.time=121; /* Raised for over60s. */
 p.v.weaponmodel=ED_NewString("progs/v_nord.mdl")-pr_strings;p.v.weaponframe=3;
 aw_character.current[1]=33;aw_character.current[2]=44;aw_character.level=7;
 aw_story.stage=AW_STAGE_RELEASED;p.v.origin[0]=0;p.v.origin[1]=300;
 assert(AW_RegionSelect("seyda",p.v.origin,0));AW_RegionWorldModel("seyda",0);
 p.v.origin[0]=1200;p.v.velocity[0]=42;p.v.v_angle[0]=12;p.v.v_angle[1]=34;
 cl.viewangles[0]=12.625f;cl.viewangles[1]=359.875f;cl.viewangles[2]=0;
 cl.time=120;cl.laststop=119.5;cl.nodrift=true;cl.pitchvel=0;cl.driftmove=.075f;
 queued[0]=0;
 {int before=clear_buttons;AW_SceneTick();
  assert(!strcmp(queued,"map seyda\n") && clear_buttons==before);
  assert(requested_loading_delays==1);
  CL_ClearState();assert(cl.viewangles[0]==0 && !cl.nodrift);
  p.v.health=100;goal._float=0;torch._float=0;p.v.movetype=MOVETYPE_WALK;
  hand_state._float=hand_started._float=attack_latched._float=0;
  p.v.weaponmodel=p.v.weaponframe=0;sv.time=2;
  VectorCopy(vec3_origin,p.v.v_angle);
  AW_SceneSpawn(&p);
  assert(p.v.health==73 && goal._float==1 && torch._float==1);
  assert(hand_state._float==2 && attack_latched._float==1 && hand_started._float== -118.75f);
  assert(p.v.weaponframe==3 && !strcmp(pr_strings+p.v.weaponmodel,"progs/v_nord.mdl"));
  assert(aw_character.current[1]==33 && aw_character.current[2]==44 && aw_character.level==7);
  assert(AW_StateGet(&aw_state,AW_ITEM,"gold_001")==87);
  assert(p.v.movetype==MOVETYPE_NOCLIP && p.v.velocity[0]==42);
  assert(p.v.origin[0]==1200 && p.v.angles[0]==12.625f && p.v.angles[1]==359.875f);
  assert(p.v.v_angle[0]==12.625f && p.v.v_angle[1]==359.875f);
  cl.time=2;finish_signon(&p);assert(AW_TorchAnimationTime()==120);
  assert(cl.viewangles[0]==12.625f && cl.viewangles[1]==359.875f);
  assert(cl.nodrift && cl.pitchvel==0 && cl.driftmove==.075f && cl.laststop==1.5);
  /* With no new mouse event, the loaded view must not begin recentering. */
  v_centermove.value=.15f;v_centerspeed.value=500;cl.onground=true;
  V_DriftPitch();V_DriftPitch();assert(cl.viewangles[0]==12.625f && cl.pitchvel==0);
  /* A later mouse delta is not overwritten by a repeated ready notification. */
  cl.viewangles[0]+=1;cl.viewangles[1]-=2;AW_SceneSignon();
  assert(cl.viewangles[0]==13.625f && cl.viewangles[1]==357.875f);
 }
 /* Repeated reverse crossings preserve arbitrary fractional/wrapped headings,
  * both walking/noclip and an explicitly active pitch-centering policy. */
 {static float views[6][2]={{-69.875f,.125f},{79.875f,181.375f},
    {-23.0625f,-.375f},{.375f,720.875f},{42.125f,265.625f},{-.625f,91.0625f}};
  int i,before=clear_buttons;
  for(i=0;i<6;i++){
   p.v.origin[0]=i%2?1200:0;p.v.origin[1]=300;
   p.v.movetype=i%2?MOVETYPE_NOCLIP:MOVETYPE_WALK;
   p.v.v_angle[0]=p.v.v_angle[1]=0;
   cl.viewangles[0]=views[i][0];cl.viewangles[1]=views[i][1];
   cl.time=90;cl.laststop=90;cl.nodrift=i!=5;cl.pitchvel=i==5?25:0;cl.driftmove=.05f;
   queued[0]=0;AW_SceneTick();assert(!strcmp(queued,"map seyda\n"));
   CL_ClearState();VectorCopy(vec3_origin,p.v.v_angle);AW_SceneSpawn(&p);
   cl.time=4;finish_signon(&p);
   assert(cl.viewangles[0]==views[i][0] && cl.viewangles[1]==views[i][1]);
   assert(p.v.v_angle[0]==views[i][0] && p.v.v_angle[1]==views[i][1]);
   assert(p.v.movetype==(i%2?MOVETYPE_NOCLIP:MOVETYPE_WALK));
   assert(cl.nodrift==(i!=5) && cl.pitchvel==(i==5?25:0));
   assert(cl.driftmove==.05f && cl.laststop==4 && clear_buttons==before);
  }
 }
 /* Legacy centering already in progress remains active after loading when opted in. */
 extern cvar_t aw_auto_center;
 aw_auto_center.value=1;cl.onground=true;cl.idealpitch=0;noclip_anglehack=false;
 V_DriftPitch();assert(cl.viewangles[0]==-.125f && cl.pitchvel==35);
 aw_auto_center.value=0;
 /* The exterior-world route rebases coordinates; view preservation is the same
  * in both directions as for a same-name town subdivision. */
 p.v.origin[0]=2200;p.v.origin[1]=300;
 cl.viewangles[0]=-31.125f;cl.viewangles[1]=287.625f;cl.nodrift=true;
 queued[0]=0;AW_SceneTick();assert(!strcmp(queued,"map vf0000\n"));
 CL_ClearState();strcpy(sv.name,"vf0000");AW_SceneSpawn(&p);finish_signon(&p);
 assert(p.v.origin[0]==-104 && p.v.origin[1]==300);
 assert(cl.viewangles[0]==-31.125f && cl.viewangles[1]==287.625f);
 p.v.origin[0]=-1500;queued[0]=0;AW_SceneTick();assert(!strcmp(queued,"map seyda\n"));
 CL_ClearState();strcpy(sv.name,"seyda");AW_SceneSpawn(&p);finish_signon(&p);
 assert(p.v.origin[0]==804 && p.v.origin[1]==300);
 assert(cl.viewangles[0]==-31.125f && cl.viewangles[1]==287.625f);
 /* An explicit named teleport following a crossing keeps its destination yaw
  * and level pitch. It must not inherit the saved streaming camera. */
 command_argc=2;command_args[0]="aw_teleport";command_args[1]="census";teleport();
 assert(!strcmp(queued,"map census\n"));CL_ClearState();
 strcpy(sv.name,"census");AW_SceneSpawn(&p);finish_signon(&p);
 assert(cl.viewangles[0]==0 && cl.viewangles[1]==90 && !cl.nodrift);
 /* A failed/mismatched arrival discards the implicit camera snapshot. */
 strcpy(sv.name,"seyda");p.v.origin[0]=0;p.v.origin[1]=300;
 assert(AW_RegionSelect("seyda",p.v.origin,0));AW_RegionWorldModel("seyda",0);
 p.v.origin[0]=1200;cl.viewangles[0]=22.5f;cl.viewangles[1]=121.75f;
 queued[0]=0;AW_SceneTick();assert(!strcmp(queued,"map seyda\n"));
 CL_ClearState();strcpy(sv.name,"prison");AW_SceneSpawn(&p);
 cl.viewangles[0]=-10;cl.viewangles[1]=75;AW_SceneSignon();
 assert(cl.viewangles[0]==-10 && cl.viewangles[1]==75);
 assert(signon_finished>=11);
 assert(scene_voice_begins==10 && scene_voice_ends==9 && scene_voice_cancels==1);
 assert(!scene_voice_armed);
 /* A deliberate scene restart invalidates queued hand/equipment restoration. */
 strcpy(sv.name,"seyda");p.v.origin[0]=0;p.v.origin[1]=300;
 assert(AW_RegionSelect("seyda",p.v.origin,0));AW_RegionWorldModel("seyda",0);
 p.v.origin[0]=1200;cls.signon=SIGNONS;goal._float=1;torch._float=1;
 hand_state._float=2;hand_started._float=(float)sv.time;AW_SceneTick();
 AW_SceneCancelTransition();
 goal._float=torch._float=hand_state._float=attack_latched._float=0;
 p.v.weaponmodel=p.v.weaponframe=0;AW_SceneSpawn(&p);finish_signon(&p);
 assert(!goal._float && !torch._float && !hand_state._float && !p.v.weaponmodel);
 assert(AW_TorchAnimationTime()==cl.time && torch_restores>0);
 /* Internal original-cell section switches use the proven automatic handoff,
  * with exact view/equipment/voice preservation and no extra door interaction. */
 {
  int before=clear_buttons,begins=scene_voice_begins,ends=scene_voice_ends,j;
  narrow_room=0;AW_SceneCancelTransition();aw_story.stage=AW_STAGE_RELEASED;
  strcpy(sv.name,"mi5b8154939f7aa");p.v.movetype=MOVETYPE_WALK;
  p.v.origin[0]=-112;p.v.origin[1]=1088;p.v.origin[2]=-192;p.v.health=77;
  cls.signon=SIGNONS;queued[0]=0;AW_SceneTick();assert(!queued[0]);
  for(j=0;j<4;j++){
   p.v.origin[0]=j%2?-145:-111;p.v.velocity[0]=j%2?-34:34;
   cl.viewangles[0]=17.125f;cl.viewangles[1]=278.625f;cl.nodrift=true;
   goal._float=torch._float=1;hand_state._float=2;
   queued[0]=0;AW_SceneTick();assert(!strcmp(queued,j%2?"map mi5b8154939f7aa\n":"map mi5b8154939f7ab\n"));
   CL_ClearState();strcpy(sv.name,j%2?"mi5b8154939f7aa":"mi5b8154939f7ab");
   goal._float=torch._float=hand_state._float=0;AW_SceneSpawn(&p);finish_signon(&p);
   assert(p.v.origin[0]==(j%2?-145:-111) && p.v.origin[1]==1088 && p.v.origin[2]==-192);
   assert(p.v.velocity[0]==(j%2?-34:34) && p.v.health==77);
   assert(goal._float==1 && torch._float==1 && hand_state._float==2);
   assert(cl.viewangles[0]==17.125f && cl.viewangles[1]==278.625f && cl.nodrift);
   queued[0]=0;AW_SceneTick();assert(!queued[0]);
  }
  assert(clear_buttons==before && scene_voice_begins==begins+4 && scene_voice_ends==ends+4);
 }
 /* Authored exterior and original exit banks are explicit interactions, not
  * transparent internal connectors: held input clears and voice isn't carried. */
 {
  int before=clear_buttons,begins=scene_voice_begins;
  section_doors=1;door_duration=0;occluded=target_trace=travel_trace=0;
  AW_SceneCancelTransition();strcpy(sv.name,"vf0000");memset(p.v.origin,0,sizeof(p.v.origin));
  p.v.view_ofs[2]=30;p.v.movetype=MOVETYPE_WALK;cl.viewangles[0]=0;cl.viewangles[1]=90;
  cls.state=ca_connected;cls.signon=SIGNONS;queued[0]=0;
  assert(AW_SceneUse() && !strcmp(queued,"map mi5b8154939f7aa\n"));
  CL_ClearState();strcpy(sv.name,"mi5b8154939f7aa");AW_SceneSpawn(&p);finish_signon(&p);
  assert(p.v.origin[0]==-380 && p.v.origin[1]==758 && cl.viewangles[1]==90);
  memset(p.v.origin,0,sizeof(p.v.origin));cl.viewangles[0]=0;cl.viewangles[1]=90;
  cls.state=ca_connected;queued[0]=0;
  assert(AW_SceneUse() && !strcmp(queued,"map vf0000\n"));
  CL_ClearState();strcpy(sv.name,"vf0000");AW_SceneSpawn(&p);finish_signon(&p);
  assert(p.v.origin[0]==12 && p.v.origin[1]==34);
  assert(clear_buttons==before+2 && scene_voice_begins==begins);section_doors=0;
 }
 /* Original plant FNAM and the Talk-style action row share actual pickup
  * eligibility, and vanish after the transaction. */
 harvest_fixture=1;target_trace=travel_trace=0;occluded=0;narrow_room=0;
 memset(&target,0,sizeof(target));memset(&harvest_model,0,sizeof(harvest_model));
 strcpy(harvest_world.name,"maps/vf0000.bsp");sv.worldmodel=&harvest_world;
 sv.models[1]=&harvest_model;harvest_model.type=mod_brush;
 for(i=0;i<3;i++){harvest_model.mins[i]=-2;harvest_model.maxs[i]=2;}
 target.v.classname=sizeof(ORIGINAL_STRINGS);target.v.model=sizeof(ORIGINAL_STRINGS)+10;
 target.v.modelindex=1;target.v.origin[0]=40;target.v.origin[2]=30;
 memset(p.v.origin,0,sizeof(p.v.origin));p.v.view_ofs[2]=30;p.v.movetype=MOVETYPE_WALK;
 memset(cl.viewangles,0,sizeof(cl.viewangles));cls.state=ca_connected;sv.num_edicts=2;
 key_dest=key_game;names_option->value=1;aw_story.stage=AW_STAGE_RELEASED;
 AW_StateReset();AW_HarvestBegin();AW_HarvestSpawn();
 hint[0]=object_name[0]=0;AW_SceneDraw();
 assert(!strcmp(hint,"(E: Pick)") && !strcmp(object_name,"Luminous Russula"));
 assert(!strcmp(AW_SceneTargetName(),"Luminous Russula"));
 occluded=1;hint[0]=0;AW_SceneDraw();assert(!hint[0] && !AW_SceneTargetName());occluded=0;
 /* Existing named NPC targeting wins without consuming the plant. */
 target.v.classname=1;target.v.netname=8;target_trace=1;voice.string=8;role._float=0;
 hint[0]=0;AW_SceneDraw();assert(!strcmp(hint,"(E: Talk)"));assert(!AW_SceneUse());
 target_trace=0;target.v.classname=sizeof(ORIGINAL_STRINGS);target.v.netname=0;
 assert(AW_SceneUse());assert(!strcmp(notice,"Picked up 2 Original item name."));
 hint[0]=object_name[0]=0;AW_SceneDraw();assert(!hint[0] && !AW_SceneTargetName());
 /* One-command regression location uses checked teleport and does not reset
  * picked facts/inventory. Final signon must not quantize the requested aim. */
 {
  aw_state_t saved;int previous_calls=map_place_calls,mode,reads,listed;
  AW_StateSet(&aw_state,AW_GLOBAL,"CharGenState",-1);saved=aw_state;
  assert(shroompicker);AW_SceneCancelTransition();
  strcpy(sv.name,"seyda");p.v.health=73;p.v.movetype=MOVETYPE_WALK;
  cls.state=ca_connected;cls.signon=SIGNONS;aw_story.stage=AW_STAGE_RELEASED;
  command_args[0]="aw_shroompicker";command_args[1]="reset";command_argc=2;
  queued[0]=0;shroompicker();assert(!queued[0]);
  command_args[1]="0";shroompicker();assert(!queued[0]);
  command_args[1]="11";shroompicker();assert(!queued[0]);
  command_args[1]="list";reads=picker_file_reads;shroompicker();
  assert(!queued[0] && picker_file_reads==reads+1 && !memcmp(&aw_state,&saved,sizeof(saved)));
  command_argc=1;
  for(mode=1;mode<=5;mode++){picker_file_mode=mode;shroompicker();assert(!queued[0]);}
  for(mode=7;mode<=8;mode++){picker_file_mode=mode;shroompicker();assert(!queued[0]);}
  picker_file_mode=6;command_argc=2;command_args[1]="list";reads=picker_file_reads;listed=picker_list_rows;
  shroompicker();assert(!queued[0] && picker_file_reads==reads+1 && picker_list_rows==listed+10);
  command_argc=1;shroompicker();assert(!strcmp(queued,"map seyda\n"));
  AW_SceneCancelTransition();queued[0]=0;
  picker_file_mode=0;
  AW_StateSet(&aw_state,AW_GLOBAL,"CharGenState",0);shroompicker();assert(!queued[0]);
  AW_StateSet(&aw_state,AW_GLOBAL,"CharGenState",-1);
  command_argc=1;world_map_unavailable=1;shroompicker();assert(!queued[0]);
  world_map_unavailable=0;p.v.health=0;shroompicker();assert(!queued[0]);p.v.health=73;
  shroompicker();assert(!strcmp(queued,"map seyda\n"));
  CL_ClearState();AW_SceneSpawn(&p);finish_signon(&p);
  assert(map_place_calls==previous_calls+1 && last_map_arrival[0]==86 && last_map_arrival[1]==-860);
  assert(cl.viewangles[0]==64 && cl.viewangles[1]==4 && cl.nodrift);
  assert(p.v.v_angle[0]==64 && p.v.v_angle[1]==4 && p.v.health==73);
  assert(!memcmp(&aw_state,&saved,sizeof(saved)));
  command_argc=2;command_args[1]="2";queued[0]=0;shroompicker();assert(!strcmp(queued,"map seyda\n"));
  CL_ClearState();AW_SceneSpawn(&p);finish_signon(&p);
  assert(map_place_calls==previous_calls+2 && last_map_arrival[0]==86 && last_map_arrival[1]==-850);
  assert(cl.viewangles[0]==60.5 && cl.viewangles[1]==17.25 && cl.nodrift);
  assert(p.v.v_angle[0]==60.5 && p.v.v_angle[1]==17.25 && !memcmp(&aw_state,&saved,sizeof(saved)));
  command_args[1]="1";queued[0]=0;shroompicker();assert(!strcmp(queued,"map seyda\n"));
  CL_ClearState();AW_SceneSpawn(&p);finish_signon(&p);
  assert(cl.viewangles[0]==64 && cl.viewangles[1]==4 && !memcmp(&aw_state,&saved,sizeof(saved)));
  command_args[1]="2";queued[0]=0;shroompicker();assert(!strcmp(queued,"map seyda\n"));
  map_place_blocked=1;CL_ClearState();AW_SceneSpawn(&p);finish_signon(&p);map_place_blocked=0;
  assert(cl.viewangles[0]!=60.5 && !memcmp(&aw_state,&saved,sizeof(saved)));
  /* A cancelled shortcut cannot change a subsequent unrelated scene view. */
  shroompicker();AW_SceneCancelTransition();
  strcpy(sv.name,"prison");AW_SceneSpawn(&p);
  cl.viewangles[0]=-10;cl.viewangles[1]=75;AW_SceneSignon();
  assert(cl.viewangles[0]==-10 && cl.viewangles[1]==75);
 }
 /* VIVEC-ARENA-TP-ARRIVAL-32: a blocked arrival falls back to the scene spawn,
  * never to the frame origin, and no spot is ever under water. */
 {
  vec3_t spawn={300,200,77},blocked={0,0,77},wet={0,0,77};edict_t q;
  svs.clients[0].edict->v.health=73;memset(&q,0,sizeof(q));
  q.v.mins[2]=-16.625f;q.v.maxs[2]=16.625f;
  water_feet=1;assert(!AW_InteriorPlace(&q,wet));water_feet=0;   /* dry feet only */
  assert(AW_InteriorPlace(&q,wet));assert(q.v.origin[2]>50 && q.v.origin[2]<51);
  /* Arrival in solid everywhere, spawn clear: the town default is used. */
  command_argc=2;command_args[0]="aw_teleport";command_args[1]="seydaneen";queued[0]=0;teleport();assert(!strcmp(queued,"map seyda\n"));
  CL_ClearState();strcpy(sv.name,"seyda");
  VectorCopy(spawn,q.v.origin);memset(q.v.oldorigin,0,sizeof(q.v.oldorigin));
  all_solid=2;AW_SceneSpawn(&q);all_solid=0;
  assert(q.v.origin[0]==300 && q.v.origin[1]==200 && q.v.origin[2]>50 && q.v.origin[2]<51);
  /* Nothing clear and no map floor: stay at the spawn, which is also the
   * stuck-recovery anchor (oldorigin), never 0 0 0. */
  command_argc=2;command_args[0]="aw_teleport";command_args[1]="seydaneen";queued[0]=0;teleport();assert(!strcmp(queued,"map seyda\n"));
  CL_ClearState();map_place_blocked=1;
  VectorCopy(spawn,q.v.origin);memset(q.v.oldorigin,0,sizeof(q.v.oldorigin));
  all_solid=1;AW_SceneSpawn(&q);all_solid=0;map_place_blocked=0;
  assert(q.v.origin[0]==300 && q.v.origin[1]==200 && q.v.origin[2]==77);
  assert(q.v.oldorigin[0]==300 && q.v.oldorigin[1]==200 && q.v.oldorigin[2]==77);
  /* dbg unstuck: nearest clear spot below; nothing clear leaves the player. */
  q.v.movetype=MOVETYPE_NOCLIP;VectorCopy(blocked,q.v.origin);
  assert(AW_Unstuck(&q));assert(q.v.movetype==MOVETYPE_WALK && q.v.origin[2]>50 && q.v.origin[2]<51);
  q.v.movetype=MOVETYPE_NOCLIP;VectorCopy(blocked,q.v.origin);all_solid=1;
  assert(!AW_Unstuck(&q));all_solid=0;
  assert(q.v.movetype==MOVETYPE_NOCLIP && q.v.origin[2]==77);
  water_feet=1;assert(!AW_Unstuck(&q));water_feet=0;assert(q.v.origin[2]==77);
 }
#ifdef BALMORA_AVAILABLE
 /* A partial-area build (aw_miniwind.c, tools/miniwind.py): the logo and New
  * Game quick-start in its town with the notice; exits to areas it does not
  * hold say "Area unavailable"; a normal build is unchanged. */
 {
  edict_t q;int before;
  assert(!AW_MiniwindActive() && quick);
  /* A normal build (no notice file): a missing room still says "Interior not found." */
  harvest_fixture=0;AW_SceneCancelTransition();strcpy(sv.name,"balmora");sv.active=true;cls.state=ca_connected;cls.signon=SIGNONS;
  key_dest=key_game;target_trace=travel_trace=occluded=0;door_duration=0;miniwind_rooms_missing=1;
  memset(p.v.origin,0,sizeof(p.v.origin));p.v.view_ofs[2]=30;p.v.movetype=MOVETYPE_WALK;p.v.health=73;
  cl.viewangles[0]=0;cl.viewangles[1]=90;queued[0]=0;
  assert(AW_SceneUse() && !strcmp(notice,"Interior not found.") && !queued[0]);
  miniwind_fixture=1;AW_MiniwindInit();assert(AW_MiniwindActive());
  /* The same door in the partial-area build. */
  assert(AW_SceneUse() && !strcmp(notice,"Area unavailable") && !queued[0]);
  miniwind_rooms_missing=0;
  /* The silt strider back to Seyda Neen, which the build does not hold. */
  world_map_unavailable=1;travel_trace=1;target.free=0;target.v.modelindex=1;
  target.v.netname=27+strlen(pr_strings+27)+1;target.v.classname=1;
  assert(AW_SceneUse() && key_dest==key_menu);queued[0]=0;
  assert(AW_TravelKey(K_ENTER));drawn[0]=0;assert(AW_TravelDraw());
  assert(strstr(drawn,"Area unavailable") && !queued[0]);
  AW_TravelKey(K_ESCAPE);assert(key_dest==key_game);travel_trace=0;world_map_unavailable=0;
  /* The quick start (after the logo, New Game): Hors at Balmora's arrival, then the notice. */
  sv.active=false;aw_character.current[0]=40;command_argc=1;command_args[0]="aw_quick_start";queued[0]=0;
  quick();assert(!strcmp(queued,"map balmora\n") && aw_character.valid && key_dest==key_game);
  command_argc=2;command_args[1]="atlantis";queued[0]=0;quick();assert(!queued[0]);command_argc=1;
  sv.active=true;memset(&q,0,sizeof(q));q.v.mins[2]=-16.625f;q.v.maxs[2]=16.625f;q.v.movetype=MOVETYPE_WALK;
  VectorCopy(vec3_origin,q.v.origin);q.v.origin[2]=77;notice[0]=0;
  CL_ClearState();strcpy(sv.name,"balmora");AW_SceneSpawn(&q);
  assert(q.v.health==40 && q.v.origin[2]>50 && q.v.origin[2]<51);
  assert(!strcmp(notice,"FEATURES ONLY: Balmora exterior (CHIM)"));
  notice[0]=0;AW_SceneSpawn(&q);assert(!notice[0]);   /* once, not on every arrival */
  /* The CHIM frame's edge: held inside, "Area unavailable", no crossing. */
  aw_chim_town_map=balmora_frame;strcpy(sv.modelname,"maps/balmora-chim.bsp");
  svs.clients[0].edict=&q;cls.signon=SIGNONS;key_dest=key_game;realtime=100;
  q.v.origin[0]=500;q.v.origin[1]=0;queued[0]=0;notice[0]=0;AW_SceneTick();
  assert(!queued[0] && !notice[0] && q.v.origin[0]==500);
  q.v.origin[0]=1010;q.v.velocity[0]=320;AW_SceneTick();
  assert(q.v.origin[0]==500 && q.v.velocity[0]==0 && !strcmp(notice,"Area unavailable") && !queued[0]);
  notice[0]=0;q.v.origin[0]=1010;realtime=101;AW_SceneTick();assert(q.v.origin[0]==500 && !notice[0]);
  realtime=104;q.v.origin[0]=1010;AW_SceneTick();assert(!strcmp(notice,"Area unavailable"));
  /* Noclip is never held; the legacy region maps (chim_towns 0) are not either. */
  q.v.movetype=MOVETYPE_NOCLIP;q.v.origin[0]=1010;AW_SceneTick();assert(q.v.origin[0]==1010);
  q.v.movetype=MOVETYPE_WALK;aw_chim_town_map=NULL;strcpy(sv.modelname,"maps/bm000.bsp");
  before=(int)q.v.origin[0];notice[0]=0;AW_SceneTick();assert((int)q.v.origin[0]==before && strcmp(notice,"Area unavailable"));
  svs.clients[0].edict=&p;
  /* --miniwind-scope exterior on a pure CHIM image: the image step removed balmora.bsp
   * and every bm*.bsp (the region table stays) and ships no room. The quick start, the
   * doors and the frame edge work from the frame map alone. */
  miniwind_pure_exterior=1;aw_chim_town_map=balmora_frame;
  AW_SceneCancelTransition();strcpy(sv.name,"balmora");strcpy(sv.modelname,"maps/balmora-chim.bsp");
  sv.active=true;cls.state=ca_connected;cls.signon=SIGNONS;key_dest=key_game;
  target_trace=travel_trace=occluded=0;door_duration=0;
  memset(p.v.origin,0,sizeof(p.v.origin));p.v.view_ofs[2]=30;p.v.movetype=MOVETYPE_WALK;p.v.health=73;
  cl.viewangles[0]=0;cl.viewangles[1]=90;queued[0]=0;notice[0]=0;
  assert(AW_SceneUse() && !strcmp(notice,"Area unavailable") && !queued[0]);
  sv.active=false;command_argc=1;command_args[0]="aw_quick_start";queued[0]=0;
  quick();assert(!strcmp(queued,"map balmora\n") && key_dest==key_game);
  sv.active=true;memset(&q,0,sizeof(q));q.v.mins[2]=-16.625f;q.v.maxs[2]=16.625f;q.v.movetype=MOVETYPE_WALK;
  VectorCopy(vec3_origin,q.v.origin);q.v.origin[2]=77;notice[0]=0;
  CL_ClearState();strcpy(sv.name,"balmora");AW_SceneSpawn(&q);
  assert(!strcmp(notice,"FEATURES ONLY: Balmora exterior (CHIM)"));
  svs.clients[0].edict=&q;cls.signon=SIGNONS;key_dest=key_game;realtime=200;
  q.v.origin[0]=500;q.v.origin[1]=0;AW_SceneTick();q.v.origin[0]=1010;q.v.velocity[0]=320;notice[0]=0;queued[0]=0;
  AW_SceneTick();assert(q.v.origin[0]==500 && !strcmp(notice,"Area unavailable") && !queued[0]);
  svs.clients[0].edict=&p;miniwind_pure_exterior=0;aw_chim_town_map=NULL;
 }
#endif
 puts("scene, real client reset/signon, exact streaming view, drift policy, reverse/world crossings and explicit arrivals passed");
 return 0;
}

void AW_IntroSpawn(void){}

void AW_OpeningSpawn(void){}
void AW_SaveCapture(void){}
void AW_SaveSpawn(void){}
void AW_SaveReset(void){}

qboolean AW_MapPlace(edict_t *p,const float *xy){map_place_calls++;VectorCopy(xy,last_map_arrival);return !map_place_blocked;}
qboolean AW_MapPlaceBelow(edict_t *p,const float *point){map_place_calls++;VectorCopy(point,last_map_arrival);return !map_place_blocked;}
const char *aw_map_place_failure="";
