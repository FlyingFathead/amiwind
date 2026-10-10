/* SPDX-License-Identifier: GPL-2.0-or-later
 * Animation kit tables and the dbg animkit parser as pure functions
 * (aw_animkit.h, docs/ANIMKIT.md). No engine state: the host test runs them.
 *
 * The group names are Morrowind's own (the skeleton's text keys in
 * base_anim.nif and its creature skeletons; the same list as OpenMW's
 * animation group table). engine: the aw_anim.h group a row plays as
 * (tools/npc_anim.py GROUPS reads that original group), -1 = present in the
 * data, not wired yet.
 */
#include <string.h>
#include "aw_anim.h"
#include "aw_animkit.h"

const aw_animkit_group_t aw_animkit_groups[]={
    {"idle",AW_ANIM_IDLE},{"idle2",-1},{"idle3",-1},{"idle4",-1},{"idle5",-1},{"idle6",-1},{"idle7",-1},
    {"idle8",-1},{"idle9",-1},{"idlehh",-1},{"idle1h",-1},{"idle2c",-1},{"idle2w",-1},{"idleswim",AW_ANIM_SWIMIDLE},
    {"idlespell",-1},{"idlecrossbow",-1},{"idlesneak",-1},{"idlestorm",-1},{"torch",-1},
    {"hit1",AW_ANIM_HIT},{"hit2",-1},{"hit3",-1},{"hit4",-1},{"hit5",-1},
    {"swimhit1",-1},{"swimhit2",-1},{"swimhit3",-1},
    {"death1",AW_ANIM_DEATH},{"death2",-1},{"death3",-1},{"death4",-1},{"death5",-1},
    {"deathknockdown",-1},{"deathknockout",-1},{"swimdeath",-1},{"swimdeath2",-1},{"swimdeath3",-1},
    {"knockdown",AW_ANIM_KNOCK},{"knockout",-1},{"swimknockdown",-1},{"swimknockout",-1},
    {"jump",-1},
    {"walkforward",AW_ANIM_WALK},{"walkback",-1},{"walkleft",-1},{"walkright",-1},
    {"turnleft",-1},{"turnright",-1},
    {"runforward",AW_ANIM_RUN},{"runback",-1},{"runleft",-1},{"runright",-1},
    {"sneakforward",-1},{"sneakback",-1},{"sneakleft",-1},{"sneakright",-1},
    {"swimwalkforward",AW_ANIM_SWIM},{"swimwalkback",-1},{"swimwalkleft",-1},{"swimwalkright",-1},
    {"swimrunforward",-1},{"swimrunback",-1},{"swimrunleft",-1},{"swimrunright",-1},
    {"swimturnleft",-1},{"swimturnright",-1},{"spellturnleft",-1},{"spellturnright",-1},
    {"handtohand",AW_ANIM_ATTACK},{"weapononehand",-1},{"weapontwohand",-1},{"weapontwowide",-1},
    {"bowandarrow",-1},{"crossbow",-1},{"throwweapon",-1},{"spellcast",-1},
    {"shield",AW_ANIM_BLOCK},
    {"inventoryhandtohand",-1},{"inventoryweapononehand",-1},{"inventoryweapontwohand",-1},
    {"inventoryweapontwowide",-1},
};
const int aw_animkit_group_count=(int)(sizeof(aw_animkit_groups)/sizeof(aw_animkit_groups[0]));

static int same(const char *a,const char *b) {
    for(;*a && *b;a++,b++){
        int x=*a>='A' && *a<='Z'?*a+32:*a,y=*b>='A' && *b<='Z'?*b+32:*b;
        if(x!=y)return 0;
    }
    return !*a && !*b;
}
int AW_AnimKitFind(const char *name) {
    int i;
    for(i=0;name && i<aw_animkit_group_count;i++)if(same(name,aw_animkit_groups[i].name))return i;
    return -1;
}
int AW_AnimKitEngineGroup(const char *name) {
    int i;
    for(i=0;name && i<AW_ANIM_GROUPS;i++)if(same(name,aw_anim_group_names[i]))return i;
    i=AW_AnimKitFind(name);
    return i<0?-1:aw_animkit_groups[i].engine;
}

static void reason(aw_animkit_cmd_t *out,const char *text) {
    out->kind=AW_ANIMKIT_HELP;
    strncpy(out->name,text,sizeof(out->name)-1);out->name[sizeof(out->name)-1]=0;
}
int AW_AnimKitParse(int argc,const char **argv,aw_animkit_cmd_t *out) {
    const char *w;
    memset(out,0,sizeof(*out));out->group=-1;out->speed=1;
    if(argc<2){out->kind=AW_ANIMKIT_STATUS;return 1;}
    w=argv[1];
    if(same(w,"on") && argc==2){out->kind=AW_ANIMKIT_ON;return 1;}
    if(same(w,"off") && argc==2){out->kind=AW_ANIMKIT_OFF;return 1;}
    if(same(w,"list") && argc==2){out->kind=AW_ANIMKIT_LIST;return 1;}
    if(same(w,"stop") && argc==2){out->kind=AW_ANIMKIT_STOP;return 1;}
    if(same(w,"play") && argc==3){
        int g=AW_AnimKitEngineGroup(argv[2]);
        if(g<0){reason(out,AW_AnimKitFind(argv[2])<0?"unknown group":"not wired yet");return 0;}
        out->kind=AW_ANIMKIT_PLAY;out->group=g;
        strncpy(out->name,argv[2],sizeof(out->name)-1);
        return 1;
    }
    if(same(w,"speed") && argc==3){
        /* Digits only (no strtod: it reaches 68040-unimplemented FPU code): N, N.D, .D in hundredths. */
        const char *q=argv[2];int whole=0,frac=0,scale=100,digits=0;
        while(*q>='0' && *q<='9'){if(whole<100)whole=whole*10+(*q-'0');q++;digits++;}
        if(*q=='.'){q++;while(*q>='0' && *q<='9'){if(scale>1){scale/=10;frac+=(*q-'0')*scale;}q++;digits++;}}
        if(!digits || *q || whole*100+frac<10 || whole*100+frac>400){reason(out,"speed 0.1..4");return 0;}
        out->kind=AW_ANIMKIT_SPEED;out->speed=(float)(whole*100+frac)/100.f;return 1;
    }
    reason(out,"unknown subcommand");
    return 0;
}
