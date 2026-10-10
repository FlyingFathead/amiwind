/* SPDX-License-Identifier: GPL-2.0-or-later
 * dbg animkit (aw_animkit, docs/ANIMKIT.md): the animation kit's debug
 * console. on/off switches the walk/run/swim selection by speed (off: movers
 * play their idle frames, the previous method); list shows the groups of the
 * actor under the crosshair and Morrowind's whole group table; play forces one
 * group on that actor until stop; speed scales every kit playback rate.
 * Not saved (the cvar aw_animkit is archived; the forced group is not).
 */
#include "quakedef.h"
#include "aw_anim.h"
#include "aw_animkit.h"

static cvar_t animkit={"aw_animkit","1",true};
static struct {edict_t *e;int group;aw_anim_play_t play;double last;} forced;

static edict_t *player(void) {
    if(!sv.active || svs.maxclients!=1 || !svs.clients || !svs.clients[0].edict)return NULL;
    return svs.clients[0].edict;
}
static edict_t *target(void) {
    edict_t *p=player();
    return p?AW_NPCTargetReach(p,cl.viewangles,1024):NULL;
}
static void sync(void) {aw_anim_kit_enabled=animkit.value!=0;}

static void list(edict_t *e) {
    const aw_anim_t *a=e?AW_AnimOf(e):NULL;int i,wired=0,unwired=0;
    if(a)Con_Printf("Animation kit groups of the target (%s):\n",a->from_layout?"layout":"no layout: idle only");
    else Con_Printf("Animation kit: no NPC under the crosshair; Morrowind's group table:\n");
    for(i=0;a && i<AW_ANIM_GROUPS;i++)
        if(a->g[i].present)Con_Printf("  %-9s %2d frames%s\n",aw_anim_group_names[i],a->g[i].count,
                                      a->mover[0] && !AW_AnimMoving(e)?" (standing model)":"");
    for(i=0;i<aw_animkit_group_count;i++){
        int g=aw_animkit_groups[i].engine;
        if(g<0){unwired++;continue;}
        wired++;
        Con_Printf("  %-22s -> %s%s\n",aw_animkit_groups[i].name,aw_anim_group_names[g],
                   a && !a->g[g].present?" (not in this model)":"");
    }
    Con_Printf("Present in data, not wired yet (%d):",unwired);
    for(i=0;i<aw_animkit_group_count;i++)if(aw_animkit_groups[i].engine<0)Con_Printf(" %s",aw_animkit_groups[i].name);
    Con_Printf("\n%d groups wired, %d not wired.\n",wired,unwired);
}

static void command(void) {
    const char *argv[4];int i,argc=Cmd_Argc();aw_animkit_cmd_t c;edict_t *e;
    if(argc>4)argc=4;
    for(i=0;i<argc;i++)argv[i]=Cmd_Argv(i);
    if(!AW_AnimKitParse(argc,argv,&c)){
        Con_Printf("dbg animkit: %s\n",c.name);
        Con_Printf("dbg animkit [on/off / list / play <group> / stop / speed <0.1..4>]\n");
        return;
    }
    switch(c.kind){
    case AW_ANIMKIT_ON:case AW_ANIMKIT_OFF:
        Cvar_SetValue(animkit.name,c.kind==AW_ANIMKIT_ON);sync();
        Con_Printf("Animation kit %s.\n",aw_anim_kit_enabled?"on: walk, run and swim by speed":"off: movers play idle");
        return;
    case AW_ANIMKIT_LIST:list(target());return;
    case AW_ANIMKIT_STOP:forced.e=NULL;Con_Printf("Animation kit: no forced group.\n");return;
    case AW_ANIMKIT_SPEED:aw_anim_kit_speed=c.speed;Con_Printf("Animation kit playback speed x%.2f.\n",c.speed);return;
    case AW_ANIMKIT_PLAY:
        if(!(e=target())){Con_Printf("Animation kit: no NPC under the crosshair.\n");return;}
        if(!AW_AnimOf(e)->g[c.group].present){Con_Printf("Animation kit: the target has no %s group.\n",aw_anim_group_names[c.group]);return;}
        memset(&forced,0,sizeof(forced));forced.e=e;forced.group=c.group;forced.play.group=255;forced.last=realtime;
        Con_Printf("Animation kit: playing %s on the NPC under the crosshair (dbg animkit stop).\n",aw_anim_group_names[c.group]);
        return;
    default:
        Con_Printf("Animation kit %s, playback speed x%.2f%s.\n",aw_anim_kit_enabled?"on":"off",aw_anim_kit_speed,
                   forced.e?", one forced group":"");
    }
}

#if !AW_ANIMKIT
static void compiled_out(void) {Con_Printf("dbg animkit: this engine was built without the animation kit (AW_ANIMKIT=0).\n");}
void AW_AnimKitInit(void) {Cmd_AddCommand("aw_animkit",compiled_out);aw_anim_kit_enabled=0;}
void AW_AnimKitTick(void) {}
#else
/* After the server frame: the forced group wins over every other driver of the target's frame. */
void AW_AnimKitTick(void) {
    float dt;
    sync();
    if(!forced.e)return;
    if(forced.e->free || !sv.active){forced.e=NULL;return;}
    dt=(float)(realtime-forced.last);forced.last=realtime;
    if(dt<0 || dt>0.5f)dt=0;
    forced.e->v.frame=(float)AW_AnimAdvance(AW_AnimOf(forced.e),&forced.play,forced.group,dt,aw_anim_kit_speed,NULL);
}

void AW_AnimKitInit(void) {
    Cvar_RegisterVariable(&animkit);
    Cmd_AddCommand("aw_animkit",command);
    sync();
}
#endif
