/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_water_rules.c alone (GETWATERLEVEL-COLUMN-NOT-ROOM-67): the WATR rows looked up by a room's stable number, and
 * GetWaterLevel's three cases (OpenMW 0.51 cellextensions.cpp OpGetWaterLevel): outdoors 0, a room with the water flag
 * its own level, a room without it the lowest float. The rows are those of the two water rooms of Old Mournhold as
 * the builder writes them (their levels from Tribunal.esm: 0 and -1500) beside rooms around them. */
#include <assert.h>
#include <float.h>
#include <string.h>
#include "aw_water.h"

static void row(unsigned char *at,unsigned number,unsigned flags,float level){
    unsigned int bits;
    memcpy(&bits,&level,4);
    at[0]=(unsigned char)(number>>8);at[1]=(unsigned char)number;at[2]=(unsigned char)flags;at[3]=0;
    at[4]=(unsigned char)(bits>>24);at[5]=(unsigned char)(bits>>16);at[6]=(unsigned char)(bits>>8);at[7]=(unsigned char)bits;
}

int main(void){
    unsigned char rows[6*AW_WATER_ROW_BYTES];float level=123.0f;unsigned n;
    /* ascending by number, as tools/mwscript/awms.py writes them */
    row(rows+0*8,7,AW_WATER_FLAG,-12.5f);
    row(rows+1*8,1196,AW_WATER_FLAG,0.0f);        /* Old Mournhold: Forgotten Sewer, WHGT 0 */
    row(rows+2*8,1211,AW_WATER_FLAG,-1500.0f);    /* Old Mournhold: Temple Sewers West, WHGT -1500 */
    row(rows+3*8,1300,0,55.0f);                   /* a row without the flag is no water room */
    row(rows+4*8,40000,AW_WATER_FLAG,850.0f);
    row(rows+5*8,65535,AW_WATER_FLAG,1.0e30f);
    /* found: the room's own level, exact */
    assert(AW_WaterRow(rows,6,1211,&level) && level==-1500.0f);
    assert(AW_WaterRow(rows,6,1196,&level) && level==0.0f);
    assert(AW_WaterRow(rows,6,7,&level) && level==-12.5f);
    assert(AW_WaterRow(rows,6,40000,&level) && level==850.0f);
    assert(AW_WaterRow(rows,6,65535,&level) && level==1.0e30f);
    /* not found: a room between the rows, before, after, a row without the flag; *level is left alone */
    level=7.0f;
    assert(!AW_WaterRow(rows,6,1212,&level) && level==7.0f);
    assert(!AW_WaterRow(rows,6,0,&level) && !AW_WaterRow(rows,6,6,&level) && !AW_WaterRow(rows,6,65534,&level));
    assert(!AW_WaterRow(rows,6,1300,&level) && level==7.0f);
    assert(!AW_WaterRow(NULL,6,1211,&level) && !AW_WaterRow(rows,0,1211,&level));
    /* every listed room is found from every table length (the search's ends) */
    for(n=1;n<=6;n++){
        assert(AW_WaterRow(rows,n,7,&level));
        if(n>=3)assert(AW_WaterRow(rows,n,1211,&level) && level==-1500.0f);
        else assert(!AW_WaterRow(rows,n,1211,&level));
    }
    /* a level that is not a number counts as not listed */
    {float nan;unsigned int bits=0x7fc00000u;memcpy(&nan,&bits,4);row(rows+0*8,7,AW_WATER_FLAG,nan);
     assert(!AW_WaterRow(rows,6,7,&level));}
    /* the three cases */
    assert(AW_WaterNone()==-FLT_MAX);
    assert(AW_WaterReading(AW_WATER_OUTDOORS,1,-1500.0f)==0.0f);     /* outdoors 0, whatever the table says */
    assert(AW_WaterReading(AW_WATER_OUTDOORS,0,0.0f)==0.0f);
    assert(AW_WaterReading(AW_WATER_NOWHERE,1,5.0f)==0.0f);          /* no player: 0 */
    assert(AW_WaterReading(AW_WATER_ROOM,1,-1500.0f)==-1500.0f);     /* the room's own level */
    assert(AW_WaterReading(AW_WATER_ROOM,1,0.0f)==0.0f);
    assert(AW_WaterReading(AW_WATER_ROOM,0,0.0f)==-FLT_MAX);         /* a room without water */
    /* Temple Sewers West: the Black Dart gang's arrival test reads 0 only outdoors, never in their room */
    assert(AW_WaterRow(rows,6,1211,&level) && AW_WaterReading(AW_WATER_ROOM,1,level)!=0.0f);
    /* MWSCRIPT-WATER-LEVEL-STATIC-67: SetWaterLevel sets, ModWaterLevel adds (OpenMW OpSetWaterLevel/OpModWaterLevel) */
    assert(AW_WaterLevelAfter(0,-1500.0f,850.0f)==850.0f);
    assert(AW_WaterLevelAfter(1,-1500.0f,20.0f)==-1480.0f);
    assert(AW_WaterLevelAfter(1,400.0f,-5.0f)==395.0f);
    /* only in a room with water: outdoors and in a dry room nothing changes */
    assert(AW_WaterCallChanges(AW_WATER_ROOM,1) && !AW_WaterCallChanges(AW_WATER_ROOM,0));
    assert(!AW_WaterCallChanges(AW_WATER_OUTDOORS,1) && !AW_WaterCallChanges(AW_WATER_NOWHERE,1));
    /* the saved fact: its id by the room's number, its value the level's bits, back exactly */
    {char id[32];float back;float kept[]={-1500.0f,0.0f,400.0f,-550.0f,850.0f,0.125f,-1.0e-7f,1.0e30f};unsigned k;
     AW_WaterFactId(id,1211);assert(!strcmp(id,"amiwind:water:1211"));
     AW_WaterFactId(id,0);assert(!strcmp(id,"amiwind:water:0"));
     AW_WaterFactId(id,65535);assert(!strcmp(id,"amiwind:water:65535"));
     for(k=0;k<sizeof(kept)/sizeof(kept[0]);k++){
         back=AW_WaterFactLevel(AW_WaterFactValue(kept[k]));
         assert(!memcmp(&back,&kept[k],4));
     }}
    return 0;
}
