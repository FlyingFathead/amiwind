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
    assert(!parse("aw_animkit","play","sneakforward",&c) && !strcmp(c.name,"not wired yet"));
    assert(!parse("aw_animkit","play","moonwalk",&c) && !strcmp(c.name,"unknown group"));
    assert(parse("aw_animkit","speed","0.5",&c) && c.kind==AW_ANIMKIT_SPEED && c.speed==.5f);
    assert(!parse("aw_animkit","speed","9",&c) && !parse("aw_animkit","speed","x",&c));
    assert(!parse("aw_animkit","dance",NULL,&c) && c.kind==AW_ANIMKIT_HELP);
    /* Every engine group but the AmiWind dodge extension has its original group in the table. */
    for(i=0;i<aw_animkit_group_count;i++)if(aw_animkit_groups[i].engine>=0)wired++;
    assert(wired==AW_ANIM_GROUPS-2 && aw_animkit_group_count>70);
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
