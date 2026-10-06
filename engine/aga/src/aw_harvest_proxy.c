/* Private shared-model prototype; not installed or linked by the live engine.
 * State facts are owned by aw_harvest/aw_state. Only render proxies live here.
 * No proximity radius, asynchronous loader, eviction policy or respawn.
 */
#include "quakedef.h"
#include "aw_harvest.h"
#include "aw_harvest_proxy.h"
static entity_t proxies[AW_HARVEST_PLANTS];
static model_t *models[AW_HARVEST_MODELS];
static unsigned char submitted[AW_HARVEST_PLANTS];
static const aw_harvest_t *catalogue;
static aw_state_t *state;
static int capacity_warning;

void AW_HarvestProxyClear(void)
{
    memset(proxies,0,sizeof(proxies));memset(models,0,sizeof(models));
    memset(submitted,0,sizeof(submitted));
    catalogue=NULL;state=NULL;capacity_warning=0;
}
int AW_HarvestProxySpawn(const aw_harvest_t *h,aw_state_t *s,int level,unsigned seed)
{
    int i,m,result,visible=0,wanted[AW_HARVEST_MODELS];entity_t *e;
    AW_HarvestProxyClear();
    if(h->representation!=4 || !AW_HarvestValidate(h))return 0;
    catalogue=h;state=s;memset(wanted,0,sizeof(wanted));
    /* Prepare every placement before loading any render asset. Model failures
     * cannot change the first-encounter roll or award an item. */
    for(i=0;i<h->plants;i++){
        result=AW_HarvestPrepare(h,i,s,level,seed+(unsigned)i);
        if(result>0)wanted[AW_HarvestModelIndex(h,i)]=1;
        else if(result<0)Con_Printf("Harvest availability unresolved; external proxy disabled.\n");
    }
    for(m=0;m<h->models;m++)if(wanted[m]){
        if(!Mod_CanFindName(h->model[m].path)){Con_Printf("Harvest model-known capacity exhausted.\n");continue;}
        models[m]=Mod_ForName((char *)h->model[m].path,false);
        if(models[m] && (models[m]->type!=mod_alias || models[m]->numframes!=1))models[m]=NULL;
        if(!models[m])Con_Printf("Harvest shared model unavailable: %s\n",h->model[m].path);
    }
    for(i=0;i<h->plants;i++){
        if(AW_HarvestHidden(h,i,s))continue;
        /* Prepare again only queries the persisted fact. Failed state/data
         * preparation remains ineligible and never gains a proxy. */
        if(AW_HarvestPrepare(h,i,s,level,seed+(unsigned)i)!=1)continue;
        m=AW_HarvestModelIndex(h,i);if(!models[m])continue;
        if(!vid.colormap){Con_Printf("Harvest colormap unavailable; proxy disabled.\n");continue;}
        e=&proxies[i];e->model=models[m];e->colormap=vid.colormap;VectorCopy(h->plant[i].origin,e->origin);
        VectorCopy(h->plant[i].angles,e->angles);e->aw_sprite_scale=h->plant[i].scale;e->effects=AW_EF_ALIAS_SCALE;
        visible++;
    }
    return visible;
}
entity_t *AW_HarvestProxyEntity(int i)
{
    if(!catalogue || i<0 || i>=catalogue->plants || !submitted[i] || !proxies[i].model ||
       AW_HarvestHidden(catalogue,i,state))return NULL;
    return &proxies[i];
}
void AW_HarvestProxyHide(int i)
{
    if(catalogue && i>=0 && i<catalogue->plants){proxies[i].model=NULL;submitted[i]=0;}
}
void AW_HarvestProxyLink(void)
{
    int i;entity_t *e;
    memset(submitted,0,sizeof(submitted));
    if(!catalogue || !sv.active || svs.maxclients!=1 || cls.state!=ca_connected)return;
    for(i=0;i<catalogue->plants;i++)if(proxies[i].model && !AW_HarvestHidden(catalogue,i,state)){
        e=&proxies[i];
        if(cl_numvisedicts>=MAX_VISEDICTS){
            if(!capacity_warning){Con_Printf("Harvest visible-proxy capacity exhausted.\n");capacity_warning=1;}
            break;
        }
        cl_visedicts[cl_numvisedicts++]=e;submitted[i]=1;
    }
}
