/* SPDX-License-Identifier: GPL-2.0-or-later */
/* LIGHTTEST-MAP-67, DBG-CYCLEITEMS-67 (aw_cycleitems.c, built with -DAW_CYCLE_HOST_TEST): the item tester reads the
 * holdable index's rows as tools/holdable_items.py writes them, refuses a damaged one, uses the attack only where the
 * item has one and writes its line for the screen; the light test's line names what the hands hold; the walk keeps the
 * head straight for 10 s, looks down at the hands from 10 to 15 s and back up to the end. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "aw_cycleitems.h"

static int parse(const char *line,aw_holdable_t *h){return AW_HoldableParse(line,(int)strlen(line),h);}
int main(void) {
    aw_holdable_t h;char line[200];float t;
    assert(parse("Iron Dagger\tchargen dagger\tshort blade\tright\tshortbladeonehand\t1",&h));
    assert(!strcmp(h.name,"Iron Dagger") && !strcmp(h.id,"chargen dagger") && !strcmp(h.kind,"short blade"));
    assert(!strcmp(h.hands,"right") && !strcmp(h.action,"shortbladeonehand") && h.equips==1 && AW_CycleHasAction(&h));
    assert(AW_CycleHudLine(line,sizeof(line),&h,3,632,AW_CYCLE_WALK));
    assert(!strcmp(line,"Iron Dagger (chargen dagger)  3/632  walk"));
    assert(AW_CycleHudLine(line,sizeof(line),&h,3,632,AW_CYCLE_HOLD) && !strcmp(line,"Iron Dagger (chargen dagger)  3/632  hold"));
    assert(AW_CycleHudLine(line,12,&h,3,632,AW_CYCLE_HOLD)==11 && strlen(line)==11);      /* cut to the buffer */
    assert(!AW_CycleHudLine(line,sizeof(line),&h,3,632,AW_CYCLE_STEPS) && !line[0]);
    assert(parse("Candle\tlight_com_candle_01_64\tlight\tleft\tnone\t1",&h) && !AW_CycleHasAction(&h));
    assert(parse("Steel Shield\tsteel_shield\tshield\tleft\tblock\t1",&h) && !AW_CycleHasAction(&h));
    assert(parse("Apprentice's Lockpick\tpick_apprentice_01\tlockpick\tright\tpickprobe\t0",&h) && !h.equips &&
           !AW_CycleHasAction(&h));
    assert(parse("Daedric Claymore\tdaedric claymore\tlong blade two-handed\tboth\tweapontwohand\t1",&h) &&
           AW_CycleHasAction(&h));
    /* damaged rows */
    assert(!parse("Iron Dagger\tchargen dagger\tshort blade\tright\tshortbladeonehand",&h));          /* five fields */
    assert(!parse("Iron Dagger\tchargen dagger\tshort blade\tright\tx\t1\textra",&h));                /* seven */
    assert(!parse("Iron Dagger\tchargen dagger\tshort blade\tup\tx\t1",&h));                          /* no such hand */
    assert(!parse("Iron Dagger\tchargen dagger\tshort blade\tright\tx\t2",&h));                       /* equips 0/1 */
    assert(!parse("\tchargen dagger\tshort blade\tright\tx\t1",&h));                                  /* no name */
    assert(!parse("Iron\nDagger\tchargen dagger\tshort blade\tright\tx\t1",&h));                      /* a line break */
    {
        char longid[100];memset(longid,'a',sizeof(longid));longid[99]=0;
        snprintf(line,sizeof(line),"N\t%s\tshort blade\tright\tx\t1",longid);
        assert(!parse(line,&h));                                                                     /* past 63 */
    }
    /* the light test's line: the game names and ids, the left hand first */
    assert(AW_LightHeldLine(line,sizeof(line),"","","","") && !strcmp(line,"empty hands"));
    assert(AW_LightHeldLine(line,sizeof(line),"Glass Lantern","light_de_lantern_02","","") &&
           !strcmp(line,"Glass Lantern (light_de_lantern_02)"));
    assert(AW_LightHeldLine(line,sizeof(line),"","","Chitin Dagger","chitin dagger") &&
           !strcmp(line,"Chitin Dagger (chitin dagger)"));
    assert(AW_LightHeldLine(line,sizeof(line),"Torch","light_com_torch_01","Chitin Dagger","chitin dagger") &&
           !strcmp(line,"Torch (light_com_torch_01)  +  Chitin Dagger (chitin dagger)"));
    assert(AW_LightHeldLine(line,sizeof(line),"","aw_debug_torch","","") && !strcmp(line,"aw_debug_torch (aw_debug_torch)"));
    assert(AW_LightHeldLine(line,8,"Torch","light_com_torch_01","","")==7 && strlen(line)==7);     /* cut to the buffer */
    /* the walk: straight on to 10 s, down at the hands from 10 to 15 s, back up to the end of its 20 s */
    assert(AW_LIGHTWALK_S==20.0f && AW_LIGHTWALK_DOWN>=40 && AW_LIGHTWALK_DOWN<=50);
    for(t=0;t<10;t+=.25f)assert(AW_LightWalkPitch(t)==0);
    assert(AW_LightWalkPitch(10.5f)>0 && AW_LightWalkPitch(10.5f)<AW_LIGHTWALK_DOWN);
    for(t=11;t<15;t+=.25f)assert(fabsf(AW_LightWalkPitch(t)-AW_LIGHTWALK_DOWN)<1e-4f);
    assert(AW_LightWalkPitch(15.5f)>0 && AW_LightWalkPitch(15.5f)<AW_LIGHTWALK_DOWN);
    for(t=16;t<=20;t+=.25f)assert(fabsf(AW_LightWalkPitch(t))<1e-4f);
    for(t=10;t<11;t+=.05f)assert(AW_LightWalkPitch(t+.05f)>=AW_LightWalkPitch(t));            /* eased, no jump */
    for(t=15;t<16;t+=.05f)assert(AW_LightWalkPitch(t+.05f)<=AW_LightWalkPitch(t));
    puts("Light test and item tester: index rows, damaged rows, actions, both lines and the walk's head passed.");
    return 0;
}
