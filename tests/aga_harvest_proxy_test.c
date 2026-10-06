/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_harvest.h"
#include "aw_harvest_proxy.h"
#include <assert.h>
server_t sv;server_static_t svs;client_static_t cls;
viddef_t vid;static byte colormap[256*64];
int cl_numvisedicts,mod_numknown;
entity_t *cl_visedicts[MAX_VISEDICTS];model_t mod_known[256];
static model_t fake[3];static int loads,fail;
static aw_harvest_t h;static aw_state_t state,before;
void Con_Printf(char *fmt,...){(void)fmt;}
qboolean Mod_CanFindName(const char *name){(void)name;return mod_numknown<256;}
model_t *Mod_ForName(char *name,qboolean crash)
{
    int i=name[15]-'0';(void)crash;assert(i>=0 && i<3);loads++;
    return fail?NULL:&fake[i];
}
#include "aga_harvest_fixture.h"
static void fixture(void)
{
    int i;AW_HarvestProxyClear();harvest_fixture_storage();memset(&state,0,sizeof state);memset(fake,0,sizeof fake);
    h.representation=4;h.models=3;h.slots=6;h.catalogue[0]=1;h.nodes=1;h.edges=1;h.plants=6;
    strcpy(HSTR(h.node[0].id),"ingredient");strcpy(HSTR(h.node[0].label),"Original item");h.edge[0].count=1;
    for(i=0;i<3;i++){
        sprintf(HSTR(h.model[i].path),"progs/harvest/a%d.mdl",i);h.model[i].digest[0]=i+1;fake[i].type=mod_alias;fake[i].numframes=1;
    }
    for(i=0;i<6;i++){
        strcpy(HSTR(h.plant[i].key),"aw:h:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");HSTR(h.plant[i].key)[5]='a'+i;
        strcpy(HSTR(h.plant[i].label),"Original mushroom");sprintf(HSTR(h.plant[i].model),"@%d",i%3);
        h.plant[i].reference=100+i;h.plant[i].slot=i+1;h.plant[i].flags=1;h.plant[i].count=1;h.plant[i].scale=1+.1f*i;
    }
    assert(AW_HarvestValidate(&h));sv.active=true;svs.maxclients=1;cls.state=ca_connected;
    loads=fail=mod_numknown=cl_numvisedicts=0;vid.colormap=colormap;
}
int main(void)
{
    int i;entity_t *first;
    fixture();assert(AW_HarvestProxySpawn(&h,&state,1,123)==6 && loads==3 && !state.count[AW_ITEM]);
    assert(!AW_HarvestProxyEntity(0));AW_HarvestProxyLink();cl_numvisedicts=0;
    first=AW_HarvestProxyEntity(0);assert(first && first->colormap==colormap && first->model==AW_HarvestProxyEntity(3)->model);
    assert(AW_HarvestProxyEntity(5)->aw_sprite_scale==1.5f);before=state;
    AW_HarvestProxyLink();assert(cl_numvisedicts==6 && !memcmp(&state,&before,sizeof state));
    assert(AW_HarvestTake(&h,0,&state,999,999)==1);assert(!AW_HarvestProxyEntity(0));
    cl_numvisedicts=0;AW_HarvestProxyLink();assert(cl_numvisedicts==5);
    before=state;AW_HarvestProxyClear();assert(!AW_HarvestProxyEntity(1));
    assert(AW_HarvestProxySpawn(&h,&state,999,999)==5 && !memcmp(&state,&before,sizeof state));
    /* Model I/O/capacity failure only disables rendering; no hidden inventory
     * grant, picked counter or persisted-roll mutation. Retry is idempotent. */
    fail=1;assert(AW_HarvestProxySpawn(&h,&state,999,777)==0 && !memcmp(&state,&before,sizeof state));
    fail=0;mod_numknown=256;assert(AW_HarvestProxySpawn(&h,&state,999,888)==0 && !memcmp(&state,&before,sizeof state));
    mod_numknown=0;assert(AW_HarvestProxySpawn(&h,&state,999,999)==5);
    cl_numvisedicts=MAX_VISEDICTS;AW_HarvestProxyLink();assert(!AW_HarvestProxyEntity(1));
    cl_numvisedicts=0;AW_HarvestProxyLink();assert(AW_HarvestProxyEntity(1));
    fixture();h.nodes=2;h.node[1]=h.node[0];h.node[0].kind=1;h.node[0].chance=100;h.node[0].count=1;strcpy(HSTR(h.node[0].id),"empty_list");h.edge[0].node=1;
    h.edges=2;h.edge[1].node=0;h.edge[1].count=1;for(i=0;i<6;i++)h.plant[i].first=1;
    assert(AW_HarvestValidate(&h));assert(AW_HarvestProxySpawn(&h,&state,1,100)==0 && !loads && !state.count[AW_ITEM]);
    for(i=0;i<6;i++)assert(AW_HarvestHidden(&h,i,&state) && !AW_HarvestProxyEntity(i));
    before=state;AW_HarvestProxyClear();assert(AW_HarvestProxySpawn(&h,&state,999,999)==0 && !memcmp(&state,&before,sizeof state));
    assert(AW_HarvestPickedCount(&state)==0);puts("proxy sharing, failed model load/capacity, map return, EMPTY and DONE state gates passed");return 0;
}
