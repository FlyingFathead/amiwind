/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "r_local.h"
#include "aw_state.h"
#include <assert.h>
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;
entity_t cl_entities[MAX_EDICTS],*cl_visedicts[MAX_VISEDICTS];int cl_numvisedicts;
dlight_t cl_dlights[MAX_DLIGHTS];viddef_t vid;refdef_t r_refdef;
vec3_t vpn,vup,vright;float aliasxcenter,aliasycenter,aliasxscale,aliasyscale;
short *d_pzbuffer;unsigned int d_zwidth;aw_state_t aw_state;
cvar_t r_drawentities={"r_drawentities","1",false,false,1};
char strings[]="\0aw_npc\0aw_corpse\0guard_a\0guard_b\0ordinary_npc\0";char *pr_strings=strings;
static edict_t actors[40];static eval_t source[40];
static byte registry[20000],torch[716],pixels[336*210];static short depths[320*200];
static int registry_size,argc_=1,clock_ms,exterior=1,gallery,liquid,blocked_x=-1;
static const char *argument="";static cvar_t *cycle;static void(*cmd)(void);
static model_t base,body,held;static int model_loads,broken_model;
int hunk_size=8*1024*1024,hunk_low_used,hunk_high_used;
void *Cache_Check(cache_user_t *c){return c->data;}
static void put16(byte*p,unsigned n){p[0]=n>>8;p[1]=n;}
static void put32(byte*p,int n){unsigned v=(unsigned)n;p[0]=v>>24;p[1]=v>>16;p[2]=v>>8;p[3]=v;}
static int add_record(int at,const char *id,int automatic,int frames)
{
    int i;byte*p=registry+at;memset(p,0,260+frames*12);
    strcpy((char*)p,id);strcpy((char*)p+64,"progs/original.mdl");strcpy((char*)p+128,"progs/heldbody.mdl");
    strcpy((char*)p+192,"progs/heldtorch.mdl");put16(p+256,frames);put16(p+258,automatic);
    for(i=0;i<frames;i++){put32(p+260+i*12+8,25*65536);}
    put32(p+260+7*12,2*65536);put32(p+260+7*12+4,3*65536);
    return at+260+frames*12;
}
static void make_registry(int frames)
{
    memset(registry,0,sizeof registry);memcpy(registry,"AWG1",4);put16(registry+4,2);
    registry_size=add_record(8,"guard_a",1,frames);registry_size=add_record(registry_size,"guard_b",0,frames);
}
int COM_FOpenFile(char *name,FILE **file){assert(!strcmp(name,"gfx/guard-torches.awg"));*file=tmpfile();assert(*file);assert(fwrite(registry,1,registry_size,*file)==(size_t)registry_size);rewind(*file);return registry_size;}
void Cvar_RegisterVariable(cvar_t *v){cycle=v;v->value=1;}
void Cmd_AddCommand(char*n,void(*f)(void)){assert(!strcmp(n,"aw_guardtorch"));cmd=f;}
int Cmd_Argc(void){return argc_;}char *Cmd_Argv(int n){assert(n==1);return (char*)argument;}
void Con_Printf(char*f,...){}
int Q_strcasecmp(char*a,char*b){while(*a && *b){int x=*a++,y=*b++;if(x>='A'&&x<='Z')x+=32;if(y>='A'&&y<='Z')y+=32;if(x!=y)return x-y;}return *a-*b;}
int AW_ClockEnsure(void){return 1;}
int32_t AW_StateGet(const aw_state_t*s,int kind,const char*id){assert(kind==AW_GLOBAL && !strcmp(id,"amiwind:clock:ms"));return clock_ms;}
int R_SkyExterior(void){return exterior;}int AW_GalleryActive(void){return gallery;}
edict_t *EDICT_NUM(int n){assert(n>=0 && n<40);return &actors[n];}
eval_t *GetEdictFieldValue(edict_t*e,char*n){assert(!strcmp(n,"aw_source_id"));return &source[e-actors];}
int SV_PointContents(vec3_t p){return liquid?CONTENTS_WATER:CONTENTS_EMPTY;}
trace_t SV_Move(vec3_t a,vec3_t lo,vec3_t hi,vec3_t b,int type,edict_t*skip){trace_t t;assert(type==MOVE_NOMONSTERS);assert(skip>=actors && skip<actors+40);memset(&t,0,sizeof t);t.fraction=(int)a[0]==blocked_x?0:1;return t;}
model_t *Mod_ForName(char*name,qboolean crash){model_t *m;assert(!crash);model_loads++;if(!strcmp(name,"progs/heldbody.mdl")){if(broken_model)return NULL;m=&body;}else{assert(!strcmp(name,"progs/heldtorch.mdl"));m=&held;}strcpy(m->name,name);m->cache.data=m;m->needload=false;return m;}
dlight_t *CL_AllocDlight(int key){int i;for(i=0;i<MAX_DLIGHTS;i++)if(cl_dlights[i].key==key)break;if(i==MAX_DLIGHTS){for(i=0;i<MAX_DLIGHTS;i++)if(!cl_dlights[i].radius)break;}assert(i<MAX_DLIGHTS);memset(&cl_dlights[i],0,sizeof cl_dlights[i]);cl_dlights[i].key=key;return &cl_dlights[i];}
static int lights(void){int i,n=0;for(i=0;i<MAX_DLIGHTS;i++)if(cl_dlights[i].radius>0 && cl_dlights[i].key<0)n++;return n;}
static int light_x(int x){int i;for(i=0;i<MAX_DLIGHTS;i++)if(cl_dlights[i].radius>0 && (int)cl_dlights[i].origin[0]==x)return 1;return 0;}
static void set_command(const char *s){argc_=2;argument=s;cmd();argc_=1;}
static void scene(int count){int i;cl_numvisedicts=count;for(i=1;i<=count;i++){cl_visedicts[i-1]=&cl_entities[i];}}
static void npc(int i,int id,int x){entity_t*e=&cl_entities[i];memset(e,0,sizeof *e);e->model=&base;e->origin[0]=x;actors[i].v.classname=1;source[i].string=id;actors[i].v.origin[0]=x;}
static int changed(void){int i,n=0;for(i=0;i<320*200;i++)if(pixels[(i/320)*336+i%320])n++;return n;}
int main(void)
{
    int i,oldloads;
    strcpy(base.name,"progs/original.mdl");base.type=body.type=held.type=mod_alias;base.numframes=body.numframes=held.numframes=8;
    sv.active=1;sv.num_edicts=40;svs.maxclients=1;cls.state=ca_connected;cl.time=1;
    make_registry(8);for(i=204;i<716;i+=2){torch[i]=220;torch[i+1]=255;}
    AW_GuardTorchInit();assert(cycle && cycle->archive && cycle->value==1 && cmd);
    AW_GuardTorchLoadAssets(torch);npc(1,18,100);npc(2,18,80);npc(3,18,120);npc(4,26,140);
    /* Actual string offsets are bound, never inferred from display names. */
    source[1].string=source[2].string=source[3].string=(int)(strstr(strings+18,"guard_a")-strings);
    source[4].string=(int)(strstr(strings+26,"guard_b")-strings);
    assert(source[1].string>0 && source[4].string>0);
    /* Mixed casing applies to every guard type, both auto and forced equipment. */
    strings[source[1].string]='G';strings[source[4].string]='G';
    scene(4);clock_ms=72000000;AW_GuardTorchUpdate();assert(!lights() && cl_numvisedicts==4);
    clock_ms++;AW_GuardTorchUpdate();assert(lights()==2 && cl_numvisedicts==7);
    assert(light_x(80)&&light_x(100)&&!light_x(120));assert(cl_visedicts[0]->model==&body);
    assert(cl_entities[1].model==&base && actors[1].v.frame==0); /* No server/base mutation. */
    assert(cl_visedicts[0]->origin[0]==100 && cl_visedicts[4]->model==&held);
    oldloads=model_loads;AW_GuardTorchUpdate();assert(model_loads==oldloads && cl_numvisedicts==7);
    /* Mod_ClearAll leaves cached aliases in unreferenced table slots. A
     * reused body slot can contain another valid 8-frame actor: cache and
     * frame counts alone must never admit it as guard equipment. */
    strcpy(body.name,"progs/unrelated_actor.mdl");body.needload=true;
    strcpy(held.name,"progs/unrelated_prop.mdl");held.needload=true;
    AW_GuardTorchUpdate();
    assert(!strcmp(cl_visedicts[0]->model->name,"progs/heldbody.mdl"));
    assert(!strcmp(cl_visedicts[4]->model->name,"progs/heldtorch.mdl"));
    /* Even without slot reuse, visiting another map marks the surviving
     * cache entries unreferenced. Optional companions must retain their
     * model table slots before unrelated models are loaded this frame. */
    body.needload=held.needload=(qboolean)2;oldloads=model_loads;
    AW_GuardTorchUpdate();assert(!body.needload && !held.needload);
    assert(model_loads==oldloads+2);
    oldloads=model_loads;AW_GuardTorchUpdate();assert(model_loads==oldloads);
    blocked_x=80;AW_GuardTorchUpdate();assert(lights()==2 && !light_x(80)&&light_x(100)&&light_x(120));blocked_x=-1;
    clock_ms=21600000;AW_GuardTorchUpdate();assert(!lights() && cl_numvisedicts==4);
    clock_ms--;AW_GuardTorchUpdate();assert(lights()==2);cycle->value=0;AW_GuardTorchUpdate();assert(!lights());
    set_command("on");AW_GuardTorchUpdate();assert(cl_numvisedicts==8 && lights()==2);
    set_command("garbage");AW_GuardTorchUpdate();assert(cl_numvisedicts==8);
    set_command("off");AW_GuardTorchUpdate();assert(!lights() && cl_numvisedicts==4);
    for(i=0;i<3;i++){const char *on[]={"1","true","ON"};const char*off[]={"0","false","OFF"};set_command(on[i]);AW_GuardTorchUpdate();assert(lights()==2);set_command(off[i]);AW_GuardTorchUpdate();assert(!lights());}
    cycle->value=1;set_command("auto");exterior=0;AW_GuardTorchUpdate();assert(!lights());
    set_command("on");AW_GuardTorchUpdate();assert(lights()==2);exterior=1;
    liquid=1;AW_GuardTorchUpdate();assert(!lights()&&cl_numvisedicts==4);liquid=0;
    actors[1].v.deadflag=1;actors[2].v.classname=8;actors[3].v.waterlevel=2;
    AW_GuardTorchUpdate();assert(cl_numvisedicts==5);actors[1].v.deadflag=0;actors[2].v.classname=1;actors[3].v.waterlevel=0;
    set_command("auto");actors[1].v.enemy=1;AW_GuardTorchUpdate();assert(cl_numvisedicts==6);actors[1].v.enemy=0;
    gallery=1;AW_GuardTorchUpdate();assert(!lights());gallery=0;
    /* Original actor frame remains the paired companion/equipment frame. */
    cl_entities[1].frame=7;cl_entities[1].angles[1]=90;AW_GuardTorchUpdate();assert(cl_visedicts[0]->frame==7 && cl_visedicts[4]->frame==7);
    assert(light_x(97));cl_entities[1].angles[1]=0;
    cl_entities[1].frame=8;AW_GuardTorchUpdate();assert(cl_visedicts[0]==&cl_entities[1]);cl_entities[1].frame=0;
    /* The original flame is visible only where real scene depth permits it. */
    scene(1);AW_GuardTorchUpdate();vid.width=320;vid.height=200;vid.rowbytes=336;vid.buffer=pixels;
    r_refdef.vrect.x=8;r_refdef.vrect.y=5;r_refdef.vrect.width=304;r_refdef.vrect.height=190;
    d_pzbuffer=depths;d_zwidth=320;vpn[0]=1;vright[1]=1;vup[2]=1;
    aliasxcenter=160;aliasycenter=100;aliasxscale=aliasyscale=160;
    memset(pixels,0,sizeof pixels);memset(depths,0,sizeof depths);AW_GuardTorchDraw();assert(changed()>0);
    memset(pixels,0,sizeof pixels);for(i=0;i<320*200;i++)depths[i]=32767;AW_GuardTorchDraw();assert(!changed());
    for(i=0;i<200;i++)assert(!pixels[i*336+320]);
    /* Visibility capacity and unrelated dynamic lights remain bounded. */
    cl_dlights[MAX_DLIGHTS-1].key=700;cl_dlights[MAX_DLIGHTS-1].radius=30;
    for(i=1;i<=33;i++)npc(i,18,80+i);scene(33);AW_GuardTorchUpdate();
    assert(cl_numvisedicts==65 && lights()==2 && cl_dlights[MAX_DLIGHTS-1].radius==30);
    r_drawentities.value=0;AW_GuardTorchUpdate();assert(cl_numvisedicts==33 && !lights());r_drawentities.value=1;
    scene(1);clock_ms=-1;AW_GuardTorchUpdate();assert(!lights());clock_ms=86400000;AW_GuardTorchUpdate();assert(!lights());clock_ms=82800000;
    /* Full21frame companions support gait/talk without an idle-only switch. */
    make_registry(21);body.numframes=held.numframes=21;AW_GuardTorchLoadAssets(torch);
    cl_entities[1].frame=20;AW_GuardTorchUpdate();assert(cl_visedicts[0]->model==&body && cl_visedicts[0]->frame==20);
    /* Eviction falls back before the renderer can lazily reload a proxy. */
    body.cache.data=NULL;
    assert(AW_GuardTorchEntity(cl_visedicts[0])==&cl_entities[1]);
    assert(!AW_GuardTorchEntity(cl_visedicts[1]));assert(!lights());
    /* Low hunk clearance never enters Mod_ForName; the base actor survives. */
    hunk_size=1024*1024;oldloads=model_loads;AW_GuardTorchUpdate();
    assert(cl_numvisedicts==1 && model_loads==oldloads && !lights());
    hunk_size=8*1024*1024;cl.time+=4;AW_GuardTorchUpdate();assert(cl_numvisedicts==2);
    /* Malformed registry/model, truncation and extra bytes all fail closed. */
    registry_size--;AW_GuardTorchLoadAssets(torch);AW_GuardTorchUpdate();assert(cl_numvisedicts==1&&!lights());
    make_registry(8);registry_size++;AW_GuardTorchLoadAssets(torch);AW_GuardTorchUpdate();assert(cl_numvisedicts==1);
    make_registry(8);registry[8+64+6]='.';registry[8+64+7]='.';AW_GuardTorchLoadAssets(torch);AW_GuardTorchUpdate();assert(cl_numvisedicts==1);
    make_registry(8);put32(registry+8+260,129*65536);AW_GuardTorchLoadAssets(torch);AW_GuardTorchUpdate();assert(cl_numvisedicts==1);
    make_registry(8);put16(registry+8+256,22);AW_GuardTorchLoadAssets(torch);AW_GuardTorchUpdate();assert(cl_numvisedicts==1);
    make_registry(8);put16(registry+8+258,2);AW_GuardTorchLoadAssets(torch);AW_GuardTorchUpdate();assert(cl_numvisedicts==1);
    make_registry(8);strcpy((char*)registry+8+356,"guard_a");AW_GuardTorchLoadAssets(torch);AW_GuardTorchUpdate();assert(cl_numvisedicts==1);
    make_registry(8);strcpy((char*)registry+8+356,"GuArD_A");AW_GuardTorchLoadAssets(torch);AW_GuardTorchUpdate();assert(cl_numvisedicts==1);
    make_registry(8);registry[8+63]=1;AW_GuardTorchLoadAssets(torch);AW_GuardTorchUpdate();assert(cl_numvisedicts==1);
    make_registry(8);put16(registry+4,33);AW_GuardTorchLoadAssets(torch);AW_GuardTorchUpdate();assert(cl_numvisedicts==1);
    make_registry(8);broken_model=1;AW_GuardTorchLoadAssets(torch);cl_entities[1].frame=0;AW_GuardTorchUpdate();assert(cl_numvisedicts==1);
    broken_model=0;body.numframes=held.numframes=8;AW_GuardTorchLoadAssets(NULL);AW_GuardTorchUpdate();assert(cl_numvisedicts==1);
    puts("guard torch registry, clock, pose, eligibility, bounded lights and scene depth passed");return 0;
}
