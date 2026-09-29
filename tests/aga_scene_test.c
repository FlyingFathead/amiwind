/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
#include "aw_story.h"
keydest_t key_dest=key_game;
char *pr_strings="\0aw_npc\0Fargoth\0worldspawn\0Darvame Hleran";
static cvar_t *names_option;
static edict_t target;static int target_trace;
static int voice_aim,prompt,travel_trace;
static char drawn[2048];
void AW_UIBox(int a,int b,int c,int d){}
void AW_UISmallBegin(void){}
void AW_UISmallEnd(void){}
void AW_UITextBox(int a,int b,int c,int d,const char *s,int e){strcat(drawn,s);strcat(drawn,"|");}
int AW_IntroPromptActive(void){return prompt;}
int AW_UIVoiceAimOnly(void){return voice_aim;}
int AW_CharacterActive(void){return 0;}
int AW_ReaderActive(void){return 0;}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void Cvar_SetValue(char *s,float v){if(names_option && !strcmp(s,names_option->name))names_option->value=v;}
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;
static char queued[64];static eval_t goal;static int clear_buttons,events,occluded;
static void (*start_demo)(void);static cvar_t *demo_option;
static int opening_track=-1,ship_available=1,narrow_room;
static char notice[96];
void AW_UISubtitle(const char *name,const char *text,double duration){strcpy(notice,text);}
void Cvar_RegisterVariable(cvar_t *c){if(!strcmp(c->name,"aw_target_names"))names_option=c;else demo_option=c;c->value=atof(c->string);}
void Cmd_AddCommand(char *name,void(*fn)(void)){if(!strcmp(name,"aw_demo_start"))start_demo=fn;}
int Cmd_Argc(void){return 0;}
char *Cmd_Argv(int i){return "";}
int AW_MusicStartTrack(int id){opening_track=id;return 1;}
int COM_FOpenFile(char *name,FILE **f){
 const char *s="AWD2\nprison seyda -5 35 25 5 45 35 0 0 77 90\tSeyda Neen\nprison evil;quit -5 35 25 5 45 35 0 0 77 90\tInvalid\nprison seyda nan 35 25 5 45 35 0 0 77 90\tInvalid\nseyda - -5 35 25 5 45 35 0 0 0 90\tCensus and Excise Office\n";
 if(!strcmp(name,"maps/prison.bsp") && !ship_available){*f=NULL;return -1;}
 *f=tmpfile();assert(*f);fputs(s,*f);rewind(*f);return strlen(s);
}
void Con_Printf(char *fmt,...){}
void Cbuf_AddText(char *s){strcpy(queued,s);}
void IN_AWClearButtons(void){clear_buttons++;}
void AW_MusicSceneEvent(const char *s){events++;}
double Sys_FloatTime(void){return 1;}
int Hunk_LowMark(void){return 1000;}
int Hunk_HighMark(void){return 0;}
eval_t *GetEdictFieldValue(edict_t *p,char *name){return &goal;}
qboolean AW_PlacePlayer(edict_t *p,vec3_t v){return false;}
void SV_LinkEdict(edict_t *p,qboolean touch){}
trace_t SV_Move(vec3_t a,vec3_t mins,vec3_t maxs,vec3_t b,int type,edict_t *p){
 trace_t t;memset(&t,0,sizeof(t));t.fraction=1;VectorCopy(b,t.endpos);
 if(travel_trace){t.fraction=.5;t.ent=occluded?NULL:&target;return t;}
 if(target_trace){assert(type==MOVE_NORMAL);assert(fabs((b[0]-a[0])*(b[0]-a[0])+(b[1]-a[1])*(b[1]-a[1])+(b[2]-a[2])*(b[2]-a[2])-96*96)<.1);t.fraction=.5;t.ent=occluded?NULL:&target;return t;}
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
 assert(AW_Interior());
 cl.viewangles[1]=0;assert(!AW_SceneUse());cl.viewangles[1]=90;
 p.v.origin[1]=-100;assert(!AW_SceneUse());p.v.origin[1]=0;
 occluded=1;assert(!AW_SceneUse());occluded=0;
 assert(AW_SceneUse());assert(!strcmp(queued,"map seyda\n"));assert(clear_buttons==1);
 assert(AW_SceneUse());assert(clear_buttons==1); /* held use cannot queue twice */
 strcpy(sv.name,"seyda");p.v.health=0;goal._float=0;AW_SceneSpawn(&p);
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
 occluded=1;assert(!AW_SceneUse());occluded=0;
 assert(AW_SceneUse() && key_dest==key_menu);
 drawn[0]=0;assert(AW_TravelDraw());assert(strstr(drawn,"Balmora") && strstr(drawn,"Gnisis") && strstr(drawn,"Suran") && strstr(drawn,"Vivec") && strstr(drawn,"Cancel"));
 {int i;for(i=0;i<4;i++){
   queued[0]=0;assert(AW_TravelKey(K_ENTER));drawn[0]=0;assert(AW_TravelDraw());
   assert(strstr(drawn,"Destination not found."));assert(!queued[0]);
   assert(AW_StateGet(&aw_state,AW_ITEM,"gold_001")==87);AW_TravelKey(K_DOWNARROW);
 }}
 assert(AW_TravelKey(K_ENTER) && key_dest==key_game);
 assert(!AW_TravelDraw());assert(AW_SceneUse());AW_TravelKey(K_ESCAPE);assert(key_dest==key_game);
 return 0;
}

void AW_IntroSpawn(void){}

void AW_OpeningSpawn(void){}
void AW_SaveCapture(void){}
void AW_SaveSpawn(void){}
void AW_SaveReset(void){}
