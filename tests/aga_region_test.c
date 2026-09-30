/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_region.h"
#include <assert.h>
server_t sv;
void Con_Printf(char *fmt,...) {}
int COM_FOpenFile(char *name,FILE **f) {
    const char *s="AWBR1 4 96 540 50 50 30 90 -500 12 20 66\n"
        "bm000 -512 -512 1024 1024 -512 -512 2048 2048\n"
        "bm001 1024 0 2048 1024 0 0 2048 2048\n"
        "bm002 0 1024 1024 2048 0 0 2048 2048\n"
        "bm003 1024 1024 2048 2048 0 0 2048 2048\n";
    *f=tmpfile();assert(*f);fputs(s,*f);
    if(!strcmp(name,"seyda-regions.txt")){long pos;int c;rewind(*f);while((c=fgetc(*f))!=EOF){if(c=='b'){pos=ftell(*f);fseek(*f,pos-1,SEEK_SET);fputc('s',*f);fputc('n',*f);fflush(*f);}}}
    rewind(*f);return strlen(s);
}
int main(void) {
    aw_region_t regions[4];vec3_t p={0,0,0};float yaw;int x,y,i;
    memset(regions,0,sizeof(regions));
    for(y=0;y<2;y++)for(x=0;x<2;x++){
        i=y*2+x;regions[i].low[0]=x*1024;regions[i].low[1]=y*1024;
        regions[i].high[0]=(x+1)*1024;regions[i].high[1]=(y+1)*1024;
    }
    p[0]=1120;p[1]=512;assert(AW_RegionOwner(regions,4,p,0,96)==0);
    p[0]=1121;assert(AW_RegionOwner(regions,4,p,0,96)==1);
    p[0]=928;assert(AW_RegionOwner(regions,4,p,1,96)==1);
    p[0]=927;assert(AW_RegionOwner(regions,4,p,1,96)==0);
    p[0]=p[1]=1500;assert(AW_RegionOwner(regions,4,p,0,96)==3);
    p[0]=p[1]=2048;assert(AW_RegionOwner(regions,4,p,-1,0)==3);
    p[0]=2049;assert(AW_RegionOwner(regions,4,p,-1,0)==-1);
    p[0]=NAN;assert(AW_RegionOwner(regions,4,p,0,96)==-1);
    assert(AW_BalmoraArrival(0,p,&yaw) && p[0]==50 && p[2]==30 && yaw==90);
    assert(!strcmp(AW_BalmoraWorldModel(),"maps/bm000.bsp"));strcpy(sv.name,"balmora");
    p[0]=1121;assert(AW_BalmoraCrossing(p));assert(AW_BalmoraSelect(p));
    assert(!strcmp(AW_BalmoraWorldModel(),"maps/bm001.bsp"));assert(!AW_BalmoraCrossing(p));
    p[0]=927;assert(AW_BalmoraCrossing(p));assert(AW_BalmoraSelect(p));
    assert(!strcmp(AW_BalmoraWorldModel(),"maps/bm000.bsp"));
    assert(AW_BalmoraArrival(1,p,&yaw) && p[0]==-500 && p[2]==20 && yaw==66);
    strcpy(sv.name,"seyda");p[0]=p[1]=50;
    assert(AW_RegionSelect("seyda",p,0));
    assert(!strcmp(AW_RegionWorldModel("seyda",0),"maps/sn000.bsp"));
    assert(AW_RegionContains(p));p[0]=1121;assert(AW_RegionCrossing(p,0));
    assert(AW_RegionSelect("seyda",p,0));
    assert(!strcmp(AW_RegionWorldModel("seyda",0),"maps/sn001.bsp"));
    p[0]=695;p[1]=50;assert(AW_RegionSelect("seyda",p,1));
    assert(!strcmp(AW_RegionWorldModel("seyda",1),"maps/intro_docks.bsp"));
    assert(!AW_RegionCrossing(p,1));assert(AW_RegionCrossing(p,0));
    p[0]=52;p[1]=-152;assert(AW_RegionSelect("seyda",p,0));
    assert(!strcmp(AW_RegionWorldModel("seyda",0),"maps/sncourt.bsp"));
    assert(AW_RegionContains(p));assert(!AW_RegionCrossing(p,0));
    p[0]=120;p[1]=-45;assert(!AW_RegionCrossing(p,0));
    p[0]=16;p[1]=44;assert(AW_RegionCrossing(p,0));
    assert(AW_RegionSelect("seyda",p,0));
    assert(!strcmp(AW_RegionWorldModel("seyda",0),"maps/sn000.bsp"));
    assert(AW_BalmoraSelect(p));assert(!strcmp(AW_BalmoraWorldModel(),"maps/bm000.bsp"));
    return 0;
}
