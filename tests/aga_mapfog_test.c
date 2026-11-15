/* SPDX-License-Identifier: GPL-2.0-or-later
 * MAP-ORIGINAL-POI-66 stage 2: the map's explored land (aw_mapfog.c): the reveal around the player (0.17 of a cell,
 * squares of 1024 units), never re-fogged, across cell borders and west/south of zero; the saved rows (a fully
 * explored cell short) read back the same; broken rows refused with nothing kept; New Game clears it. */
#include "aw_mapfog.h"
#include <assert.h>
#include <string.h>
#include <stdio.h>

int main(void){
    static unsigned char saved[65536];int n,i,x,y,again;const unsigned char *bits;
    AW_MapFogReset();
    assert(!AW_MapFogSeen(100,100) && !AW_MapFogCells());
    /* the centre of cell 0,0: squares within 1392.6 units of 4096,4096 by their centres */
    assert(AW_MapFogReveal(4096,4096));
    assert(AW_MapFogSeen(4096,4096) && AW_MapFogSeen(3500,3500) && AW_MapFogSeen(4600,4600) && !AW_MapFogSeen(5200,4096));
    assert(!AW_MapFogSeen(4096,6200) && !AW_MapFogSeen(1000,4096) && !AW_MapFogSeen(-4096,4096));
    assert(AW_MapFogCells()==1 && !AW_MapFogReveal(4096,4096));          /* nothing new on the same spot */
    /* on a cell corner: four cells, the negative ones included */
    assert(AW_MapFogReveal(0,0));
    assert(AW_MapFogSeen(-100,-100) && AW_MapFogSeen(100,-100) && AW_MapFogSeen(-100,100) && AW_MapFogCells()==4);
    assert(AW_MapFogSeen(4096,4096));                                     /* never fogged again */
    /* a whole cell walked over: saved in its short form */
    for(y=8192*2+256;y<8192*3;y+=512)for(x=-8192*3+256;x<-8192*2;x+=512)AW_MapFogReveal((float)x,(float)y);
    for(i=again=0;AW_MapFogRow(i,&x,&y,&bits);i++)if(x==-3 && y==2){int k;for(k=0;k<8;k++)assert(bits[k]==255);again=1;}
    assert(again);
    n=AW_MapFogExport(saved,sizeof saved);
    assert(n>6 && !memcmp(saved,"AWFG",4) && AW_MapFogExport(NULL,0)==n);
    /* MAP-EXPLORED-SAVE-BLOCK-66 and the save contract: the land is never cut: one byte short writes nothing and says
     * every cell was left out (the save sizes the section to the whole need, so it never meets this) */
    {int cells,rooms,k=AW_MapFogExport(saved,n-1);AW_MapFogLeftOut(&cells,&rooms);
     assert(k==0 && cells==AW_MapFogCells() && rooms==0);
     n=AW_MapFogExport(saved,sizeof saved);AW_MapFogLeftOut(&cells,&rooms);assert(!cells && !rooms);
     assert(saved[6+4]==1);}                                               /* the fully explored cell first */
    /* save, New Game, load: the same land is open again */
    i=AW_MapFogCells();AW_MapFogReset();assert(!AW_MapFogSeen(4096,4096) && !AW_MapFogCells());
    assert(AW_MapFogImport(saved,n)==n && AW_MapFogCells()==i);
    assert(AW_MapFogSeen(4096,4096) && AW_MapFogSeen(-100,-100) && AW_MapFogSeen(-8192*3+600,8192*2+600));
    assert(!AW_MapFogSeen(4096,6200));
    /* broken data: refused, nothing kept */
    assert(AW_MapFogImport(saved,n-1)==-1 && !AW_MapFogCells());
    saved[10]=7;assert(AW_MapFogImport(saved,n)==-1 && !AW_MapFogCells());
    assert(AW_MapFogImport((const unsigned char *)"AWXX\0\0",6)==-1);
    assert(AW_MapFogImport((const unsigned char *)"AWFG\0\0",6)==6 && !AW_MapFogCells());
    /* stage 3: a room's own fog over its box, kept by name, saved after the land and read back; an older save
     * (no AWFI part) reads as before; a save too small for the rooms keeps the land */
    {   static const float mins[2]={-1000,-500},maxs[2]={3000,1500};int land;
        AW_MapFogReset();AW_MapFogReveal(4096,4096);
        assert(!AW_MapFogRoomSeen("census",0,0,mins,maxs));
        assert(AW_MapFogRoomReveal("census",0,0,mins,maxs) && AW_MapFogRooms()==1);
        assert(AW_MapFogRoomSeen("census",0,0,mins,maxs) && AW_MapFogRoomSeen("census",150,100,mins,maxs));
        assert(!AW_MapFogRoomSeen("census",2800,1400,mins,maxs) && !AW_MapFogRoomSeen("other",0,0,mins,maxs));
        assert(!AW_MapFogRoomSeen("census",5000,0,mins,maxs) && !AW_MapFogRoomReveal("census",5000,0,mins,maxs));
        assert(!AW_MapFogRoomReveal("",0,0,mins,maxs) && !AW_MapFogRoomReveal("a_name_too_long_",0,0,mins,maxs));
        for(y=-480;y<1500;y+=60)for(x=-980;x<3000;x+=100)AW_MapFogRoomReveal("hall",(float)x,(float)y,mins,maxs);
        assert(AW_MapFogRooms()==2);
        land=AW_MapFogExport(saved,6+5+8);assert(land==6+5+8);              /* no room for the rooms: the land alone */
        {int cells,rooms;                                                     /* room for one: the fully explored hall */
         assert(AW_MapFogExport(saved,land+6+2+4)==land+6+2+4);AW_MapFogLeftOut(&cells,&rooms);assert(!cells && rooms==1);}
        n=AW_MapFogExport(saved,sizeof saved);
        assert(n==land+6+(2+6+32)+(2+4) && !memcmp(saved+land,"AWFI",4));    /* the hall fully explored: short form */
        AW_MapFogReset();assert(!AW_MapFogRooms());                          /* New Game */
        assert(AW_MapFogImport(saved,n)==n && AW_MapFogRooms()==2 && AW_MapFogCells()==1);
        assert(AW_MapFogRoomSeen("census",0,0,mins,maxs) && !AW_MapFogRoomSeen("census",2800,1400,mins,maxs));
        assert(AW_MapFogRoomSeen("hall",2900,1400,mins,maxs));
        assert(AW_MapFogImport(saved,land)==land && !AW_MapFogRooms() && AW_MapFogCells()==1);   /* an older save */
        assert(AW_MapFogImport(saved,n-1)==-1 && !AW_MapFogRooms() && !AW_MapFogCells());
        saved[land+6]=0;assert(AW_MapFogImport(saved,n)==-1 && !AW_MapFogRooms());
    }
    /* a cell twice in a save is refused (checked by a sorted copy taken for the load only) */
    {static const unsigned char twice[]={'A','W','F','G',2,0, 1,0,2,0,1, 1,0,2,0,1};
     static const unsigned char two[]={'A','W','F','G',2,0, 1,0,2,0,1, 2,0,2,0,1};
     assert(AW_MapFogImport(twice,sizeof twice)==-1 && !AW_MapFogCells());
     assert(AW_MapFogImport(two,sizeof two)==(int)sizeof two && AW_MapFogCells()==2);}
    /* MAP-EXPLORED-ROOMS-CAP-66: 2,048 rooms (was 256), every one found again by its name through the index, the
     * 2,049th refused; the room's bits for a whole picture in one lookup; save and load keep them all */
    {   static const float mins[2]={0,0},maxs[2]={1600,1600};static unsigned char all[200000];char name[16];
        int i,k;unsigned long per;const unsigned char *bits;
        AW_MapFogReset();
        assert(!AW_MapFogRoomBits("ri0000000000") && !AW_MapFogRoomBits(NULL));
        for(i=0;i<AW_MAPFOG_ROOMS;i++){sprintf(name,"ri%010d",i);assert(AW_MapFogRoomReveal(name,800,800,mins,maxs));}
        assert(AW_MapFogRooms()==2048);
        assert(!AW_MapFogRoomReveal("ri9999999999",800,800,mins,maxs) && AW_MapFogRooms()==2048);
        for(i=0;i<AW_MAPFOG_ROOMS;i+=97){
            sprintf(name,"ri%010d",i);assert(AW_MapFogRoomSeen(name,800,800,mins,maxs) && !AW_MapFogRoomSeen(name,50,50,mins,maxs));
            bits=AW_MapFogRoomBits(name);k=8*AW_MAPFOG_ROOM_GRID+8;assert(bits && (bits[k>>3]>>(k&7)&1) && !(bits[0]&1));
        }
        per=AW_MapFogBytes()/AW_MAPFOG_ROOMS;
        assert(AW_MapFogBytes()==2048UL*AW_MAPFOG_ROOM_BYTES+4096UL*2 && per==AW_MAPFOG_ROOM_BYTES+AW_MAPFOG_ROOM_INDEX_BYTES);
        printf("rooms 2048: %lu bytes held, %lu a room\n",AW_MapFogBytes(),per);
        n=AW_MapFogExport(all,sizeof all);assert(n==AW_MapFogExport(NULL,0));
        AW_MapFogReset();assert(AW_MapFogImport(all,n)==n && AW_MapFogRooms()==2048);
        sprintf(name,"ri%010d",2047);assert(AW_MapFogRoomSeen(name,800,800,mins,maxs));
        /* a room twice in a save is refused */
        AW_MapFogReset();AW_MapFogRoomReveal("hall",800,800,mins,maxs);AW_MapFogRoomReveal("cave",800,800,mins,maxs);
        n=AW_MapFogExport(all,sizeof all);memcpy(all+6+6+1,"cave",4);assert(AW_MapFogImport(all,n)==-1 && !AW_MapFogRooms());
        AW_MapFogReset();assert(!AW_MapFogBytes());
    }
    AW_MapFogReset();
    puts("map fog ok");
    return 0;
}
