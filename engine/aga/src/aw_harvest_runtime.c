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
static edict_t *plants[AW_HARVEST_PLANTS];
static unsigned char available[AW_HARVEST_PLANTS];
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
void AW_HarvestInit(void){Cvar_RegisterVariable(&harvest_mode);Cmd_AddCommand("aw_shroomtracker",shroomtracker);}
void AW_HarvestClear(void)
{
    AW_HarvestProxyClear();memset(&harvest,0,sizeof(harvest));memset(plants,0,sizeof(plants));
    memset(available,0,sizeof(available));pickup_available=0;
}
void AW_HarvestLink(void){AW_HarvestProxyLink();}
void AW_HarvestBegin(void)
{
    FILE *f=NULL;char map[32],path[64];const char *start,*end;int n,bytes;
    AW_HarvestClear();
    if(!sv.worldmodel)return;
    start=strrchr(sv.worldmodel->name,'/');start=start?start+1:sv.worldmodel->name;
    end=strrchr(start,'.');n=end?(int)(end-start):(int)strlen(start);
    if(n<1 || n>24)return;
    memcpy(map,start,n);map[n]=0;
    sprintf(path,"harvest-%s.txt",map);bytes=COM_FOpenFile(path,&f);
    if(f){if(!AW_HarvestRead(f,bytes,&harvest))Con_Printf("Rejected harvest catalogue: %s\n",path);fclose(f);}
}
static int binding(edict_t *e)
{
    int i,k,result=-1;eval_t *reference;float a;aw_harvest_plant_t *p;
    if(harvest.representation==4 || !harvest.plants || !e || e->free || !e->v.model || !e->v.classname || strcmp(pr_strings+e->v.classname,"func_wall"))return -1;
    reference=GetEdictFieldValue(e,"aw_ref");if(!reference || !isfinite(reference->_float))return -1;
    for(i=0;i<harvest.plants;i++){
        p=&harvest.plant[i];
        if(reference->_float!=(float)p->reference || strcmp(pr_strings+e->v.model,p->model))continue;
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
    memset(plants,0,sizeof(plants));memset(available,0,sizeof(available));memset(duplicate,0,sizeof(duplicate));
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
    edict_t *p,*e;entity_t *proxy;model_t *m;trace_t tr;int i,j,index,best=-1;float limit,lo,hi,a,b,t,o,d,scale;
    vec3_t eye,forward,right,up,end,delta,axis,ray,local,angles;
    if(!harvest.plants || harvest_mode.value!=1 || !sv.active || svs.maxclients!=1 || !svs.clients ||
       !(p=svs.clients[0].edict) || p->v.movetype!=MOVETYPE_WALK || cls.state!=ca_connected || key_dest!=key_game)return -1;
    VectorAdd(p->v.origin,p->v.view_ofs,eye);AngleVectors(cl.viewangles,forward,right,up);
    VectorMA(eye,72,forward,end);tr=SV_Move(eye,vec3_origin,vec3_origin,end,MOVE_NORMAL,p);
    if(tr.startsolid || tr.allsolid)return -1;
    limit=72*tr.fraction;
    for(i=0;i<harvest.plants;i++){
        if(harvest.representation==4){
            proxy=AW_HarvestProxyEntity(i);if(!proxy)continue;m=proxy->model;scale=harvest.plant[i].scale;
            VectorSubtract(eye,proxy->origin,delta);VectorCopy(proxy->angles,angles);angles[PITCH]=-angles[PITCH];
        }else{
            e=plants[i];if(!available[i] || !e || e->free || AW_HarvestHidden(&harvest,i,&aw_state))continue;
            index=(int)e->v.modelindex;if(index<=0 || index>=MAX_MODELS || !(m=sv.models[index]) || m->type!=mod_brush)continue;
            VectorSubtract(eye,e->v.origin,delta);VectorCopy(e->v.angles,angles);scale=1;
        }
        AngleVectors(angles,axis,right,up);
        ray[0]=DotProduct(forward,axis)/scale;ray[1]=-DotProduct(forward,right)/scale;ray[2]=DotProduct(forward,up)/scale;
        local[0]=DotProduct(delta,axis)/scale;local[1]=-DotProduct(delta,right)/scale;local[2]=DotProduct(delta,up)/scale;
        lo=0;hi=limit+.01f;
        for(j=0;j<3;j++){
            o=local[j];d=ray[j];
            if(fabs(d)<.00001f){if(o<m->mins[j] || o>m->maxs[j])break;}
            else{
                a=(m->mins[j]-o)/d;b=(m->maxs[j]-o)/d;
                if(a>b){t=a;a=b;b=t;}if(a>lo)lo=a;if(b<hi)hi=b;
                if(lo>hi)break;
            }
        }
        if(j==3 && lo<=limit+.01f){limit=lo;best=i;}
    }
    return best;
}
const char *AW_HarvestHint(void){int i=target();return i<0?NULL:harvest.plant[i].label;}
int AW_HarvestUse(void)
{
    int i=target(),result,level,j,k;int32_t before[AW_HARVEST_NODES],amount;
    char message[4096],line[96];const char *label;
    if(i<0)return 0;
    for(j=0;j<harvest.nodes;j++)before[j]=AW_StateGet(&aw_state,AW_ITEM,harvest.node[j].id);
    level=aw_character.valid?aw_character.level:1;
    result=AW_HarvestTake(&harvest,i,&aw_state,level,(uint32_t)rand());
    if(result>0){
        if(harvest.representation==4)AW_HarvestProxyHide(i);else hide(plants[i]);
        if(result==1){
            pickup_sound();message[0]=0;
            for(j=0;j<harvest.nodes;j++){
                if(harvest.node[j].kind!=0)continue;
                for(k=0;k<j;k++)if(!strcmp(harvest.node[j].id,harvest.node[k].id))break;
                if(k<j)continue;
                amount=AW_StateGet(&aw_state,AW_ITEM,harvest.node[j].id)-before[j];
                if(amount<=0)continue;
                label=harvest.node[j].label[0]?harvest.node[j].label:"items"; /* AWH1 compatibility, never an internal record ID. */
                sprintf(line,"Picked up %ld %s.",(long)amount,label);
                if(message[0])strcat(message,"\n");
                strcat(message,line);
            }
            if(message[0])AW_UIPickupNotice(message,3);
        }
    }
    else if(result<0)AW_UISubtitle(harvest.plant[i].label,"Cannot collect: inventory/state capacity or data rejected.",3);
    return 1;
}
