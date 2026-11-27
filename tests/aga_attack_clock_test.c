/* SPDX-License-Identifier: GPL-2.0-or-later
 * ACTOR-ATTACK-ONE-CLOCK-69: a fighter's swing or shot timed by the group it is seen to play (aw_animpick_rules.inc:
 * AW_AnimPick's hit key, AW_PickAttackClock), on the real text-key times of base_anim.nif (the original's common
 * skeleton) turned into table frames the way the builder writes them (tools/skeletal_actor.py text_keys: the group's
 * first frame plus round((key - the group's first key) x rate), at the table's 8 frames a second).
 *
 * Before: every swing ran on one clock, the layout's attack group (a person's hand-to-hand chop, 8 table frames, 1 s,
 * the blow at 0.714 of it, the share of its own keys), while the picture played the weapon's own group stretched onto
 * that clock. So the frame on screen when the blow landed was not the group's hit frame for 11 of these 15 attacks (a
 * one-handed thrust two frames past it, a crossbow six), and every class and type took the same second. Now each
 * span's own time, at the weapon's speed, and its hit key's share: the hit frame is on screen when the blow lands. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "aw_animpick.h"

#define RATE 8.f                 /* the shared tables' frames a second (tools/skeletal_actor.py TABLE_RATE) */
/* the old clock: the hand-to-hand chop's own share (its hit key 304.1333 between 303.4667 and 304.4) */
#define OLD_SHARE ((304.1333-303.4667)/(304.4-303.4667))

/* the common humanoid table's weapon groups (progs/humanoid.awsk; no shortbladeonehand, bluntonehand, blunttwohand:
 * the pick falls back as OpenMW does) */
static int humanoid_has(void *context,const char *n) {
    static const char *const g[]={"handtohand","weapononehand","weapontwohand","weapontwowide","bowandarrow","crossbow",
        "throwweapon","idle",0};
    int i;(void)context;
    for(i=0;g[i];i++)if(!strcmp(g[i],n))return 1;
    return 0;
}
/* a creature's own table: attack1..3, no weapon group */
static int creature_has(void *context,const char *n) {
    (void)context;return !strcmp(n,"attack1") || !strcmp(n,"attack2") || !strcmp(n,"attack3") || !strcmp(n,"idle");
}
static int frame_of(double first,double t) {return (int)floor((t-first)*RATE+.5);}

typedef struct {
    const char *group;int weapon,attack;
    double first,start,hit,stop;   /* the group's first key, "<type> start", "<type> hit" or "shoot release", the stop */
    int span,at,old_off;           /* expected: frames start..stop, start..hit, and the old clock's frame at its blow
                                    * minus the hit frame */
} row_t;
static const row_t rows[]={
    {"handtohand",AW_PW_HANDTOHAND,AW_PA_CHOP,  299.0667,303.4667,304.1333,304.4,     8, 6, 0},
    {"handtohand",AW_PW_HANDTOHAND,AW_PA_SLASH, 299.0667,299.6,   300.1333,300.7333,  9, 5, 1},
    {"handtohand",AW_PW_HANDTOHAND,AW_PA_THRUST,299.0667,301.7333,302.2,   302.6667,  8, 4, 2},
    {"weapononehand",1,AW_PA_CHOP,              313.4,   315.9333,316.7333,317.1333, 10, 7, 0},
    {"weapononehand",1,AW_PA_SLASH,             313.4,   313.9333,314.7333,315.0667,  9, 7,-1},
    {"weapononehand",1,AW_PA_THRUST,            313.4,   318.0,   318.5334,319.0,     8, 4, 2},
    {"weapontwohand",2,AW_PA_CHOP,              320.8,   321.2,   322.0,   322.3333,  9, 7,-1},
    {"weapontwohand",2,AW_PA_SLASH,             320.8,   323.2667,324.0,   324.4,     9, 6, 0},
    {"weapontwohand",2,AW_PA_THRUST,            320.8,   325.2667,325.9333,326.2667,  8, 5, 1},
    {"weapontwowide",6,AW_PA_CHOP,              327.4,   327.8,   328.4,   328.7333,  8, 5, 1},
    {"weapontwowide",6,AW_PA_SLASH,             327.4,   329.5334,330.0667,330.4667,  8, 4, 2},
    {"weapontwowide",6,AW_PA_THRUST,            327.4,   331.4,   331.8667,332.2,     6, 4, 0},
    {"bowandarrow",9,AW_PA_CHOP,                308.4667,309.0,   310.4667,310.9333, 16,12,-1},
    {"crossbow",10,AW_PA_CHOP,                  305.6667,306.2,   306.5334,307.7333, 13, 3, 6},
    {"throwweapon",11,AW_PA_CHOP,               311.2,   311.6667,312.0,   312.5334,  7, 2, 3},
};

static void attack(int weapon,int type,aw_pick_has_t has,aw_pick_t *o) {
    aw_pick_state_t s;memset(&s,0,sizeof(s));
    s.weapon=(signed char)weapon;s.event=AW_PE_ATTACK;s.attack=(unsigned char)type;s.follow=AW_PF_LARGE;
    assert(AW_AnimPick(&s,has,NULL,o));
}

int main(void) {
    static const char *const types[3]={"chop","slash","thrust"};
    aw_pick_t o;float sec,share;int i,w,off=0;char key[40];
    const int n=(int)(sizeof(rows)/sizeof(rows[0]));
    printf("attack            old: s / blow s / frame vs hit | new: s / blow s / share / at speed 1.5 s\n");
    for(i=0;i<n;i++){
        const row_t *r=&rows[i];int from=frame_of(r->first,r->start),hit=frame_of(r->first,r->hit),to=frame_of(r->first,r->stop);
        int shown,old_shown,ranged=r->weapon>=9;float fast,fast_share,old_sec;
        /* the pick: the group, its span's keys and the hit key the blow lands on */
        attack(r->weapon,r->attack,humanoid_has,&o);
        assert(!strcmp(o.group,r->group));
        if(ranged){assert(!strcmp(o.start,"shoot start") && !strcmp(o.stop,"shoot follow stop") && !strcmp(o.hit,"shoot release"));}
        else{
            snprintf(key,sizeof(key),"%s start",types[r->attack]);assert(!strcmp(o.start,key));
            snprintf(key,sizeof(key),"%s large follow stop",types[r->attack]);assert(!strcmp(o.stop,key));
            snprintf(key,sizeof(key),"%s hit",types[r->attack]);assert(!strcmp(o.hit,key));
        }
        /* the clock of that span: its own time at the table's rate, the hit key's share */
        assert(to-from==r->span && hit-from==r->at);
        assert(AW_PickAttackClock(from,hit,to,RATE,1,&sec,&share));
        assert(sec==(float)r->span/RATE && fabsf(share-(float)r->at/(float)r->span)<1e-6f);
        /* within a frame of the original's own key times (each key is rounded to a frame: half a frame each) */
        assert(fabs(sec-(r->stop-r->start))<=1/RATE+1e-4 && fabs(sec*share-(r->hit-r->start))<=1/RATE+1e-4);
        /* the picture: the pick shows FROM + progress x (TO - FROM); at the blow (progress = share) the hit frame */
        shown=from+(int)(share*(float)(to-from)+.5f);
        assert(shown==hit);
        /* the weapon's speed scales the time, never the share */
        assert(AW_PickAttackClock(from,hit,to,RATE,1.5f,&fast,&fast_share));
        assert(fabsf(fast-sec/1.5f)<1e-6f && fast_share==share);
        /* the old clock: every attack on the hand-to-hand chop's 8 frames (1 s) with the blow at its share */
        old_sec=8/RATE;
        old_shown=from+(int)((float)OLD_SHARE*(float)(to-from)+.5f);
        assert(old_shown-hit==r->old_off);
        if(old_shown!=hit)off++;
        printf("%-13s %-6s %.3f / %.3f / %+d     | %.3f / %.3f / %.3f / %.3f\n",r->group,ranged?"shoot":types[r->attack],
               (double)old_sec,(double)(old_sec*(float)OLD_SHARE),old_shown-hit,(double)sec,(double)(sec*share),(double)share,(double)fast);
    }
    assert(off==11);   /* the old clock showed another frame than the hit frame at the blow for 11 of the 15 */
    /* the weapon classes the base table has no own group for take the pick's fallback, with its keys and clock */
    {static const struct {int weapon;const char *group;} fallback[]={{0,"weapononehand"},{3,"weapononehand"},
         {7,"weapononehand"},{4,"weapontwohand"},{8,"weapontwohand"},{5,"weapontwowide"}};
     for(w=0;w<(int)(sizeof(fallback)/sizeof(fallback[0]));w++){
         attack(fallback[w].weapon,AW_PA_THRUST,humanoid_has,&o);
         assert(!strcmp(o.group,fallback[w].group) && !strcmp(o.hit,"thrust hit"));
     }}
    /* a creature's own attackN (its picture rolled at the send) names no hit key: the fight keeps its layout's clock */
    attack(AW_PW_HANDTOHAND,AW_PA_SLASH,creature_has,&o);
    assert(!strncmp(o.group,"attack",6) && !o.hit[0]);
    /* every other pick names none either */
    {aw_pick_state_t s;memset(&s,0,sizeof(s));s.weapon=AW_PW_NONE;s.event=AW_PE_HIT;
     assert(!AW_AnimPick(&s,humanoid_has,NULL,&o) || !o.hit[0]);}
    /* refused: a key missing, keys out of order, an empty span, no rate or speed */
    assert(!AW_PickAttackClock(-1,4,8,RATE,1,&sec,&share));
    assert(!AW_PickAttackClock(4,3,8,RATE,1,&sec,&share));
    assert(!AW_PickAttackClock(4,9,8,RATE,1,&sec,&share));
    assert(!AW_PickAttackClock(4,4,4,RATE,1,&sec,&share));
    assert(!AW_PickAttackClock(4,5,8,0,1,&sec,&share));
    assert(!AW_PickAttackClock(4,5,8,RATE,0,&sec,&share));
    printf("attack clock ok: %d attacks on their own keys, %d of them off the hit frame on the old clock\n",n,off);
    return 0;
}
