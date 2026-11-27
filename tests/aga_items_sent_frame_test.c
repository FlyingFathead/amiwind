/* Host fixture (tests/test_held_item_sent_frame.py): a held weapon stays on the hand of the frame an actor is sent
 * with, for every weapon class. One server frame in the engine's order: the driver sets the actor's frame inside the
 * layout's engine group and the items are posed from it (SV_Physics); the state pick moves the frame into the group
 * of the weapon's class just before the send; the items are posed again when aw_items.c's rule says they are stale
 * (AW_ItemsPreSend's test, AW_ItemsStale); the driver's frame comes back after the send. The pose here is a small
 * arm whose hand takes its own path in each group, standing in for the animation table; the item pose and the
 * rule are the engine's own (aw_items.c). */
#define AW_ITEMS_HOST_TEST
#include "aw_items.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

float Q_SinRad(float r) {return (float)sin(r);}
float Q_CosRad(float r) {return (float)cos(r);}
int AW_ItemsStale(int posed_frame,const float posed[4],int frame,const float origin[3],float yaw);
int AW_ItemsStanceGroup(const char *name);

/* the groups of the table: the layout's engine groups first (what the drivers set), then one per weapon class */
enum {G_IDLE,G_RUN,G_HANDTOHAND,G_ONEHAND,G_TWOHAND,G_TWOWIDE,G_BOW,G_CROSSBOW,G_THROWN,G_IDLE1H,G_RUN2W,GROUPS};
#define SPAN 16
static const char *const names[GROUPS]={"idle","runforward","handtohand","weapononehand","weapontwohand",
    "weapontwowide","bowandarrow","crossbow","throwweapon","idle1h","runforward2w"};

/* the Weapon Bone's tag (origin and angles in the model's space) at a table frame: each group swings the hand on its
 * own arc, at its own height and reach, so two groups never agree on where the hand is */
static void hand_tag(int frame,float tag[6]) {
    int g=frame/SPAN,i=frame%SPAN;
    float phase=(float)i/(float)(SPAN-1),reach=4.0f+2.5f*(float)g,turn=(0.5f+phase)*(0.7f+0.2f*(float)g);
    tag[0]=reach*(float)cos(turn);tag[1]=reach*(float)sin(turn);tag[2]=14.0f+1.5f*(float)g+6.0f*phase;
    tag[3]=10.0f*(float)g-40.0f*phase;tag[4]=25.0f*(float)g+90.0f*phase;tag[5]=5.0f*(float)g;
}

typedef struct {float frame,origin[3],yaw;} actor_t;
typedef struct {float origin[3],angles[3];int posed_frame;float posed_at[4];} item_t;

static void pose(const actor_t *a,item_t *it) {
    float tag[6];
    hand_tag((int)a->frame,tag);
    AW_ItemsPose(tag,a->origin,a->yaw,it->origin,it->angles);
    it->posed_frame=(int)a->frame;
    it->posed_at[0]=a->origin[0];it->posed_at[1]=a->origin[1];it->posed_at[2]=a->origin[2];it->posed_at[3]=a->yaw;
}
/* the distance of the item's grip from the hand of the frame the actor is sent with */
static float grip_gap(const actor_t *sent,const item_t *it) {
    float tag[6],o[3],a[3],d[3];
    hand_tag((int)sent->frame,tag);
    AW_ItemsPose(tag,sent->origin,sent->yaw,o,a);
    d[0]=it->origin[0]-o[0];d[1]=it->origin[1]-o[1];d[2]=it->origin[2]-o[2];
    return (float)sqrt(d[0]*d[0]+d[1]*d[1]+d[2]*d[2]);
}

/* one server frame; FOLLOW 0 is the order before the fix (the items keep the driver's frame). Returns the gap. */
static float server_frame(actor_t *a,item_t *it,int driver_frame,int picked_frame,int follow,int *posed_again) {
    float saved,gap;
    a->frame=(float)driver_frame;
    pose(a,it);                                 /* SV_Physics: the fight's AW_ItemsUpdate */
    saved=a->frame;a->frame=(float)picked_frame;  /* AW_AnimPickPreSend */
    *posed_again=0;
    if(follow && AW_ItemsStale(it->posed_frame,it->posed_at,(int)a->frame,a->origin,a->yaw)){pose(a,it);*posed_again=1;}
    gap=grip_gap(a,it);                         /* what the client draws */
    a->frame=saved;                             /* AW_AnimPickPostSend */
    return gap;
}

int main(void) {
    static const struct {const char *weapon;int attack,idle,run;} classes[]={
        {"one-handed (blade, axe, blunt)",G_ONEHAND,G_IDLE1H,G_RUN},
        {"two-handed close (blade, axe, blunt)",G_TWOHAND,G_IDLE,G_RUN},
        {"two-handed wide (spear, staff)",G_TWOWIDE,G_IDLE,G_RUN2W},
        {"bow",G_BOW,G_IDLE,G_RUN},
        {"crossbow",G_CROSSBOW,G_IDLE,G_RUN},
        {"thrown",G_THROWN,G_IDLE1H,G_RUN},
    };
    actor_t a={0,{512,-300,24},37};item_t it;
    int c,i,again,n=(int)(sizeof(classes)/sizeof(classes[0]));
    for(c=0;c<n;c++){
        float worst_old=0,worst_new=0,g;int reposed=0;
        /* the attack: the driver plays the layout's attack (the hand-to-hand chop), the pick the class's own group at
         * the same progress; then the fight's idle and run, picked into the class's stance groups */
        for(i=0;i<SPAN;i++){
            int drivers[3],picks[3],k;
            drivers[0]=G_HANDTOHAND*SPAN+i;picks[0]=classes[c].attack*SPAN+i;
            drivers[1]=G_IDLE*SPAN+i;picks[1]=classes[c].idle*SPAN+i;
            drivers[2]=G_RUN*SPAN+i;picks[2]=classes[c].run*SPAN+i;
            for(k=0;k<3;k++){
                g=server_frame(&a,&it,drivers[k],picks[k],0,&again);if(g>worst_old)worst_old=g;
                assert(!again);
                g=server_frame(&a,&it,drivers[k],picks[k],1,&again);if(g>worst_new)worst_new=g;
                reposed+=again;
                assert(again==(drivers[k]!=picks[k]));     /* posed again exactly when the pick moved the frame */
                assert(g<0.01f);                           /* the grip on the hand in every frame */
            }
        }
        printf("%-40s before %.2f units off, with the sent frame %.4f (%d poses again)\n",classes[c].weapon,
               worst_old,worst_new,reposed);
        assert(worst_old>1.0f);     /* the order before the fix fails this class: the weapon off its hand */
        assert(worst_new<0.01f);
    }
    {   /* the rule itself: the frame, each coordinate and the yaw */
        float at[4]={1,2,3,90},o[3]={1,2,3},m[3]={1,2,3.5f};
        assert(!AW_ItemsStale(7,at,7,o,90));
        assert(AW_ItemsStale(7,at,8,o,90) && AW_ItemsStale(7,at,7,m,90) && AW_ItemsStale(7,at,7,o,91));
        assert(AW_ItemsStale(-1,at,0,o,90));    /* a set not posed yet */
    }
    {   /* an actor moved after its items were posed (a later mover in the same frame) is followed too */
        float gap;
        a.frame=(float)(G_IDLE*SPAN);pose(&a,&it);a.origin[0]+=3;a.yaw+=45;
        assert(AW_ItemsStale(it.posed_frame,it.posed_at,(int)a.frame,a.origin,a.yaw));
        pose(&a,&it);gap=grip_gap(&a,&it);assert(gap<0.01f);
    }
    {   /* weapon stance groups take no storm arm layer: the hand stays on its weapon */
        static const char *const stance[]={"idle1h","idle2c","idle2w","idlehh","runforward1h","walkback2c","turnleft2w",
            "sneakrighthh","jump1h"};
        static const char *const plain[]={"idle","idle2","idle9","walkforward","runback","turnleft","sneakforward",
            "idlestorm","torch","weapononehand","handtohand","h","hh",""};
        for(i=0;i<(int)(sizeof(stance)/sizeof(stance[0]));i++)assert(AW_ItemsStanceGroup(stance[i]));
        for(i=0;i<(int)(sizeof(plain)/sizeof(plain[0]));i++)assert(!AW_ItemsStanceGroup(plain[i]));
        assert(!AW_ItemsStanceGroup(NULL));
        (void)names;
    }
    printf("items sent frame ok\n");
    return 0;
}
