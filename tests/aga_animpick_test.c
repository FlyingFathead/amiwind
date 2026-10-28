/* SPDX-License-Identifier: GPL-2.0-or-later
 * Every humanoid animation group hooked up (aw_animpick_rules.c, ANIM-GROUPS-NOT-HOOKED-54): OpenMW's group rules case
 * by case, then the coverage proof: every group of the default tables is in
 * the engine's catalogue (the group list: aga_animpick_groups.h), and every catalogue row the picker owns ("pick:")
 * comes out of AW_AnimPick for some state;
 * a view row ("view:") is reached through its plain name. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_animpick.h"
#include "aga_animpick_groups.h"
#include "aw_animpick_catalogue.inc"

#define MAXG 256
static char names[MAXG][32];
static int count,reached[MAXG];
static int find(const char *n) {int i;for(i=0;i<count;i++)if(!strcmp(names[i],n))return i;return -1;}
/* the actor's table: the common names; a view also answers a name by its own prefixed group (f:, d:) */
static int has(void *context,const char *n) {
    char v[40];(void)context;
    if(find(n)>=0)return 1;
    snprintf(v,sizeof(v),"f:%s",n);if(find(v)>=0)return 1;
    snprintf(v,sizeof(v),"d:%s",n);return find(v)>=0;
}
static void mark(const char *n) {
    char v[40];int i;
    if((i=find(n))>=0)reached[i]=1;
    snprintf(v,sizeof(v),"f:%s",n);if((i=find(v))>=0)reached[i]=1;
    snprintf(v,sizeof(v),"d:%s",n);if((i=find(v))>=0)reached[i]=1;
}
static aw_pick_state_t st(int weapon,int event,int move) {
    aw_pick_state_t s;memset(&s,0,sizeof(s));s.weapon=(signed char)weapon;s.event=(unsigned char)event;s.move=(unsigned char)move;
    return s;
}
static const char *pick(aw_pick_state_t s,aw_pick_t *o) {assert(AW_AnimPick(&s,has,NULL,o));return o->group;}

int main(void) {
    aw_pick_t o;aw_pick_state_t s;int w,e,m,r,k,sw,i,idle,storm,missing=0;
    static const int idles[]={0,2,3,4,5,6,7,8,9};
    for(i=0;i<(int)(sizeof(table_groups)/sizeof(table_groups[0]));i++){
        assert(count<MAXG && strlen(table_groups[i])<32);
        strcpy(names[count++],table_groups[i]);
    }
    assert(count>=140);

    /* the rules, case by case (character.cpp, weapontype.cpp) */
    assert(!strcmp(pick(st(AW_PW_NONE,AW_PE_NONE,AW_PM_NONE),&o),"idle") && o.loop);
    assert(!strcmp(pick(st(0,AW_PE_NONE,AW_PM_FORWARD),&o),"walkforward1h"));        /* short blade "1s" -> 1h */
    s=st(4,AW_PE_NONE,AW_PM_NONE);assert(!strcmp(pick(s,&o),"idle2c"));               /* blunt two-close "2b" -> 2c */
    s=st(9,AW_PE_NONE,AW_PM_NONE);assert(!strcmp(pick(s,&o),"idle1h"));               /* bow -> 1h */
    s=st(10,AW_PE_NONE,AW_PM_NONE);assert(!strcmp(pick(s,&o),"idlecrossbow"));
    s=st(AW_PW_SPELL,AW_PE_NONE,AW_PM_TURNLEFT);assert(!strcmp(pick(s,&o),"spellturnleft"));
    s=st(AW_PW_SPELL,AW_PE_NONE,AW_PM_NONE);assert(!strcmp(pick(s,&o),"idlespell"));
    s=st(AW_PW_SPELL,AW_PE_NONE,AW_PM_BACK);assert(!strcmp(pick(s,&o),"walkback"));   /* no spell walk set: the base */
    s=st(1,AW_PE_NONE,AW_PM_LEFT);s.run=1;assert(!strcmp(pick(s,&o),"runleft1h"));
    s=st(5,AW_PE_NONE,AW_PM_RIGHT);s.sneak=1;assert(!strcmp(pick(s,&o),"sneakright2w"));
    s=st(1,AW_PE_NONE,AW_PM_FORWARD);s.swim=1;s.run=1;assert(!strcmp(pick(s,&o),"swimrunforward")); /* no stance in water */
    s=st(AW_PW_NONE,AW_PE_NONE,AW_PM_TURNRIGHT);s.swim=1;assert(!strcmp(pick(s,&o),"swimturnright"));
    s=st(AW_PW_NONE,AW_PE_NONE,AW_PM_TURNRIGHT);s.sneak=1;assert(!strcmp(pick(s,&o),"idlesneak"));   /* no turn sneaking */
    s=st(AW_PW_NONE,AW_PE_NONE,AW_PM_NONE);s.storm=1;assert(!strcmp(pick(s,&o),"idlestorm") && !strcmp(o.loop_start,"loop start"));
    s=st(AW_PW_NONE,AW_PE_NONE,AW_PM_NONE);s.idle=9;assert(!strcmp(pick(s,&o),"idle9"));
    s=st(1,AW_PE_NONE,AW_PM_NONE);s.idle=9;assert(!strcmp(pick(s,&o),"idle1h"));     /* drawn: no wander idle */
    s=st(AW_PW_NONE,AW_PE_HIT,0);s.swim=1;s.roll=7;assert(!strncmp(pick(s,&o),"hit",3) && !o.loop);   /* no swimhit: hit */
    s=st(AW_PW_NONE,AW_PE_KNOCKOUT,0);assert(!strcmp(pick(s,&o),"knockout") && !strcmp(o.loop_stop,"loop stop"));
    s=st(AW_PW_NONE,AW_PE_DEATH,0);s.knocked=1;assert(!strcmp(pick(s,&o),"deathknockdown"));
    s=st(AW_PW_NONE,AW_PE_DEATH,0);s.knocked=2;s.swim=1;assert(!strcmp(pick(s,&o),"swimdeathknockout"));
    s=st(AW_PW_NONE,AW_PE_DEATH,0);s.roll=4;assert(!strcmp(pick(s,&o),"death5"));
    s=st(3,AW_PE_ATTACK,0);s.attack=AW_PA_CHOP;s.follow=AW_PF_LARGE;
    assert(!strcmp(pick(s,&o),"weapononehand") && !strcmp(o.start,"chop start") && !strcmp(o.stop,"chop large follow stop"));
    s=st(AW_PW_NONE,AW_PE_ATTACK,0);s.attack=AW_PA_THRUST;assert(!strcmp(pick(s,&o),"handtohand") && !strcmp(o.start,"thrust start"));
    s=st(9,AW_PE_ATTACK,0);assert(!strcmp(pick(s,&o),"bowandarrow") && !strcmp(o.start,"shoot start"));
    s=st(AW_PW_SPELL,AW_PE_ATTACK,0);s.range=AW_PR_TARGET;assert(!strcmp(pick(s,&o),"spellcast") && !strcmp(o.start,"target start"));
    s=st(5,AW_PE_EQUIP,0);assert(!strcmp(pick(s,&o),"weapontwowide") && !strcmp(o.start,"equip start"));
    s=st(AW_PW_SPELL,AW_PE_UNEQUIP,0);assert(!strcmp(pick(s,&o),"spellcast") && !strcmp(o.stop,"unequip stop"));
    s=st(6,AW_PE_INVENTORY,0);assert(!strcmp(pick(s,&o),"inventoryweapontwowide"));
    s=st(9,AW_PE_INVENTORY,0);assert(!strcmp(pick(s,&o),"inventoryweapononehand"));
    s=st(11,AW_PE_JUMP,0);assert(!strcmp(pick(s,&o),"jump1h"));
    s=st(AW_PW_NONE,AW_PE_BLOCK,0);assert(!strcmp(pick(s,&o),"shield") && !strcmp(o.start,"block start"));
    s=st(AW_PW_PICKPROBE,AW_PE_ATTACK,0);assert(!strcmp(pick(s,&o),"pickprobe"));
    {   /* aiwander.cpp getRandomIdle: the dancers' chances; one roll per idle, the highest under its chance wins */
        static const unsigned char dancer[8]={20,20,20,10,0,0,0,80},r1[8]={50,50,50,50,50,50,50,60},r2[8]={15,90,90,90,90,90,90,90};
        assert(AW_PickWanderIdle(dancer,100,40,r1)==9);
        assert(AW_PickWanderIdle(dancer,100,40,r2)==2);
        assert(AW_PickWanderIdle(dancer,30,40,r1)==0);
    }

    /* coverage: every state the game logic can be in */
    for(w=AW_PW_PICKPROBE;w<=AW_PW_LAST;w++)for(e=0;e<AW_PE_COUNT;e++)for(m=0;m<AW_PM_COUNT;m++)
    for(r=0;r<2;r++)for(sw=0;sw<4;sw++)for(i=0;i<9;i++)for(storm=0;storm<2;storm++)for(k=0;k<27;k++){
        idle=idles[i];
        if(e!=AW_PE_NONE && (m || r || idle || storm))continue;          /* one-shots: the rest does not matter */
        if(e==AW_PE_NONE && k)continue;
        s=st(w,e,m);s.run=(unsigned char)r;s.swim=(unsigned char)(sw&1);s.sneak=(unsigned char)(sw>>1);s.idle=(unsigned char)idle;
        s.storm=(unsigned char)storm;s.attack=(unsigned char)(k%3);s.follow=(unsigned char)(k/3%3);s.range=(unsigned char)(k%3);
        s.knocked=(unsigned char)(k/9);s.roll=(unsigned char)k;
        if(AW_AnimPick(&s,has,NULL,&o))mark(o.group);
    }
    /* the catalogue: exactly the tables' groups, each with its hook */
    for(i=0;i<aw_pick_catalogue_count;i++){
        int at=find(aw_pick_catalogue[i].group),j;
        if(at<0){printf("catalogue row %s: not a group of the tables\n",aw_pick_catalogue[i].group);missing++;}
        for(j=0;j<i;j++)assert(strcmp(aw_pick_catalogue[j].group,aw_pick_catalogue[i].group));
        assert(aw_pick_catalogue[i].hook && aw_pick_catalogue[i].hook[0]);
        if(at>=0 && !strncmp(aw_pick_catalogue[i].hook,"pick:",5) && !reached[at]){
            printf("NOT HOOKED: %s (no state picks it)\n",aw_pick_catalogue[i].group);missing++;
        }
        if(at>=0 && !strncmp(aw_pick_catalogue[i].hook,"view:",5) && !reached[at]){
            printf("NOT HOOKED: %s (its plain name is never picked)\n",aw_pick_catalogue[i].group);missing++;
        }
    }
    for(i=0;i<count;i++){
        int j,in=0;
        for(j=0;j<aw_pick_catalogue_count;j++)if(!strcmp(aw_pick_catalogue[j].group,names[i]))in=1;
        if(!in){printf("NOT IN THE CATALOGUE: %s\n",names[i]);missing++;}
    }
    printf("%d groups, %d catalogue rows, %d problems\n",count,aw_pick_catalogue_count,missing);
    assert(!missing);
    return 0;
}
