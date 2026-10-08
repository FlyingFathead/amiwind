/* SPDX-License-Identifier: GPL-2.0-or-later
 * Table sine/cosine (ENGINE-FPU-UNIMPL-31): error against the C library
 * below 1.5e-7 over a wide angle range, exact at multiples of 90 degrees and
 * at zero, AngleVectors still orthonormal, and Q_atan2 equal to the C
 * library's atan2 (exact on the axes and diagonals). */
#include "quakedef.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>

void Sys_Error(char *fmt,...) {assert(0);}
static double worst;
static void one(double degrees)
{
    float s,c;double r=degrees*M_PI/180,es,ec;
    Q_SinCosDeg((float)degrees,&s,&c);
    r=(float)degrees*M_PI/180;  /* the angle actually passed */
    es=fabs(s-sin(r));ec=fabs(c-cos(r));
    if(es>worst)worst=es;
    if(ec>worst)worst=ec;
}
int main(void)
{
    int i,k;float s,c;vec3_t angles,f,r,u;double x;
    Q_SinCosDeg(0,&s,&c);assert(s==0 && c==1);
    for(k=-8;k<=8;k++){
        Q_SinCosDeg(k*90.0f,&s,&c);
        assert(s==(float)((k%4+4)%4==1?1:(k%4+4)%4==3?-1:0));
        assert(c==(float)((k%4+4)%4==0?1:(k%4+4)%4==2?-1:0));
    }
    for(i=-200000;i<=200000;i++)one(i*0.0137);
    for(x=1;x<1e9;x*=1.37)one(x),one(-x);
    printf("max error %.3g\n",worst);
    assert(worst<1.5e-7);
    assert(fabs(Q_SinRad(0.5f)-sin(0.5))<4e-7 && fabs(Q_CosRad(-2.0f)-cos(-2.0))<4e-7);
    for(i=0;i<500;i++){
        angles[0]=i*0.73f-180;angles[1]=i*2.9f;angles[2]=i*1.1f-90;
        AngleVectors(angles,f,r,u);
        assert(fabs(DotProduct(f,f)-1)<2e-6 && fabs(DotProduct(r,r)-1)<2e-6 && fabs(DotProduct(u,u)-1)<2e-6);
        assert(fabs(DotProduct(f,r))<2e-6 && fabs(DotProduct(f,u))<2e-6 && fabs(DotProduct(r,u))<2e-6);
    }
    {
        static const double v[]={0,1,-1,0.5,-0.25,3,-7,1e-6,-1e6,0.26794919243112270,1.7320508075688772};
        double e=0;int a,b;
        for(a=0;a<11;a++)for(b=0;b<11;b++){
            double y=v[a],x=v[b],d=fabs(Q_atan2(y,x)-atan2(y,x));
            if(!(y==0 && x==0) && d>e)e=d;
        }
        for(i=0;i<20000;i++){
            double y=sin(i*0.37)*(1+i%7),x=cos(i*0.53)*(1+i%5),d=fabs(Q_atan2(y,x)-atan2(y,x));
            if(d>e)e=d;
        }
        printf("atan2 max error %.3g\n",e);
        assert(e<1e-12);
        assert(Q_atan2(1,1)==M_PI/4 && fabs(Q_atan2(-1,-1)+3*M_PI/4)<1e-15);
        assert(Q_atan2(0,1)==0 && Q_atan2(0,-1)==M_PI && Q_atan2(1,0)==M_PI/2 && Q_atan2(-1,0)==-M_PI/2);
        assert((int)(Q_atan2(1,1)*180/M_PI)==(int)(atan2(1,1)*180/M_PI));
        assert(fabs(Q_TanRad(0.5f)-tan(0.5))<5e-7);
    }
    return 0;
}
