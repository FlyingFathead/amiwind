/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "aw_hand_models.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

static void put32(unsigned char *p,unsigned long v){p[0]=v>>24;p[1]=v>>16;p[2]=v>>8;p[3]=v;}
static unsigned char raw[372];
static void metadata(void){
    int i;static const unsigned long times[8]={0,167,333,533,733,933,1133,1333};
    memset(raw,0,sizeof(raw));memcpy(raw,"AWB1",4);raw[5]=1;raw[7]=132;
    put32(raw+8,1333);put32(raw+12,333);
    for(i=0;i<8;i++){put32(raw+16+i*28,times[i]);put32(raw+20+i*28,(unsigned long)(unsigned int)(-8*65536));}
    strcpy((char *)raw+240,"nord");strcpy((char *)raw+308,"progs/hands/nord_m_b.mdl");
}
static void mul(double a[3][3],double b[3][3],double out[3][3]){
    int i,j,k;for(i=0;i<3;i++)for(j=0;j<3;j++){out[i][j]=0;for(k=0;k<3;k++)out[i][j]+=a[i][k]*b[k][j];}
}
/* Independent rotation oracle: three elementary row-vector rotation matrices,
 * rather than the renderer's closed-form AngleVectors expressions. */
static void rotations(double pitch,double yaw,double roll,double out[3][3]){
    double d=.017453292519943295,x[3][3]={{1,0,0},{0,0,0},{0,0,0}};
    double y[3][3]={{0,0,0},{0,1,0},{0,0,0}},z[3][3]={{0,0,0},{0,0,0},{0,0,1}},tmp[3][3];
    pitch*=d;yaw*=d;roll*=d;
    x[1][1]=x[2][2]=cos(roll);x[1][2]=sin(roll);x[2][1]=-sin(roll);
    y[0][0]=y[2][2]=cos(pitch);y[0][2]=-sin(pitch);y[2][0]=sin(pitch);
    z[0][0]=z[1][1]=cos(yaw);z[0][1]=sin(yaw);z[1][0]=-sin(yaw);
    mul(x,y,tmp);mul(tmp,z,out);
}
static void transform_case(const float base[3],const float local[3]){
    float pos[3]={17,-31,9},tag[6]={7,-5,3,0,0,0},origin[3],angles[3];
    double b[3][3],l[3][3],expected[3][3],actual[3][3],point;int i,j;
    memcpy(tag+3,local,3*sizeof(float));AW_BlockCompose(pos,base,tag,origin,angles);
    rotations(-base[0],base[1],base[2],b);rotations(local[0],local[1],local[2],l);mul(l,b,expected);
    rotations(-angles[0],angles[1],angles[2],actual);
    for(j=0;j<3;j++){
        point=pos[j];for(i=0;i<3;i++)point+=tag[i]*b[i][j];assert(fabs(origin[j]-point)<.0001);
        for(i=0;i<3;i++)assert(isfinite(angles[i]) && fabs(actual[i][j]-expected[i][j])<.00001);
    }
}
static void poles(void){
    static const float pitch[]={-90.01f,-90.f,-89.99999f,-89.9999f,-89.99f,-89.95f,
        89.95f,89.99f,89.9999f,89.99999f,90.f,90.01f};
    static const float yaw[]={-179,-90,-1,0,73,179};
    static const float roll[]={-179,-93,3,89,177};
    float base[3]={0,0,0},local[3];int i,j,k;
    for(i=0;i<12;i++)for(j=0;j<6;j++)for(k=0;k<5;k++){
        local[0]=pitch[i];local[1]=yaw[j];local[2]=roll[k];transform_case(base,local);
    }
    /* Cancellation in composed float matrices, not only identity-base poles. */
    base[0]=70;base[1]=123;base[2]=0;
    for(i=0;i<12;i++)for(k=0;k<5;k++){
        local[0]=pitch[i]+70;local[1]=0;local[2]=roll[k];transform_case(base,local);
    }
    for(i=0;i<1500;i++){
        base[0]=(i%179)-89;base[1]=(i*73%719)-359;base[2]=(i*31%359)-179;
        local[0]=(i*17%359)-179;local[1]=(i*67%719)-359;local[2]=(i*41%359)-179;
        transform_case(base,local);
    }
}
int main(int argc,char **argv){
    aw_block_view_t a;aw_block_clock_t c={0,0};int i,frame;
    const float base[][3]={{0,0,0},{-25,71,18},{43,-133,-31},{-89,178,27},{25,90,-65}};
    const float local[][3]={{30,0,0},{17,123,-47},{-38,72,41},{0,0,0},{-15,42,74}};
    if(argc==2){
        unsigned char actual[4464];FILE *f=fopen(argv[1],"rb");size_t size;
        assert(f);size=fread(actual,1,sizeof(actual),f);assert(!ferror(f) && fgetc(f)==EOF);fclose(f);
        assert(AW_BlockViewDecode(&a,actual,(int)size));
        printf("Actual block catalogue parsed: %d appearances, guard frame %d.\n",a.count,a.hold);
    }
    metadata();assert(AW_BlockViewDecode(&a,raw,sizeof(raw)) && a.count==1 && a.hold==2);
    assert(fabs(a.tag[0][0]+8)<.00001);
    assert(!AW_BlockViewDecode(&a,raw,sizeof(raw)-1) && !a.count);
    raw[7]=131;assert(!AW_BlockViewDecode(&a,raw,sizeof(raw)));metadata();
    put32(raw+16+28,0);assert(!AW_BlockViewDecode(&a,raw,sizeof(raw)));metadata();
    put32(raw+12,334);assert(!AW_BlockViewDecode(&a,raw,sizeof(raw)));metadata();
    strcpy((char *)raw+308,"../shield.mdl");assert(!AW_BlockViewDecode(&a,raw,sizeof(raw)));metadata();
    put32(raw+20,129*65536UL);assert(!AW_BlockViewDecode(&a,raw,sizeof(raw)));metadata();
    assert(AW_BlockViewDecode(&a,raw,sizeof(raw)));
    assert(AW_BlockPlayback(&a,&c,0,0,.05f)==-1);
    for(i=0;i<40;i++)frame=AW_BlockPlayback(&a,&c,1,0,.05f);
    assert(frame==2 && fabs(c.phase-a.hit)<.00001);
    assert(AW_BlockPlayback(&a,&c,1,0,0)==2); /* modal pause */
    for(i=0;i<30;i++)frame=AW_BlockPlayback(&a,&c,0,0,.05f);
    assert(frame==-1 && !c.mode);
    frame=AW_BlockPlayback(&a,&c,0,.5f,.05f);assert(frame>=a.hold && frame<8);
    for(i=0;i<5;i++)transform_case(base[i],local[i]);
    poles();
    {   /* First-person weapons (PLAYER-GEAR-VISUAL-59): stance by weapon value, the tag table, item paths. */
        static unsigned char w[8+3*28*24];static aw_hand_weapons_t h;int s;
        assert(AW_HandStance(0)==-1 && AW_HandStance(1)==0 && AW_HandStance(2)==0 && AW_HandStance(4)==0 && AW_HandStance(8)==0);
        assert(AW_HandStance(3)==1 && AW_HandStance(5)==1 && AW_HandStance(9)==1 && AW_HandStance(6)==2 && AW_HandStance(7)==2);
        assert(AW_HandStance(10)==3 && AW_HandStance(11)==4 && AW_HandStance(12)==5);   /* bow, crossbow, thrown */
        for(s=13;s<16;s++)assert(AW_HandStance(s)==-1);
        memset(w,0,sizeof(w));memcpy(w,"AWW1",4);w[5]=3;w[7]=28;
        put32(w+8+(2*28+27)*24,(unsigned long)(-5*65536L));put32(w+8+(2*28+27)*24+20,90*65536UL);
        assert(AW_HandWeaponsDecode(&h,w,sizeof(w)) && h.stances==3);
        assert(fabs(h.tag[2][27][0]+5)<.00001 && fabs(h.tag[2][27][5]-90)<.00001);
        assert(!AW_HandWeaponsDecode(&h,w,sizeof(w)-1) && !h.stances);
        w[7]=27;assert(!AW_HandWeaponsDecode(&h,w,sizeof(w)));w[7]=28;
        w[5]=4;assert(!AW_HandWeaponsDecode(&h,w,sizeof(w)));w[5]=1;
        assert(AW_HandWeaponsDecode(&h,w,8+28*24) && h.stances==1);w[5]=3;
        put32(w+8+4,129*65536UL);assert(!AW_HandWeaponsDecode(&h,w,sizeof(w)));put32(w+8+4,0);
        assert(AW_HandItemPath("progs/inv/steel_shield.mdl") && AW_HandItemPath("progs/items/m0123456789abcdef.mdl"));
        assert(!AW_HandItemPath("progs/hands/nord_m.mdl") && !AW_HandItemPath("progs/items/../x.mdl") &&
               !AW_HandItemPath("progs/items/M01.mdl") && !AW_HandItemPath("progs/items/m01.bsp") && !AW_HandItemPath(NULL));
    }
    puts("Block metadata/timing and 1925 matrix/translation cases including both poles passed.");return 0;
}
