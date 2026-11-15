/* SPDX-License-Identifier: GPL-2.0-or-later
 * The active-effect icons' rules (aw_fxrow.h): grouping, the grid with "+N", the texts, the effect file's directory.
 * Pure C, no engine headers. */
#include <stdio.h>
#include <string.h>
#include "aw_fxrow.h"

int AW_FxSort(aw_fx_entry_t *e,int n){
    int i,j;aw_fx_entry_t t;
    if(!e || n<1)return 0;
    for(i=1;i<n;i++){   /* insertion sort: stable, at most AW_FX_ENTRIES */
        t=e[i];
        for(j=i;j>0 && e[j-1].effect>t.effect;j--)e[j]=e[j-1];
        e[j]=t;
    }
    return n;
}
int AW_FxGroups(const aw_fx_entry_t *e,int n,aw_fx_group_t *g,int max){
    int i,k=0;
    if(!e || !g || max<1)return 0;
    for(i=0;i<n;i++){
        /* an effect number outside the game's is not shown (an entry the list never takes) */
        if(e[i].effect<0 || e[i].effect>=AW_FX_EFFECTS)continue;
        if(k==0 || g[k-1].effect!=e[i].effect){
            if(k==max)break;
            g[k].effect=e[i].effect;g[k].first=(short)i;g[k].count=0;g[k].left=-1;g[k].permanent=0;k++;
        }
        g[k-1].count=(short)(i-g[k-1].first+1);   /* a sorted list keeps one effect's entries together */
        if(e[i].left<0)g[k-1].permanent=1;
        else if(g[k-1].left<0 || e[i].left<g[k-1].left)g[k-1].left=e[i].left;
    }
    return k;
}
int AW_FxLayout(int groups,int width,int height,int icon,int step,int max_rows,int max_places,aw_fx_layout_t *out){
    int per_row,rows,capacity;
    memset(out,0,sizeof(*out));
    if(icon<1 || step<icon || width<icon || height<icon || max_rows<1 || max_places<1)return 0;
    per_row=(width-icon)/step+1;
    rows=(height-icon)/step+1;if(rows>max_rows)rows=max_rows;
    capacity=per_row*rows;if(capacity>max_places)capacity=max_places;
    out->per_row=per_row;
    if(groups<=0)return 1;
    if(groups<=capacity){out->shown=groups;out->more=0;}
    else{out->shown=capacity-1;out->more=groups-out->shown;}
    out->places=out->shown+(out->more?1:0);
    out->rows=(out->places+per_row-1)/per_row;
    return 1;
}
void AW_FxPlace(const aw_fx_layout_t *l,int i,int x0,int y_bottom,int step,int *x,int *y){
    int per=l->per_row>0?l->per_row:1;
    *x=x0+(i%per)*step;*y=y_bottom-(i/per)*step;
}
void AW_FxMoreText(int n,char *out,int size){if(size>0)snprintf(out,(size_t)size,"+%d",n);}
void AW_FxTimeText(float left,char *out,int size){
    long s;
    if(size<1)return;
    if(left<0){snprintf(out,(size_t)size,"permanent");return;}
    s=(long)(left+.5f);
    if(s<60)snprintf(out,(size_t)size,"%ld s",s);
    else if(s<3600){if(s%60)snprintf(out,(size_t)size,"%ld min %ld s",s/60,s%60);else snprintf(out,(size_t)size,"%ld min",s/60);}
    else if((s/60)%60)snprintf(out,(size_t)size,"%ld h %ld min",s/3600,(s/60)%60);
    else snprintf(out,(size_t)size,"%ld h",s/3600);
}
const char *AW_FxFromName(int from){
    static const char *const names[AW_FX_FROMS]={"spell","potion or item","worn item","ability","blight disease",
                                                 "disease","curse","power"};
    return from>=0 && from<AW_FX_FROMS?names[from]:"";
}
static int blank(char c){return c==' ' || c=='\t' || c=='\r' || c=='\n';}
int AW_FxWrap(const char *text,int bytes,int width,char out[][AW_FX_LINE],int max){
    int i=0,n=0,len,w,k;
    if(!text || width<1 || max<1)return 0;
    if(width>AW_FX_LINE-1)width=AW_FX_LINE-1;
    while(n<max){
        while(i<bytes && text[i] && blank(text[i]))i++;
        if(i>=bytes || !text[i])break;
        len=0;out[n][0]=0;
        while(i<bytes && text[i]){
            for(w=0;i+w<bytes && text[i+w] && !blank(text[i+w]);w++);
            if(len && len+1+w>width)break;
            if(len)out[n][len++]=' ';
            for(k=0;k<w && len<width;k++)out[n][len++]=text[i+k];
            i+=w;
            if(k<w){i-=w-k;break;}            /* a word longer than the line: the rest on the next */
            while(i<bytes && text[i] && blank(text[i]))i++;
        }
        out[n][len]=0;n++;
    }
    return n;
}
int AW_FxFromSpellType(int type){
    switch(type){
    case 1:return AW_FX_FROM_ABILITY;
    case 2:return AW_FX_FROM_BLIGHT;
    case 3:return AW_FX_FROM_DISEASE;
    case 4:return AW_FX_FROM_CURSE;
    case 5:return AW_FX_FROM_POWER;
    }
    return AW_FX_FROM_SPELL;
}
static unsigned long u32le(const unsigned char *p){
    return (unsigned long)p[0]|((unsigned long)p[1]<<8)|((unsigned long)p[2]<<16)|((unsigned long)p[3]<<24);
}
int AW_FxDirectory(const unsigned char *data,unsigned long head_bytes,unsigned long file_bytes,aw_fx_dir_t *dir,int max){
    int count,i,small,large;
    if(!data || head_bytes<8 || head_bytes>file_bytes || memcmp(data,"AWE1",4))return -1;
    count=data[4]|(data[5]<<8);small=data[6];large=data[7];
    if(small!=AW_FX_HUD_ICON || large!=AW_FX_LIST_ICON || count>AW_FX_EFFECTS)return -1;
    if(head_bytes<8+(unsigned long)count*AW_FX_ROW_BYTES)return -1;
    for(i=0;i<count;i++){
        const unsigned char *r=data+8+i*AW_FX_ROW_BYTES;
        unsigned long s=u32le(r),l=u32le(r+4),d=u32le(r+8),n=(unsigned long)(r[12]|(r[13]<<8));
        if((s && s+(unsigned long)(small*small)>file_bytes) || (l && l+(unsigned long)(large*large)>file_bytes) ||
           (d && d+n>file_bytes) || (!d && n))return -1;
        if(i<max){dir[i].small=s;dir[i].large=l;dir[i].desc=d;dir[i].desc_bytes=(unsigned short)n;}
    }
    for(i=count;i<max;i++)memset(&dir[i],0,sizeof(dir[i]));
    return count;
}
