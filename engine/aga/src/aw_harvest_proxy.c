/* SPDX-License-Identifier: GPL-2.0-or-later
 * Map-owned exact-count proxies. First rolls and DONE/EMPTY facts belong to
 * aw_state; proxy retirement, allocation and model failures never reset them.
 * All available map placements are admitted, without a distance/visibility cap.
 */
#include "quakedef.h"
#include "aw_harvest.h"
#include "aw_harvest_proxy.h"
static entity_t *proxies;
static unsigned short *indices;
static unsigned char *submitted;
static model_t *models[AW_HARVEST_MODELS];
static const aw_harvest_t *catalogue;
static aw_state_t *state;
static int capacity_warning,proxy_count;
static unsigned allocated_bytes;

unsigned AW_HarvestProxyBytes(void){return allocated_bytes;}
void AW_HarvestProxyClear(void)
{
    int i,j,next=0,owned;
    /* A same-frame reload can still have submitted entities. Remove only this
     * owner's pointers before freeing their memory; preserve other renderers. */
    if(proxies){
        for(i=0;i<cl_numvisedicts;i++){
            owned=0;for(j=0;j<proxy_count;j++)if(cl_visedicts[i]==proxies+j){owned=1;break;}
            if(!owned)cl_visedicts[next++]=cl_visedicts[i];
        }
        cl_numvisedicts=next;
    }
    free(proxies);proxies=NULL;indices=NULL;submitted=NULL;allocated_bytes=0;proxy_count=0;
    memset(models,0,sizeof(models));catalogue=NULL;state=NULL;capacity_warning=0;
}
int AW_HarvestProxySpawn(const aw_harvest_t *h,aw_state_t *s,int level,unsigned seed)
{
    int i,m,result,visible=0,unresolved=0,wanted[AW_HARVEST_MODELS];entity_t *e;
    unsigned char ready[AW_HARVEST_PLANTS];const char *path;
    AW_HarvestProxyClear();
    if(h->representation!=4 || !AW_HarvestValidate(h))return 0;
    memset(wanted,0,sizeof(wanted));memset(ready,0,sizeof(ready));
    /* Every original keeps its first roll even if later allocation or model
     * admission fails. No item is awarded by this preparation. */
    for(i=0;i<h->plants;i++){
        result=AW_HarvestPrepare(h,i,s,level,seed+(unsigned)i);
        if(result>0){ready[i]=1;visible++;wanted[AW_HarvestModelIndex(h,i)]=1;}
        else if(result<0)unresolved++;
    }
    if(unresolved){Con_Printf("Harvest admission failed: %d/%d unresolved placements.\n",unresolved,h->plants);return 0;}
    catalogue=h;state=s;if(!visible)return 0;
    if(!vid.colormap){Con_Printf("Harvest admission failed: colormap unavailable, %d placements.\n",visible);goto bad;}
    allocated_bytes=visible*sizeof(entity_t)+h->plants*(sizeof(*indices)+sizeof(*submitted));
    proxies=(entity_t *)calloc(1,allocated_bytes);
    if(!proxies){Con_Printf("Harvest proxy allocation failed: %u bytes, %d placements.\n",allocated_bytes,visible);goto bad;}
    proxy_count=visible;indices=(unsigned short *)(proxies+visible);
    submitted=(unsigned char *)(indices+h->plants);
    for(m=0;m<h->models;m++)if(wanted[m]){
        path=AW_HarvestText(h,h->model[m].path);
        if(!Mod_CanFindName(path)){Con_Printf("Harvest admission failed: model-known capacity, %s.\n",path);goto bad;}
        models[m]=Mod_ForName((char *)path,false);
        if(models[m] && (models[m]->type!=mod_alias || models[m]->numframes!=1))models[m]=NULL;
        if(!models[m]){Con_Printf("Harvest admission failed: shared model %s unavailable.\n",path);goto bad;}
    }
    visible=0;
    for(i=0;i<h->plants;i++)if(ready[i]){
        m=AW_HarvestModelIndex(h,i);e=&proxies[visible++];indices[i]=(unsigned short)visible;
        e->model=models[m];e->colormap=vid.colormap;VectorCopy(h->plant[i].origin,e->origin);
        VectorCopy(h->plant[i].angles,e->angles);e->aw_sprite_scale=h->plant[i].scale;e->effects=AW_EF_ALIAS_SCALE;
    }
    return visible;
bad:AW_HarvestProxyClear();return 0;
}
entity_t *AW_HarvestProxyEntity(int i)
{
    if(!catalogue || !indices || i<0 || i>=catalogue->plants || !submitted[i] || !indices[i] ||
       !proxies[indices[i]-1].model || AW_HarvestHidden(catalogue,i,state))return NULL;
    return &proxies[indices[i]-1];
}
void AW_HarvestProxyHide(int i)
{
    if(catalogue && indices && i>=0 && i<catalogue->plants && indices[i]){
        proxies[indices[i]-1].model=NULL;submitted[i]=0;
    }
}
void AW_HarvestProxyLink(void)
{
    int i,needed=0;entity_t *e;
    if(!catalogue || !indices)return;
    memset(submitted,0,catalogue->plants);
    if(!sv.active || svs.maxclients!=1 || cls.state!=ca_connected)return;
    /* Admission is all-or-none for the active set. No clipped submitted set
     * may be mistaken for complete map coverage or become pickable. */
    for(i=0;i<catalogue->plants;i++)if(indices[i] && proxies[indices[i]-1].model && !AW_HarvestHidden(catalogue,i,state))needed++;
    if(needed>MAX_VISEDICTS-cl_numvisedicts){
        if(!capacity_warning){Con_Printf("Harvest visible admission failed: need %d, free %d.\n",needed,MAX_VISEDICTS-cl_numvisedicts);capacity_warning=1;}
        return;
    }
    capacity_warning=0;
    for(i=0;i<catalogue->plants;i++)if(indices[i] && proxies[indices[i]-1].model && !AW_HarvestHidden(catalogue,i,state)){
        e=&proxies[indices[i]-1];cl_visedicts[cl_numvisedicts++]=e;submitted[i]=1;
    }
}
