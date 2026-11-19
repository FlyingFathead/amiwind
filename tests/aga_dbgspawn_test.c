/* SPDX-License-Identifier: GPL-2.0-or-later
 * dbg spawn's list rules (DBG-SPAWN-MENU-67; engine/aga/src/aw_dbgspawn.c built with AW_DBGSPAWN_RULES_ONLY): a row's
 * label keeps the whole record id (the name gives way), the id comes back from a label, the list is in name order
 * with the tab sorting first ("Rat" before "Rat Queen"), the line of properties for a creature and an NPC, and the
 * second word of dbg spawn ID [model]. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_dbgspawn.h"

static void labels(void){
    char out[AW_SPAWN_LABEL],small[12],id[64];int n;
    n=AW_SpawnLabel("Mudcrab","crab",out,sizeof(out));
    assert(n==12 && !strcmp(out,"Mudcrab\tcrab"));
    assert(AW_SpawnLabelId(out,id,sizeof(id)) && !strcmp(id,"crab"));
    /* no name: the id alone, and it is its own id */
    assert(AW_SpawnLabel("","cliff racer",out,sizeof(out))==11 && !strcmp(out,"cliff racer"));
    assert(AW_SpawnLabel(NULL,"rat",out,sizeof(out))==3 && !strcmp(out,"rat"));
    assert(AW_SpawnLabelId(out,id,sizeof(id)) && !strcmp(id,"rat"));
    /* a long name gives way to the id: "Mudcra" + tab + "crab" in 12 bytes */
    n=AW_SpawnLabel("Mudcrab","crab",small,sizeof(small));
    assert(n==11 && !strcmp(small,"Mudcra\tcrab"));
    assert(AW_SpawnLabelId(small,id,sizeof(id)) && !strcmp(id,"crab"));
    /* an id that does not fit, or none: no row */
    assert(AW_SpawnLabel("Name","a_very_long_record_id",small,sizeof(small))==-1);
    assert(AW_SpawnLabel("Name","",out,sizeof(out))==-1);
    assert(AW_SpawnLabel("Name",NULL,out,sizeof(out))==-1);
    /* a tab or a control in a name never splits the label twice */
    assert(AW_SpawnLabel("A\tB","ab",out,sizeof(out))==6 && !strcmp(out,"A B\tab"));
    /* the id read back needs its room */
    assert(!AW_SpawnLabelId("Mudcrab\tcrab",id,4) && !id[0]);
    assert(!AW_SpawnLabelId("Mudcrab\t",id,sizeof(id)));
    puts("labels passed");
}
static void order(void){
    assert(AW_SpawnCompare("Rat\trat","Rat Queen\trat_queen")<0);     /* the tab sorts before the space */
    assert(AW_SpawnCompare("mudcrab\tcrab","Mudcrab\tcrab")==0);       /* case ignored */
    assert(AW_SpawnCompare("Mudcrab\tcrab","Mudcrab\tcrab_02")<0);     /* the same name: by id */
    assert(AW_SpawnCompare("Ajira\tajira","Fargoth\tfargoth")<0);
    assert(AW_SpawnCompare("fargoth","Fargoth\tfargoth")<0);            /* an id alone sorts as a name, first */
    puts("order passed");
}
static void details(void){
    aw_spawn_facts_t f;char out[AW_SPAWN_DETAIL],tiny[16];
    memset(&f,0,sizeof(f));
    f.kind=1;f.level=3;f.health=13;f.magicka=0;f.fight=90;f.type=0;
    assert(AW_SpawnDetail(&f,out,sizeof(out))>0 && !strcmp(out,"Level 3, health 13, magicka 0, Fight 90\tcreature"));
    f.type=1;AW_SpawnDetail(&f,out,sizeof(out));assert(strstr(out,"\tdaedra"));
    f.type=2;AW_SpawnDetail(&f,out,sizeof(out));assert(strstr(out,"\tundead"));
    f.type=3;AW_SpawnDetail(&f,out,sizeof(out));assert(strstr(out,"\thumanoid"));
    f.type=9;AW_SpawnDetail(&f,out,sizeof(out));assert(strstr(out,"\tcreature"));
    memset(&f,0,sizeof(f));
    f.kind=0;f.level=2;f.health=36;f.magicka=50;f.fight=30;strcpy(f.race,"Wood Elf");strcpy(f.cls,"Pauper");
    AW_SpawnDetail(&f,out,sizeof(out));
    assert(!strcmp(out,"Level 2, health 36, magicka 50, Fight 30\tWood Elf Pauper"));
    f.cls[0]=0;AW_SpawnDetail(&f,out,sizeof(out));assert(!strcmp(out,"Level 2, health 36, magicka 50, Fight 30\tWood Elf"));
    /* cut to the room it has */
    assert(AW_SpawnDetail(&f,tiny,sizeof(tiny))==15 && !strcmp(tiny,"Level 2, health"));
    assert(AW_SpawnDetail(NULL,out,sizeof(out))==0 && !out[0]);
    puts("details passed");
}
static void how(void){
    assert(AW_SpawnHow(NULL)==1 && AW_SpawnHow("")==1 && AW_SpawnHow("full")==1 && AW_SpawnHow("attributes")==1);
    assert(AW_SpawnHow("model")==0 && AW_SpawnHow("placeholder")==0);
    assert(AW_SpawnHow("maybe")==-1);
    puts("how passed");
}
int main(void){
    labels();order();details();how();
    puts("dbg spawn rules passed");
    return 0;
}
