/* SPDX-License-Identifier: GPL-2.0-or-later
 * The levelling rules as pure functions (aw_levelup.h; host tested by tests/aga_levelup_rules_test.c).
 * Rule from OpenMW 0.51 files/data-mw/scripts/omw/playerskillhandlers.lua, apps/openmw/mwgui/levelupdialog.cpp
 * and apps/openmw/mwmechanics/npcstats.cpp; independent code, numbers from the master file's game settings. */
#include <string.h>
#include "aw_levelup.h"

static const char *const setting_names[AW_LEVELUP_SETTING_COUNT]={
    "fMajorSkillBonus","fMinorSkillBonus","fMiscSkillBonus","fSpecialSkillBonus","fLevelUpHealthEndMult",
    "iLevelupTotal","iLevelupMajorMult","iLevelupMinorMult","iLevelupMajorMultAttribute","iLevelupMinorMultAttribute",
    "iLevelupMiscMultAttriubte","iLevelupSpecialization",
    "iLevelUp01Mult","iLevelUp02Mult","iLevelUp03Mult","iLevelUp04Mult","iLevelUp05Mult",
    "iLevelUp06Mult","iLevelUp07Mult","iLevelUp08Mult","iLevelUp09Mult","iLevelUp10Mult"};
static int same(const char *a,const char *b)
{
    for(;*a && *b;a++,b++){
        int x=*a>='A' && *a<='Z'?*a+32:*a,y=*b>='A' && *b<='Z'?*b+32:*b;
        if(x!=y)return 0;
    }
    return !*a && !*b;
}
const char *AW_LevelupSettingName(int index){return index>=0 && index<AW_LEVELUP_SETTING_COUNT?setting_names[index]:"";}
int AW_LevelupSettingSet(aw_levelup_rules_t *r,const char *name,float value)
{
    int i;
    for(i=0;i<AW_LEVELUP_SETTING_COUNT;i++)if(same(name,setting_names[i]))break;
    if(i==AW_LEVELUP_SETTING_COUNT)return 0;
    switch(i){
    case 0:r->major=value;break;
    case 1:r->minor=value;break;
    case 2:r->misc=value;break;
    case 3:r->special=value;break;
    case 4:r->health_end=value;break;
    case 5:r->total=(int)value;break;
    case 6:r->major_mult=(int)value;break;
    case 7:r->minor_mult=(int)value;break;
    case 8:r->major_attribute=(int)value;break;
    case 9:r->minor_attribute=(int)value;break;
    case 10:r->misc_attribute=(int)value;break;
    case 11:r->specialization=(int)value;break;
    default:r->mult[i-12]=(int)value;break;
    }
    r->seen_settings|=1UL<<i;
    return 1;
}
int AW_LevelupSkillRow(aw_levelup_rules_t *r,int skill,int attribute,int special,const float *use)
{
    int i;
    if(skill<0 || skill>=AW_LEVELUP_SKILLS || attribute<0 || attribute>7 || special<0 || special>2)return 0;
    for(i=0;i<4;i++)if(!(use[i]>=0 && use[i]<=1000))return 0;
    r->attribute[skill]=(unsigned char)attribute;r->spec[skill]=(unsigned char)special;
    for(i=0;i<4;i++)r->use[skill][i]=use[i];
    r->seen_skills|=1UL<<skill;
    return 1;
}
int AW_LevelupRulesComplete(const aw_levelup_rules_t *r)
{
    return r->seen_settings==(1UL<<AW_LEVELUP_SETTING_COUNT)-1 && r->seen_skills==(1UL<<AW_LEVELUP_SKILLS)-1 &&
        r->major>0 && r->minor>0 && r->misc>0 && r->special>0 && r->total>0;
}
int AW_LevelupSkillClass(const aw_class_t *k,int skill)
{
    int i;
    if(!k)return 0;
    for(i=0;i<10;i++)if(k->skills[i]==skill)return (i&1)?2:1;
    return 0;
}
float AW_LevelupRequirement(const aw_levelup_rules_t *r,const aw_class_t *k,int skill,int base)
{
    int place=AW_LevelupSkillClass(k,skill);
    float factor=place==2?r->major:place==1?r->minor:r->misc;
    if(k && skill>=0 && skill<AW_LEVELUP_SKILLS && r->spec[skill]==k->special)factor*=r->special;
    return (float)(base+1)*factor;
}
int AW_LevelupSkillRaise(const aw_levelup_rules_t *r,const aw_class_t *k,aw_character_t *c,int skill,int source)
{
    int place,attribute,spec;
    if(skill<0 || skill>=AW_LEVELUP_SKILLS || c->skills[skill]>=100)return 0;
    place=AW_LevelupSkillClass(k,skill);
    c->skills[skill]++;
    if(place==2)c->level_progress=(short)(c->level_progress+r->major_mult);
    else if(place==1)c->level_progress=(short)(c->level_progress+r->minor_mult);
    attribute=r->attribute[skill];spec=r->spec[skill];
    c->raises[attribute]=(short)(c->raises[attribute]+(place==2?r->major_attribute:place==1?r->minor_attribute:r->misc_attribute));
    c->special[spec]=(short)(c->special[spec]+r->specialization);
    if(source==AW_RAISE_USAGE)c->progress[skill]=0;
    return 1;
}
int AW_LevelupSkillUsed(const aw_levelup_rules_t *r,const aw_class_t *k,aw_character_t *c,int skill,int use,float scale)
{
    float gain,need;
    if(!r->loaded || skill<0 || skill>=AW_LEVELUP_SKILLS || use<0 || use>3 || c->skills[skill]>=100)return -1;
    gain=r->use[skill][use]*scale;
    if(!(gain>0))return 0;
    need=AW_LevelupRequirement(r,k,skill,c->skills[skill]);
    if(!(need>0))return -1;
    c->progress[skill]+=gain/need;
    if(c->progress[skill]<1)return 0;
    return AW_LevelupSkillRaise(r,k,c,skill,AW_RAISE_USAGE);
}
float AW_LevelupMercantileScale(int buying,int final_price,int merchant_offer)
{
    long p=final_price<0?-(long)final_price:final_price,o=merchant_offer<0?-(long)merchant_offer:merchant_offer;
    if(!buying && p>o && p>0)return (float)((100*(p-o))/p);
    if(buying && p<o && o>0)return (float)((100*(o-p))/o);
    return 0;
}
int AW_LevelupDue(const aw_levelup_rules_t *r,const aw_character_t *c)
{
    return r->total>0 && c->level_progress>=r->total;
}
int AW_LevelupMultiplier(const aw_levelup_rules_t *r,const aw_character_t *c,int attribute)
{
    int n;
    if(attribute<0 || attribute>7 || c->raises[attribute]<=0)return 1;
    n=c->raises[attribute]>10?10:c->raises[attribute];
    return r->mult[n-1]>0?r->mult[n-1]:1;
}
int AW_LevelupApply(const aw_levelup_rules_t *r,aw_character_t *c,const int *picks,int count)
{
    int i,j,value;float gain;
    if(count<0 || count>3)return 0;
    for(i=0;i<count;i++){
        if(picks[i]<0 || picks[i]>7)return 0;
        for(j=0;j<i;j++)if(picks[j]==picks[i])return 0;
    }
    for(i=0;i<count;i++){
        value=c->attributes[picks[i]]+AW_LevelupMultiplier(r,c,picks[i]);
        c->attributes[picks[i]]=(short)(value>100?100:value);
    }
    c->level_progress=(short)(c->level_progress-r->total);
    if(c->level_progress<0)c->level_progress=0;
    memset(c->raises,0,sizeof(c->raises));memset(c->special,0,sizeof(c->special));
    gain=c->attributes[5]*r->health_end;
    c->maximum[0]+=gain;
    c->current[0]+=gain;
    if(c->current[0]<1)c->current[0]=1;
    if(c->current[0]>c->maximum[0])c->current[0]=c->maximum[0];
    return ++c->level;
}
const char *AW_LevelupClassImage(int combat,int magic,int stealth)
{
    const char *name="acrobat";
    int total=combat+magic+stealth,cf,mf,sf;
    if(total<=0)return name;
    cf=(int)((float)combat/total*10.f);mf=(int)((float)magic/total*10.f);sf=(int)((float)stealth/total*10.f);
    if(cf>7)name="warrior";else if(mf>7)name="mage";else if(sf>7)name="thief";
    switch(cf){
    case 7:name="warrior";break;
    case 6:name=sf==1?"barbarian":sf==3?"crusader":"knight";break;
    case 5:name=sf==3?"scout":"archer";break;
    case 4:name="rogue";break;
    default:break;
    }
    switch(mf){
    case 7:name="mage";break;
    case 6:name=cf==2?"sorcerer":combat==3?"healer":"battlemage";break;
    case 5:name="witchhunter";break;
    case 4:name="spellsword";break;
    default:break;
    }
    switch(sf){
    case 7:name="thief";break;
    case 6:name=mf==1?"agent":magic==3?"assassin":"acrobat";break;
    case 5:name=magic==3?"monk":"pilgrim";break;
    case 3:if(mf==3)name="bard";break;
    default:break;
    }
    return name;
}
void AW_LevelupBoxOpen(const aw_character_t *c,aw_levelup_box_t *b)
{
    int i,open=0;
    for(i=0;i<8;i++)if(c->attributes[i]<100)open++;
    b->coins=open<3?open:3;b->count=0;b->picks[0]=b->picks[1]=b->picks[2]=-1;
}
int AW_LevelupBoxPicked(const aw_levelup_box_t *b,int attribute)
{
    int i;
    for(i=0;i<b->count;i++)if(b->picks[i]==attribute)return 1;
    return 0;
}
int AW_LevelupBoxClick(const aw_character_t *c,aw_levelup_box_t *b,int attribute)
{
    int i;
    if(attribute<0 || attribute>7 || b->coins<=0)return 0;
    for(i=0;i<b->count;i++)if(b->picks[i]==attribute){
        for(;i<b->count-1;i++)b->picks[i]=b->picks[i+1];
        b->picks[--b->count]=-1;return 1;
    }
    if(c->attributes[attribute]>=100)return 0;
    if(b->count==b->coins)b->picks[b->coins-1]=attribute;
    else b->picks[b->count++]=attribute;
    return 1;
}
int AW_LevelupBoxValue(const aw_levelup_rules_t *r,const aw_character_t *c,const aw_levelup_box_t *b,int attribute)
{
    int v;
    if(attribute<0 || attribute>7)return 0;
    v=c->attributes[attribute];
    if(AW_LevelupBoxPicked(b,attribute))v+=AW_LevelupMultiplier(r,c,attribute);
    return v>100?100:v;
}
int AW_LevelupBoxReady(const aw_levelup_box_t *b){return b->count>=b->coins;}
