/* FOCUS-NPC-OVERRIDES-ITEM-62: what the use key acts on, by number (engine/aga/src/aw_activate_rules.c). As in OpenMW
 * 0.51 the nearest thing along the view ray within the activation distance takes the use, never the nearest actor.
 * Map units; the eye at 0 0 0, the actor's box in his own frame (not turned here). */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include "aw_activate.h"

static float length3(const float v[3]){return (float)sqrt(v[0]*v[0]+v[1]*v[1]+v[2]*v[2]);}
/* the ray from the eye toward POINT against the box MINS..MAXS of an actor standing at AT: 1 when met */
static int actor_on_ray(const float point[3],const float at[3],const float mins[3],const float maxs[3],float *near_hit,
                        float *far_hit){
    float dir[3],origin[3],n=length3(point);int j;
    for(j=0;j<3;j++){dir[j]=point[j]/n;origin[j]=-at[j];}
    return AW_RayBox(origin,dir,mins,maxs,near_hit,far_hit);
}

int main(void){
    float near_hit,far_hit,item;
    /* 1. Sellus Gravius and the candle: a standing actor 60 ahead (box 20 wide, 56 high from his feet, 40 below the
     * eye); the candle on the table 35 ahead in the same line. The ray meets him (50..70) but the candle first: the
     * candle is taken. */
    {
        const float at[3]={60,0,-40},mins[3]={-10,-10,0},maxs[3]={10,10,56},candle[3]={35,0,0};
        assert(actor_on_ray(candle,at,mins,maxs,&near_hit,&far_hit));
        item=length3(candle);
        printf("candle before him: item %.1f, actor %.1f..%.1f\n",item,near_hit,far_hit);
        assert(fabs(near_hit-50)<.01f && fabs(far_hit-70)<.01f);
        assert(AW_ActivateItemFirst(item,near_hit,far_hit));
        /* by his side, inside his box (his arm's reach): still the candle */
        assert(AW_ActivateItemFirst(55,near_hit,far_hit));
        /* behind him, past his box: he is in the way, the talk */
        assert(!AW_ActivateItemFirst(80,near_hit,far_hit));
        /* nothing aimed at but him: the talk */
        assert(!AW_ActivateItemFirst(-1,near_hit,far_hit));
    }
    /* 2. Tarhiel's journal beside his body: the body lies 40 ahead on the floor 46 below the eye, its lying box 60 long,
     * 40 wide, 12 high; the journal lies 16 to the side of it, 2 above the floor, inside the box. The aim at the journal
     * meets the box first, yet the journal is not behind the body: the journal is taken, not the body searched. */
    {
        const float at[3]={40,0,-46},mins[3]={-30,-20,0},maxs[3]={30,20,12},journal[3]={40,16,-44};
        assert(actor_on_ray(journal,at,mins,maxs,&near_hit,&far_hit));
        item=length3(journal);
        printf("journal by the body: item %.1f, body %.1f..%.1f\n",item,near_hit,far_hit);
        assert(near_hit<item && item<=far_hit);
        assert(AW_ActivateItemFirst(item,near_hit,far_hit));
        /* the aim on the body itself (no item on the ray): the body is searched */
        assert(!AW_ActivateItemFirst(-1,near_hit,far_hit));
    }
    /* 3. A bracket fungus on a tree 30 ahead with a resident 45 ahead behind it: the plant is picked */
    {
        const float at[3]={45,0,-40},mins[3]={-10,-10,0},maxs[3]={10,10,56},fungus[3]={30,0,-2};
        assert(actor_on_ray(fungus,at,mins,maxs,&near_hit,&far_hit));
        item=AW_ActivateNearest(-1,length3(fungus));
        printf("fungus before a resident: plant %.1f, actor %.1f..%.1f\n",item,near_hit,far_hit);
        assert(AW_ActivateItemFirst(item,near_hit,far_hit));
    }
    /* the ray and the box: a miss, a start inside, a parallel ray outside */
    {
        const float mins[3]={-1,-1,-1},maxs[3]={1,1,1},inside[3]={0,0,0},away[3]={-5,3,0},along[3]={1,0,0};
        assert(!AW_RayBox(away,along,mins,maxs,&near_hit,&far_hit));
        assert(AW_RayBox(inside,along,mins,maxs,&near_hit,&far_hit) && near_hit==0 && fabs(far_hit-1)<.0001f);
    }
    /* no actor: the item; neither: nothing; the nearer of an item and a plant */
    assert(AW_ActivateItemFirst(20,-1,-1));
    assert(AW_ActivateNearest(-1,-1)<0 && AW_ActivateNearest(12,30)==12 && AW_ActivateNearest(40,-1)==40);
    printf("activate rules ok\n");
    return 0;
}
