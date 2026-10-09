/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_character.h"
#include "aw_harvest_runtime.h"
#include "aw_state.h"
#include <assert.h>
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;
keydest_t key_dest=key_game;aw_character_t aw_character;
char strings[]="\0func_wall\0*1\0";char *pr_strings=strings;
int pr_edict_size=sizeof(edict_t);static edict_t edicts[4];static client_t client;
static model_t world,model;static cvar_t *mode;static int linked,missing,corrupt,subtitle;
static int sounds,sound_missing,sound_checks,empty;
static char notice[4096];
static void (*tracker)(void);static int command_argc=1,tracker_reports;static long tracker_count;
static float wall=1;static eval_t reference;
#ifndef AW_HARVEST_EXTERNAL_FIXTURE
/* The legacy fixture never requests an external model. Link the real proxy
 * implementation, but fail if this brush-only case starts loading one. */
viddef_t vid;int cl_numvisedicts;entity_t *cl_visedicts[MAX_VISEDICTS];
qboolean Mod_CanFindName(const char *name){(void)name;assert(0);return false;}
model_t *Mod_ForName(char *name,qboolean crash){(void)name;(void)crash;assert(0);return NULL;}
#endif
void Cvar_RegisterVariable(cvar_t *c){mode=c;c->value=atof(c->string);}
void Con_Printf(char *s,...){va_list args;if(!strcmp(s,"Mushrooms picked: %ld\n")){va_start(args,s);tracker_count=va_arg(args,long);va_end(args);tracker_reports++;}}
void Cmd_AddCommand(char *name,void (*fn)(void)){assert(!strcmp(name,"aw_shroomtracker"));tracker=fn;}
int Cmd_Argc(void){return command_argc;}
void S_LocalSound(char *name){assert(!strcmp(name,"pool/a031af0520e9edfa2.wav"));assert(linked && !edicts[2].v.modelindex);sounds++;}
void AW_UISubtitle(const char *who,const char *message,double seconds){(void)who;(void)seconds;strcpy(notice,message);subtitle++;}
void AW_UIPickupNotice(const char *message,double seconds){AW_UISubtitle("",message,seconds);}
edict_t *EDICT_NUM(int n){assert(n>=0 && n<4);return &edicts[n];}
eval_t *GetEdictFieldValue(edict_t *e,char *name){assert(!strcmp(name,"aw_ref"));reference._float=e==&edicts[3]?43:42;return &reference;}
void SV_LinkEdict(edict_t *e,qboolean touch){assert(e==&edicts[2]);assert(!touch);linked++;}
/* enclosing: a solid that holds the plant's centre (HARVEST-BITTERCOAST-29); a zero-length move is
 * the point test, made past the plant's own brush, not past the player. */
static int enclosing,point_tests;
trace_t SV_Move(vec3_t a,vec3_t b,vec3_t c,vec3_t d,int type,edict_t *e){
    trace_t t;memset(&t,0,sizeof(t));(void)b;(void)c;(void)type;
    if(VectorCompare(a,d)){point_tests++;assert(e==&edicts[2] || e==&edicts[1]); /* the brush plant, or the player for alias proxies */t.startsolid=enclosing;t.fraction=enclosing?0:1;return t;}
    t.fraction=wall;return t;
}
int COM_FOpenFile(char *name,FILE **out){
    FILE *f;int size;*out=NULL;
    if(!strcmp(name,"sound/pool/a031af0520e9edfa2.wav")){
        sound_checks++;if(sound_missing)return -1;
        f=tmpfile();assert(f);*out=f;return 44;
    }
    assert(!strcmp(name,"harvest-vf0000.txt"));if(missing)return -1;
    f=tmpfile();assert(f);*out=f;
    if(corrupt)fputs("bad\n",f);
    else{
        fprintf(f,"AWH2 1 1 1\n%d 0 0 0 0 synthetic_ingredient\tOriginal ingredient name\n0 0 2\n",empty?2:0);
        fputs("aw:h:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 42 *1 11 0 1 20 0 0 0 0 0 Synthetic mushroom\n",f);
    }
    size=(int)ftell(f);fputs("NEXT PAK MEMBER",f);rewind(f);return size;
}
static void reset(void){
    memset(edicts,0,sizeof(edicts));sv.edicts=edicts;sv.num_edicts=3;sv.active=true;sv.worldmodel=&world;sv.models[1]=&model;
    strcpy(world.name,"maps/vf0000.bsp");model.type=mod_brush;
    model.mins[0]=model.mins[1]=model.mins[2]=-2;model.maxs[0]=model.maxs[1]=model.maxs[2]=2;
    svs.clients=&client;svs.maxclients=1;client.edict=&edicts[1];edicts[1].v.movetype=MOVETYPE_WALK;
    edicts[2].v.classname=1;edicts[2].v.model=11;edicts[2].v.modelindex=1;edicts[2].v.origin[0]=20;
    cls.state=ca_connected;key_dest=key_game;cl.viewangles[0]=cl.viewangles[1]=cl.viewangles[2]=0;
    missing=corrupt=linked=subtitle=sounds=sound_missing=sound_checks=empty=0;notice[0]=0;wall=1;mode->value=1;AW_StateReset();AW_HarvestBegin();
}
int main(void){
    int i;char id[64];AW_HarvestInit();reset();assert(AW_HarvestProtect(&edicts[2]));
    edicts[2].v.origin[0]=21;assert(!AW_HarvestProtect(&edicts[2]));edicts[2].v.origin[0]=20;
    edicts[2].v.angles[1]=360;assert(AW_HarvestProtect(&edicts[2]));edicts[2].v.angles[1]=0;
    AW_HarvestSpawn();assert(!strcmp(AW_HarvestHint(),"Synthetic mushroom"));
    edicts[1].v.origin[0]=-100;assert(!AW_HarvestHint() && !AW_HarvestUse());edicts[1].v.origin[0]=0;
    cl.viewangles[1]=90;assert(!AW_HarvestHint() && !AW_HarvestUse());cl.viewangles[1]=0;
    wall=.1f;assert(!AW_HarvestHint() && !AW_HarvestUse());assert(point_tests);
    /* A solid between the eye and the plant hides it; one that contains the plant does not. */
    enclosing=1;assert(!strcmp(AW_HarvestHint(),"Synthetic mushroom"));enclosing=0;wall=1;point_tests=0;
    assert(!strcmp(AW_HarvestHint(),"Synthetic mushroom") && !point_tests);
    assert(AW_HarvestUse());assert(AW_StateGet(&aw_state,AW_ITEM,"synthetic_ingredient")==2);
    assert(edicts[2].v.modelindex==0 && edicts[2].v.solid==SOLID_NOT && linked==1 && subtitle==1 && sounds==1 && sound_checks==1);
    assert(!strcmp(notice,"Picked up 2 Original ingredient name."));
    assert(tracker);tracker();assert(tracker_reports==1 && tracker_count==1);
    command_argc=2;tracker();assert(tracker_reports==1);command_argc=1;
    assert(!AW_HarvestHint() && !AW_HarvestUse() && sounds==1 && sound_checks==1);
    /* Crossings reload the catalogue and a fresh brush, retaining game facts. */
    AW_HarvestBegin();edicts[2].v.modelindex=1;AW_HarvestSpawn();assert(edicts[2].v.modelindex==0 && linked==2 && sounds==1);
    reset();for(i=0;i<AW_STATE_VALUES;i++){sprintf(id,"item%d",i);assert(AW_ItemAdd(&aw_state,id,1));}
    AW_HarvestSpawn();assert(AW_HarvestUse());assert(edicts[2].v.modelindex==1 && !linked && !sounds && !sound_checks);
    reset();empty=1;AW_HarvestBegin();AW_HarvestSpawn();assert(!AW_HarvestHint() && !AW_HarvestUse());
    assert(!edicts[2].v.modelindex && !sounds && !subtitle && !sound_checks && !AW_StateGet(&aw_state,AW_ITEM,"synthetic_ingredient"));
    tracker();assert(tracker_count==0);
    assert(!AW_HarvestUse() && !sounds && !subtitle);
    /* Empty state survives return and is absent before the first input. */
    AW_HarvestBegin();edicts[2].v.modelindex=1;AW_HarvestSpawn();
    assert(!edicts[2].v.modelindex && !AW_HarvestHint() && !AW_HarvestUse() && !sounds && !subtitle);
    reset();sound_missing=1;AW_HarvestSpawn();assert(AW_HarvestUse());
    assert(!edicts[2].v.modelindex && !sounds && sound_checks==1 && AW_StateGet(&aw_state,AW_ITEM,"synthetic_ingredient")==2);
    reset();mode->value=0;AW_HarvestSpawn();assert(!AW_HarvestHint() && !AW_HarvestUse());
    reset();for(i=0;i<AW_STATE_VALUES;i++){sprintf(id,"global%d",i);assert(AW_StateSet(&aw_state,AW_GLOBAL,id,1));}
    AW_HarvestSpawn();assert(edicts[2].v.modelindex==1 && !AW_HarvestHint() && !AW_HarvestUse() && !sounds);
    reset();edicts[3]=edicts[2];sv.num_edicts=4;AW_HarvestSpawn(); /* unmatched original ref remains untouched */
    assert(AW_HarvestUse());assert(edicts[3].v.modelindex==1);
    reset();corrupt=1;AW_HarvestBegin();assert(!AW_HarvestProtect(&edicts[2]));AW_HarvestSpawn();assert(!AW_HarvestUse());
    puts("harvest binding, reach/occlusion, hide ordering and crossing passed");return 0;
}
