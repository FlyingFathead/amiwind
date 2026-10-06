/* SPDX-License-Identifier: GPL-2.0-or-later */
#define main guard_registry_fixture_main
#define Con_Printf ignored_Con_Printf
#define SV_PointContents fixture_PointContents
#include "aga_guard_torch_test.c"
#undef main
#undef Con_Printf
#undef SV_PointContents
#include <stdarg.h>
static char diagnostic[1024];
static int solid_emitter;
void Con_Printf(char *format,...)
{
    va_list args;va_start(args,format);vsnprintf(diagnostic,sizeof diagnostic,format,args);va_end(args);
}
int SV_PointContents(vec3_t point)
{
    return solid_emitter && point[2]==25 && point[0]==80?CONTENTS_SOLID:fixture_PointContents(point);
}
int main(void)
{
    assert(guard_registry_fixture_main()==0);
    make_registry(8);body.numframes=held.numframes=8;AW_GuardTorchLoadAssets(torch);
    npc(1,18,80);npc(2,18,100);npc(3,18,400);scene(3);set_command("on");
    AW_GuardTorchUpdate();cmd();
    assert(strstr(diagnostic,"active 2; last selected 2/2, outside range 1, contents rejects 0, trace rejects 0"));
    blocked_x=80;AW_GuardTorchUpdate();cmd();
    assert(strstr(diagnostic,"active 1; last selected 1/2, outside range 1, contents rejects 0, trace rejects 1"));
    blocked_x=-1;solid_emitter=1;AW_GuardTorchUpdate();cmd();
    assert(strstr(diagnostic,"active 1; last selected 1/2, outside range 1, contents rejects 1, trace rejects 0"));
    assert(cl_numvisedicts==6); /* Visible flame proxies do not imply admitted lights. */
    puts(diagnostic);solid_emitter=0;
    /* The first emitter was rejected; losing its proxy must not clear the
     * second guard's admitted light. Shared model eviction reaches the second
     * proxy separately, at which point its own light is removed. */
    assert(lights()==1 && light_x(100) && !light_x(80));
    body.cache.data=NULL;assert(AW_GuardTorchEntity(cl_visedicts[0])==&cl_entities[1]);cmd();
    assert(lights()==1 && light_x(100));
    assert(strstr(diagnostic,"active 1; last selected 1/2"));
    assert(AW_GuardTorchEntity(cl_visedicts[1])==&cl_entities[2]);cmd();
    assert(!lights() && strstr(diagnostic,"active 0; last selected 1/2"));
    set_command("off");AW_GuardTorchUpdate();cmd();
    assert(strstr(diagnostic,"active 0; last selected 0/2"));
    puts("guard diagnostics distinguish live lights, emitter/trace rejection, range and eviction");
    return 0;
}
