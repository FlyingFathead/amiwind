/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "r_local.h"
#include <assert.h>
client_state_t cl;
dlight_t cl_dlights[MAX_DLIGHTS];
entity_t *currententity;
vec3_t r_entorigin,modelorg;
cvar_t aw_torch_strength;
void VectorInverse(vec3_t v){v[0]=-v[0];v[1]=-v[1];v[2]=-v[2];}
static model_t arm_model,shield_model;
static int draws,item_visible=1;
static alight_t *first_lighting;
int AW_HandBlockApply(void){return 1;}
int AW_HandModelsApply(void){assert(0);return 0;}
void AW_TorchViewModel(void){assert(0);}
int AW_HandBlockItemApply(void){
    if(!item_visible)return 0;
    cl.viewent.model=&shield_model;cl.viewent.frame=0;
    cl.viewent.origin[0]=15;cl.viewent.origin[1]=-7;cl.viewent.angles[0]=33;return 1;
}
int R_ActorLight(entity_t *e,int flags){assert(e==&cl.viewent);return 72;}
float AW_TorchLightGain(int key,float radius,int mode){assert(0);return 1;}
void R_AliasDrawModel(alight_t *lighting){
    assert(currententity==&cl.viewent); /* Both aliases retain viewmodel depth. */
    if(!draws){assert(currententity->model==&arm_model);first_lighting=lighting;}
    else{assert(currententity->model==&shield_model && lighting==first_lighting);assert(r_entorigin[0]==15 && r_entorigin[1]==-7);}
    draws++;
}
int main(void){
    entity_t before;
    extern cvar_t r_drawviewmodel;
    r_drawviewmodel.value=1;cl.stats[STAT_HEALTH]=100;
    cl.viewent.model=&arm_model;cl.viewent.frame=2;cl.viewent.origin[0]=3;cl.viewent.origin[1]=9;cl.viewent.angles[0]=-23;
    before=cl.viewent;R_DrawViewModel();
    assert(draws==2 && currententity==&cl.viewent && !memcmp(&before,&cl.viewent,sizeof(before)));
    assert(r_entorigin[0]==3 && r_entorigin[1]==9);
    item_visible=0;draws=0;R_DrawViewModel();
    assert(draws==1 && currententity==&cl.viewent && !memcmp(&before,&cl.viewent,sizeof(before)));
    puts("Actual renderer preserves viewmodel depth/lighting and restores entity/shared transform state.");return 0;
}
