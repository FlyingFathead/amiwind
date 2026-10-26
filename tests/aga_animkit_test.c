/* SPDX-License-Identifier: GPL-2.0-or-later
 * dbg animkit parser and group table (aw_animkit_rules.c), and the kit switch and speed in the
 * walk/run selection (aw_anim.c AW_AnimMoveGroup). */
#include <assert.h>
#include <string.h>
#include "aw_anim.h"
#include "aw_animkit.h"

static int parse(const char *a,const char *b,const char *c,aw_animkit_cmd_t *out) {
    const char *argv[3]={a,b,c};
    return AW_AnimKitParse(c?3:b?2:1,argv,out);
}

int main(void) {
    aw_animkit_cmd_t c;aw_anim_t a;float rate;int i,wired=0;
    assert(parse("aw_animkit",NULL,NULL,&c) && c.kind==AW_ANIMKIT_STATUS);
    assert(parse("aw_animkit","on",NULL,&c) && c.kind==AW_ANIMKIT_ON);
    assert(parse("aw_animkit","OFF",NULL,&c) && c.kind==AW_ANIMKIT_OFF);
    assert(parse("aw_animkit","list",NULL,&c) && c.kind==AW_ANIMKIT_LIST);
    assert(parse("aw_animkit","stop",NULL,&c) && c.kind==AW_ANIMKIT_STOP);
    assert(parse("aw_animkit","play","run",&c) && c.kind==AW_ANIMKIT_PLAY && c.group==AW_ANIM_RUN);
    assert(parse("aw_animkit","play","runforward",&c) && c.group==AW_ANIM_RUN);
    assert(parse("aw_animkit","play","death1",&c) && c.group==AW_ANIM_DEATH);
    /* Any other name is played from a skeletal actor's table by name (SKEL-ANIM-STAGE-52): group -1. */
    assert(parse("aw_animkit","play","sneakforward",&c) && c.kind==AW_ANIMKIT_PLAY && c.group==-1 && !strcmp(c.name,"sneakforward"));
    assert(parse("aw_animkit","play","idle2",&c) && c.group==-1);
    assert(parse("aw_animkit","play","dodgel",&c) && c.group==AW_ANIM_DODGEL);   /* an engine group name */
    assert(parse("aw_animkit","play","moonwalk",&c) && c.group==-1);
    assert(!parse("aw_animkit","play","a_group_name_far_longer_than_any_table",&c) && !strcmp(c.name,"unknown group"));
    /* The animation stage: groups, cycle [all], stage [1..8]. */
    assert(parse("aw_animkit","groups",NULL,&c) && c.kind==AW_ANIMKIT_GROUPS);
    assert(parse("aw_animkit","cycle",NULL,&c) && c.kind==AW_ANIMKIT_CYCLE && c.count==0);
    assert(parse("aw_animkit","cycle","all",&c) && c.kind==AW_ANIMKIT_CYCLE && c.count==1);
    assert(!parse("aw_animkit","cycle","some",&c));
    assert(parse("aw_animkit","stage",NULL,&c) && c.kind==AW_ANIMKIT_STAGE && c.count==AW_ANIMKIT_STAGE_MAX);
    assert(parse("aw_animkit","stage","5",&c) && c.count==5);
    assert(!parse("aw_animkit","stage","0",&c) && !parse("aw_animkit","stage","9",&c) && !parse("aw_animkit","stage","x",&c));
    /* A table group played from its first to its last frame: loops wrap, one-shots hold the last and end. */
    {float t=0;int done=0,f;
     assert(AW_AnimKitSpanFrame(100,103,8,&t,0,1,&done)==100 && !done);
     assert(AW_AnimKitSpanFrame(100,103,8,&t,.25f,1,&done)==102 && !done);
     assert(AW_AnimKitSpanFrame(100,103,8,&t,.25f,1,&done)==100 && !done);   /* 4 frames = .5 s: wrapped */
     t=0;f=AW_AnimKitSpanFrame(100,103,8,&t,.49f,0,&done);assert(f==103 && !done);
     f=AW_AnimKitSpanFrame(100,103,8,&t,.02f,0,&done);assert(f==103 && done);
     t=0;assert(AW_AnimKitSpanFrame(7,7,8,&t,1,0,&done)==7 && done);           /* a one-frame group */
     t=0;assert(AW_AnimKitSpanFrame(2000,2729,8,&t,90,1,&done)==2000+720 && !done);   /* past frame 255 */
     t=0;assert(AW_AnimKitSpanFrame(5,9,0,&t,-1,1,&done)==5);                    /* no rate, no time: the first */
    }
    assert(parse("aw_animkit","speed","0.5",&c) && c.kind==AW_ANIMKIT_SPEED && c.speed==.5f);
    assert(!parse("aw_animkit","speed","9",&c) && !parse("aw_animkit","speed","x",&c));
    assert(!parse("aw_animkit","dance",NULL,&c) && c.kind==AW_ANIMKIT_HELP);
    assert(parse("aw_animkit","play","jump",&c) && c.group==AW_ANIM_JUMP);
    assert(parse("aw_animkit","play","land",&c) && c.group==AW_ANIM_LAND);
    assert(parse("aw_animkit","play","idlehh",&c) && c.group==AW_ANIM_READY);
    assert(parse("aw_animkit","play","walkforwardhh",&c) && c.group==AW_ANIM_READYWALK);
    assert(parse("aw_animkit","play","runforwardhh",&c) && c.group==AW_ANIM_READYRUN);
    assert(parse("aw_animkit","play","jumphh",&c) && c.group==AW_ANIM_READYJUMP);
    /* Dodge is an extension; land/readyland are second sections of jump/jumphh. */
    for(i=0;i<aw_animkit_group_count;i++)if(aw_animkit_groups[i].engine>=0)wired++;
    assert(wired==AW_ANIM_GROUPS-4 && aw_animkit_group_count>70);
    assert(AW_AnimKitFind("WalkForward")>=0 && AW_AnimKitFind("dodgel")<0);
    /* The kit switch: off = idle (the previous method); speed scales the rate. */
    memset(&a,0,sizeof(a));
    a.g[AW_ANIM_IDLE].present=a.g[AW_ANIM_WALK].present=a.g[AW_ANIM_RUN].present=1;
    a.g[AW_ANIM_WALK].x=40;a.g[AW_ANIM_RUN].x=60;
#if !AW_ANIMKIT
    /* Built without the kit: movers play idle whatever the switch says. */
    assert(AW_AnimMoveGroup(&a,60,0,&rate)==AW_ANIM_IDLE && AW_AnimMoveGroup(&a,40,0,&rate)==AW_ANIM_IDLE);
    return 0;
#endif
    assert(AW_AnimMoveGroup(&a,60,0,&rate)==AW_ANIM_RUN && rate==1);
    assert(AW_AnimMoveGroup(&a,40,0,&rate)==AW_ANIM_WALK);
    aw_anim_kit_speed=2;assert(AW_AnimMoveGroup(&a,60,0,&rate)==AW_ANIM_RUN && rate==2);aw_anim_kit_speed=1;
    aw_anim_kit_enabled=0;assert(AW_AnimMoveGroup(&a,60,0,&rate)==AW_ANIM_IDLE);aw_anim_kit_enabled=1;
    return 0;
}
