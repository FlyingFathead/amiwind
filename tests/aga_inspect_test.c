/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_inspect.h"
#include <assert.h>
client_state_t cl;
client_static_t cls;
server_t sv;
server_static_t svs;
refdef_t r_refdef;
viddef_t vid;
keydest_t key_dest;
entity_t cl_static_entities[MAX_STATIC_ENTITIES];
entity_t cl_entities[MAX_EDICTS];
char *pr_strings;
int scr_copyeverything;
int (*aw_inspect_buttons)(int);
int (*aw_inspect_crosshair)(void);
void (*aw_inspect_draw)(void),(*aw_inspect_reset)(void);
static edict_t entities[5];
static model_t alias,world;
static struct {aliashdr_t header;maliasframedesc_t extra;mdl_t mdl;} model_cache;
static client_t local;
static eval_t ids[5],refs[5];
static int argc=2,traces,draws,characters;
static float wall=1,all;
static char *arg="on",output[4096],strings[512];
static int used=1;
static float overlay;
static void (*hud)(void),(*ent)(void);
edict_t *EDICT_NUM(int i){assert(i>=0 && i<5);return &entities[i];}
int NUM_FOR_EDICT(edict_t *e){return (int)(e-entities);}
eval_t *GetEdictFieldValue(edict_t *e,char *field){
 int n=NUM_FOR_EDICT(e);
 if(!strcmp(field,"aw_ref"))return &refs[n];
 if(!strcmp(field,"aw_source_id"))return &ids[n];
 return NULL;
}
int Cmd_Argc(void){return argc;}
char *Cmd_Argv(int i){return i?arg:"aw_debug_hud";}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void Con_Printf(char *fmt,...){va_list args;size_t n=strlen(output);va_start(args,fmt);vsnprintf(output+n,sizeof(output)-n,fmt,args);va_end(args);}
void Cmd_AddCommand(char *name,void (*fn)(void)){
 if(!strcmp(name,"aw_debug_hud"))hud=fn;else if(!strcmp(name,"aw_inspect"))ent=fn;else assert(0);
}
void Cvar_SetValue(char *name,float value){if(!strcmp(name,"_aw_debug_all"))overlay=value;else assert(!strcmp(name,"_aw_debug_coords"));}
void *Cache_Check(cache_user_t *cache){return cache->data;}
float R_SpriteEntityScale(const entity_t *e){return e->aw_sprite_scale>0?e->aw_sprite_scale:1;}
int AW_DebugOverlaysEnabled(void){return overlay!=0;}
int AW_CharacterActive(void){return characters;}
int AW_ReaderActive(void){return 0;}
int AW_IntroPromptActive(void){return 0;}
int AW_WorldToSource(const char *map,const float *p,float *out){int i;if(strcmp(map,"seyda"))return 0;for(i=0;i<3;i++)out[i]=p[i]*4;return 1;}
void Draw_Fill(int x,int y,int w,int h,int color){assert(x>=0 && y>=0 && w>=0 && x+w<=vid.width && y+h<=vid.height);}
void AW_SmallString(int x,int y,const char *s){assert(x+(int)strlen(s)*4<=vid.width-8 && y+7<vid.height-22);draws++;}
trace_t SV_Move(vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,int type,edict_t *pass){
 trace_t tr;memset(&tr,0,sizeof(tr));traces++;assert(type==MOVE_NOMONSTERS && pass==entities+1);
 tr.fraction=wall;tr.ent=wall<1?entities:NULL;tr.allsolid=all!=0;return tr;
}
static int string(char *s){int n=used;strcpy(strings+n,s);used+=(int)strlen(s)+1;return n;}
static void command(char *s){arg=s;argc=2;output[0]=0;hud();}
static void click(void){aw_inspect_buttons(0);output[0]=0;assert(aw_inspect_buttons(3)==2);}
int main(void){
 edict_t before[5];int prior,j;
 pr_strings=strings;sv.edicts=entities;sv.num_edicts=4;sv.active=true;
 svs.clients=&local;svs.maxclients=1;local.edict=entities+1;local.edict->v.health=100;
 cls.state=ca_connected;key_dest=key_game;strcpy(sv.name,"seyda");
 alias.type=mod_alias;strcpy(alias.name,"progs/test.mdl");
 alias.mins[0]=alias.mins[1]=alias.mins[2]=-4;alias.maxs[0]=alias.maxs[1]=alias.maxs[2]=4;
 alias.cache.data=&model_cache;model_cache.header.model=(int)((byte *)&model_cache.mdl-(byte *)&model_cache);
 model_cache.mdl.numframes=2;
 for(j=0;j<3;j++){
  model_cache.mdl.scale[j]=1;model_cache.mdl.scale_origin[j]=-40;
  model_cache.header.frames[0].bboxmin.v[j]=36;model_cache.header.frames[0].bboxmax.v[j]=44;
  model_cache.extra.bboxmin.v[j]=36;model_cache.extra.bboxmax.v[j]=44;
 }
 model_cache.extra.bboxmin.v[1]=0;model_cache.extra.bboxmax.v[1]=80;
 world.type=mod_brush;strcpy(world.name,"maps/seyda.bsp");sv.models[1]=&world;sv.models[2]=&alias;
 entities[0].v.modelindex=1;entities[0].v.classname=string("worldspawn");
 entities[2].v.modelindex=entities[3].v.modelindex=2;
 entities[2].v.classname=entities[3].v.classname=string("aw_npc");
 entities[2].v.netname=string("Eloroth");ids[2].string=string("eloroth");refs[2]._float=201388;
 entities[3].v.netname=string("Ordinator");ids[3].string=string("ordinator wander");refs[3]._float=201385;
 entities[2].v.origin[0]=20;entities[3].v.origin[0]=40;
 cl.num_entities=4;cl_entities[2].model=cl_entities[3].model=&alias;
 cl_entities[2].origin[0]=20;cl_entities[3].origin[0]=40;
 vid.width=320;vid.height=200;
 AW_InspectInit();assert(hud && ent && aw_inspect_reset);
 assert(aw_inspect_buttons(3)==3 && !aw_inspect_crosshair());aw_inspect_draw();assert(!traces && !draws);
 aw_inspect_buttons(0);command("on");assert(aw_inspect_crosshair() && overlay==1);
 memcpy(before,entities,sizeof(before));click();assert(strstr(output,"201388") && strstr(output,"eloroth"));
 assert(!memcmp(before,entities,sizeof(before))); /* selection never changes actors */
 assert(strstr(output,"entity 2") && strstr(output,"bounds pick") && strstr(output,"80.0 0.0 0.0"));
 prior=traces;aw_inspect_buttons(3);aw_inspect_buttons(3);assert(traces==prior); /* hold selects once */
 aw_inspect_draw();assert(draws>1 && traces==prior); /* draw does not trace */
 /* Off during a held click must not punch until release and a fresh press. */
 command("off");assert(aw_inspect_buttons(3)==2);aw_inspect_buttons(0);assert(aw_inspect_buttons(3)==3);
 aw_inspect_buttons(0);command("TRUE");click();command("false");assert(!aw_inspect_crosshair());
 aw_inspect_buttons(0);command("1");assert(aw_inspect_crosshair());command("0");assert(!aw_inspect_crosshair());
 command("garbage");assert(!aw_inspect_crosshair());command("on");
 /* Wall at ten units occludes both NPCs; no invented original static ref. */
 wall=10/2048.0f;click();assert(strstr(output,"entity 0") && strstr(output,"source ref: unavailable") && !strstr(output,"201388"));
 wall=1;all=1;click();assert(strstr(output,"camera inside collision"));all=0;
 /* The camera's ray controls selection (e.g. displaced third-person view). */
 r_refdef.vieworg[1]=20;click();assert(strstr(output,"no target"));
 r_refdef.vieworg[1]=0;entities[2].free=true;click();assert(strstr(output,"201385"));entities[2].free=false;
 /* A background actor's death envelope must not beat the visible standing
  * foreground actor. Client pose/frame is authoritative, not server pose. */
 alias.mins[1]=-40;alias.maxs[1]=40;
 cl_entities[3].origin[0]=12;cl_entities[3].origin[1]=12;
 click();assert(strstr(output,"201388") && !strstr(output,"201385"));
 cl_entities[3].frame=1;click();assert(strstr(output,"201385") && strstr(output,"server runtime: frame 0") && strstr(output,"server local XYZ: 40.0 0.0 0.0"));
 cl_entities[3].frame=99;click();assert(strstr(output,"201388")); /* renderer falls back to frame zero */
 cl_entities[3].frame=0;cl_entities[3].origin[0]=40;cl_entities[3].origin[1]=0;
 /* No I/O or whole-model fallback when frame data is no longer resident. */
 alias.cache.data=NULL;click();assert(strstr(output,"no target"));alias.cache.data=&model_cache;
 /* Stale/disappeared client entities cannot borrow live server identities. */
 cl_entities[2].msgtime=-1;click();assert(strstr(output,"201385"));cl_entities[2].msgtime=0;
 /* Alias pitch sign and per-entity scale match the renderer. */
 entities[3].free=true;cl_entities[2].angles[PITCH]=90;r_refdef.vieworg[2]=10;
 model_cache.header.frames[0].bboxmin.v[0]=40;model_cache.header.frames[0].bboxmax.v[0]=60;
 model_cache.header.frames[0].bboxmin.v[2]=39;model_cache.header.frames[0].bboxmax.v[2]=41;
 click();assert(strstr(output,"201388"));
 cl_entities[2].angles[PITCH]=0;r_refdef.vieworg[2]=0;
 for(j=0;j<3;j++){model_cache.header.frames[0].bboxmin.v[j]=36;model_cache.header.frames[0].bboxmax.v[j]=44;}
 r_refdef.vieworg[1]=6;click();assert(strstr(output,"no target"));
 cl_entities[2].aw_sprite_scale=2;click();assert(strstr(output,"201388"));
 cl_entities[2].aw_sprite_scale=0;r_refdef.vieworg[1]=0;entities[3].free=false;
 /* Static aliases have model/position, no made-up edict/reference. */
 cl.num_statics=1;cl_static_entities[0].model=&alias;cl_static_entities[0].origin[0]=10;
 click();assert(strstr(output,"static 0") && strstr(output,"source id: unavailable"));cl.num_statics=0;
 /* Scene reset clears even a same-name/same-pointer map, holding an attack. */
 aw_inspect_reset();prior=traces;assert(aw_inspect_buttons(1)==0 && traces==prior);
 draws=0;aw_inspect_draw();assert(draws==1);click();assert(strstr(output,"201388"));
 /* No selection behind menus, during character UI, or while dead. */
 key_dest=key_menu;prior=traces;click();assert(traces==prior && !aw_inspect_crosshair());key_dest=key_game;
 characters=1;click();assert(traces==prior);characters=0;
 entities[1].v.health=0;click();assert(traces==prior && !aw_inspect_crosshair());entities[1].v.health=100;
 /* Missing field and narrow HUD stay safe; full identity is in the console. */
 ids[2].string=0;refs[2]._float=0;click();assert(strstr(output,"source id: unavailable"));
 vid.width=160;aw_inspect_draw();vid.width=8;aw_inspect_draw();
 command("off");output[0]=0;ent();assert(strstr(output,"entity 2") && !aw_inspect_crosshair());
 return 0;
}
