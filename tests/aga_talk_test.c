/* SPDX-License-Identifier: GPL-2.0-or-later
 * Who can be talked to (TALK-PROMPT-RULES, engine/aga/src/aw_talk.c): the rule alone, then the facts read from an
 * edict, its combat slot and its actor record, as the prompt and E ask them. Rules from OpenMW 0.51
 * (mwclass/npc.cpp, creature.cpp activate; mwdialogue/dialoguemanagerimp.cpp startDialogue). */
#include "quakedef.h"
#include "aw_talk.h"
#include "aw_combat.h"
#include "aw_actorstate.h"
#include "aw_glut.h"
#include <assert.h>

int host_framecount;
int (*aw_can_talk)(edict_t *e);	/* aw_scene.c's in the engine */
char *pr_strings="\0aw_npc\0aw_flora\0vo/hello.wav";
#define S_NPC 1
#define S_FLORA 8
#define S_VOICE 17
static edict_t edicts[4];
static eval_t voice[4],role[4],ref[4];
eval_t *GetEdictFieldValue(edict_t *e,char *name){
    int i=(int)(e-edicts);
    if(!strcmp(name,"aw_voice"))return &voice[i];
    if(!strcmp(name,"aw_intro_role"))return &role[i];
    if(!strcmp(name,"aw_ref"))return &ref[i];
    return NULL;
}
/* the voice table: edict 2 has a row */
int AW_GlutNpcOf(edict_t *e){return e==&edicts[2]?7:-1;}
/* combat slots (aw_combat.c): one fighter for one edict */
static edict_t *fighting;static aw_fighter_t fighter;static int fighter_reads;
const aw_fighter_t *AW_CombatFighter(edict_t *e){fighter_reads++;return e==fighting?&fighter:NULL;}
/* the actor record pool (aw_actorstate.c): one record */
static aw_actor_t record;static int record_reads;
aw_actor_t *AW_ActorGet(uint32_t reference,int row,int create){
    record_reads++;assert(row==AW_ACTOR_NONE && !create);
    return reference==record.reference?&record:NULL;
}
static int can(int i){host_framecount++;return AW_CanTalk(&edicts[i]);}

int main(void){
    aw_talk_facts_t f;int i,reads;
    /* the rule: an actor with something to say, alive, not fighting the player, standing */
    memset(&f,0,sizeof(f));f.actor=f.dialogue=1;assert(AW_TalkAllowed(&f));
    f.dead=1;assert(!AW_TalkAllowed(&f));f.dead=0;
    f.hostile=1;assert(!AW_TalkAllowed(&f));f.hostile=0;
    f.knocked=1;assert(!AW_TalkAllowed(&f));f.knocked=0;
    f.paralyzed=1;assert(!AW_TalkAllowed(&f));f.paralyzed=0;
    f.dialogue=0;assert(!AW_TalkAllowed(&f));f.dialogue=1;
    f.actor=0;assert(!AW_TalkAllowed(&f));
    /* the edicts: 0 a voiced NPC, 1 an NPC with nothing to say, 2 one with a voice table row, 3 flora */
    for(i=0;i<4;i++){edicts[i].v.classname=S_NPC;ref[i]._float=(float)(100+i);}
    edicts[3].v.classname=S_FLORA;voice[0].string=S_VOICE;voice[3].string=S_VOICE;
    AW_TalkInit();assert(aw_can_talk==AW_CanTalk);
    assert(can(0) && !can(1) && can(2) && !can(3));
    /* an opening story role talks by its own story, not by E */
    role[0]._float=6;assert(!can(0));role[0]._float=0;
    /* in combat with the player (a combat slot): the name stays, no talk (OpenMW: sActorInCombat) */
    fighting=&edicts[0];memset(&fighter,0,sizeof(fighter));assert(!can(0) && can(2));
    assert(AW_TalkFacts(&edicts[0],&f) && f.hostile && !f.dead);
    /* knocked down in the fight */
    fighter.knocked=2;assert(!can(0) && AW_TalkFacts(&edicts[0],&f) && f.knocked);fighter.knocked=0;
    /* dead: looted, never talked to (and no longer hostile) */
    fighter.dead=1;assert(!can(0) && AW_TalkFacts(&edicts[0],&f) && f.dead && !f.hostile);fighter.dead=0;
    /* Calm Humanoid / dbg combat calm: the slot goes, the talk comes back */
    fighting=NULL;assert(can(0));
    /* the actor record: a script's StartCombat, a death the record keeps */
    record.reference=100;record.flags=AWL_USED|AWL_COMBAT;assert(!can(0));
    record.flags=AWL_USED|AWL_DEAD;assert(!can(0));
    record.flags=AWL_USED;assert(can(0));
    /* cost: one answer per frame for the same actor (the prompt and E in one frame read the flags once) */
    host_framecount++;reads=fighter_reads+record_reads;
    for(i=0;i<5;i++)assert(AW_CanTalk(&edicts[0]));
    assert(fighter_reads+record_reads==reads+2);
    /* nothing there */
    assert(!AW_TalkFacts(NULL,&f) && !AW_CanTalk(NULL));
    puts("talk: rule, voice/table/nothing to say, story roles, combat, knocked, dead, calm, record, one read a frame");
    return 0;
}
