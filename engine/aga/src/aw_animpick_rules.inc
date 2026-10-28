/* SPDX-License-Identifier: GPL-2.0-or-later
 * Every humanoid animation group hooked up: the group choice by OpenMW's rules (aw_animpick.h). Pure, host-tested.
 * Included by aw_animkit_rules.c (one unit).
 *
 * Rules read in OpenMW 0.51 (apps/openmw/mwmechanics/character.cpp: refreshMovementAnims, refreshIdleAnims,
 * refreshHitRecoilAnims, refreshJumpAnims, playRandomDeath, updateWeaponState, fallbackShortWeaponGroup,
 * getWeaponAnimation; weapontype.cpp: the short and long groups; aiwander.cpp: getRandomIdle; mwrender/
 * characterpreview.cpp: the inventory picture) and written here independently; no code copied.
 */
#include <string.h>
#include "aw_animpick.h"

/* index weapon + 4 (AW_PW_PICKPROBE .. AW_PW_LAST) */
static const char *const shorts[16]={"1h","hh","spell","","1s","1h","2c","1b","2b","2w","2w","1b","2b","bow","crossbow","1t"};
static const char *const longs[16]={"pickprobe","handtohand","spellcast","","shortbladeonehand","weapononehand",
    "weapontwohand","bluntonehand","blunttwohand","weapontwowide","weapontwowide","bluntonehand","blunttwohand",
    "bowandarrow","crossbow","throwweapon"};
static int known(int w) {return w>=AW_PW_PICKPROBE && w<=AW_PW_LAST;}
static int real(int w) {return w>=0 && w<=AW_PW_LAST;}
/* weapontype.cpp: TwoHanded and Melee (long blade, blunt and axe two-handed, two-wide blunt, spear) */
static int two_handed_melee(int w) {return w==2 || w==4 || w==5 || w==6 || w==8;}
static int ranged(int w) {return w==9 || w==10 || w==11;}
const char *AW_PickShortGroup(int w) {return known(w)?shorts[w+4]:"";}
const char *AW_PickLongGroup(int w) {return known(w)?longs[w+4]:"";}

static void put(char *out,int size,const char *a,const char *b) {
    int n=0;
    while(a && *a && n<size-1)out[n++]=*a++;
    while(b && *b && n<size-1)out[n++]=*b++;
    out[n]=0;
}
static int has(aw_pick_has_t f,void *c,const char *name) {return name[0] && f(c,name);}

/* getWeaponAnimation: the weapon's own group, else the two-handed or one-handed long blade's */
static void weapon_group(int w,aw_pick_has_t h,void *c,char *out) {
    put(out,AW_PICK_NAME,AW_PickLongGroup(w),NULL);
    if(real(w) && !has(h,c,out))put(out,AW_PICK_NAME,two_handed_melee(w)?"weapontwohand":"weapononehand",NULL);
}
/* fallbackShortWeaponGroup: a real weapon's missing stance group -> the long blade's (2c / 1h), else the base group */
static void fallback_short(int w,const char *base,aw_pick_has_t h,void *c,char *out) {
    if(!real(w)){put(out,AW_PICK_NAME,base,NULL);return;}
    put(out,AW_PICK_NAME,base,two_handed_melee(w)?"2c":"1h");
    if(!has(h,c,out))put(out,AW_PICK_NAME,base,NULL);
}
/* chooseRandomGroup: PREFIX1..PREFIXn (n consecutive groups present), one of them by the roll */
static int random_group(const char *prefix,int roll,aw_pick_has_t h,void *c,char *out) {
    int n=0;char name[AW_PICK_NAME],digit[2]={0,0};
    for(;n<9;n++){digit[0]=(char)('1'+n);put(name,sizeof(name),prefix,digit);if(!has(h,c,name))break;}
    if(!n)return 0;
    digit[0]=(char)('1'+roll%n);put(out,AW_PICK_NAME,prefix,digit);
    return 1;
}
static void keys(aw_pick_t *o,const char *start,const char *stop) {
    put(o->start,AW_PICK_KEY,start,NULL);put(o->stop,AW_PICK_KEY,stop,NULL);
}

static int movement(const aw_pick_state_t *s,aw_pick_has_t h,void *c,aw_pick_t *o) {
    static const char *const dirs[AW_PM_COUNT]={"","forward","back","left","right","left","right"};
    char name[AW_PICK_NAME],w[AW_PICK_NAME];const char *kind,*sg=AW_PickShortGroup(s->weapon);int swim=s->swim,turning;char *p;
    turning=s->move==AW_PM_TURNLEFT || s->move==AW_PM_TURNRIGHT;
    if(turning && s->sneak)return 0;              /* no turning animation while sneaking (character.cpp) */
    if(turning)kind=swim?"swimturn":"turn";
    else kind=swim?(s->run?"swimrun":"swimwalk"):s->sneak?"sneak":s->run?"run":"walk";
    put(name,sizeof(name),kind,dirs[s->move]);
    o->rule="moving or turning: refreshMovementAnims";
    if(swim && !has(h,c,name)){put(name,sizeof(name),kind+4,dirs[s->move]);swim=0;}   /* swimturnleft -> turnleft */
    if(!swim && sg[0]){
        if(s->weapon==AW_PW_SPELL && turning)put(w,sizeof(w),sg,name);      /* spellturnleft */
        else put(w,sizeof(w),name,sg);                                      /* walkforward1h, runleft2c ... */
        if(!has(h,c,w))fallback_short(s->weapon,name,h,c,w);
        put(name,sizeof(name),w,NULL);
        o->rule="moving or turning with the stance drawn: refreshMovementAnims + weapon short group";
    }
    if(!has(h,c,name)){
        if((p=strstr(name,"run"))!=NULL){char tail[AW_PICK_NAME];put(tail,sizeof(tail),p+3,NULL);*p=0;put(w,sizeof(w),name,"walk");put(name,sizeof(name),w,tail);}
        if(!has(h,c,name))return 0;
    }
    put(o->group,AW_PICK_NAME,name,NULL);keys(o,"start","stop");o->loop=1;
    return 1;
}

static int standing(const aw_pick_state_t *s,aw_pick_has_t h,void *c,aw_pick_t *o) {
    char name[AW_PICK_NAME],w[AW_PICK_NAME];const char *sg=AW_PickShortGroup(s->weapon);
    o->loop=1;keys(o,"start","stop");
    if(s->idle>=2 && s->idle<=9 && s->weapon==AW_PW_NONE && !s->swim && !s->sneak){
        char digit[2]={(char)('0'+s->idle),0};
        put(name,sizeof(name),"idle",digit);
        if(has(h,c,name)){put(o->group,AW_PICK_NAME,name,NULL);o->rule="wander idle: aiwander.cpp getRandomIdle";return 1;}
    }
    if(s->storm && s->weapon==AW_PW_NONE && !s->swim && has(h,c,"idlestorm")){
        put(o->group,AW_PICK_NAME,"idlestorm",NULL);put(o->loop_start,AW_PICK_KEY,"loop start",NULL);
        put(o->loop_stop,AW_PICK_KEY,"loop stop",NULL);o->rule="standing in a storm: updateIdleStormState";
        return 1;
    }
    put(name,sizeof(name),s->swim?"idleswim":s->sneak?"idlesneak":"idle",NULL);
    o->rule=s->swim?"standing in water: refreshIdleAnims":s->sneak?"standing, sneaking: refreshIdleAnims":"standing: refreshIdleAnims";
    if((s->swim || s->sneak) && !has(h,c,name))put(name,sizeof(name),"idle",NULL);
    if(!strcmp(name,"idle") && sg[0]){
        put(w,sizeof(w),"idle",sg);
        if(!has(h,c,w))fallback_short(s->weapon,"idle",h,c,w);
        put(name,sizeof(name),w,NULL);
        o->rule="standing with the stance drawn: refreshIdleAnims + weapon short group";
    }
    if(!has(h,c,name))return 0;
    put(o->group,AW_PICK_NAME,name,NULL);
    return 1;
}

int AW_AnimPick(const aw_pick_state_t *s,aw_pick_has_t h,void *c,aw_pick_t *o) {
    static const char *const attacks[3]={"chop","slash","thrust"},*const follows[3]={"small","medium","large"},
        *const ranges[3]={"self","touch","target"};
    char a[AW_PICK_KEY],b[AW_PICK_KEY];int w=known(s->weapon)?s->weapon:AW_PW_NONE;
    memset(o,0,sizeof(*o));o->rule="";
    switch(s->event){
    case AW_PE_NONE:
        return s->move!=AW_PM_NONE && s->move<AW_PM_COUNT && movement(s,h,c,o)?1:standing(s,h,c,o);
    case AW_PE_HIT:
        o->rule="hit recovery, a random one: refreshHitRecoilAnims";
        if(!(s->swim && random_group("swimhit",s->roll,h,c,o->group)) && !random_group("hit",s->roll,h,c,o->group))return 0;
        break;
    case AW_PE_KNOCKDOWN:
        o->rule="knocked down: refreshHitRecoilAnims";
        put(o->group,AW_PICK_NAME,s->swim?"swimknockdown":"knockdown",NULL);
        break;
    case AW_PE_KNOCKOUT:
        o->rule="knocked out, looped while out: refreshHitRecoilAnims";
        put(o->group,AW_PICK_NAME,s->swim?"swimknockout":"knockout",NULL);
        put(o->loop_start,AW_PICK_KEY,"loop start",NULL);put(o->loop_stop,AW_PICK_KEY,"loop stop",NULL);
        break;
    case AW_PE_BLOCK:
        o->rule="block: refreshHitRecoilAnims";
        put(o->group,AW_PICK_NAME,"shield",NULL);keys(o,"block start","block stop");
        return has(h,c,o->group);
    case AW_PE_DEATH:
        o->rule="death: playRandomDeath / hitStateToDeathState";
        if(s->knocked==1)put(o->group,AW_PICK_NAME,s->swim?"swimdeathknockdown":"deathknockdown",NULL);
        else if(s->knocked==2)put(o->group,AW_PICK_NAME,s->swim?"swimdeathknockout":"deathknockout",NULL);
        else if(s->swim)put(o->group,AW_PICK_NAME,"swimdeath",NULL);
        if(!has(h,c,o->group) && !random_group("death",s->roll,h,c,o->group))return 0;
        break;
    case AW_PE_ATTACK:
        if(w==AW_PW_SPELL){aw_pick_state_t t=*s;t.event=AW_PE_CAST;return AW_AnimPick(&t,h,c,o);}
        if(w==AW_PW_PICKPROBE){aw_pick_state_t t=*s;t.event=AW_PE_USE;return AW_AnimPick(&t,h,c,o);}
        if(w==AW_PW_NONE)w=AW_PW_HANDTOHAND;      /* drawn with nothing in the hand: hand-to-hand */
        weapon_group(w,h,c,o->group);
        if(ranged(w)){keys(o,"shoot start","shoot follow stop");o->rule="attack, shoot: updateWeaponState";}
        else{
            put(a,sizeof(a),attacks[s->attack%3]," start");
            put(b,sizeof(b),attacks[s->attack%3]," ");put(b,sizeof(b),b,follows[s->follow%3]);put(b,sizeof(b),b," follow stop");
            keys(o,a,b);o->rule="attack, chop/slash/thrust: updateWeaponState";
        }
        return has(h,c,o->group);
    case AW_PE_CAST:
        o->rule="casting, the first effect's range: updateWeaponState";
        put(o->group,AW_PICK_NAME,"spellcast",NULL);
        put(a,sizeof(a),ranges[s->range%3]," start");put(b,sizeof(b),ranges[s->range%3]," stop");keys(o,a,b);
        return has(h,c,o->group);
    case AW_PE_EQUIP:case AW_PE_UNEQUIP:
        if(w==AW_PW_NONE)return 0;
        o->rule=s->event==AW_PE_EQUIP?"drawing: updateWeaponState equip start":"putting away: updateWeaponState unequip start";
        weapon_group(w==AW_PW_PICKPROBE?1:w,h,c,o->group);
        if(s->event==AW_PE_EQUIP)keys(o,"equip start","equip stop");else keys(o,"unequip start","unequip stop");
        return has(h,c,o->group);
    case AW_PE_JUMP:{
        const char *sg=AW_PickShortGroup(w);
        o->rule="jump: refreshJumpAnims";
        put(o->group,AW_PICK_NAME,"jump",sg);
        if(sg[0] && !has(h,c,o->group))fallback_short(w,"jump",h,c,o->group);
        put(o->loop_start,AW_PICK_KEY,"loop start",NULL);put(o->loop_stop,AW_PICK_KEY,"loop stop",NULL);
        break;}
    case AW_PE_USE:
        o->rule="a lockpick or probe used: updateWeaponState";
        put(o->group,AW_PICK_NAME,"pickprobe",NULL);
        break;
    case AW_PE_INVENTORY:
        o->rule="the inventory picture: characterpreview.cpp";
        put(o->group,AW_PICK_NAME,"inventoryhandtohand",NULL);
        if(real(w)){
            put(a,sizeof(a),"inventory",AW_PickLongGroup(w));
            if(has(h,c,a))put(o->group,AW_PICK_NAME,a,NULL);
            else put(o->group,AW_PICK_NAME,two_handed_melee(w)?"inventoryweapontwohand":"inventoryweapononehand",NULL);
        }
        break;
    default:
        return 0;
    }
    if(!o->start[0])keys(o,"start","stop");
    return has(h,c,o->group);
}

int AW_PickWanderIdle(const unsigned char chances[8],int multiplier100,int roll_gate,const unsigned char rolls[8]) {
    int i,best=0,pick=0;
    if(roll_gate>multiplier100)return 0;
    /* one roll per idle; the highest roll at or under its own chance wins */
    for(i=0;i<8;i++)if(rolls[i]<=chances[i] && rolls[i]>best){best=rolls[i];pick=2+i;}
    return pick;
}

/* The catalogue of every table group and its hook: aw_animpick_catalogue.inc (source data, never in the engine). */
