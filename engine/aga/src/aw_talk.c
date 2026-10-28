/* SPDX-License-Identifier: GPL-2.0-or-later
 * Who can be talked to: ONE predicate for the prompt ("E: Talk") and for E itself (TALK-PROMPT-RULES; the
 * maintainer, 27 October 2026: an actor that cannot be talked to shows its name but no talk option, "a combat mode
 * usually disables the talking ... if you manage to calm them down with a calm humanoid spell, they can be talked
 * with"; "it should go according to OpenMW and MWscript definitions, compute cheaply").
 *
 * Rules from OpenMW 0.51 (read, not copied):
 *   apps/openmw/mwclass/npc.cpp Npc::activate: a dead NPC is looted (ActionOpen), never talked to; a knocked-down
 *     one is looted; talking only when not in combat with the player (inCombatWithActor: a combat package against
 *     the player, or pursuit) - in combat the use fails with sActorInCombat;
 *   apps/openmw/mwclass/creature.cpp Creature::activate: the same for creatures (dead: loot; knocked down: loot;
 *     otherwise ActionTalk);
 *   apps/openmw/mwdialogue/dialoguemanagerimp.cpp DialogueManager::startDialogue: no dialogue with a dead actor;
 *     an actor with nothing to say opens no dialogue (AmiWind: no hello line of its own and no voice table row).
 * Calm Humanoid / Calm Creature end the combat (OpenMW: the actor's combat package goes): the combat slot is
 * released (aw_combat.c AW_CombatForget / AW_CombatClear), so the talk comes back by this same rule.
 *
 * Cost: flags only. One read of the combat slots (4), one of the actor record pool (at most 128 live records,
 * a compare each) and the voice table row the edict already caches (aw_glut.c), done once per host frame for the
 * one actor under the crosshair (cached on the frame stamp); nothing over the world, no allocation. */
#include "quakedef.h"
#include "aw_talk.h"
#include "aw_combat.h"
#include "aw_actorstate.h"
#include "aw_glut.h"

int AW_TalkAllowed(const aw_talk_facts_t *f) {
    return f->actor && f->dialogue && !f->dead && !f->hostile && !f->knocked && !f->paralyzed;
}
static const char *text(edict_t *e,char *field) {
    eval_t *v=GetEdictFieldValue(e,field);
    return v && v->string?pr_strings+v->string:"";
}
static float number(edict_t *e,char *field) {
    eval_t *v=GetEdictFieldValue(e,field);
    return v?v->_float:0;
}
int AW_TalkFacts(edict_t *e,aw_talk_facts_t *f) {
    const aw_fighter_t *fighter;aw_actor_t *a;float ref;
    memset(f,0,sizeof(*f));
    if(!e || e->free)return 0;
    f->actor=!strcmp(pr_strings+e->v.classname,"aw_npc") && !number(e,"aw_intro_role");
    f->dialogue=text(e,"aw_voice")[0] || AW_GlutNpcOf(e)>=0;
    /* the fight: a combat slot (aw_combat.c), its sheet's death and knockdown */
    if((fighter=AW_CombatFighter(e))!=NULL){
        f->dead=fighter->dead!=0;f->hostile=!fighter->dead;f->knocked=fighter->knocked!=0;
    }
    /* the actor record (aw_actorstate.c): dead, or a script's StartCombat */
    ref=number(e,"aw_ref");
    if(ref>0 && (a=AW_ActorGet((uint32_t)ref,AW_ACTOR_NONE,0))!=NULL){
        if(a->flags&AWL_DEAD)f->dead=1;
        if(a->flags&AWL_COMBAT)f->hostile=1;
    }
    return 1;
}
/* once per frame for the same edict (the prompt and E ask in the same frame) */
static int cached_frame=-1,cached_result;static edict_t *cached_edict;
int AW_CanTalk(edict_t *e) {
    aw_talk_facts_t f;
    if(e==cached_edict && cached_frame==host_framecount)return cached_result;
    cached_edict=e;cached_frame=host_framecount;
    cached_result=AW_TalkFacts(e,&f) && AW_TalkAllowed(&f);
    return cached_result;
}
void AW_TalkInit(void) {aw_can_talk=AW_CanTalk;}
