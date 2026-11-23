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
void AW_AimEye(const float at[3],float dx,float dy,float lift,float eye[3],float *yaw,float *pitch){
    float flat;
    if(lift<0)lift=0;
    if(lift>AW_AIM_EYE-1)lift=AW_AIM_EYE-1;
    flat=(float)sqrt(AW_AIM_EYE*AW_AIM_EYE-lift*lift);
    eye[0]=at[0]+dx*flat;eye[1]=at[1]+dy*flat;eye[2]=at[2]+lift;
    *yaw=(float)(atan2(-dy,-dx)*180/3.14159265358979);
    *pitch=(float)(atan2(lift,flat)*180/3.14159265358979);
}
/* FOCUS-NPC-OVERRIDES-ITEM-62 (aw_activate.h): a person's use box from his body, not from the every-pose box */
int AW_ActorPersonHull(const float mins[3],const float maxs[3]){
    static const float lo[3]={-AW_PERSON_HALF_X,-AW_PERSON_HALF_Y,0},hi[3]={AW_PERSON_HALF_X,AW_PERSON_HALF_Y,AW_PERSON_TOP};
    int j;
    if(!mins || !maxs)return 0;
    for(j=0;j<3;j++)if(fabs(mins[j]-lo[j])>0.01f || fabs(maxs[j]-hi[j])>0.01f)return 0;
    return 1;
}
int AW_ActorUseBox(int frames,int dead,int person,float scale,const float mins[3],const float maxs[3],float out_mins[3],
                   float out_maxs[3]){
    float lo[3],hi[3],half;int j;
    for(j=0;j<3;j++){lo[j]=mins[j];hi[j]=maxs[j];}   /* read first: OUT may be the stored box itself */
    for(j=0;j<3;j++){out_mins[j]=lo[j];out_maxs[j]=hi[j];}
    if(frames!=1 || !person)return AW_USEBOX_STORED;
    if(!(scale>0.01f && scale<64.0f))scale=1;
    if(dead){
        if(lo[2]+AW_BODY_TOP*scale<hi[2])out_maxs[2]=lo[2]+AW_BODY_TOP*scale;
        return AW_USEBOX_LYING;
    }
    /* a stored box beside the origin (a model drawn off its feet) is kept whole */
    for(j=0;j<2;j++){
        half=(j?AW_PERSON_HALF_Y:AW_PERSON_HALF_X)*scale;
        if(lo[j]>half || hi[j]<-half)return AW_USEBOX_STORED;
    }
    for(j=0;j<2;j++){
        half=(j?AW_PERSON_HALF_Y:AW_PERSON_HALF_X)*scale;
        if(lo[j]<-half)out_mins[j]=-half;
        if(hi[j]>half)out_maxs[j]=half;
    }
    return AW_USEBOX_BODY;
}
float AW_FocusDistance(const aw_focus_aim_t *aim,int kind){
    if(!aim)return -1;
    switch(kind){
    case AW_FOCUS_ACTOR:return aim->actor_far<0?-1:aim->actor_near;
    case AW_FOCUS_THING:return aim->thing;
    case AW_FOCUS_DOOR:return aim->door;
    case AW_FOCUS_HINGED:return aim->hinged;
    }
    return -1;
}
/* HUD-TEXTS-OVERLAP-67 (aw_activate.h): the kinds in the order a tie goes */
int AW_FocusChoose(const aw_focus_aim_t *aim,int previous){
    static const int order[4]={AW_FOCUS_ACTOR,AW_FOCUS_THING,AW_FOCUS_HINGED,AW_FOCUS_DOOR};
    float d,best_d=-1,held;int i,best=AW_FOCUS_NONE,actor_out;
    if(!aim)return AW_FOCUS_NONE;
    /* an item or plant before the actor or inside his box takes him out of the choice (FOCUS-NPC-OVERRIDES-ITEM-62);
     * FOCUS-EYE-INSIDE-ACTOR-BOX-68: so does a load or hinged door the ray meets while the eye is INSIDE the actor's use
     * box (its entry 0): the box then says nothing of where his body is along the ray, and the original's focus is what
     * the crosshair ray meets first (OpenMW World::getFacedObject, a ray against the drawn meshes). A creature whose
     * drawn box is far wider than its body (a dreugh beside the sunken Unmarked Shipwreck, its box 0..50 around the
     * swimmer's eye) kept the focus from the trapdoor the crosshair was on (20 units off), and E did nothing. */
    actor_out=aim->actor_far<0 || AW_ActivateItemFirst(aim->thing,aim->actor_near,aim->actor_far) ||
              (aim->actor_near<=0 && (aim->door>=0 || aim->hinged>=0));
    for(i=0;i<4;i++){
        if(order[i]==AW_FOCUS_ACTOR && actor_out)continue;
        d=AW_FocusDistance(aim,order[i]);
        if(d<0)continue;
        if(best==AW_FOCUS_NONE || d<best_d){best=order[i];best_d=d;}
    }
    /* the frame before's kind stays while it is still met and the new one is not clearly nearer */
    if(best!=AW_FOCUS_NONE && previous!=best && previous>AW_FOCUS_NONE && previous<AW_FOCUS_KINDS &&
       !(previous==AW_FOCUS_ACTOR && actor_out) && (held=AW_FocusDistance(aim,previous))>=0 && held-best_d<AW_FOCUS_HOLD)
        return previous;
    return best;
}
