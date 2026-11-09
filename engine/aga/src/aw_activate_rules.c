/* What the use key acts on (FOCUS-NPC-OVERRIDES-ITEM-62): the rules as pure functions (aw_activate.h); host tested by
 * tests/aga_activate_rules_test.c. */
#include <math.h>
#include "aw_activate.h"

int AW_RayBox(const float origin[3],const float dir[3],const float mins[3],const float maxs[3],float *near_hit,
              float *far_hit){
    float lo=0,hi=1e30f,a,b,t;int j;
    for(j=0;j<3;j++){
        if(fabs(dir[j])<0.00001f){
            if(origin[j]<mins[j] || origin[j]>maxs[j])return 0;
            continue;
        }
        a=(mins[j]-origin[j])/dir[j];b=(maxs[j]-origin[j])/dir[j];
        if(a>b){t=a;a=b;b=t;}
        if(a>lo)lo=a;
        if(b<hi)hi=b;
        if(lo>hi)return 0;
    }
    if(near_hit)*near_hit=lo;
    if(far_hit)*far_hit=hi;
    return 1;
}
int AW_ActivateItemFirst(float item,float actor_near,float actor_far){
    if(item<0)return 0;
    if(actor_far<0)return 1;
    /* the item before the actor, or inside his box (the box is coarser than his body); behind him, he is in the way */
    (void)actor_near;
    return item<=actor_far;
}
float AW_ActivateNearest(float a,float b){
    if(a<0)return b;
    if(b<0)return a;
    return a<b?a:b;
}
