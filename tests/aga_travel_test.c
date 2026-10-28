/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_travel_rules.c alone (TRAVEL-SERVICES-CHIM-51): the table's rows of one provider, the OpenMW price and hours.
 * Rules from OpenMW file apps/openmw/mwgui/travelwindow.cpp (outdoors: 3D distance / fTravelMult, at least 1, 2D
 * distance / fTravelTimeMult hours; indoors: fMagesGuildTravel, no time). */
#include <stdio.h>
#include <string.h>
#include "aw_travel.h"

static int failures;
#define CHECK(c) do{if(!(c)){printf("FAIL %s:%d %s\n",__FILE__,__LINE__,#c);failures++;}}while(0)

static const char table[]=
    "AWT1|4000.000|16000.000|10\n"
    "D|darvame hleran|0|balmora-chim|10.000|-20.500|56.875|90.000|-21319.0|-18232.0|1178.0|5|1|Balmora\n"
    "D|darvame hleran|0|vf0147|1.000|2.000|3.000|180.000|32207.0|-72224.0|1006.0|17|4|Vivec, Foreign Quarter\n"
    "D|Erranil|1|rifa414fba1a|-188.750|-250.750|-144.375|45.000|-756.0|-1003.0|-645.0|10|0|Balmora, Guild of Mages\n"
    "D|broken|0|vf0001|x|0|0|0|0|0|0|1|0|Bad number\n"
    "D|broken|0|vf0001|0|0|0|0|0|0|0|0|0|Zero price\n"
    "D|broken|2|vf0001|0|0|0|0|0|0|0|1|0|Bad flag\n"
    "D|broken|0||0|0|0|0|0|0|0|1|0|No map\n"
    "D|broken|0|vf0001|99999|0|0|0|0|0|0|1|0|Out of range\n";

int main(void){
    aw_travel_t t;int price,hours;float player[3]={-21319.f,-18232.f,1178.f};
    /* not a table */
    CHECK(AW_TravelParse("AWD3\n",NULL,&t)==-1);
    CHECK(AW_TravelParse(NULL,"x",&t)==-1);
    CHECK(AW_TravelParse("AWT1|x|1|1\n","x",&t)==-1);
    /* the header alone */
    CHECK(AW_TravelParse(table,NULL,&t)==0 && t.mult==4000.f && t.time_mult==16000.f && t.guild_price==10);
    /* a provider, by id without case */
    CHECK(AW_TravelParse(table,"Darvame Hleran",&t)==2);
    CHECK(!strcmp(t.rows[0].map,"balmora-chim") && !strcmp(t.rows[1].label,"Vivec, Foreign Quarter"));
    CHECK(t.rows[0].arrival[1]==-20.5f && t.rows[0].yaw==90.f && t.interior==0);
    CHECK(t.rows[1].price==17 && t.rows[1].hours==4);
    /* outdoors from the player's own spot: Balmora's square is next to him, so at least 1 and no hours */
    AW_TravelCost(&t,0,player,&price,&hours);CHECK(price==1 && hours==0);
    /* from (-8681 -70134 918) to Vivec: 3D distance 40,941.5 / 4000 = 10 (truncated), 2D 40,941.4 / 16000 = 2 hours */
    player[0]=-8681.f;player[1]=-70134.f;player[2]=918.f;
    AW_TravelCost(&t,1,player,&price,&hours);CHECK(price==10 && hours==2);
    /* no player position: the table's own */
    AW_TravelCost(&t,1,NULL,&price,&hours);CHECK(price==17 && hours==4);
    /* fTravelMult 0: the distance itself */
    t.mult=0;AW_TravelCost(&t,1,player,&price,&hours);CHECK(price==40941);
    /* a guild guide (an interior provider): the guild price, no time */
    CHECK(AW_TravelParse(table,"erranil",&t)==1 && t.interior==1);
    AW_TravelCost(&t,0,player,&price,&hours);CHECK(price==10 && hours==0);
    /* malformed rows are skipped, never half read */
    CHECK(AW_TravelParse(table,"broken",&t)==0);
    CHECK(AW_TravelParse(table,"nobody",&t)==0);
    if(failures)return 1;
    printf("travel rules: ok\n");return 0;
}
