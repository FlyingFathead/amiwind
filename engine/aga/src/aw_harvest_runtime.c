/* SPDX-License-Identifier: GPL-2.0-or-later
 * Only exact catalogue-bound brushes participate. Geometry conversion alone
 * cannot opt a generic container into harvesting or immutable scenery capture.
 */
#include "quakedef.h"
#include "aw_character.h"
#include "aw_harvest.h"
#include "aw_harvest_runtime.h"
#include "aw_harvest_proxy.h"
static aw_harvest_t harvest;
static edict_t **plants;
static unsigned char *available;
static cvar_t harvest_mode={"aw_harvest_mode","1",true};
/* Stable complete-media path for the selected original Fx/item/item.wav. */
#define PICKUP_SOUND "pool/a031af0520e9edfa2.wav"
static int pickup_available;
static void pickup_sound(void)
{
    FILE *f=NULL;int bytes;
    if(!pickup_available){
        bytes=COM_FOpenFile("sound/" PICKUP_SOUND,&f);
        pickup_available=bytes>=44 && f?1:-1;
        if(f)fclose(f);
        if(pickup_available<0)Con_Printf("Harvest pickup sound unavailable: " PICKUP_SOUND "\n");
    }
    if(pickup_available>0)S_LocalSound(PICKUP_SOUND);
}
static void hide(edict_t *e){e->v.modelindex=0;e->v.solid=SOLID_NOT;SV_LinkEdict(e,false);}
static void shroomtracker(void)
{
    if(Cmd_Argc()!=1){Con_Printf("Usage: aw_shroomtracker\n");return;}
    Con_Printf("Mushrooms picked: %ld\n",(long)AW_HarvestPickedCount(&aw_state));
}
void AW_HarvestInit(void){AW_HarvestInitData(&harvest);Cvar_RegisterVariable(&harvest_mode);Cmd_AddCommand("aw_shroomtracker",shroomtracker);}
void AW_HarvestClear(void)
{
    AW_HarvestProxyClear();free(plants);plants=NULL;available=NULL;
    AW_HarvestRelease(&harvest);pickup_available=0;
}
void AW_HarvestLink(void){AW_HarvestProxyLink();}
static void load(const char *map)
{
    FILE *f=NULL;char path[64];int bytes;
    if(strlen(map)>24)return;
    sprintf(path,"harvest-%s.txt",map);bytes=COM_FOpenFile(path,&f);
    if(f){if(!AW_HarvestLoad(f,bytes,&harvest))Con_Printf("Rejected harvest catalogue (data or allocation): %s\n",path);fclose(f);}
}
void AW_HarvestBegin(void)
{
    char map[32];const char *start,*end;int n;
    AW_HarvestClear();
    if(!sv.worldmodel)return;
    start=strrchr(sv.worldmodel->name,'/');start=start?start+1:sv.worldmodel->name;
    end=strrchr(start,'.');n=end?(int)(end-start):(int)strlen(start);
    if(n<1 || n>24)return;
    memcpy(map,start,n);map[n]=0;
    load(map);
}
/* CHIM: a town running its frame map keeps its per-region catalogues
 * (harvest-<region map>.txt; the frame map has none). region_at (aw_region.c
 * AW_RegionAt) names the region the player is in; at arrival and on each
 * region change within the frame the previous region's catalogue and
 * proxies are released and the new one is loaded and spawned. The per-file
 * limits and the saved facts are unchanged. Returns 0 on a legacy map
 * (nothing done: the loaded region map's catalogue is the region's). */
static int follow_region=-1;
int AW_HarvestFollow(aw_harvest_region_at_t region_at,const float *origin,int arrival)
{
    char map[16];int id=region_at(origin,arrival?-1:follow_region,map,sizeof(map));
    if(id<-1){follow_region=-1;return 0;}
    if(!arrival && id==follow_region)return 1;
    follow_region=id;AW_HarvestClear();
    if(id>=0)load(map);
    AW_HarvestSpawn();
    return 1;
}
static int binding(edict_t *e)
{
    int i,k,result=-1;eval_t *reference;float a;aw_harvest_plant_t *p;
    if(harvest.representation==4 || !harvest.plants || !e || e->free || !e->v.model || !e->v.classname || strcmp(pr_strings+e->v.classname,"func_wall"))return -1;
    reference=GetEdictFieldValue(e,"aw_ref");if(!reference || !isfinite(reference->_float))return -1;
    for(i=0;i<harvest.plants;i++){
        p=&harvest.plant[i];
        if(reference->_float!=(float)p->reference || strcmp(pr_strings+e->v.model,AW_HarvestText(&harvest,p->model)))continue;
        for(k=0;k<3;k++){
            if(!isfinite(e->v.origin[k]) || !isfinite(e->v.angles[k]) || fabs(e->v.origin[k]-p->origin[k])>.002f)break;
            a=fmod(e->v.angles[k]-p->angles[k],360.0);if(a>180)a-=360;if(a< -180)a+=360;
            if(fabs(a)>.002f)break;
        }
        if(k==3){if(result>=0)return -1;result=i;}
    }
    return result;
}
int AW_HarvestProtect(edict_t *e){return binding(e)>=0;}
void AW_HarvestSpawn(void)
{
    int i,b,result,level=aw_character.valid?aw_character.level:1;unsigned char duplicate[AW_HARVEST_PLANTS];edict_t *e;
    if(harvest.representation==4){AW_HarvestProxySpawn(&harvest,&aw_state,level,(unsigned)rand());return;}
    free(plants);plants=NULL;available=NULL;if(!harvest.plants)return;
    plants=(edict_t **)calloc(harvest.plants,sizeof(*plants)+sizeof(*available));
    if(!plants){Con_Printf("Harvest brush allocation failed: %d placements unavailable.\n",harvest.plants);return;}
    available=(unsigned char *)(plants+harvest.plants);memset(duplicate,0,sizeof(duplicate));
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);b=binding(e);if(b<0)continue;
        if(plants[b])duplicate[b]=1;else plants[b]=e;
    }
    for(i=0;i<harvest.plants;i++){
        if(duplicate[i]){plants[i]=NULL;Con_Printf("Ambiguous harvest placement rejected\n");}
        else if(plants[i]){
            result=AW_HarvestPrepare(&harvest,i,&aw_state,level,(uint32_t)rand());
            if(!result)hide(plants[i]);
            else if(result>0)available[i]=1;
            else Con_Printf("Harvest availability unresolved: data or saved-state capacity; pickup disabled.\n");
        }
    }
}
static int target(void)
{
    edict_t *p,*e=NULL;entity_t *proxy;model_t *m;trace_t tr,inside;int i,j,index,best=-1;
    float limit,lo,hi,a,b,t,o,d,scale,reach=72,nearest=0;
    vec3_t eye,forward,right,up,end,delta,axis,ray,local,angles,base,centre,world;
    if(!harvest.plants || harvest_mode.value!=1 || !sv.active || svs.maxclients!=1 || !svs.clients ||
       !(p=svs.clients[0].edict) || p->v.movetype!=MOVETYPE_WALK || cls.state!=ca_connected || key_dest!=key_game)return -1;
    VectorAdd(p->v.origin,p->v.view_ofs,eye);AngleVectors(cl.viewangles,forward,right,up);
    VectorMA(eye,reach,forward,end);tr=SV_Move(eye,vec3_origin,vec3_origin,end,MOVE_NORMAL,p);
    if(tr.startsolid || tr.allsolid)return -1;
    limit=reach*tr.fraction;
    for(i=0;i<harvest.plants;i++){
        if(harvest.representation==4){
            proxy=AW_HarvestProxyEntity(i);if(!proxy)continue;m=proxy->model;scale=harvest.plant[i].scale;
            VectorCopy(proxy->origin,base);VectorSubtract(eye,base,delta);VectorCopy(proxy->angles,angles);angles[PITCH]=-angles[PITCH];
        }else{
            if(!plants || !available)continue;
            e=plants[i];if(!available[i] || !e || e->free || AW_HarvestHidden(&harvest,i,&aw_state))continue;
            index=(int)e->v.modelindex;if(index<=0 || index>=MAX_MODELS || !(m=sv.models[index]) || m->type!=mod_brush)continue;
            VectorCopy(e->v.origin,base);VectorSubtract(eye,base,delta);VectorCopy(e->v.angles,angles);scale=1;
        }
        AngleVectors(angles,axis,right,up);
        ray[0]=DotProduct(forward,axis)/scale;ray[1]=-DotProduct(forward,right)/scale;ray[2]=DotProduct(forward,up)/scale;
        local[0]=DotProduct(delta,axis)/scale;local[1]=-DotProduct(delta,right)/scale;local[2]=DotProduct(delta,up)/scale;
        lo=0;hi=reach+.01f;
        for(j=0;j<3;j++){
            o=local[j];d=ray[j];
            if(fabs(d)<.00001f){if(o<m->mins[j] || o>m->maxs[j])break;}
            else{
                a=(m->mins[j]-o)/d;b=(m->maxs[j]-o)/d;
                if(a>b){t=a;a=b;b=t;}if(a>lo)lo=a;if(b<hi)hi=b;
                if(lo>hi)break;
            }
        }
        if(j<3 || lo>reach+.01f || (best>=0 && lo>nearest+.01f))continue;
        /* The view trace hit a solid before the box. Collision of converted scenery is an
         * approximation; when the solid also contains the plant's own centre (a tree's convex root
         * collision over the mushrooms under it), it is not what hides the drawn plant: the plant
         * stays the target (HARVEST-BITTERCOAST-29). Tested only for boxes on the ray. */
        if(lo>limit+.01f){
            for(j=0;j<3;j++)centre[j]=(m->mins[j]+m->maxs[j])*.5f;
            for(j=0;j<3;j++)world[j]=base[j]+scale*(centre[0]*axis[j]-centre[1]*right[j]+centre[2]*up[j]);
            /* a brush plant is solid itself: pass it, not the player */
            inside=SV_Move(world,vec3_origin,vec3_origin,world,MOVE_NORMAL,harvest.representation==4?p:e);
            if(!inside.startsolid && !inside.allsolid)continue;
        }
        nearest=lo;best=i;
    }
    return best;
}
const char *AW_HarvestHint(void){int i=target();return i<0?NULL:AW_HarvestText(&harvest,harvest.plant[i].label);}
int AW_HarvestUse(void)
{
    int i=target(),result,level,j,k;int32_t before[AW_HARVEST_NODES],amount;
    char message[4096],line[96];const char *label;
    if(i<0)return 0;
    for(j=0;j<harvest.nodes;j++)before[j]=AW_StateGet(&aw_state,AW_ITEM,AW_HarvestText(&harvest,harvest.node[j].id));
    level=aw_character.valid?aw_character.level:1;
    result=AW_HarvestTake(&harvest,i,&aw_state,level,(uint32_t)rand());
    if(result>0){
        if(harvest.representation==4)AW_HarvestProxyHide(i);else hide(plants[i]);
        if(result==1){
            pickup_sound();message[0]=0;
            for(j=0;j<harvest.nodes;j++){
                if(harvest.node[j].kind!=0)continue;
                for(k=0;k<j;k++)if(!strcmp(AW_HarvestText(&harvest,harvest.node[j].id),AW_HarvestText(&harvest,harvest.node[k].id)))break;
                if(k<j)continue;
                amount=AW_StateGet(&aw_state,AW_ITEM,AW_HarvestText(&harvest,harvest.node[j].id))-before[j];
                if(amount<=0)continue;
                label=AW_HarvestText(&harvest,harvest.node[j].label);if(!label[0])label="items"; /* AWH1 compatibility. */
                /* ENGINE-HARVEST-MESSAGE-BOUND-35: bounded line and message. */
                snprintf(line,sizeof(line),"Picked up %ld %s.",(long)amount,label);
                if(strlen(message)+strlen(line)+2>sizeof(message))break;
                if(message[0])strcat(message,"\n");
                strcat(message,line);
            }
            if(message[0])AW_UIPickupNotice(message,3);
        }
    }
    else if(result<0)AW_UISubtitle(AW_HarvestText(&harvest,harvest.plant[i].label),"Cannot collect: inventory/state capacity or data rejected.",3);
    return 1;
}
