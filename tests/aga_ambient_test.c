/* SPDX-License-Identifier: GPL-2.0-or-later
 * The ambient table reader (engine/aga/src/aw_ambient.c pure part, AW_AMBIENT_HOST_TEST) on a real AWAM1 file the
 * builder made (tests/test_ambient_lut.py): aga_ambient_test TABLE EXPECTATIONS (tab-separated lines: row, point,
 * hop, profile, idle, hash, missing). Also the decisions: allowed destinations, picks, the idle roll's table, and the
 * door rule (WANDER-DOOR-RULE-66: a door ahead, the idle check, a stuck walker's dropped destinations). */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_ambient.h"

static unsigned char *slurp(const char *path,long *size) {
    FILE *f=fopen(path,"rb");unsigned char *d;
    assert(f);fseek(f,0,SEEK_END);*size=ftell(f);fseek(f,0,SEEK_SET);
    d=(unsigned char *)malloc((size_t)*size);assert(d);
    assert((long)fread(d,1,(size_t)*size,f)==*size);fclose(f);
    return d;
}
static aw_ambient_table_t t;
static unsigned char *data;
/* WANDER-DOOR-RULE-66: the facing of a Quake yaw (degrees) as the engine gets it, its sine and cosine (Q_SinCosDeg
 * there, the C library here) into AW_AmbientForward */
static void facing(double yaw,float f[2]) {double a=yaw*3.14159265358979323846/180.0;AW_AmbientForward((float)sin(a),(float)cos(a),f);}
static void pkg_of(long row,aw_ambient_pkg_t *p) {
    aw_ambient_row_t r;long pa,pb,ha,hb;unsigned char *blob;
    AW_AmbientRow(&t,row,&r);AW_AmbientBlobAt(&t,&r,&pa,&pb,&ha,&hb);
    blob=(unsigned char *)malloc((size_t)(pb+hb));assert(blob);
    memcpy(blob,data+pa,(size_t)pb);memcpy(blob+pb,data+ha,(size_t)hb);
    memset(p,0,sizeof(*p));p->blob=blob;p->points=r.points;p->destinations=r.destinations;p->record_distance=r.distance;
}
int main(int argc,char **argv) {
    long size,rows;char line[1024];FILE *x;int checks=0;
    /* a third argument (AMBIENT-WALK-PER-AREA-60): a per-area table, its rows only (the decisions below need the
     * synthetic room's wanderer, which only one table holds) */
    assert(argc==3 || argc==4);
    data=slurp(argv[1],&size);
    rows=AW_AmbientRowsSize(data,size);
    assert(rows>=AW_AMBIENT_HEADER);
    {   /* the profiles are the file's last bytes */
        long n=(long)((unsigned long)data[20]<<24|(unsigned long)data[21]<<16|(unsigned long)data[22]<<8|data[23]);
        assert(AW_AmbientOpen(&t,data,rows,data+size-16*n,size));
        {aw_ambient_table_t bad;assert(!AW_AmbientOpen(&bad,data,rows,data+size-16*n,size+4));}
    }
    x=fopen(argv[2],"r");assert(x);
    while(fgets(line,sizeof(line),x)){
        char *f[24];int n=0;char *p=strtok(line,"\t\n");
        while(p && n<24){f[n++]=p;p=strtok(NULL,"\t\n");}
        if(!n)continue;
        if(!strcmp(f[0],"row")){
            aw_ambient_row_t r;long i=atol(f[3]);
            assert(AW_AmbientFind(&t,strtoul(f[1],NULL,10),strtoul(f[2],NULL,10))==i);
            AW_AmbientRow(&t,i,&r);
            assert(r.points==atoi(f[4]) && r.destinations==atoi(f[5]) && r.profile==atoi(f[6]));
        }else if(!strcmp(f[0],"point")){
            aw_ambient_pkg_t pk;int xyz[3],kind;
            pkg_of(atol(f[1]),&pk);AW_AmbientPoint(&pk,atoi(f[2]),xyz,&kind);
            assert(xyz[0]==atoi(f[3]) && xyz[1]==atoi(f[4]) && xyz[2]==atoi(f[5]) && kind==atoi(f[6]));
            free((void *)pk.blob);
        }else if(!strcmp(f[0],"hop")){
            aw_ambient_pkg_t pk;
            pkg_of(atol(f[1]),&pk);
            assert(AW_AmbientHop(&pk,atoi(f[2]),atoi(f[3]))==atoi(f[4]));
            free((void *)pk.blob);
        }else if(!strcmp(f[0],"profile")){
            unsigned short cdf[8];int i;
            AW_AmbientProfile(&t,atoi(f[1]),cdf);
            for(i=0;i<8;i++)assert(cdf[i]==(unsigned short)atoi(f[2+i]));
        }else if(!strcmp(f[0],"idle")){
            unsigned char c[8];unsigned short cdf[8];int i;
            for(i=0;i<8;i++)c[i]=(unsigned char)atoi(f[1+i]);
            AW_AmbientIdleProfile(c,t.multiplier,cdf);
            for(i=0;i<8;i++)assert(cdf[i]==(unsigned short)atoi(f[9+i]));
            /* picks follow the table: a roll under the first step is Idle2, one at the top is none */
            if(cdf[0])assert(AW_AmbientPickIdle(cdf,0)==2);
            if(cdf[7]<65535)assert(AW_AmbientPickIdle(cdf,65535)==0);
        }else if(!strcmp(f[0],"hash")){
            assert(AW_AmbientHash(f[1])==strtoul(f[2],NULL,10));
        }else if(!strcmp(f[0],"missing")){
            assert(AW_AmbientFind(&t,strtoul(f[1],NULL,10),strtoul(f[2],NULL,10))==-1);
        }else if(!strcmp(f[0],"levelled")){
            /* a levelled reference's routes joined with the picked creature's package (aw_ambient.c find_actor) */
            aw_ambient_row_t routes,pkg;unsigned long ref=strtoul(f[1],NULL,10);
            long a=AW_AmbientFind(&t,ref,AW_AMBIENT_LEVELLED_HASH),b=AW_AmbientFind(&t,AW_AMBIENT_LEVELLED_REF,strtoul(f[2],NULL,10));
            assert(a>=0 && b>=0);
            AW_AmbientRow(&t,a,&routes);AW_AmbientRow(&t,b,&pkg);
            assert(routes.flags&AW_AMBIENT_LEVELLED);
            AW_AmbientLevelled(&routes,&pkg);
            assert(routes.ref==ref && routes.distance==(unsigned)atoi(f[3]) && routes.duration==(unsigned)atoi(f[4]) &&
                   routes.flags==(unsigned)atoi(f[5]) && routes.profile==(unsigned)atoi(f[6]) && routes.destinations>1);
            {aw_ambient_table_t h;assert(AW_AmbientHeader(&h,data,size) && h.rows==t.rows && h.profiles_at==t.profiles_at);}
        }else assert(0);
        checks++;
    }
    fclose(x);
    if(argc==3){   /* decisions on the synthetic room: the wanderer (reference 7) has four grid destinations at 900, three at
         * the record's 700 is still four (offset 148 x 4 = 592 < 700); at 100 one point, so its start joins; at 0
         * nothing (stands) */
        long row=-1,i;aw_ambient_pkg_t pk;int seen[AW_AMBIENT_MAX_DEST],k,goal;
        for(i=0;i<t.rows;i++){aw_ambient_row_t r;AW_AmbientRow(&t,i,&r);if(r.ref==7)row=i;}
        assert(row>=0);pkg_of(row,&pk);
        AW_AmbientAllow(&pk,700);assert(pk.count==4 && !pk.manual);
        {int xyz[3];AW_AmbientPoint(&pk,pk.cur,xyz,NULL);assert(xyz[0]==-2);}   /* the closest to the start */
        memset(seen,0,sizeof(seen));
        for(k=0;k<300;k++){goal=AW_AmbientPickDestination(&pk,(unsigned)k*7919u);assert(goal>=0 && goal!=pk.cur);seen[goal]++;}
        for(k=0,i=0;i<pk.destinations;i++)k+=seen[i]>0;
        assert(k==3);                                       /* every other destination comes up */
        AW_AmbientAllow(&pk,100);assert(pk.count==2 && !pk.manual);   /* the one point and the start */
        AW_AmbientAllow(&pk,0);assert(pk.count==0 && !pk.manual);
        assert(AW_AmbientNearest(&pk,150,0,0)>=0);
        {   /* AITravel (v0.0.57): the route starts at the point nearest the actor and ends at the destination nearest
             * the target; a package without points plans nothing (the walk goes straight) */
            int from,xyz[3],best=-1,j;long bd=0,d;aw_ambient_pkg_t none;
            AW_AmbientPoint(&pk,pk.destinations-1,xyz,NULL);
            from=AW_AmbientTravelPlan(&pk,150,0,0,xyz[0]+1,xyz[1],xyz[2],&goal);
            assert(from==AW_AmbientNearest(&pk,150,0,0) && goal>=0 && goal<pk.destinations);
            for(j=0;j<pk.destinations;j++){int q[3];AW_AmbientPoint(&pk,j,q,NULL);
                d=(long)(q[0]-xyz[0]-1)*(q[0]-xyz[0]-1)+(long)(q[1]-xyz[1])*(q[1]-xyz[1])+(long)(q[2]-xyz[2])*(q[2]-xyz[2]);
                if(best<0 || d<bd){best=j;bd=d;}}
            assert(goal==best);
            memset(&none,0,sizeof(none));
            assert(AW_AmbientTravelPlan(&none,0,0,0,10,10,0,&goal)==-1 && goal==-1);
            /* the maximum range: 7168 original units = 1792 engine units */
            assert(AW_AmbientTravelInRange(1792,0,0) && !AW_AmbientTravelInRange(1793,0,0));
        }
        {   /* WANDER-DOOR-RULE-66 on the wanderer's routes: at 700 the four grid destinations lie on one line, cur (x -2)
             * at one end; FAR is the other end, FIRST the hop from cur toward it, MID the one between */
            int far=-1,first,mid,xyz[3],j,best=-1000,n,cur_was,seen3[AW_AMBIENT_MAX_DEST];
            static const float door_east[2]={30,0};
            float at[2],forward[2];
#define ALLOWED(p,i) (((p).allowed[(i)>>3]>>((i)&7))&1)
            AW_AmbientAllow(&pk,700);
            for(j=0;j<pk.destinations;j++)if(ALLOWED(pk,j)){AW_AmbientPoint(&pk,j,xyz,NULL);if(xyz[0]>best){best=xyz[0];far=j;}}
            first=AW_AmbientHop(&pk,pk.cur,far);mid=AW_AmbientHop(&pk,first,far);
            assert(far>=0 && first>=0 && mid>=0 && first!=far && mid!=far && ALLOWED(pk,first) && ALLOWED(pk,mid));
            assert(AW_AmbientHop(&pk,mid,far)==far);
            /* an idle wanderer at a destination, facing a door within 1.6 x the activation distance (76.8), walks on:
             * the idle check applies, the door is ahead, and it gets a destination other than where it stands */
            AW_AmbientPoint(&pk,pk.cur,xyz,NULL);at[0]=(float)xyz[0];at[1]=(float)xyz[1];
            facing(-90,forward);                                              /* facing +x, toward FIRST and the door */
            {float door[2];door[0]=at[0]+door_east[0];door[1]=at[1]+door_east[1];
             assert(AW_AmbientIdleCheck(&pk) && AW_AmbientDoorAhead(at,forward,door,76.8f));
             assert((n=AW_AmbientPickDestination(&pk,12345u))>=0 && n!=pk.cur);
             /* facing away from it, or the door farther than the distance: it stays in its idle */
             facing(90,forward);assert(!AW_AmbientDoorAhead(at,forward,door,76.8f));
             facing(-90,forward);door[0]=at[0]+80;assert(!AW_AmbientDoorAhead(at,forward,door,76.8f));}
            /* a stationary one (wander distance 0) and one that only wanders near its start never take the check */
            {aw_ambient_pkg_t still=pk;AW_AmbientAllow(&still,0);assert(!AW_AmbientIdleCheck(&still));
             still.distance=700;still.manual=1;assert(!AW_AmbientIdleCheck(&still));}
            /* a walker stuck by a door while walking to FIRST, bound for FAR, drops MID (its route after FIRST); FAR
             * stays while only two others would (OpenMW puts the destination back), and it never picks MID again */
            assert(AW_AmbientTrimRoute(&pk,first,far)==1);
            assert(!ALLOWED(pk,mid) && ALLOWED(pk,far) && ALLOWED(pk,first) && pk.count==3 && !pk.manual);
            for(k=0;k<300;k++){goal=AW_AmbientPickDestination(&pk,(unsigned)k*7919u);assert(goal>=0 && goal!=mid && goal!=pk.cur);}
            /* bound for FIRST (cur = its goal, as a walk sets it) with three others allowed: FIRST itself is dropped,
             * and every other destination can come up next, the start's included */
            AW_AmbientAllow(&pk,700);cur_was=pk.cur;pk.cur=(unsigned char)first;
            assert(AW_AmbientTrimRoute(&pk,cur_was,first)==1 && !ALLOWED(pk,first) && pk.count==3 && !pk.manual);
            memset(seen3,0,sizeof(seen3));
            for(k=0;k<300;k++){goal=AW_AmbientPickDestination(&pk,(unsigned)k*7919u);assert(goal>=0 && goal!=first);seen3[goal]++;}
            assert(seen3[cur_was] && seen3[mid] && seen3[far]);
            /* the routes behind a door take every other destination: one left, so the package wanders near its start */
            AW_AmbientAllow(&pk,700);pk.allowed[cur_was>>3]&=(unsigned char)~(1u<<(cur_was&7));pk.count=3;
            pk.cur=(unsigned char)far;
            assert(AW_AmbientTrimRoute(&pk,cur_was,far)==2 && pk.count==1 && pk.manual && ALLOWED(pk,far));
            assert(AW_AmbientPickDestination(&pk,0)==-1);
            assert(AW_AmbientTrimRoute(&pk,-1,far)==0 && AW_AmbientTrimRoute(&pk,cur_was,pk.destinations)==0);
#undef ALLOWED
            checks+=17;
        }
        free((void *)pk.blob);
    }
    assert(AW_AmbientWithin(0,0,0,0) && AW_AmbientWithin(25,0,0,100) && !AW_AmbientWithin(26,0,0,100));
    assert(!AW_AmbientWithin(20000,0,0,65535));
    {   /* AIFollowCell (v0.0.62, OpenMW aifollow.cpp): no place named: near the point anywhere; a room: only there;
         * a cell that is no room: never by its position */
        assert(AW_AmbientFollowDone(0,0,99,10) && !AW_AmbientFollowDone(0,0,100,10));
        assert(AW_AmbientFollowDone(7,7,1,10) && !AW_AmbientFollowDone(7,8,1,10) && !AW_AmbientFollowDone(7,0,1,10));
        assert(!AW_AmbientFollowDone(-1,0,0,10) && !AW_AmbientFollowDone(-1,5,0,10));
    }
    {   /* AIEscort (v0.0.62, OpenMW aiescort.cpp): 450 to start, then the half extent + 450 while near, + 250 once the
         * target fell behind; done within 64 of the destination; outside its place it waits */
        float max=0;
        assert(AW_AmbientEscortStep(0,0,100.0f*100.0f,500.0f*500.0f,16,&max)==AW_ESCORT_WALK && max==16+112.5f);
        assert(AW_AmbientEscortStep(0,0,120.0f*120.0f,500.0f*500.0f,16,&max)==AW_ESCORT_WALK);   /* 128.5 now */
        assert(AW_AmbientEscortStep(0,0,130.0f*130.0f,500.0f*500.0f,16,&max)==AW_ESCORT_WAIT && max==16+62.5f);
        assert(AW_AmbientEscortStep(0,0,100.0f*100.0f,500.0f*500.0f,16,&max)==AW_ESCORT_WAIT);   /* 78.5: still behind */
        assert(AW_AmbientEscortStep(0,0,70.0f*70.0f,500.0f*500.0f,16,&max)==AW_ESCORT_WALK);
        assert(AW_AmbientEscortStep(0,0,70.0f*70.0f,15.0f*15.0f,16,&max)==AW_ESCORT_DONE);
        max=0;
        assert(AW_AmbientEscortStep(9,3,0,0,16,&max)==AW_ESCORT_WAIT && max==0);   /* another room: waits */
        assert(AW_AmbientEscortStep(9,9,0,0,16,&max)==AW_ESCORT_DONE);
        assert(AW_AmbientEscortStep(-1,9,0,0,16,&max)==AW_ESCORT_WAIT);           /* outdoors only */
        assert(AW_AmbientEscortStep(-1,0,0,0,16,&max)==AW_ESCORT_DONE);
        checks+=14;
    }
    {   /* WANDER-DOOR-RULE-66 (OpenMW obstacle.cpp getNearbyDoor): ahead = within the distance and at most 60 degrees off
         * the facing; a converted character of yaw 0 faces +y, of yaw -90 +x; heights play no part */
        float at[2]={100,200},f[2],d[2];
        facing(0,f);assert(fabs(f[0])<1e-6 && fabs(f[1]-1)<1e-6);
        facing(-90,f);assert(fabs(f[0]-1)<1e-6 && fabs(f[1])<1e-6);
        facing(90,f);assert(fabs(f[0]+1)<1e-6 && fabs(f[1])<1e-6);
        facing(0,f);
        d[0]=100;d[1]=250;assert(AW_AmbientDoorAhead(at,f,d,76.8f));                     /* 50 straight ahead */
        d[0]=100;d[1]=276.8f;assert(AW_AmbientDoorAhead(at,f,d,76.8f));                  /* at the distance itself */
        d[0]=100;d[1]=277.5f;assert(!AW_AmbientDoorAhead(at,f,d,76.8f));                 /* past it */
        d[0]=100;d[1]=150;assert(!AW_AmbientDoorAhead(at,f,d,76.8f));                    /* behind */
        d[0]=100+50*(float)sin(55*3.14159265/180);d[1]=200+50*(float)cos(55*3.14159265/180);
        assert(AW_AmbientDoorAhead(at,f,d,76.8f));                                       /* 55 degrees off */
        d[0]=100+50*(float)sin(65*3.14159265/180);d[1]=200+50*(float)cos(65*3.14159265/180);
        assert(!AW_AmbientDoorAhead(at,f,d,76.8f));                                      /* 65 degrees off */
        d[0]=100;d[1]=200;assert(!AW_AmbientDoorAhead(at,f,d,76.8f));                    /* on its own spot */
        /* a walker's check uses the activation distance itself (48): a door 50 ahead is not by it */
        d[0]=100;d[1]=250;assert(!AW_AmbientDoorAhead(at,f,d,48.0f));
        checks+=12;
    }
    printf("aga_ambient_test: %d checks passed\n",checks);
    free(data);
    return 0;
}
