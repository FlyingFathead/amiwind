/* SPDX-License-Identifier: GPL-2.0-or-later
 * The travel services' rules (aw_travel.h): no engine dependencies, host-tested (tests/aga_travel_test.c).
 *
 * Rules from OpenMW file apps/openmw/mwgui/travelwindow.cpp (OpenMW 0.51; our own code, none copied):
 * - a provider in an interior (the guild guides) charges fMagesGuildTravel; no time passes;
 * - one outdoors charges the 3D distance from the player to the destination / fTravelMult (the distance alone when
 *   the setting is 0), truncated, at least 1; the ride takes the 2D distance / fTravelTimeMult whole hours.
 * Not applied yet: the barter adjustment (disposition, Mercantile) and the price of travelling followers.
 */
#include <math.h>
#include <string.h>
#include "aw_travel.h"

static int lower(int c){return c>='A' && c<='Z'?c+32:c;}
/* the next '|' field of *P (up to the end of the line); returns its length, -1 at the end of the line */
static int field(const char **p,const char **start){
    const char *s=*p;int n=0;
    if(!*s || *s=='\n' || *s=='\r')return -1;
    *start=s;while(s[n] && s[n]!='|' && s[n]!='\n' && s[n]!='\r')n++;
    *p=s+n+(s[n]=='|');
    return n;
}
static int number(const char *s,int n,float *out){
    float v=0,scale=0;int i=0,sign=1,digits=0;
    if(i<n && (s[i]=='-' || s[i]=='+')){sign=s[i]=='-'?-1:1;i++;}
    for(;i<n;i++){
        if(s[i]=='.' && !scale){scale=1;continue;}
        if(s[i]<'0' || s[i]>'9')return 0;
        digits++;
        if(scale){scale*=.1f;v+=(s[i]-'0')*scale;}else v=v*10+(s[i]-'0');
    }
    if(!digits)return 0;
    *out=v*sign;return 1;
}
static int copy(char *out,int size,const char *s,int n){
    if(n<1 || n>=size)return 0;
    memcpy(out,s,n);out[n]=0;return 1;
}
static int same(const char *s,int n,const char *id){
    int i;for(i=0;i<n;i++)if(!id[i] || lower((unsigned char)s[i])!=lower((unsigned char)id[i]))return 0;
    return !id[n];
}
static const char *next_line(const char *p){
    while(*p && *p!='\n')p++;
    return *p?p+1:p;
}
int AW_TravelParse(const char *text,const char *provider,aw_travel_t *out){
    const char *p=text,*s;int n,k;float v[4];
    memset(out,0,sizeof(*out));
    if(!text || strncmp(text,"AWT1|",5))return -1;
    p=text+5;
    for(k=0;k<3;k++){if((n=field(&p,&s))<0 || !number(s,n,&v[k]))return -1;}
    if(!(v[0]>=0) || !(v[1]>=0) || !(v[2]>=0))return -1;
    out->mult=v[0];out->time_mult=v[1];out->guild_price=(int)v[2];
    if(!provider || !provider[0])return 0;
    for(p=next_line(p);*p;p=next_line(p)){
        aw_travel_row_t r;const char *q=p;int interior;
        if(out->count>=AW_TRAVEL_ROWS)break;
        if((n=field(&q,&s))!=1 || s[0]!='D')continue;
        if((n=field(&q,&s))<1 || !same(s,n,provider))continue;
        memset(&r,0,sizeof(r));
        if((n=field(&q,&s))!=1 || (s[0]!='0' && s[0]!='1'))continue;
        interior=s[0]=='1';
        if((n=field(&q,&s))<0 || !copy(r.map,sizeof(r.map),s,n))continue;
        for(k=0;k<4;k++){if((n=field(&q,&s))<0 || !number(s,n,&v[k]))break;}
        if(k<4)continue;
        r.arrival[0]=v[0];r.arrival[1]=v[1];r.arrival[2]=v[2];r.yaw=v[3];
        for(k=0;k<3;k++){if((n=field(&q,&s))<0 || !number(s,n,&r.source[k]))break;}
        if(k<3)continue;
        if((n=field(&q,&s))<0 || !number(s,n,&v[0]) || (n=field(&q,&s))<0 || !number(s,n,&v[1]))continue;
        r.price=(int)v[0];r.hours=(int)v[1];
        if(r.price<1 || r.hours<0)continue;
        if((n=field(&q,&s))<0 || !copy(r.label,sizeof(r.label),s,n))continue;
        for(k=0;k<3;k++)if(!(fabs(r.arrival[k])<32768))break;
        if(k<3 || !(r.yaw>=-360 && r.yaw<=360))continue;
        out->interior=interior;out->rows[out->count++]=r;
    }
    return out->count;
}
void AW_TravelCost(const aw_travel_t *t,int row,const float *player,int *price,int *hours){
    const aw_travel_row_t *r=&t->rows[row];double dx,dy,dz,d3,d2;
    if(t->interior){*price=t->guild_price>1?t->guild_price:1;*hours=0;return;}
    if(!player || !isfinite(player[0]) || !isfinite(player[1]) || !isfinite(player[2])){*price=r->price;*hours=r->hours;return;}
    dx=r->source[0]-player[0];dy=r->source[1]-player[1];dz=r->source[2]-player[2];
    d3=sqrt(dx*dx+dy*dy+dz*dz);d2=sqrt(dx*dx+dy*dy);
    *price=(int)(t->mult!=0?d3/t->mult:d3);
    if(*price<1)*price=1;
    *hours=t->time_mult>0?(int)(d2/t->time_mult):0;
}
