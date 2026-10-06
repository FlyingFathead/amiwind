/* SPDX-License-Identifier: GPL-2.0-or-later
 * Actual model-name allocator and actual cache; synthetic aliases only. */
#define main alias_residency_fixture_main
#include "aga_alias_residency_test.c"
#undef main
extern model_t mod_known[256];extern int mod_numknown;
extern model_t *Mod_FindName(char *);
int main(void)
{
    int i,n;cache_system_t *head,*tail;static model_t before[256];
    reset();memset(mod_known,0,sizeof(mod_known));mod_numknown=256;
    for(i=0;i<256;i++)sprintf(mod_known[i].name,"occupied%d",i);
    n=make_alias(0);decode(&mod_known[12],n);decode(&mod_known[42],n);
    memcpy(before,mod_known,sizeof(before));head=cache_head.lru_next;tail=cache_head.lru_prev;
    assert(Mod_CanFindName("occupied12"));assert(!Mod_CanFindName("missing"));
    assert(!memcmp(before,mod_known,sizeof(before)) && head==cache_head.lru_next && tail==cache_head.lru_prev);
    mod_known[42].needload=2; /* NL_UNREFERENCED, as set by Mod_ClearAll. */
    memcpy(before,mod_known,sizeof(before));
    assert(Mod_CanFindName("shared-new"));
    assert(!memcmp(before,mod_known,sizeof(before)) && head==cache_head.lru_next && tail==cache_head.lru_prev);
    assert(Mod_FindName("shared-new")==&mod_known[42]);
    assert(!mod_known[42].cache.data && mod_known[12].cache.data);
    assert(!strcmp(mod_known[12].name,"occupied12") && mod_numknown==256);
    assert(!Mod_CanFindName("second-missing"));Cache_Flush();
    puts("Optional model admission preserves names/LRU and reuses only an unreferenced cache slot");
    return 0;
}
