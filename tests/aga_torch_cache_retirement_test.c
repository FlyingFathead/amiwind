/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "../engine/aga/src/aw_torch.c"
#include <assert.h>
client_state_t cl;
static int freed;
void Cache_Free(cache_user_t *c){assert(c->data);c->data=NULL;freed++;}
int main(void){
    model_t legacy,active;byte token;memset(&legacy,0,sizeof(legacy));memset(&active,0,sizeof(active));
    strcpy(legacy.name,"progs/v_torch.mdl");legacy.type=mod_alias;legacy.cache.data=&token;
    torch_model=&legacy;cl.viewent.model=&legacy;AW_TorchReleaseLegacyCache();assert(!freed && legacy.cache.data);
    cl.viewent.model=&active;AW_TorchReleaseLegacyCache();assert(freed==1 && !legacy.cache.data);
    assert(torch_model==&legacy && legacy.type==mod_alias && !strcmp(legacy.name,"progs/v_torch.mdl"));
    AW_TorchReleaseLegacyCache();assert(freed==1);
    legacy.cache.data=&token;strcpy(legacy.name,"progs/other.mdl");AW_TorchReleaseLegacyCache();assert(freed==1 && legacy.cache.data);
    strcpy(legacy.name,"progs/v_torch.mdl");legacy.type=mod_brush;AW_TorchReleaseLegacyCache();assert(freed==1 && legacy.cache.data);
    torch_model=NULL;AW_TorchReleaseLegacyCache();assert(freed==1);
    puts("Actual torch cache hook preserves active viewmodel, metadata and reused/unowned slots.");return 0;
}
