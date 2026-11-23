/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_TALK_H
#define AW_TALK_H
/* Who can be talked to (TALK-PROMPT-RULES, aw_talk.c). The facts of one actor, all read from flags the engine
 * already keeps (no search over the world): */
typedef struct {
    unsigned char actor;      /* an NPC or creature the player's E reaches (aw_npc, not an opening story role) */
    unsigned char dialogue;   /* it has something to say: its own hello line (aw_voice, build time) or a voice table row */
    unsigned char dead;       /* dead: looted, never talked to */
    unsigned char hostile;    /* in combat with the player (a combat slot, or a script's StartCombat) */
    unsigned char knocked;    /* knocked down or knocked out */
    unsigned char paralyzed;  /* paralyzed (no paralysis on actors in the engine yet: always 0) */
    unsigned char werewolf;   /* a character in werewolf form: the use never talks to it (NPC-WEREWOLF-TALK-OFFERED-68) */
    unsigned char player_werewolf;   /* the player is in werewolf form: he uses no actor */
} aw_talk_facts_t;
/* The rule alone (pure; tests/aga_talk_test.c). */
int AW_TalkAllowed(const aw_talk_facts_t *f);
/* The facts of edict E (0 for none); AW_CanTalk = the facts allow it (the prompt, E and the caravaners). */
struct edict_s;
int AW_TalkFacts(struct edict_s *e,aw_talk_facts_t *f);
int AW_CanTalk(struct edict_s *e);
void AW_TalkInit(void);
/* aw_scene.c holds it, AW_TalkInit sets it; NULL in fixtures without aw_talk.c (the old rule: a voice means talk). */
extern int (*aw_can_talk)(struct edict_s *e);
/* aw_talk.c holds them, the host sets them (aw_mwhost.c): E is a character in werewolf form; the player is. */
extern int (*aw_talk_werewolf)(struct edict_s *e);
extern int (*aw_talk_player_werewolf)(void);
#endif
