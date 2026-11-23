/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_objpose.c alone (MWSCRIPT-PLAYGROUP-ACTORS-ONLY-68): a script's PlayGroup / LoopGroup on a placed object takes the
 * group's end pose from the store's pose table: the fact at once, the swap when the group has played (its seconds,
 * plus a loop's for each extra loop), queued behind a group still playing in mode 0; a group whose end pose is the
 * model as placed swaps back and clears the fact; one that draws nothing hides; a room that loads applies its facts;
 * either form of the reference finds the row; a call with no row is not taken (the engine before: no placed object
 * ever played a group). Compiled with AW_OBJPOSE_HOST_TEST: the engine's side is this file's. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_objpose.h"

static char room_name[32];
static unsigned long room_serial;
static int room_on;
static double clock_now;
static struct {unsigned ref;int model;short box[6];} swaps[64];
static int swap_count;
static struct {char id[48];long value;} facts[16];
static int fact_count;

static int loaded(char *name,int size,unsigned long *serial){
    if(!room_on)return 0;
    strncpy(name,room_name,(size_t)size-1);name[size-1]=0;*serial=room_serial;
    return 1;
}
static int swap(unsigned ref,int model,const short *box){
    swaps[swap_count].ref=ref;swaps[swap_count].model=model;memcpy(swaps[swap_count].box,box,sizeof(short)*6);
    swap_count++;
    return 1;
}
static long get(const char *id){
    int i;
    for(i=0;i<fact_count;i++)if(!strcmp(facts[i].id,id))return facts[i].value;
    return 0;
}
static void set(const char *id,long value){
    int i;
    for(i=0;i<fact_count && strcmp(facts[i].id,id);i++)
        ;
    if(i==fact_count){strcpy(facts[i].id,id);fact_count++;}
    facts[i].value=value;
}
static double now(void){return clock_now;}

/* the Halls of Penumbra's ice wall (merged reference 8417459 = stable id 2126003) and a Clockwork City pre-door and
 * its lever, as the room conversion writes them (tools/chim/anim_poses.py write_pose_table) */
static const char *TABLE =
    "AWPG1\n"
    "R rif61f4dc044 8417459 idle B 7318 2.6667 2.6667 227 1653 -453 537 1907 -247\n"
    "R rif61f4dc044 8417459 idle2 M 7900 7.2000 7.2000 220 1600 -460 540 1950 -240\n"
    "R ri60b45e81e3 4198000 idle2 M 7901 9.3333 0.0000 10 20 30 40 50 60\n"
    "R ri60b45e81e3 4198000 idle3 B 7001 9.3333 0.0000 11 21 31 41 51 61\n"
    "R ri60b45e81e3 4198001 idle2 H -1 0.9000 0.9000 0 0 0 1 1 1\n"
    "R toolongroomnamexxxxxxxxxxxxxxx 5 idle2 M 1 1.0 1.0 0 0 0 1 1 1\n"
    "R bad\n";

int main(void){
    aw_objpose_host_t h;unsigned long c[4];char id[48];
    memset(&h,0,sizeof(h));
    h.loaded=loaded;h.swap=swap;h.get=get;h.set=set;h.now=now;
    AW_ObjPoseSetHost(&h);
    assert(AW_ObjPoseParse("AWPG2\nR x 1 idle M 1 1 1 0 0 0 1 1 1\n")==-1);   /* not this table */
    assert(AW_ObjPoseParse(TABLE)==5);                                        /* two malformed rows left out */
    AW_ObjPoseCounts(c);assert(c[0]==5 && c[1]==0);
    assert(AW_ObjPoseGroupCode("Idle2")==AW_ObjPoseGroupCode("idle2") && AW_ObjPoseGroupCode("idle2")!=0 &&
           AW_ObjPoseGroupCode("idle2")!=AW_ObjPoseGroupCode("idle3"));

    /* the Halls of Penumbra loaded: nothing saved yet, nothing swapped */
    strcpy(room_name,"rif61f4dc044");room_serial=1;room_on=1;clock_now=100.0;
    AW_ObjPoseTick();assert(swap_count==0);
    /* a group the table does not hold, and a reference with no row: not taken (the old engine: nothing at all) */
    assert(!AW_ObjPosePlay(8417459,"idle3",0,0) && !AW_ObjPosePlay(12345,"idle2",0,0));
    /* icewallScript: PlayGroup idle (doOnce): the model as placed; the fact stays clear */
    assert(AW_ObjPosePlay(8417459,"idle",0,0));
    AW_ObjPoseFact(8417459,id,sizeof(id));assert(!strcmp(id,"amiwind:pose:8417459") && get(id)==0);
    /* on Yes: LoopGroup idle2 0 1 by the stable id: the fact at once; mode 1 starts it at once (the idle's own end is
     * dropped, OpenMW playGroup clears the queue), the swap 7.2 s later */
    assert(AW_ObjPosePlay(2126003,"idle2",0,1));
    assert(get(id)==AW_ObjPoseGroupCode("idle2"));
    clock_now=103.0;AW_ObjPoseTick();assert(swap_count==0);
    clock_now=107.1;AW_ObjPoseTick();assert(swap_count==0);
    clock_now=107.3;AW_ObjPoseTick();
    assert(swap_count==1 && swaps[0].ref==8417459 && swaps[0].model==7900 && swaps[0].box[0]==220 && swaps[0].box[5]==-240);
    AW_ObjPoseTick();assert(swap_count==1);                      /* made once */

    /* the player leaves and comes back (a new load of the same room): the saved end pose at once */
    room_on=0;AW_ObjPoseTick();room_on=1;room_serial=2;
    AW_ObjPoseTick();assert(swap_count==2 && swaps[1].model==7900);

    /* the Clockwork City: lever 1 opens pre-door 1 (idle2, 9.33 s), pulled again before it opened: the close (idle3)
     * is queued behind the open in mode 0, then the door stands as placed and the fact is cleared */
    strcpy(room_name,"ri60b45e81e3");room_serial=3;clock_now=200.0;AW_ObjPoseTick();
    swap_count=0;
    assert(AW_ObjPosePlay(4198000,"idle2",0,0));
    clock_now=205.0;assert(AW_ObjPosePlay(4198000,"idle3",0,0));
    AW_ObjPoseFact(4198000,id,sizeof(id));assert(get(id)==0);
    clock_now=209.4;AW_ObjPoseTick();assert(swap_count==0);     /* the open would have ended, but the close replaced it */
    clock_now=218.6;AW_ObjPoseTick();assert(swap_count==0);
    clock_now=218.7;AW_ObjPoseTick();assert(swap_count==1 && swaps[0].model==7001 && swaps[0].box[0]==11);
    /* a group that draws nothing at its end: hidden (model -1), LoopGroup 2 more loops = 3 x 0.9 s */
    assert(AW_ObjPosePlay(4198001,"idle2",2,1));
    clock_now=221.3;AW_ObjPoseTick();assert(swap_count==1);
    clock_now=221.4;AW_ObjPoseTick();assert(swap_count==2 && swaps[1].model==-1);

    /* in another room: only its rows apply; a call on an object of a room not loaded keeps its fact, that room's next
     * load applies it */
    strcpy(room_name,"rif61f4dc044");room_serial=4;swap_count=0;AW_ObjPoseTick();
    assert(swap_count==1 && swaps[0].ref==8417459);
    assert(AW_ObjPosePlay(4198000,"idle2",0,0));
    clock_now=500.0;AW_ObjPoseTick();assert(swap_count==1);     /* nothing waits here for it */
    strcpy(room_name,"ri60b45e81e3");room_serial=5;swap_count=0;AW_ObjPoseTick();
    assert(swap_count==2 && swaps[0].model+swaps[1].model==7901-1);   /* the door's open pose and the hidden one */

    /* New Game: the waiting swaps go */
    assert(AW_ObjPosePlay(4198000,"idle3",0,1));
    AW_ObjPoseReset();clock_now=1000.0;
    room_on=0;AW_ObjPoseTick();
    swap_count=0;room_on=1;AW_ObjPoseTick();assert(swap_count==0 || swaps[0].model!=7001);
    AW_ObjPoseCounts(c);assert(c[1]==7 && c[3]==2);
    printf("aga_objpose_test: ok\n");
    return 0;
}
