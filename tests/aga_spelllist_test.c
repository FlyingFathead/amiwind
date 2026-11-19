/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHARGEN-ABILITY-DESCRIPTIONS-65: the character windows' spell lists, aw_spelllist_rules.c alone (with the wrap of
 * aw_fxrow_rules.c): the effect line as the original words it (OpenMW 0.51 MWSpellEffect::updateWidgets), the groups
 * Abilities, Powers, Spells in that order, every effect under its spell, the scroll limits. The records are the ones of
 * The Thief, The Lady and the Breton (their published values), written here by hand; nothing of the game. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_fxrow.h"
#include "aw_spelllist.h"

static aw_sl_effect_t fx(int effect,const char *name,const char *arg,int min,int max,int duration,int range,unsigned long flags){
    aw_sl_effect_t e;memset(&e,0,sizeof(e));
    e.effect=(short)effect;e.min=(unsigned short)min;e.max=(unsigned short)max;e.duration=(unsigned short)duration;
    e.range=(unsigned char)range;e.flags=flags;
    strcpy(e.name,name);if(arg)strcpy(e.arg,arg);
    return e;
}
static const char *line(const aw_sl_effect_t *e,int constant){static char out[160];AW_SpellEffectText(e,constant,out,sizeof(out));return out;}

int main(void){
    aw_sl_effect_t e;aw_sl_spell_t s[4];aw_sl_list_t l;int i,n,top,h;
    /* the magnitude kinds (loadmgef.cpp getMagnitudeDisplayType) */
    assert(AW_SpellMagnitudeKind(93,0)==AW_SL_MAG_PERCENT && AW_SpellMagnitudeKind(28,0)==AW_SL_MAG_PERCENT);
    assert(AW_SpellMagnitudeKind(84,0)==AW_SL_MAG_TIMES_INT && AW_SpellMagnitudeKind(59,0)==AW_SL_MAG_FEET);
    assert(AW_SpellMagnitudeKind(118,0)==AW_SL_MAG_LEVEL && AW_SpellMagnitudeKind(42,0)==AW_SL_MAG_POINTS);
    assert(AW_SpellMagnitudeKind(42,AW_SL_NO_MAGNITUDE)==AW_SL_MAG_NONE);
    /* an ability's effect: constant, no duration and no range */
    e=fx(42,"Sanctuary",NULL,10,10,0,0,0);assert(!strcmp(line(&e,1),"Sanctuary 10 pts"));
    e=fx(79,"Fortify Attribute","Personality",25,25,0,0,0);assert(!strcmp(line(&e,1),"Fortify Personality 25 pts"));
    e=fx(21,"Fortify Skill","Long Blade",1,1,0,0,0);assert(!strcmp(line(&e,1),"Fortify Long Blade 1 pt"));
    e=fx(93,"Resist Magicka",NULL,50,50,0,0,0);assert(!strcmp(line(&e,1),"Resist Magicka 50%"));
    e=fx(84,"Fortify Maximum Magicka",NULL,5,5,0,0,0);assert(!strcmp(line(&e,1),"Fortify Maximum Magicka 0.5x INT"));
    /* a power or a spell: the duration and the range follow */
    e=fx(3,"Shield",NULL,50,50,60,0,0);assert(!strcmp(line(&e,0),"Shield 50 pts for 60 secs on Self"));
    e=fx(14,"Fire Damage",NULL,5,20,1,2,0);assert(!strcmp(line(&e,0),"Fire Damage 5 to 20 pts for 1 sec on Target"));
    e.area=10;assert(!strcmp(line(&e,0),"Fire Damage 5 to 20 pts for 1 sec in 10 ft area on Target"));
    e=fx(63,"Almsivi Intervention",NULL,0,0,0,0,AW_SL_NO_DURATION|AW_SL_NO_MAGNITUDE);
    assert(!strcmp(line(&e,0),"Almsivi Intervention on Self"));
    e=fx(117,"Restore Health",NULL,1,1,0,1,0);assert(!strcmp(line(&e,0),"Restore Health 1 pt for 1 sec on Touch"));
    /* INVENTORY-ITEM-INFO-67: a potion's effect has its duration and no target (widgets.cpp mNoTarget) */
    e=fx(75,"Restore Health",NULL,10,10,5,0,0);assert(!strcmp(line(&e,AW_SL_NO_TARGET),"Restore Health 10 pts for 5 secs"));
    e=fx(85,"Damage Health",NULL,4,4,0,1,AW_SL_APPLIED_ONCE);assert(!strcmp(line(&e,0),"Damage Health 4 pts on Touch"));
    /* the groups in the original's order whatever the record order: a power listed first goes under Powers */
    memset(s,0,sizeof(s));
    strcpy(s[0].name,"Dragon Skin");s[0].type=5;s[0].n=1;s[0].e[0]=fx(3,"Shield",NULL,50,50,60,0,0);
    strcpy(s[1].name,"Resist Magicka");s[1].type=1;s[1].n=1;s[1].e[0]=fx(93,"Resist Magicka",NULL,50,50,0,0,0);
    strcpy(s[2].name,"Magicka Bonus");s[2].type=1;s[2].n=1;s[2].e[0]=fx(84,"Fortify Maximum Magicka",NULL,5,5,0,0,0);
    n=AW_SpellListBuild(s,3,30,30,&l);
    assert(n==l.rows && l.spells==3);
    {
        static const struct {int kind;const char *text;int effect;} want[]={
            {AW_SL_HEAD,"Abilities",-1},{AW_SL_NAME,"Resist Magicka",-1},{AW_SL_EFFECT,"Resist Magicka 50%",93},
            {AW_SL_NAME,"Magicka Bonus",-1},{AW_SL_EFFECT,"Fortify Maximum Magicka 0.5x",84},{AW_SL_MORE,"INT",-1},
            {AW_SL_HEAD,"Powers",-1},{AW_SL_NAME,"Dragon Skin",-1},{AW_SL_EFFECT,"Shield 50 pts for 60 secs on",3},
            {AW_SL_MORE,"Self",-1}};
        for(i=0;i<l.rows;i++)printf("%d %-34s %d\n",l.row[i].kind,l.row[i].text,l.row[i].effect);
        assert(n==(int)(sizeof(want)/sizeof(want[0])));
        for(i=0;i<n;i++){
            assert(l.row[i].kind==want[i].kind && !strcmp(l.row[i].text,want[i].text) && l.row[i].effect==want[i].effect);
            assert(l.row[i].height==(want[i].kind==AW_SL_HEAD?AW_SL_HEAD_H:want[i].kind==AW_SL_NAME?AW_SL_NAME_H:
                                     want[i].kind==AW_SL_EFFECT?AW_SL_EFFECT_H:AW_SL_MORE_H));
        }
    }
    /* The Lady: two abilities, each effect under its own name; no Powers or Spells heading when the sign has none */
    memset(s,0,sizeof(s));
    strcpy(s[0].name,"Lady's Favor");s[0].type=1;s[0].n=1;s[0].e[0]=fx(79,"Fortify Attribute","Personality",25,25,0,0,0);
    strcpy(s[1].name,"Lady's Grace");s[1].type=1;s[1].n=1;s[1].e[0]=fx(79,"Fortify Attribute","Endurance",25,25,0,0,0);
    n=AW_SpellListBuild(s,2,40,40,&l);
    assert(n==5 && !strcmp(l.row[0].text,"Abilities") && !strcmp(l.row[2].text,"Fortify Personality 25 pts"));
    assert(!strcmp(l.row[4].text,"Fortify Endurance 25 pts"));
    for(i=0;i<n;i++)assert(strcmp(l.row[i].text,"Powers") && strcmp(l.row[i].text,"Spells"));
    /* a spell (type 0) under Spells; a disease (3) with the abilities, as always active */
    s[1].type=0;s[0].type=3;n=AW_SpellListBuild(s,2,40,40,&l);
    assert(!strcmp(l.row[0].text,"Abilities") && !strcmp(l.row[3].text,"Spells"));
    assert(!strcmp(l.row[5].text,"Fortify Endurance 25 pts for 1 sec on") && !strcmp(l.row[6].text,"Self"));
    /* a narrow panel wraps, and never past a row's text */
    n=AW_SpellListBuild(s,2,10,10,&l);
    for(i=0;i<n;i++)assert((int)strlen(l.row[i].text)<=10);
    /* the scroll limits: rows from TOP that fit, the lowest TOP that fills the panel to the end */
    for(h=20;h<200;h+=7){
        int used=0;
        top=AW_SpellListMaxTop(&l,h);
        for(i=top;i<l.rows;i++)used+=l.row[i].height;
        assert(used<=h || top==l.rows-1);
        if(top>0)assert(used+l.row[top-1].height>h);
        assert(AW_SpellListFit(&l,top,h)==l.rows-top || top==l.rows-1);
        assert(AW_SpellListFit(&l,0,h)>=1);
    }
    assert(AW_SpellListMaxTop(&l,1000)==0 && AW_SpellListFit(&l,0,1000)==l.rows);
    /* nothing in, nothing out; an unnamed spell is never blank */
    assert(AW_SpellListBuild(s,0,20,20,&l)==0 && l.rows==0);
    memset(s,0,sizeof(s));s[0].type=1;n=AW_SpellListBuild(s,1,20,20,&l);assert(n==2 && !strcmp(l.row[1].text,"Unnamed"));
    printf("spell lists: ok\n");
    return 0;
}
