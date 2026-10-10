/* SPDX-License-Identifier: GPL-2.0-or-later
 * Lava in game (aw_lava.h, docs/LAVA.md): damage while the player stands in a
 * CONTENTS_LAVA volume and the blood-red view tint. The volumes and the warp
 * texture come from the builder; this file is only the game logic id's
 * client.qc did in WaterMove, with Morrowind's numbers: the pool script hurts
 * a standing actor 20 health a second, continuously (no 1-second ticks). */
#include "quakedef.h"
#include "r_local.h"
#include "aw_lava.h"

static cvar_t lava_on={"aw_lava","1"};
static cvar_t lava_dps={"aw_lava_dps","20"};
static cvar_t lava_tint={"aw_lava_tint",AW_LAVA_DEFAULT_TINT};
static cvar_t lava_tint_min={"aw_lava_tint_min","110"};
static cvar_t lava_tint_max={"aw_lava_tint_max","230"};
static cvar_t lava_tint_ramp={"aw_lava_tint_ramp","3"};
static cvar_t lava_embers={"aw_lava_embers","2"};     /* embers a second per pool (0: none) */

static float seconds_in;     /* time the player has stood in lava, 0 when out */
static int feet_in;          /* the player is in lava this frame */

void AW_LavaInit(void) {
    Cvar_RegisterVariable(&lava_on);Cvar_RegisterVariable(&lava_dps);Cvar_RegisterVariable(&lava_tint);
    Cvar_RegisterVariable(&lava_tint_min);Cvar_RegisterVariable(&lava_tint_max);Cvar_RegisterVariable(&lava_tint_ramp);
    Cvar_RegisterVariable(&lava_embers);
}
float AW_LavaSeconds(void) {return seconds_in;}

void AW_LavaPhysics(void) {
    edict_t *p;float dt=(float)host_frametime;
    if(!sv.active || svs.maxclients!=1 || !svs.clients || !(p=svs.clients[0].edict)){feet_in=0;seconds_in=0;return;}
    feet_in=lava_on.value!=0 && p->v.movetype!=MOVETYPE_NOCLIP &&
        AW_LavaIn((int)p->v.watertype,(int)p->v.waterlevel);
    if(!feet_in){seconds_in=0;return;}
    if(dt>0)seconds_in+=dt;
    if(p->v.health>0)AW_CombatHurtPlayer(AW_LavaDamage(lava_dps.value,dt),"lava");
}
int AW_LavaContentsShift(int eye_contents, int rgb[3], int *percent) {
    if(!lava_on.value || (eye_contents!=AW_LAVA_CONTENTS && !feet_in))return 0;
    AW_LavaParseTint(lava_tint.string,rgb);
    /* The eye under the surface: the full tint at once, as id's preset did. */
    *percent=eye_contents==AW_LAVA_CONTENTS?AW_LavaTintPercent(1,0,(int)lava_tint_max.value,0):
        AW_LavaTintPercent(seconds_in,(int)lava_tint_min.value,(int)lava_tint_max.value,lava_tint_ramp.value);
    return 1;
}

/* Rising embers over the pools: an AmiWind addition (the original pools have
 * no particles), through the hearth's ember particles (AW_EmberSpawn, r_part.c).
 * The builder writes one "aw_lava" entity per pool (origin on the surface,
 * _aw_lava_radius); the table is read once per map, like the static flames, and
 * at most LAVA_EMBER_POOLS pools within LAVA_EMBER_RANGE emit each frame. */
#define LAVA_POOL_MAX 128
#define LAVA_EMBER_POOLS 8
#define LAVA_EMBER_RANGE (1024.0f*1024.0f)
static struct {vec3_t origin;float radius;} pools[LAVA_POOL_MAX];
static int pool_count;
static model_t *pool_world;
static void pools_load(model_t *world)
{
    char *data,key[64];int lava;vec3_t origin;float radius;
    pool_count=0;pool_world=world;
    if(!world || !world->entities)return;
    data=world->entities;
    while((data=COM_Parse(data))!=NULL && com_token[0]=='{'){
        lava=0;origin[0]=origin[1]=origin[2]=0;radius=0;
        while((data=COM_Parse(data))!=NULL && com_token[0]!='}'){
            strncpy(key,com_token,sizeof(key)-1);key[sizeof(key)-1]=0;
            if(!(data=COM_Parse(data)))break;
            if(!strcmp(key,"classname"))lava=!strcmp(com_token,"aw_lava");
            else if(!strcmp(key,"origin"))Q_sscanf(com_token,"%f %f %f",&origin[0],&origin[1],&origin[2]);
            else if(!strcmp(key,"_aw_lava_radius"))radius=(float)Q_strtod(com_token,NULL);
        }
        if(lava && pool_count<LAVA_POOL_MAX && isfinite(radius) && radius>0 && radius<=4096){
            VectorCopy(origin,pools[pool_count].origin);pools[pool_count++].radius=radius;
        }
        if(!data)break;
    }
}
int AW_LavaPoolCount(void) {return pool_count;}
void AW_LavaEmbersDraw(void)
{
    int i,n=0;vec3_t delta;float rate=lava_embers.value;
    if(!lava_on.value || rate<=0 || !cl.worldmodel)return;
    if(cl.worldmodel!=pool_world)pools_load(cl.worldmodel);
    for(i=0;i<pool_count && n<LAVA_EMBER_POOLS;i++){
        VectorSubtract(pools[i].origin,r_refdef.vieworg,delta);
        if(DotProduct(delta,delta)>LAVA_EMBER_RANGE)continue;
        n++;
        if((rand()&1023)<(int)(host_frametime*rate*1024))
            AW_EmberSpawn(pools[i].origin,pools[i].radius*0.8f,20);
    }
}
