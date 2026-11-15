/* SPDX-License-Identifier: GPL-2.0-or-later
 * The character windows' spell lists, the rules (aw_spelllist.h): the effect line, the groups and the rows, the
 * scroll limits. Pure C, no engine headers; the wrap is the active-effect list's own (aw_fxrow_rules.c AW_FxWrap). */
#include <stdio.h>
#include <string.h>
#include "aw_fxrow.h"
#include "aw_spelllist.h"

int AW_SpellMagnitudeKind(int effect,unsigned long flags){
    if(flags&AW_SL_NO_MAGNITUDE)return AW_SL_MAG_NONE;
    if(effect==84)return AW_SL_MAG_TIMES_INT;                           /* Fortify Maximum Magicka */
    if(effect==59 || (effect>=64 && effect<=66))return AW_SL_MAG_FEET;  /* Telekinesis, the Detects */
    if(effect==118 || effect==119)return AW_SL_MAG_LEVEL;               /* Command Creature, Command Humanoid */
    if((effect>=28 && effect<=36) || (effect>=90 && effect<=99) || effect==40 || effect==47 || effect==57 || effect==68)
        return AW_SL_MAG_PERCENT;                                       /* weaknesses, resistances, Chameleon ... */
    return AW_SL_MAG_POINTS;
}

/* the length of TEXT, at most MAX (a field that may fill its array with no terminator) */
static int bounded(const char *text,int max){int n=0;while(n<max && text[n])n++;return n;}
/* appends the text of FORMAT to OUT at *AT, never past CAPACITY */
static void add(char *out,int capacity,int *at,const char *text){
    while(*text && *at<capacity-1)out[(*at)++]=*text++;
    out[*at]=0;
}
/* NAME with its attribute or skill: "Fortify Attribute" + Agility = "Fortify Agility" (the record's word for what it
 * names is replaced, as the original's "Fortify", "Drain", "Damage", "Restore", "Absorb" + the name) */
static void effect_name(const aw_sl_effect_t *e,char *out,int capacity,int *at){
    int n=bounded(e->name,(int)sizeof(e->name)),cut=n;
    char name[sizeof(e->name)+1];
    memcpy(name,e->name,(size_t)n);name[n]=0;
    if(e->arg[0]){
        if(n>10 && !strcmp(name+n-10," Attribute"))cut=n-10;
        else if(n>6 && !strcmp(name+n-6," Skill"))cut=n-6;
        name[cut]=0;
    }
    add(out,capacity,at,name[0]?name:"Unknown effect");
    if(e->arg[0]){char arg[sizeof(e->arg)+2];snprintf(arg,sizeof(arg)," %.*s",(int)sizeof(e->arg)-1,e->arg);add(out,capacity,at,arg);}
}
int AW_SpellEffectText(const aw_sl_effect_t *e,int constant,char *out,int capacity){
    int at=0,kind,d;char t[64];
    if(!out || capacity<1)return 0;
    out[0]=0;
    if(!e)return 0;
    effect_name(e,out,capacity,&at);
    kind=AW_SpellMagnitudeKind(e->effect,e->flags);
    if((e->min || e->max) && kind!=AW_SL_MAG_NONE){
        if(kind==AW_SL_MAG_TIMES_INT){
            if(e->min!=e->max)snprintf(t,sizeof(t)," %d.%d to %d.%dx INT",e->min/10,e->min%10,e->max/10,e->max%10);
            else snprintf(t,sizeof(t)," %d.%dx INT",e->min/10,e->min%10);
        }else{
            int one=e->min==e->max && e->min==1;
            if(e->min!=e->max)snprintf(t,sizeof(t)," %u to %u",e->min,e->max);
            else snprintf(t,sizeof(t)," %u",e->min);
            add(out,capacity,&at,t);
            t[0]=0;
            if(kind==AW_SL_MAG_PERCENT)snprintf(t,sizeof(t),"%%");
            else if(kind==AW_SL_MAG_FEET)snprintf(t,sizeof(t)," ft");
            else if(kind==AW_SL_MAG_LEVEL)snprintf(t,sizeof(t),one?" level":" levels");
            else snprintf(t,sizeof(t),one?" pt":" pts");
        }
        add(out,capacity,&at,t);
    }
    if(!constant){
        static const char *ranges[]={"Self","Touch","Target"};
        d=e->duration;
        if(!(e->flags&AW_SL_APPLIED_ONCE) && d<1)d=1;
        if(d>0 && !(e->flags&AW_SL_NO_DURATION)){snprintf(t,sizeof(t)," for %d %s",d,d==1?"sec":"secs");add(out,capacity,&at,t);}
        if(e->area>0){snprintf(t,sizeof(t)," in %u ft area",e->area);add(out,capacity,&at,t);}
        snprintf(t,sizeof(t)," on %s",ranges[e->range<3?e->range:0]);add(out,capacity,&at,t);
    }
    return at;
}

static void row(aw_sl_list_t *l,int kind,int effect,const char *text){
    aw_sl_row_t *r;int n=0;
    if(l->rows>=AW_SL_ROWS)return;
    r=&l->row[l->rows++];r->kind=(unsigned char)kind;r->effect=(short)effect;
    r->height=(unsigned char)(kind==AW_SL_HEAD?AW_SL_HEAD_H:kind==AW_SL_NAME?AW_SL_NAME_H:kind==AW_SL_EFFECT?AW_SL_EFFECT_H:AW_SL_MORE_H);
    while(text && text[n] && n<AW_SL_TEXT-1){r->text[n]=text[n];n++;}
    r->text[n]=0;
}
/* the group of a spell type: 0 abilities (and the other always-active kinds), 1 powers, 2 spells */
static int group_of(int type){return type==5?1:type==0?2:0;}
int AW_SpellListBuild(const aw_sl_spell_t *s,int n,int name_chars,int effect_chars,aw_sl_list_t *out){
    static const char *heads[]={"Abilities","Powers","Spells"};
    char wrapped[6][AW_FX_LINE],text[160];int g,i,j,k,m,shown;
    if(!out)return 0;
    memset(out,0,sizeof(*out));
    if(!s || n<1)return 0;
    if(name_chars<4)name_chars=4;
    if(effect_chars<4)effect_chars=4;
    if(name_chars>AW_SL_TEXT-1)name_chars=AW_SL_TEXT-1;
    if(effect_chars>AW_SL_TEXT-1)effect_chars=AW_SL_TEXT-1;
    for(g=0;g<3;g++){
        shown=0;
        for(i=0;i<n;i++){
            if(group_of(s[i].type)!=g)continue;
            if(!shown++)row(out,AW_SL_HEAD,-1,heads[g]);
            out->spells++;
            m=AW_FxWrap(s[i].name,bounded(s[i].name,(int)sizeof(s[i].name)),name_chars,wrapped,2);
            if(!m)row(out,AW_SL_NAME,-1,"Unnamed");
            for(k=0;k<m;k++)row(out,k?AW_SL_MORE:AW_SL_NAME,-1,wrapped[k]);
            for(j=0;j<s[i].n && j<AW_SL_EFFECTS;j++){
                AW_SpellEffectText(&s[i].e[j],g==0,text,sizeof(text));
                m=AW_FxWrap(text,(int)strlen(text),effect_chars,wrapped,6);
                for(k=0;k<m;k++)row(out,k?AW_SL_MORE:AW_SL_EFFECT,k?-1:s[i].e[j].effect,wrapped[k]);
            }
        }
    }
    return out->rows;
}
int AW_SpellListFit(const aw_sl_list_t *l,int top,int h){
    int i,used=0;
    if(!l || top<0 || top>=l->rows)return 0;
    for(i=top;i<l->rows;i++){
        if(used+l->row[i].height>h)break;
        used+=l->row[i].height;
    }
    return i>top?i-top:1;
}
int AW_SpellListMaxTop(const aw_sl_list_t *l,int h){
    int top,used=0;
    if(!l || l->rows<1)return 0;
    for(top=l->rows;top>0 && used+l->row[top-1].height<=h;top--)used+=l->row[top-1].height;
    return top<l->rows?top:l->rows-1;
}
