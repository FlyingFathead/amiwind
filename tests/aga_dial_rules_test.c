/* SPDX-License-Identifier: GPL-2.0-or-later
 * The dialogue's speaker-against-player functions and the disposition's last terms (DIALOGUE-COMPLETE-58): SameSex,
 * SameRace and ShouldAttack through the shared condition evaluator (aw_glut.c AW_GlutCond, its live function hook),
 * and a disease, a drawn weapon and Charm in AW_DialDisposition (the rule of OpenMW's getDerivedDisposition). */
#include "aw_dial.h"
#include <assert.h>
#include <string.h>

static unsigned char settings[4*AW_DIAL_SETTINGS];
static void put_setting(int s,float value){
    union {unsigned long u;float f;} v;v.f=value;
    settings[4*s]=(unsigned char)(v.u>>24);settings[4*s+1]=(unsigned char)(v.u>>16);
    settings[4*s+2]=(unsigned char)(v.u>>8);settings[4*s+3]=(unsigned char)v.u;
}
static aw_dial_pair_t pair;
static int pair_hook(const aw_glut_cond_t *c,unsigned fn,long *out){(void)c;return AW_DialPairFunction(&pair,fn,out);}
static const aw_glut_live_t live={NULL,NULL,NULL,NULL,NULL,pair_hook,NULL};
/* a function condition record: FN compared (CMP 0 ==, 1 !=) with VALUE */
static int holds(unsigned fn,int cmp,long value){
    aw_glut_cond_t c;aw_glut_state_t s;unsigned char r[8];
    memset(&c,0,sizeof(c));memset(&s,0,sizeof(s));c.rank=-1;c.choice=-1;c.speaker=1;
    r[0]=AW_GLUT_OP_FUNC;r[1]=(unsigned char)cmp;r[2]=(unsigned char)(fn>>8);r[3]=(unsigned char)fn;
    r[4]=(unsigned char)((unsigned long)value>>24);r[5]=(unsigned char)((unsigned long)value>>16);
    r[6]=(unsigned char)((unsigned long)value>>8);r[7]=(unsigned char)value;
    return AW_GlutCond(&c,r,&s);
}
int main(void){
    aw_dial_t d;aw_dial_facts_t f;long out;
    /* the speaker functions: nothing known, none of them passes (the start-of-game table knows none of them) */
    aw_glut_live=&live;
    memset(&pair,0,sizeof(pair));pair.fight_rating=-1;
    assert(!holds(AW_DIAL_FN_SAME_SEX,0,1) && !holds(AW_DIAL_FN_SAME_SEX,0,0));
    assert(!AW_DialPairFunction(&pair,AW_DIAL_FN_SAME_RACE,&out));
    pair.known=1;pair.player_female=1;pair.speaker_female=1;pair.player_race="Dark Elf";pair.speaker_race="dark elf";
    assert(holds(AW_DIAL_FN_SAME_SEX,0,1) && !holds(AW_DIAL_FN_SAME_SEX,0,0));
    assert(holds(AW_DIAL_FN_SAME_RACE,0,1));                 /* race ids compare without case */
    pair.speaker_female=0;pair.speaker_race="Imperial";
    assert(holds(AW_DIAL_FN_SAME_SEX,0,0) && holds(AW_DIAL_FN_SAME_RACE,0,0));
    pair.speaker_race=NULL;assert(holds(AW_DIAL_FN_SAME_RACE,0,0));   /* a speaker without a race: not the same */
    assert(!holds(AW_DIAL_FN_SHOULD_ATTACK,0,0) && !holds(AW_DIAL_FN_SHOULD_ATTACK,0,1));   /* no rating: never */
    pair.fight_rating=99;assert(holds(AW_DIAL_FN_SHOULD_ATTACK,0,0));
    pair.fight_rating=100;assert(holds(AW_DIAL_FN_SHOULD_ATTACK,0,1) && holds(AW_DIAL_FN_SHOULD_ATTACK,1,0));
    assert(!AW_DialPairFunction(&pair,2,&out));               /* RankRequirement is not one of them */
    aw_glut_live=NULL;

    /* the disposition: base 50, Personality at its base, then each last term alone */
    memset(&d,0,sizeof(d));d.data=settings;d.settings=settings;
    put_setting(AW_DIAL_SET_PERSONALITY_MULT,0.5f);put_setting(AW_DIAL_SET_PERSONALITY_BASE,50);
    put_setting(AW_DIAL_SET_DISEASE,-10);put_setting(AW_DIAL_SET_WEAPON_DRAWN,-5);
    memset(&f,0,sizeof(f));f.base=50;f.personality=50;
    assert(AW_DialDisposition(&d,&f,1)==50);
    f.diseased=1;assert(AW_DialDisposition(&d,&f,1)==40);
    f.weapon_drawn=1;assert(AW_DialDisposition(&d,&f,1)==35);
    f.charm=20.5f;assert(AW_DialDisposition(&d,&f,1)==55);   /* Charm's magnitude added last, then cut toward zero */
    f.charm=80;assert(AW_DialDisposition(&d,&f,1)==100 && AW_DialDisposition(&d,&f,0)==115);
    f.charm=0;f.base=5;assert(AW_DialDisposition(&d,&f,1)==0 && AW_DialDisposition(&d,&f,0)==-10);
    return 0;
}
