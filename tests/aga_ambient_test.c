/* SPDX-License-Identifier: GPL-2.0-or-later
 * The ambient table reader (engine/aga/src/aw_ambient.c pure part, AW_AMBIENT_HOST_TEST) on a real AWAM1 file the
 * builder made (tests/test_ambient_lut.py): aga_ambient_test TABLE EXPECTATIONS (tab-separated lines: row, point,
 * hop, profile, idle, hash, missing). Also the decisions: allowed destinations, picks, the idle roll's table. */
#include <assert.h>
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
static void pkg_of(long row,aw_ambient_pkg_t *p) {
    aw_ambient_row_t r;long pa,pb,ha,hb;unsigned char *blob;
    AW_AmbientRow(&t,row,&r);AW_AmbientBlobAt(&t,&r,&pa,&pb,&ha,&hb);
    blob=(unsigned char *)malloc((size_t)(pb+hb));assert(blob);
    memcpy(blob,data+pa,(size_t)pb);memcpy(blob+pb,data+ha,(size_t)hb);
    memset(p,0,sizeof(*p));p->blob=blob;p->points=r.points;p->destinations=r.destinations;p->record_distance=r.distance;
}
int main(int argc,char **argv) {
    long size,rows;char line[1024];FILE *x;int checks=0;
    assert(argc==3);
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
    {   /* decisions on the synthetic room: the wanderer (reference 7) has four grid destinations at 900, three at
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
        free((void *)pk.blob);
    }
    assert(AW_AmbientWithin(0,0,0,0) && AW_AmbientWithin(25,0,0,100) && !AW_AmbientWithin(26,0,0,100));
    assert(!AW_AmbientWithin(20000,0,0,65535));
    printf("aga_ambient_test: %d checks passed\n",checks);
    free(data);
    return 0;
}
