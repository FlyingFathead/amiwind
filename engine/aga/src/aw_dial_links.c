/* SPDX-License-Identifier: GPL-2.0-or-later */
/* The dialogue window's link rules (aw_dial_links.h; DIALOGUE-LINKS-62). */
#include <string.h>
#include "aw_dial_links.h"

void AW_DialLinksSet(unsigned char *bits,int topics,const int *list,int n){
    int i;
    if(!bits || topics<0)return;
    memset(bits,0,(size_t)(topics/8+1));
    for(i=0;i<n;i++)if(list[i]>=0 && list[i]<topics)bits[list[i]>>3]|=(unsigned char)(1<<(list[i]&7));
}
int AW_DialLinkOn(const unsigned char *bits,int topics,int topic){
    return bits && topic>=0 && topic<topics && (bits[topic>>3]&(1<<(topic&7)));
}
int AW_DialBar(int total,int visible,int first,int track,int *pos,int *len){
    int range,span;
    *pos=*len=0;
    if(visible<=0 || total<=visible || track<=0)return 0;
    *len=track*visible/total;
    if(*len<AW_DIAL_BAR_MIN_THUMB)*len=AW_DIAL_BAR_MIN_THUMB;
    if(*len>track)*len=track;
    range=track-*len;span=total-visible;
    if(first<0)first=0;
    if(first>span)first=span;
    *pos=(range*first+span/2)/span;
    return 1;
}
int AW_DialBarFirst(int total,int visible,int track,int y){
    int pos,len,range,span,p;
    if(!AW_DialBar(total,visible,0,track,&pos,&len))return 0;
    range=track-len;span=total-visible;
    if(range<=0)return 0;
    p=y-len/2;
    if(p<0)p=0;
    if(p>range)p=range;
    return (p*span+range/2)/range;
}
int AW_DialBarClick(int total,int visible,int first,int h,int y,int *grab){
    int track=h-2*AW_DIAL_BAR_ARROW,pos,len,page=visible>1?visible-1:1,span=total-visible;
    *grab=0;
    if(span<=0)return 0;
    if(y<AW_DIAL_BAR_ARROW)first--;
    else if(y>=h-AW_DIAL_BAR_ARROW)first++;
    else if(AW_DialBar(total,visible,first,track,&pos,&len)){
        y-=AW_DIAL_BAR_ARROW;
        if(y<pos)first-=page;
        else if(y>=pos+len)first+=page;
        else *grab=1;
    }
    if(first<0)first=0;
    if(first>span)first=span;
    return first;
}
int AW_DialLinkHit(const aw_dial_hit_t *hits,int n,int x,int y,int row_h){
    int h;
    for(h=0;h<n;h++)
        if(x>=hits[h].x && x<hits[h].x+hits[h].w && y>=hits[h].y-1 && y<hits[h].y-1+row_h)return h;
    return -1;
}
int AW_DialChoiceAt(const aw_dial_hit_t *hits,int n,int x,int y,int row_h){
    int h=AW_DialLinkHit(hits,n,x,y,row_h);
    return h>=0 && hits[h].para==AW_DIAL_HIT_CHOICE?hits[h].span:-1;
}
int AW_DialChoiceStep(int count,int focus,int dir){
    if(count<=0)return -1;
    if(focus<0 || focus>=count)return dir>0?0:count-1;
    return dir>0?(focus+1)%count:(focus+count-1)%count;
}
