/* SPDX-License-Identifier: GPL-2.0-or-later
 * Execute compiled QC and the real carried-torch lifecycle in one fixture. */
#include "quakedef.h"
#include "r_local.h"
#include "aw_hand_state.h"
#include <assert.h>
#include <stddef.h>
server_t sv;
server_static_t svs;
client_static_t cls;
client_state_t cl;
dlight_t cl_dlights[MAX_DLIGHTS];
refdef_t r_refdef;
keydest_t key_dest = key_game;
dprograms_t *progs;dfunction_t *pr_functions;char *pr_strings;
ddef_t *pr_globaldefs,*pr_fielddefs;dstatement_t *pr_statements;
globalvars_t *pr_global_struct;float *pr_globals;int pr_edict_size;
int com_filesize;
/* Indices come from the engine's actual builtin table in the Python runner. */
static builtin_t builtins[TEST_FLOOR_BUILTIN_INDEX+1];
builtin_t *pr_builtins=builtins;int pr_numbuiltins=sizeof(builtins)/sizeof(builtins[0]);
static byte assets[716];
static model_t torch_model_fixture,arrival_torch_model;
static model_t *active_torch_model=&torch_model_fixture;
static void (*toggle_torch)(void);
static int metadata_warnings;
static cvar_t *radius_setting,*flame_setting;
static int setting_argc=1;static char *setting_value="";
static void (*set_radius)(void),(*set_flame)(void);
int Cmd_Argc(void){return setting_argc;}
char *Cmd_Argv(int n){return n==1?setting_value:"";}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void Cvar_RegisterVariable(cvar_t *c){c->value=atof(c->string);if(!strcmp(c->name,"aw_torch_radius"))radius_setting=c;else if(!strcmp(c->name,"aw_torch_flame_style"))flame_setting=c;}
void Cvar_SetValue(char *name,float value){if(!strcmp(name,"aw_torch_radius"))radius_setting->value=value;else flame_setting->value=value;}
int AW_UIColor(int r,int g,int b){assert(r==255 && g==244 && b==214);return 254;}

void Con_Printf(char *fmt,...){}
void Host_Error(char *fmt,...){assert(0);abort();}
void Sys_Error(char *fmt,...){assert(0);abort();}
void ED_Print(edict_t *e){assert(0);}
char *PR_GlobalString(int offset){return "test";}
char *PR_GlobalStringNoContents(int offset){return "test";}
int AW_GalleryActive(void){return 0;}
int AW_TorchTestActive(void){return 0;}
int AW_IntroImpulse(int impulse){return impulse;}
void AW_GuardTorchLoadAssets(const byte *data){assert(data==assets);}
void AW_GuardTorchInit(void){}
void AW_GuardTorchUpdate(void){}
void AW_LampInit(void){}void AW_LampUpdate(void){}
void Cmd_AddCommand(char *name,void (*fn)(void)){
    if(!strcmp(name,"aw_torch_radius_set"))set_radius=fn;
    else if(!strcmp(name,"aw_torch_flame_set"))set_flame=fn;
    else if(!strcmp(name,"aw_torch_strength_set")){}
    else if(!strcmp(name,"aw_headlamp_set")){}
    else {assert(!strcmp(name,"aw_torch"));toggle_torch=fn;}
}
byte *COM_LoadHunkFile(char *name){
    assert(!strcmp(name,"gfx/torch.awt"));com_filesize=sizeof(assets);return assets;
}
model_t *Mod_ForName(char *name,qboolean crash){
    assert(!strcmp(name,"progs/v_torch.mdl"));return active_torch_model;
}
dlight_t *CL_AllocDlight(int key){cl_dlights[0].key=key;return &cl_dlights[0];}
static void rint_builtin(void){
    float value=G_FLOAT(OFS_PARM0);
    G_FLOAT(OFS_RETURN)=value>0?(int)(value+.5f):(int)(value-.5f);
}
static void floor_builtin(void){G_FLOAT(OFS_RETURN)=floor(G_FLOAT(OFS_PARM0));}
static void sprint_builtin(void){
    assert(!strcmp(G_STRING(OFS_PARM1),"Hands unavailable: invalid animation timings; rebuild converted maps.\n"));
    metadata_warnings++;
}
static float *field(edict_t *e,const char *name)
{
    int i;
    for(i=0;i<progs->numfielddefs;i++)if(!strcmp(pr_strings+pr_fielddefs[i].s_name,name))
        return (float *)&e->v+pr_fielddefs[i].ofs;
    assert(0);return NULL;
}
eval_t *GetEdictFieldValue(edict_t *e,char *name){return (eval_t *)field(e,name);}
static void hands_model(edict_t *p){
    assert(!strcmp(pr_strings+p->v.weaponmodel,"progs/v_nord.mdl"));
}
/* ED_NewString binds copied model identity into the destination VM strings. */
char *ED_NewString(char *text){
    int i;for(i=0;i<progs->numstrings;i++)if(!strcmp(pr_strings+i,text))return pr_strings+i;
    assert(0);return NULL;
}
/* Quarter-frame samples catch rounding into a different sequence before
 * its timer expires; all four authored sequences retain their exact bounds. */
static void animation_boundaries(edict_t *p,edict_t *world,int fn)
{
    static const int first[]={8,0,18,14},count[]={6,8,10,4};
    static const char *timing[]={"aw_hand_draw","aw_hand_idle","aw_hand_punch","aw_hand_lower"};
    static const float duration[]={.4f,2.666667938232422f,.5f,.3f};
    int state,sample,tick;
    for(state=0;state<4;state++)*field(world,timing[state])=duration[state];
    for(state=0;state<4;state++)for(sample=0;sample<count[state]*4;sample++){
        memset(&p->v,0,progs->entityfields*4);p->v.health=100;
        *field(p,"aw_hand_state")=state+1;*field(p,"aw_hand_goal")=state!=3;
        *field(p,"aw_hand_started")=32;
        pr_global_struct->time=32+duration[state]*(sample+.25f)/(count[state]*4);
        PR_ExecuteProgram(fn);hands_model(p);
        if(p->v.weaponframe!=first[state]+sample/4){
            fprintf(stderr,"Hand sequence %d sample %d: frame %.9g expected %d\n",
                state+1,sample,p->v.weaponframe,first[state]+sample/4);
            assert(0);
        }
    }
    memset(&p->v,0,progs->entityfields*4);p->v.health=100;
    *field(p,"aw_hand_state")=2;*field(p,"aw_hand_goal")=1;
    for(tick=0;tick<2000;tick++){
        pr_global_struct->time=tick*.02f;PR_ExecuteProgram(fn);hands_model(p);
        assert(p->v.weaponframe>=0 && p->v.weaponframe<8);
        assert(*field(p,"aw_hand_state")==2);
    }
}
static void transition_states(edict_t *p,int fn)
{
    static const int states[6]={0,1,2,2,3,4};
    static const int goals[6]={0,1,1,1,1,0};
    static const int torches[6]={0,1,1,0,0,0};
    int i,frame,expected,torch_frame;float radius;double torch_time;
    aw_hand_snapshot_t saved;
    sv.model_precache[1]="progs/v_nord.mdl";arrival_torch_model.type=mod_alias;
    for(i=0;i<6;i++){
        memset(&p->v,0,progs->entityfields*4);p->v.health=100;p->v.button0=1;
        *field(p,"aw_hand_state")=states[i];*field(p,"aw_hand_goal")=goals[i];
        *field(p,"aw_torch")=torches[i];*field(p,"aw_attack_latched")=1;
        *field(p,"aw_hand_started")=99.89f;pr_global_struct->time=100;
        PR_ExecuteProgram(fn);frame=p->v.weaponframe;
        active_torch_model=&torch_model_fixture;AW_TorchResetAnimation();cl.time=123.456;torch_time=AW_TorchAnimationTime();
        torch_frame=AW_TorchFrame();AW_TorchUpdate();AW_TorchViewModel();radius=cl_dlights[0].radius;
        assert(AW_HandSnapshotCapture(&saved,p,100));
        pr_global_struct->time=100.03125f;PR_ExecuteProgram(fn);expected=p->v.weaponframe;
        /* Host_Spawn_f really zeroes all QC fields, including model and timer. */
        memset(&p->v,0,progs->entityfields*4);p->v.health=100;
        memset(&cl.viewent,0,sizeof(cl.viewent));memset(cl_dlights,0,sizeof(cl_dlights));
        active_torch_model=&arrival_torch_model;cl.time=2;pr_global_struct->time=2;
        assert(AW_HandSnapshotRestore(&saved,p,2));AW_TorchRestoreAnimation(torch_time);
        assert(*field(p,"aw_hand_state")==states[i] && *field(p,"aw_hand_goal")==goals[i]);
        assert(*field(p,"aw_torch")==torches[i] && *field(p,"aw_attack_latched")==1);
        assert(p->v.weaponframe==frame);
        if(states[i])hands_model(p);else assert(!p->v.weaponmodel);
        assert(AW_TorchEquipped()==(states[i]==2 && torches[i]));
        AW_TorchUpdate();assert(cl_dlights[0].radius==radius);
        assert(AW_TorchFrame()==torch_frame);
        if(AW_TorchEquipped()){
            AW_TorchViewModel();assert(cl.viewent.model==&arrival_torch_model);
            assert(cl.viewent.frame==torch_frame); /* Before the first QC tick. */
        }
        p->v.button0=1;PR_ExecuteProgram(fn);
        assert(*field(p,"aw_hand_state")==states[i] && p->v.weaponframe==frame);
        pr_global_struct->time=2.03125f;PR_ExecuteProgram(fn);assert(p->v.weaponframe==expected);
        /* Repeated crossings rebase the same phase without restarting it. */
        assert(AW_HandSnapshotCapture(&saved,p,2.03125));
        assert(AW_HandSnapshotRestore(&saved,p,7));
        pr_global_struct->time=7;PR_ExecuteProgram(fn);assert(p->v.weaponframe==expected);
    }
    /* Long-held ready state must not lose equipment at the handoff, even
     * when its last QC idle timestamp predates a long simulation pause. */
    memset(&p->v,0,progs->entityfields*4);p->v.health=100;p->v.button0=1;
    *field(p,"aw_hand_goal")=1;*field(p,"aw_hand_state")=2;*field(p,"aw_torch")=1;
    *field(p,"aw_attack_latched")=1;*field(p,"aw_hand_started")=.25f;
    p->v.weaponmodel=ED_NewString("progs/v_nord.mdl")-pr_strings;p->v.weaponframe=3;
    assert(AW_HandSnapshotCapture(&saved,p,121));assert(saved.age==120.75);
    pr_global_struct->time=121;PR_ExecuteProgram(fn);expected=p->v.weaponframe;
    memset(&p->v,0,progs->entityfields*4);p->v.health=100;
    assert(AW_HandSnapshotRestore(&saved,p,2));
    assert(p->v.weaponframe==3 && *field(p,"aw_hand_started")== -118.75f);
    assert(AW_TorchEquipped());AW_TorchUpdate();assert(cl_dlights[0].radius>0);
    p->v.button0=1;pr_global_struct->time=2;PR_ExecuteProgram(fn);
    assert(*field(p,"aw_hand_state")==2 && p->v.weaponframe==expected && AW_TorchEquipped());
    /* Equipment intent is independent at the capture boundary. QC decides
     * when lowering/death consumes it; the transfer must not erase the bit. */
    *field(p,"aw_hand_goal")=0;*field(p,"aw_hand_state")=4;*field(p,"aw_torch")=1;
    *field(p,"aw_hand_started")=7;
    assert(AW_HandSnapshotCapture(&saved,p,7));*field(p,"aw_torch")=0;
    assert(AW_HandSnapshotRestore(&saved,p,2));assert(*field(p,"aw_torch")==1);
    /* Invalid source state and destination model identity fail closed. */
    *field(p,"aw_hand_state")=9;assert(!AW_HandSnapshotCapture(&saved,p,2));
    assert(!AW_HandSnapshotRestore(&saved,p,2));
    *field(p,"aw_hand_state")=2;*field(p,"aw_hand_started")=1.9f;
    assert(AW_HandSnapshotCapture(&saved,p,2));sv.model_precache[1]=NULL;
    assert(!AW_HandSnapshotRestore(&saved,p,2));sv.model_precache[1]="progs/v_nord.mdl";
    active_torch_model=&torch_model_fixture;
    AW_TorchResetAnimation();assert(AW_TorchAnimationTime()==cl.time);
}
int main(int argc,char **argv)
{
    FILE *f;byte *raw;long size;int fn,i,before,baseline;edict_t *p,*world;
    client_t client;
    assert(argc==2 || argc==3);baseline=argc==3 && !strcmp(argv[2],"baseline");
    f=fopen(argv[1],"rb");assert(f);fseek(f,0,SEEK_END);size=ftell(f);rewind(f);
    assert(size>sizeof(dprograms_t) && size<1048576);raw=malloc(size);assert(raw);
    assert(fread(raw,1,size,f)==size);fclose(f);progs=(dprograms_t *)raw;
    assert(progs->version==6);
    pr_functions=(dfunction_t *)(raw+progs->ofs_functions);pr_strings=(char *)(raw+progs->ofs_strings);
    pr_fielddefs=(ddef_t *)(raw+progs->ofs_fielddefs);pr_statements=(dstatement_t *)(raw+progs->ofs_statements);
    pr_globals=(float *)(raw+progs->ofs_globals);pr_global_struct=(globalvars_t *)pr_globals;
    pr_edict_size=(offsetof(edict_t,v)+progs->entityfields*4+7)&~7;
    sv.edicts=calloc(2,pr_edict_size);assert(sv.edicts);world=sv.edicts;p=NEXT_EDICT(world);
    pr_global_struct->self=EDICT_TO_PROG(p);builtins[TEST_RINT_BUILTIN_INDEX]=rint_builtin;builtins[TEST_FLOOR_BUILTIN_INDEX]=floor_builtin;builtins[24]=sprint_builtin;
    fn=0;for(i=1;i<progs->numfunctions;i++)if(!strcmp(pr_strings+pr_functions[i].s_name,"aw_hands_update"))fn=i;
    assert(fn);p->v.health=100;
    memset(&client,0,sizeof(client));client.edict=p;svs.clients=&client;svs.maxclients=1;
    sv.active=true;cls.state=ca_connected;
    memcpy(assets,"AWT1",4);assets[5]=8;assets[7]=16;assets[10]=3;assets[11]=232;
    torch_model_fixture.type=mod_alias;AW_TorchInit();AW_TorchLoadAssets();assert(toggle_torch);

    /* Released region payload: no derived worldspawn timings. */
    p->v.impulse=202;PR_ExecuteProgram(fn);
    if(baseline){
        assert(*field(p,"aw_hand_goal")==1 && *field(p,"aw_hand_state")==1);
        assert(!pr_strings[p->v.weaponmodel]);toggle_torch();
        assert(*field(p,"aw_torch")==1 && !AW_TorchEquipped());
        pr_global_struct->time=10;PR_ExecuteProgram(fn);AW_TorchUpdate();
        assert(*field(p,"aw_hand_state")==1 && !pr_strings[p->v.weaponmodel]);
        assert(cl_dlights[0].radius==0);
        puts("Baseline reproduced: F stays invisible; V accepts on but never equips model/light.");
        free(sv.edicts);free(raw);return 0;
    }
    assert(!*field(p,"aw_hand_goal") && !*field(p,"aw_hand_state") && !*field(p,"aw_torch"));
    assert(!pr_strings[p->v.weaponmodel] && metadata_warnings==1);
    PR_ExecuteProgram(fn);assert(metadata_warnings==1); /* no per-frame warning flood */
    toggle_torch();assert(!AW_TorchEquipped() && !*field(p,"aw_torch"));

    *field(world,"aw_hand_draw")=.4;*field(world,"aw_hand_idle")=2;
    *field(world,"aw_hand_lower")=.3;*field(world,"aw_hand_punch")=.5;
    p->v.impulse=202;PR_ExecuteProgram(fn);
    assert(*field(p,"aw_hand_goal")==1 && *field(p,"aw_hand_state")==1);hands_model(p);
    toggle_torch();assert(*field(p,"aw_torch")==1 && !AW_TorchEquipped());
    pr_global_struct->time=.6;PR_ExecuteProgram(fn);assert(*field(p,"aw_hand_state")==2);hands_model(p);
    assert(AW_TorchEquipped());AW_TorchUpdate();
    assert(cl_dlights[0].radius>=189 && cl_dlights[0].radius<=196);
    AW_TorchViewModel();assert(cl.viewent.model==&torch_model_fixture);
    p->v.button0=1;PR_ExecuteProgram(fn);
    assert(*field(p,"aw_hand_state")==2 && *field(p,"aw_torch")==1);
    toggle_torch();AW_TorchUpdate();assert(!AW_TorchEquipped() && cl_dlights[0].radius==0);
    toggle_torch();AW_TorchUpdate();assert(AW_TorchEquipped() && cl_dlights[0].radius>0);
    p->v.impulse=202;PR_ExecuteProgram(fn);AW_TorchUpdate();
    assert(!*field(p,"aw_hand_goal") && !*field(p,"aw_torch") && *field(p,"aw_hand_state")==4);
    assert(cl_dlights[0].radius==0);
    pr_global_struct->time=1;PR_ExecuteProgram(fn);
    assert(!*field(p,"aw_hand_state") && !pr_strings[p->v.weaponmodel]);
    p->v.button0=0;p->v.impulse=202;PR_ExecuteProgram(fn);pr_global_struct->time=2;PR_ExecuteProgram(fn);
    p->v.button0=1;PR_ExecuteProgram(fn);assert(*field(p,"aw_hand_state")==3);
    *field(p,"aw_torch")=1;p->v.health=0;PR_ExecuteProgram(fn);assert(!*field(p,"aw_torch"));
    animation_boundaries(p,world,fn);
    transition_states(p,fn);
    /* A resumed/transitioned state with a missing idle stamp must be rejected
     * before raise completion can divide by an invalid next-state duration. */
    p->v.health=100;*field(p,"aw_hand_goal")=1;*field(p,"aw_hand_state")=1;
    *field(p,"aw_torch")=1;*field(world,"aw_hand_idle")=0;
    before=metadata_warnings;PR_ExecuteProgram(fn);AW_TorchUpdate();
    assert(!*field(p,"aw_hand_state") && !*field(p,"aw_torch") && !pr_strings[p->v.weaponmodel]);
    assert(cl_dlights[0].radius==0 && metadata_warnings==before+1);
    puts("QC/torch lifecycle passed: missing metadata, raise, V toggle, viewmodel, light, lower, punch, death and zeroed-VM handoff phases.");
    free(sv.edicts);free(raw);return 0;
}
