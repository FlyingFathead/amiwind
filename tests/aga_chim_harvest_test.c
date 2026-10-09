/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM: a town running its frame map keeps its per-region harvest catalogues
 * (harvest-<region map>.txt): the catalogue follows the region the player is
 * in, without a map change, and a legacy map is left alone. */
#include "quakedef.h"
#include "aw_character.h"
#include "aw_harvest.h"
#include "aw_harvest_runtime.h"
#include "aw_region.h"
#include "aw_state.h"
#include <assert.h>
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;
keydest_t key_dest=key_game;aw_character_t aw_character;
char strings[]="\0func_wall\0*1\0";char *pr_strings=strings;
int pr_edict_size=sizeof(edict_t);static edict_t edicts[4];static client_t client;
static model_t world,model;static int opens[2],linked;static eval_t reference;
viddef_t vid;int cl_numvisedicts;entity_t *cl_visedicts[MAX_VISEDICTS];
extern const char *(*aw_chim_town_map)(const char *);
/* This fixture's catalogues are brush-bound: no external model is loaded. */
qboolean Mod_CanFindName(const char *name){(void)name;assert(0);return false;}
model_t *Mod_ForName(char *name,qboolean crash){(void)name;(void)crash;assert(0);return NULL;}
void Cvar_RegisterVariable(cvar_t *c){c->value=atof(c->string);}
void Con_Printf(char *s,...){(void)s;}
void Cmd_AddCommand(char *name,void (*fn)(void)){(void)name;(void)fn;}
int Cmd_Argc(void){return 1;}
void S_LocalSound(char *name){(void)name;}
void AW_UISubtitle(const char *who,const char *message,double seconds){(void)who;(void)message;(void)seconds;}
void AW_UIPickupNotice(const char *message,double seconds){(void)message;(void)seconds;}
edict_t *EDICT_NUM(int n){assert(n>=0 && n<4);return &edicts[n];}
eval_t *GetEdictFieldValue(edict_t *e,char *name){assert(!strcmp(name,"aw_ref"));reference._float=e==&edicts[3]?43:42;return &reference;}
void SV_LinkEdict(edict_t *e,qboolean touch){(void)e;(void)touch;linked++;}
trace_t SV_Move(vec3_t a,vec3_t b,vec3_t c,vec3_t d,int type,edict_t *e){trace_t t;memset(&t,0,sizeof(t));t.fraction=1;return t;}
static const char *town_map(const char *town){return !strcmp(town,"balmora")?"maps/balmora-chim.bsp":NULL;}
int COM_FOpenFile(char *name,FILE **out){
    FILE *f;int size,k;*out=NULL;
    if(!strcmp(name,"balmora-regions.txt")){
        f=tmpfile();assert(f);*out=f;
        fputs("AWBR1 4 96 540 50 50 30 90 -500 12 20 66\n"
              "bm000 -512 -512 1024 1024 -512 -512 2048 2048\n"
              "bm001 1024 0 2048 1024 0 0 2048 2048\n"
              "bm002 0 1024 1024 2048 0 0 2048 2048\n"
              "bm003 1024 1024 2048 2048 0 0 2048 2048\n",f);
        size=(int)ftell(f);rewind(f);return size;
    }
    if(!strcmp(name,"harvest-bm000.txt"))k=0;
    else if(!strcmp(name,"harvest-bm001.txt"))k=1;
    else return -1;	/* no catalogue for the frame map or other regions */
    opens[k]++;
    f=tmpfile();assert(f);*out=f;
    fputs("AWH2 1 1 1\n0 0 0 0 0 synthetic_ingredient\tOriginal ingredient name\n0 0 2\n",f);
    if(k==0)fputs("aw:h:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 42 *1 11 0 1 20 0 0 0 0 0 Region 0 mushroom\n",f);
    else fputs("aw:h:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb 43 *1 11 0 1 1100 0 0 0 0 0 Region 1 mushroom\n",f);
    size=(int)ftell(f);rewind(f);return size;
}
int main(void){
    vec3_t p={50,50,0};
    typedef char limits[AW_HARVEST_NODES==64 && AW_HARVEST_EDGES==256 && AW_HARVEST_MODELS==8 ? 1 : -1];
    (void)sizeof(limits);
    AW_HarvestInit();AW_StateReset();
    sv.edicts=edicts;sv.num_edicts=4;sv.active=true;sv.worldmodel=&world;sv.models[1]=&model;model.type=mod_brush;
    model.mins[0]=model.mins[1]=model.mins[2]=-2;model.maxs[0]=model.maxs[1]=model.maxs[2]=2;
    svs.clients=&client;svs.maxclients=1;client.edict=&edicts[1];edicts[1].v.movetype=MOVETYPE_WALK;
    edicts[2].v.classname=1;edicts[2].v.model=11;edicts[2].v.modelindex=1;edicts[2].v.origin[0]=20;
    edicts[3].v.classname=1;edicts[3].v.model=11;edicts[3].v.modelindex=1;edicts[3].v.origin[0]=1100;
    /* Balmora runs its frame map: the map begin loads no catalogue. */
    aw_chim_town_map=town_map;strcpy(sv.name,"balmora");
    strcpy(sv.modelname,"maps/balmora-chim.bsp");strcpy(world.name,sv.modelname);
    AW_HarvestBegin();assert(!AW_HarvestProtect(&edicts[2]) && !AW_HarvestProtect(&edicts[3]));
    /* Arrival in bm000: its catalogue. */
    assert(AW_HarvestFollow(AW_RegionAt,p,1));
    assert(opens[0]==1 && AW_HarvestProtect(&edicts[2]) && !AW_HarvestProtect(&edicts[3]));
    /* Inside bm000: nothing reloads. */
    p[0]=1000;assert(AW_HarvestFollow(AW_RegionAt,p,0) && opens[0]==1);
    /* Past the hysteresis into bm001, without a map change: bm001's catalogue. */
    p[0]=1121;assert(AW_HarvestFollow(AW_RegionAt,p,0));
    assert(opens[1]==1 && !AW_HarvestProtect(&edicts[2]) && AW_HarvestProtect(&edicts[3]));
    /* Back within the hysteresis: still bm001; back past it: bm000 again. */
    p[0]=1000;assert(AW_HarvestFollow(AW_RegionAt,p,0) && opens[0]==1 && opens[1]==1);
    p[0]=927;assert(AW_HarvestFollow(AW_RegionAt,p,0));
    assert(opens[0]==2 && AW_HarvestProtect(&edicts[2]) && !AW_HarvestProtect(&edicts[3]));
    /* Picked plants stay picked across the reloads (saved facts). */
    {
        vec3_t at={0,0,0};int before=opens[1];
        VectorCopy(at,edicts[1].v.origin);cls.state=ca_connected;
        assert(AW_HarvestUse() && !edicts[2].v.modelindex);
        p[0]=1121;AW_HarvestFollow(AW_RegionAt,p,0);p[0]=927;AW_HarvestFollow(AW_RegionAt,p,0);
        assert(opens[1]==before+1 && !edicts[2].v.modelindex && !AW_HarvestUse());
    }
    /* A legacy region map (or chim_towns 0: no frame map): left alone. */
    strcpy(sv.modelname,"maps/bm000.bsp");
    assert(!AW_HarvestFollow(AW_RegionAt,p,1) && !AW_HarvestFollow(AW_RegionAt,p,0));
    aw_chim_town_map=NULL;strcpy(sv.modelname,"maps/balmora-chim.bsp");
    assert(!AW_HarvestFollow(AW_RegionAt,p,1));
    puts("chim harvest regions passed");
    return 0;
}
