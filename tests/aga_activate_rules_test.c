/* FOCUS-NPC-OVERRIDES-ITEM-62: what the use key acts on, by number (engine/aga/src/aw_activate_rules.c). As in OpenMW
 * 0.51 the nearest thing along the view ray within the activation distance takes the use, never the nearest actor.
 * Map units; the eye at 0 0 0, the actor's box in his own frame (not turned here). */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include "aw_activate.h"

static float length3(const float v[3]){return (float)sqrt(v[0]*v[0]+v[1]*v[1]+v[2]*v[2]);}
/* The view ray from EYE (Quake's view angles: YAW, PITCH down positive) into the frame of an actor standing at AT
 * turned ACTOR_YAW, as aw_scene.c AW_NPCTargetReach turns it (AngleVectors: forward, right, up; y = -right). */
static void turned_ray(const float eye[3],float yaw,float pitch,const float at[3],float actor_yaw,float origin[3],
                       float dir[3]){
    const float d2r=(float)(3.14159265358979/180);
    float cy=(float)cos(yaw*d2r),sy=(float)sin(yaw*d2r),cp=(float)cos(pitch*d2r),sp=(float)sin(pitch*d2r);
    float ay=(float)cos(actor_yaw*d2r),by=(float)sin(actor_yaw*d2r);
    float f[3],delta[3],fwd[3],right[3];int j;
    f[0]=cp*cy;f[1]=cp*sy;f[2]=-sp;
    fwd[0]=ay;fwd[1]=by;fwd[2]=0;right[0]=by;right[1]=-ay;right[2]=0;
    for(j=0;j<3;j++)delta[j]=eye[j]-at[j];
    dir[0]=f[0]*fwd[0]+f[1]*fwd[1];dir[1]=-(f[0]*right[0]+f[1]*right[1]);dir[2]=f[2];
    origin[0]=delta[0]*fwd[0]+delta[1]*fwd[1];origin[1]=-(delta[0]*right[0]+delta[1]*right[1]);origin[2]=delta[2];
}
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
    /* 4. HUD-TEXTS-OVERLAP-67: ONE focus a frame (AW_FocusChoose): the title, the action line and E all go to it */
    {
        aw_focus_aim_t a;
        /* Sellus Gravius in front of the Seyda Neen door (the maintainer's picture): his box 40..60, the door 70 behind
         * him. Before, both names were drawn and E opened the door; now he alone has the focus and E talks to him */
        a.actor_near=40;a.actor_far=60;a.thing=-1;a.door=70;a.hinged=-1;
        assert(AW_FocusChoose(&a,AW_FOCUS_NONE)==AW_FOCUS_ACTOR);
        /* also when the door had the focus the frame before (he stepped in front of it) */
        assert(AW_FocusChoose(&a,AW_FOCUS_DOOR)==AW_FOCUS_ACTOR);
        /* beside the door, the ray meets only the door: the door */
        a.actor_near=a.actor_far=-1;
        assert(AW_FocusChoose(&a,AW_FOCUS_NONE)==AW_FOCUS_DOOR);
        /* the door before him (he stands past the doorway): the door */
        a.actor_near=80;a.actor_far=100;a.door=50;
        assert(AW_FocusChoose(&a,AW_FOCUS_NONE)==AW_FOCUS_DOOR && AW_FocusChoose(&a,AW_FOCUS_ACTOR)==AW_FOCUS_DOOR);
        /* an item between the player and an NPC: the item, whoever had the focus before */
        a.actor_near=50;a.actor_far=70;a.thing=35;a.door=-1;
        assert(AW_FocusChoose(&a,AW_FOCUS_NONE)==AW_FOCUS_THING && AW_FocusChoose(&a,AW_FOCUS_ACTOR)==AW_FOCUS_THING);
        /* an item beside a corpse, inside its lying box: the item */
        a.actor_near=30;a.actor_far=90;a.thing=46;
        assert(AW_FocusChoose(&a,AW_FOCUS_ACTOR)==AW_FOCUS_THING);
        /* a mushroom on a tree trunk with an NPC near it whose box the ray enters first: the mushroom inside his box is
         * picked; one past his box is behind him, he is talked to */
        a.actor_near=20;a.actor_far=40;a.thing=33;
        assert(AW_FocusChoose(&a,AW_FOCUS_NONE)==AW_FOCUS_THING);
        a.thing=45;
        assert(AW_FocusChoose(&a,AW_FOCUS_NONE)==AW_FOCUS_ACTOR && AW_FocusChoose(&a,AW_FOCUS_THING)==AW_FOCUS_ACTOR);
        /* the hold: an animated actor's box 2 units behind the door's hit keeps a focus he had, never the other way
         * once the door is clearly nearer */
        a.actor_near=52;a.actor_far=70;a.thing=-1;a.door=50;
        assert(AW_FocusChoose(&a,AW_FOCUS_NONE)==AW_FOCUS_DOOR);
        assert(AW_FocusChoose(&a,AW_FOCUS_ACTOR)==AW_FOCUS_ACTOR);
        a.door=40;
        assert(AW_FocusChoose(&a,AW_FOCUS_ACTOR)==AW_FOCUS_DOOR);
        /* FOCUS-EYE-INSIDE-ACTOR-BOX-68: the eye inside a creature's use box (a dreugh beside the sunken shipwreck,
         * entry 0, exit 50) and the trapdoor 20 along the ray: the trapdoor, whatever had the focus before; a hinged
         * door likewise; with no door met he keeps it (E still acts on him), and from outside his box he is nearer */
        a.actor_near=0;a.actor_far=50.4f;a.thing=-1;a.door=20.1f;a.hinged=-1;
        assert(AW_FocusChoose(&a,AW_FOCUS_NONE)==AW_FOCUS_DOOR && AW_FocusChoose(&a,AW_FOCUS_ACTOR)==AW_FOCUS_DOOR);
        a.door=-1;a.hinged=12;
        assert(AW_FocusChoose(&a,AW_FOCUS_ACTOR)==AW_FOCUS_HINGED);
        a.hinged=-1;
        assert(AW_FocusChoose(&a,AW_FOCUS_NONE)==AW_FOCUS_ACTOR);
        a.actor_near=5;a.door=20.1f;
        assert(AW_FocusChoose(&a,AW_FOCUS_NONE)==AW_FOCUS_ACTOR);
        /* a hinged door and a load door at one distance: the hinged door; nothing met: none */
        a.actor_near=a.actor_far=-1;a.door=30;a.hinged=30;
        assert(AW_FocusChoose(&a,AW_FOCUS_NONE)==AW_FOCUS_HINGED);
        a.door=a.hinged=-1;
        assert(AW_FocusChoose(&a,AW_FOCUS_ACTOR)==AW_FOCUS_NONE && AW_FocusChoose(NULL,AW_FOCUS_NONE)==AW_FOCUS_NONE);
        assert(AW_FocusDistance(&a,AW_FOCUS_ACTOR)<0 && AW_FocusDistance(&a,AW_FOCUS_NONE)<0);
        printf("one focus a frame: Gravius before the door, item before an NPC, item by a body, mushroom by an NPC ok\n");
    }
    /* 5. DBG-CONTAINER-AIM-OUT-OF-REACH-67: the check command's view of a container (aw_placed container aim): the eye
     * 24 units from the row's point (the centre of its box), looking at it. The Ornate Dwemer Chest of Bamz-Amschend,
     * Hall of Winds (its box 6.2 x 2.9 x 2.9 half axes, map units) is met well within the 48-unit reach from every side
     * and lift tried; from the old stand point (40 out over the floor, the eye 44 above the point, looking 8 above it)
     * the view ray met the room's box of it at 54 and the use took nothing. */
    {
        const float at[3]={1346.5f,1351.5f,3139.8f},half[3]={6.2f,2.9f,2.9f},lifts[4]={12,6,18,0};
        float eye[3],yaw,pitch,f[3],lo[3],hi[3],d[3],t;int j,k,l;
        float dx=1,dy=0;
        for(j=0;j<3;j++){lo[j]=at[j]-half[j];hi[j]=at[j]+half[j];}
        for(k=0;k<16;k++,t=dx*0.92388f-dy*0.38268f,dy=dx*0.38268f+dy*0.92388f,dx=t)
            for(l=0;l<4;l++){
                AW_AimEye(at,dx,dy,lifts[l],eye,&yaw,&pitch);
                for(j=0;j<3;j++)d[j]=at[j]-eye[j];
                assert(fabs(length3(d)-AW_AIM_EYE)<.01f);                       /* 24 from the point */
                f[0]=(float)(cos(pitch*3.14159265/180)*cos(yaw*3.14159265/180));
                f[1]=(float)(cos(pitch*3.14159265/180)*sin(yaw*3.14159265/180));
                f[2]=(float)(-sin(pitch*3.14159265/180));                       /* Quake: +pitch looks down */
                assert(fabs(f[0]*d[0]+f[1]*d[1]+f[2]*d[2]-AW_AIM_EYE)<.01f);   /* the view on the point */
                assert(fabs(eye[2]-at[2]-lifts[l])<.01f && pitch>=0 && pitch<50);
                assert(AW_RayBox(eye,f,lo,hi,&near_hit,&far_hit) && near_hit<AW_AIM_EYE && near_hit<48);
            }
        /* the eye on the +x side looks back along -x */
        AW_AimEye(at,1,0,12,eye,&yaw,&pitch);
        assert(fabs(fabs(yaw)-180)<.01f && fabs(pitch-30)<.01f && fabs(eye[0]-at[0]-20.78f)<.01f);
        /* a lift past the distance is held under it (the view never straight down) */
        AW_AimEye(at,0,1,30,eye,&yaw,&pitch);assert(eye[2]-at[2]<AW_AIM_EYE && eye[1]>at[1] && pitch<90);
        /* the old stand point: 40 out, the eye 44 above the point, looking 8 above it: the box is past the reach */
        {
            float old_eye[3],aim[3],n;
            old_eye[0]=at[0]+40;old_eye[1]=at[1];old_eye[2]=at[2]+44;
            aim[0]=at[0];aim[1]=at[1];aim[2]=at[2]+8;
            for(j=0;j<3;j++)f[j]=aim[j]-old_eye[j];
            n=length3(f);for(j=0;j<3;j++)f[j]/=n;
            assert(!AW_RayBox(old_eye,f,lo,hi,&near_hit,&far_hit) || near_hit>48);
        }
        printf("container aim view: 24 from the point, met within the reach from 16 sides and 4 lifts ok\n");
    }
    /* 6. FOCUS-NPC-OVERRIDES-ITEM-62, a person's use box from his body (AW_ActorUseBox). Aleri Aren in the Mournhold
     * Guards' Quarters: her model stores ONE frame (a skeletal actor, the default since v0.0.52) whose box encloses
     * every pose (the census office's Fargoth's stored range: -23.5..39.4 by -40.2..36.8 by -2.5..33.9); she stands at
     * -27 158 -32 turned 280 degrees. The player arrives at the eye -59 128 0 and aims at the door back to the
     * courtyard (yaw 180, pitch 13.9; the door 35.5 along the ray). The stored box holds the eye: the ray starts inside
     * it (0.0, the session's "actor 0.0..3.8") and she took the use; her body's box lies 36 units off: the door. */
    {
        const float eye[3]={-59,128,0},at[3]={-27,158,-32};
        const float stored_lo[3]={-23.5f,-40.2f,-2.5f},stored_hi[3]={39.4f,36.8f,33.9f};
        float origin[3],dir[3],lo[3],hi[3],body_near,body_far;aw_focus_aim_t a;
        turned_ray(eye,180.0f,13.9f,at,280.0f,origin,dir);
        /* the old box: met at the eye */
        assert(AW_RayBox(origin,dir,stored_lo,stored_hi,&near_hit,&far_hit) && near_hit==0 && far_hit<5);
        a.actor_near=near_hit;a.actor_far=far_hit;a.thing=-1;a.door=35.5f;a.hinged=-1;
        /* FOCUS-EYE-INSIDE-ACTOR-BOX-68: even with that old box the door has it now (a box that holds the eye says
         * nothing of where the body is along the ray); before that rule this was the actor */
        assert(AW_FocusChoose(&a,AW_FOCUS_NONE)==AW_FOCUS_DOOR);
        printf("Aleri Aren, stored box: actor %.1f..%.1f around the eye, the door at 35.5: the door\n",near_hit,far_hit);
        /* the new box: her body, the stored height */
        assert(AW_ActorUseBox(1,0,1,1.0f,stored_lo,stored_hi,lo,hi)==AW_USEBOX_BODY);
        assert(lo[0]==-AW_PERSON_HALF_X && hi[0]==AW_PERSON_HALF_X && lo[1]==-AW_PERSON_HALF_Y && hi[1]==AW_PERSON_HALF_Y);
        assert(lo[2]==stored_lo[2] && hi[2]==stored_hi[2]);
        assert(!AW_RayBox(origin,dir,lo,hi,&near_hit,&far_hit));
        a.actor_near=a.actor_far=-1;
        assert(AW_FocusChoose(&a,AW_FOCUS_NONE)==AW_FOCUS_DOOR && AW_FocusChoose(&a,AW_FOCUS_ACTOR)==AW_FOCUS_DOOR);
        /* aimed at her (yaw 43.2, pitch 10.3): still met, where the ray reaches her body, within the talk's 72 */
        turned_ray(eye,43.2f,10.3f,at,280.0f,origin,dir);
        assert(AW_RayBox(origin,dir,stored_lo,stored_hi,&near_hit,&far_hit) && near_hit==0);
        assert(AW_RayBox(origin,dir,lo,hi,&body_near,&body_far) && body_near>30 && body_near<40 && body_far>body_near);
        a.actor_near=body_near;a.actor_far=body_far;a.door=-1;
        assert(AW_FocusChoose(&a,AW_FOCUS_NONE)==AW_FOCUS_ACTOR);
        printf("Aleri Aren, her body: the door aim misses her, aimed at her %.1f..%.1f\n",body_near,body_far);
        /* the same from her other side, turned 100 degrees (the box turns with her): the door again */
        turned_ray(eye,180.0f,13.9f,at,100.0f,origin,dir);
        assert(!AW_RayBox(origin,dir,lo,hi,&near_hit,&far_hit));
    }
    /* the rule's other cases: more than one frame, a creature, frames not known keep the stored box; a body lies low;
     * the scale; never wider than the stored box; a stored box beside the origin kept whole; the person's hull */
    {
        const float st_lo[3]={-30,-30,-2},st_hi[3]={30,30,40},narrow_lo[3]={-5,-3,0},narrow_hi[3]={5,20,30};
        const float off_lo[3]={10,-4,0},off_hi[3]={40,4,30};
        const float hull_lo[3]={-7.32f,-7.12f,0},hull_hi[3]={7.32f,7.12f,33.25f};
        const float player_lo[3]={-7.32f,-7.12f,-16.625f},player_hi[3]={7.32f,7.12f,16.625f},none[3]={0,0,0};
        float lo[3],hi[3],box_lo[3],box_hi[3];int j;
        assert(AW_ActorUseBox(2,0,1,1,st_lo,st_hi,lo,hi)==AW_USEBOX_STORED && lo[0]==-30 && hi[1]==30 && hi[2]==40);
        assert(AW_ActorUseBox(0,0,1,1,st_lo,st_hi,lo,hi)==AW_USEBOX_STORED && lo[1]==-30);
        assert(AW_ActorUseBox(1,0,0,1,st_lo,st_hi,lo,hi)==AW_USEBOX_STORED && hi[0]==30);
        assert(AW_ActorUseBox(2,1,1,1,st_lo,st_hi,lo,hi)==AW_USEBOX_STORED && hi[2]==40);
        /* a body: x and y kept, the top 8 over the stored floor (-2 + 8); twice the size: 16 */
        assert(AW_ActorUseBox(1,1,1,1,st_lo,st_hi,lo,hi)==AW_USEBOX_LYING);
        assert(lo[0]==-30 && hi[0]==30 && lo[1]==-30 && hi[1]==30 && lo[2]==-2 && fabs(hi[2]-6)<.001f);
        assert(AW_ActorUseBox(1,1,1,2,st_lo,st_hi,lo,hi)==AW_USEBOX_LYING && fabs(hi[2]-14)<.001f);
        /* twice his size: 14.64 by 14.24; a bad scale counts as 1 */
        assert(AW_ActorUseBox(1,0,1,2,st_lo,st_hi,lo,hi)==AW_USEBOX_BODY && fabs(hi[0]-14.64f)<.001f && fabs(lo[1]+14.24f)<.001f);
        assert(AW_ActorUseBox(1,0,1,0,st_lo,st_hi,lo,hi)==AW_USEBOX_BODY && hi[0]==AW_PERSON_HALF_X);
        /* never wider than the stored box (a child's, 10 wide) */
        assert(AW_ActorUseBox(1,0,1,1,narrow_lo,narrow_hi,lo,hi)==AW_USEBOX_BODY);
        assert(lo[0]==-5 && hi[0]==5 && lo[1]==-3 && hi[1]==AW_PERSON_HALF_Y && hi[2]==30);
        /* a stored box beside the origin: kept whole */
        assert(AW_ActorUseBox(1,0,1,1,off_lo,off_hi,lo,hi)==AW_USEBOX_STORED && lo[0]==10 && hi[0]==40);
        /* the stored box as its own output (aw_scene.c narrows in place) */
        for(j=0;j<3;j++){box_lo[j]=st_lo[j];box_hi[j]=st_hi[j];}
        assert(AW_ActorUseBox(1,0,1,1,box_lo,box_hi,box_lo,box_hi)==AW_USEBOX_BODY);
        assert(box_lo[0]==-AW_PERSON_HALF_X && box_hi[1]==AW_PERSON_HALF_Y && box_lo[2]==-2 && box_hi[2]==40);
        /* the person's hull: world.qc aw_npc_floor's; not the player's centred one, not the 0 0 0 before aw_npc_floor */
        assert(AW_ActorPersonHull(hull_lo,hull_hi));
        assert(!AW_ActorPersonHull(player_lo,player_hi) && !AW_ActorPersonHull(none,none) && !AW_ActorPersonHull(NULL,hull_hi));
        printf("a person's use box: one frame narrowed, a body low, creatures and more frames as stored ok\n");
    }
    /* 7. PLANT-BOX-AIM-69: a container aimed by its measured box (a plant's box holds its leaves and stems whole) gives
     * way to what the view ray meets inside that box. Numbers from the three masters (game units, the boxes as
     * tools/prepare_focus.py CONTAINER_BOXES measures them, turned by nothing here): */
    {
        /* a Slough Fern west of Seyda Neen (flora_bc_fern_01: half axes 174 x 158.6 x 103, centre 0 0 0) with a
         * Bungler's Bane growing in it 60 to the side; the eye 300 out on the fern's +x side, 80 up */
        const float fern[3]={0,0,0},fern_axis[3][3]={{174,0,0},{0,158.6f,0},{0,0,103}};
        const float mushroom[3]={-20,60,-70},behind[3]={-260,0,0},beside[3]={0,190,0},corner[3]={174,158.6f,103};
        const float eye[3]={300,0,80};
        float dir[3],n,fern_hit,mushroom_hit;int j;
        for(j=0;j<3;j++)dir[j]=mushroom[j]-eye[j];
        n=length3(dir);for(j=0;j<3;j++)dir[j]/=n;
        mushroom_hit=n;
        /* the ray enters the fern's box first (its +x face, about 141 from the eye), the mushroom lies 358 along it */
        {float lo[3],hi[3];for(j=0;j<3;j++){lo[j]=fern[j]-fern_axis[j][j];hi[j]=fern[j]+fern_axis[j][j];}
         assert(AW_RayBox(eye,dir,lo,hi,&fern_hit,&far_hit) && fern_hit<mushroom_hit && mushroom_hit<far_hit);}
        printf("fern box at %.1f, the mushroom in it at %.1f\n",fern_hit,mushroom_hit);
        assert(AW_BoxHolds(fern,fern_axis,mushroom) && AW_BoxHolds(fern,fern_axis,fern) && AW_BoxHolds(fern,fern_axis,corner));
        assert(!AW_BoxHolds(fern,fern_axis,behind) && !AW_BoxHolds(fern,fern_axis,beside));
        /* a degenerate box holds nothing, not even its centre */
        {const float flat[3][3]={{174,0,0},{0,0,0},{0,0,103}};assert(!AW_BoxHolds(fern,flat,fern));}
        assert(!AW_BoxHolds(NULL,fern_axis,fern) && !AW_BoxHolds(fern,fern_axis,NULL));
        /* the plant to pick inside the fern's box takes the use from the fern, nearer or not (before: the fern, an item
         * or container always went first); with no box around it, the nearer: */
        assert(AW_PlantFirst(fern_hit,mushroom_hit,1));
        assert(!AW_PlantFirst(fern_hit,mushroom_hit,0));
        assert(AW_PlantFirst(90,40,0) && !AW_PlantFirst(40,90,0) && AW_PlantFirst(-1,40,0) && !AW_PlantFirst(40,-1,1));
        assert(!AW_PlantFirst(-1,-1,0));
        /* among the placed rows (placed_target): the fern met first (none before it) takes the aim; the mushroom's own
         * row (a harvest kind keeps one, aimed at its point) met farther but inside the fern's box takes it from the
         * fern; and the other way round, the fern met nearer does not take it from the mushroom standing in it */
        assert(AW_AimTakes(fern_hit,48*4,48*4,0,0,0));
        assert(AW_AimTakes(mushroom_hit,fern_hit,1e9f,1,1,0));
        assert(!AW_AimTakes(fern_hit,mushroom_hit,1e9f,1,0,1));
        /* a chest behind the fern, outside its box: the fern hides it (the nearer keeps the aim), as before */
        assert(!AW_AimTakes(400,fern_hit,1e9f,1,0,0));
        /* no box around either: the nearer, a tie to the later row (as placed_target always did), never past the reach */
        assert(AW_AimTakes(30,40,48,1,0,0) && !AW_AimTakes(50,40,48,1,0,0) && AW_AimTakes(40,40,48,1,0,0));
        assert(!AW_AimTakes(60,48,48,0,0,0) && !AW_AimTakes(60,40,48,1,1,0) && !AW_AimTakes(-1,40,48,1,1,0));
    }
    {
        /* Shara Atinsabia standing in a Hackle-lo by the road (flora_hackle-lo_01, half axes 96.1 x 96.2 x 128.5), a
         * signpost board inside a Trama Root's box on the road west of Balmora (contain_tramaroot_01, 116 x 42.8 x 56.1):
         * the focus choice is made after the box gave way (aw_scene.c focus_kind sets the thing to -1 when the actor's
         * or the door's point lies inside the box of the container aimed at): the actor or the door, as without the plant */
        aw_focus_aim_t a;
        a.actor_near=60;a.actor_far=75;a.thing=20;a.door=-1;a.hinged=-1;
        assert(AW_FocusChoose(&a,AW_FOCUS_NONE)==AW_FOCUS_THING);        /* the box would take her focus */
        a.thing=-1;
        assert(AW_FocusChoose(&a,AW_FOCUS_NONE)==AW_FOCUS_ACTOR && AW_FocusChoose(&a,AW_FOCUS_THING)==AW_FOCUS_ACTOR);
        a.actor_near=a.actor_far=-1;a.door=55;
        assert(AW_FocusChoose(&a,AW_FOCUS_THING)==AW_FOCUS_DOOR);
        printf("plant boxes: the mushroom in the fern, a person and a door in a plant's box ok\n");
    }
    printf("activate rules ok\n");
    return 0;
}
