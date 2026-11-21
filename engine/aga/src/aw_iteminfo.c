/* SPDX-License-Identifier: GPL-2.0-or-later
 * INVENTORY-ITEM-INFO-67: the item information box (aw_iteminfo.h). Its text by kind, the wrap, the layout through the
 * shared helper, the drawing through aw_ui.c and the console font, the keys. No engine state: the window
 * (aw_worldui.c) gathers what the box shows and owns when it opens and closes. */
#include "quakedef.h"
#include "aw_iteminfo.h"
#include "aw_tryalloc.h"

/* ---- the text ---- */
static void add(char *out,int size,int *at,const char *text){
    while(*text && *at<size-1)out[(*at)++]=*text++;
    out[*at]=0;
}
static void add_line(char *out,int size,int *at,const char *text){add(out,size,at,text);add(out,size,at,"\n");}
/* a weight or a quality the original's way: "2", "0.1", "15.25" */
static void number(char *out,int size,float v){
    int n;
    snprintf(out,(size_t)size,"%.2f",v);n=(int)strlen(out);
    while(n>0 && out[n-1]=='0')out[--n]=0;
    if(n>0 && out[n-1]=='.')out[--n]=0;
}
/* the skill a weapon type trains (WPDT 0..11; the original's sSkill words) */
static const char *const weapon_skill[12]={"Short Blade","Long Blade","Long Blade","Blunt Weapon","Blunt Weapon",
    "Blunt Weapon","Spear","Axe","Axe","Marksman","Marksman","Marksman"};
static const char *const enchant_word[5]={"","Cast Once","Cast When Strikes","Cast When Used","Constant Effect"};
static const char *const armour_class[3]={"Light","Medium","Heavy"};
int AW_ItemInfoText(const aw_inventory_item_t *it,const aw_iteminfo_extra_t *x,char *out,int size){
    char t[160],w[24];int at=0,type;
    static const aw_iteminfo_extra_t none;
    if(!out || size<1)return 0;
    out[0]=0;
    if(!it)return 0;
    if(!x)x=&none;
    if(it->category==AW_INV_WEAPON && it->weapon>=1 && it->weapon<=12){
        type=it->weapon-1;
        if(type<=8){
            snprintf(t,sizeof(t),"Type: %s, %s",weapon_skill[type],AW_INV_TWO_HANDED(it->weapon)?"Two Handed":"One Handed");
            add_line(out,size,&at,t);
            snprintf(t,sizeof(t),"Chop: %d - %d",it->damage[0],it->damage[1]);add_line(out,size,&at,t);
            snprintf(t,sizeof(t),"Slash: %d - %d",it->damage[2],it->damage[3]);add_line(out,size,&at,t);
            snprintf(t,sizeof(t),"Thrust: %d - %d",it->damage[4],it->damage[5]);add_line(out,size,&at,t);
        }else{
            int k=type==11?2:1;   /* a thrown weapon is the weapon and the ammunition: twice its damage */
            snprintf(t,sizeof(t),"Type: %s",weapon_skill[type]);add_line(out,size,&at,t);
            snprintf(t,sizeof(t),"Attack: %d - %d",it->damage[0]*k,it->damage[1]*k);add_line(out,size,&at,t);
        }
    }
    if(it->category==AW_INV_ARMOUR && it->slots){
        snprintf(t,sizeof(t),"Armor Rating: %d",(int)(it->armor+.5f));add_line(out,size,&at,t);
    }
    if((it->category==AW_INV_WEAPON || it->category==AW_INV_ARMOUR) && it->health>0){
        float now=x->condition_known?x->condition*it->health:it->health;   /* the share of its full health */
        if(now<0)now=0;
        snprintf(t,sizeof(t),"Condition: %d/%d",(int)(now+.5f),(int)(it->health+.5f));add_line(out,size,&at,t);
    }
    if((it->flags&AW_INV_ALCHEMY) && it->alchemy_kind==AW_ALCHEMY_APPARATUS){
        number(w,sizeof(w),it->apparatus_quality);snprintf(t,sizeof(t),"Quality: %s",w);add_line(out,size,&at,t);
    }
    number(w,sizeof(w),it->weight);
    if(it->category==AW_INV_ARMOUR && it->slots && it->shield_class>=0 && it->shield_class<=2)
        snprintf(t,sizeof(t),"Weight: %s (%s)",w,armour_class[it->shield_class]);
    else snprintf(t,sizeof(t),"Weight: %s",w);
    add_line(out,size,&at,t);
    snprintf(t,sizeof(t),"Value: %d",it->value);add_line(out,size,&at,t);
    if(it->enchant_kind>AW_ENCH_NONE && it->enchant_kind<=AW_ENCH_CONSTANT){
        add_line(out,size,&at,"");
        add_line(out,size,&at,enchant_word[it->enchant_kind]);
        if(x->magic && *x->magic)add_line(out,size,&at,x->magic);
        if((it->enchant_kind==AW_ENCH_STRIKES || it->enchant_kind==AW_ENCH_USED) && it->charge_max>0){
            float now=x->charge_known?x->charge:it->charge_max;
            snprintf(t,sizeof(t),"Charge: %d/%d",(int)(now+.5f),(int)(it->charge_max+.5f));add_line(out,size,&at,t);
        }
    }else if(x->magic && *x->magic){   /* a potion's, an ingredient's effects */
        add_line(out,size,&at,"");
        add_line(out,size,&at,x->magic);
    }
    if(x->body && *x->body){
        const char *p=x->body;
        add_line(out,size,&at,"");
        for(;*p && at<size-1;p++){   /* a page break is a line break here; carriage returns go */
            if(*p=='\r')continue;
            out[at++]=*p=='\f'?'\n':*p;
        }
        out[at]=0;
    }
    while(at>0 && out[at-1]=='\n')out[--at]=0;
    return at;
}

/* ---- the box ---- */
/* the wrapped lines of the text in lines of CHARS characters, broken at the last space (a longer word is cut), empty
 * lines kept; into LINE and LEN when not NULL; their count */
static int wrap(const char *t,int chars,int *line,unsigned char *len){
    int at=0,n=0,size=(int)strlen(t);
    if(chars<8)chars=8;
    if(chars>255)chars=255;
    while(at<size && n<AW_ITEMINFO_LINES_MAX){
        int end=at,brk=-1,next,wrapped;
        while(end<size && t[end]!='\n' && end-at<chars){if(t[end]==' ')brk=end;end++;}
        wrapped=end<size && t[end]!='\n';
        if(end<size && (t[end]=='\n' || t[end]==' '))next=end+1;
        else if(wrapped && brk>at){end=brk;next=brk+1;}
        else next=end;
        if(line){line[n]=at;len[n]=(unsigned char)(end-at);}
        n++;
        at=next;
        if(wrapped)while(at<size && t[at]==' ')at++;
    }
    return n;
}
static int box_buttons(const aw_iteminfo_t *b,const char *labels[2],int w[2]){
    int n=0;
    labels[n]="OK";w[n++]=AW_UIWidth("OK");
    if(b->action[0]){labels[n]=b->action;w[n]=AW_UIWidth(b->action);n++;}
    return n;
}
void AW_ItemInfoLayout(const aw_iteminfo_t *b,aw_layout_t *l,int text[4],int *visible){
    const char *labels[2];int w[2],n=box_buttons(b,labels,w),full;
    AW_LayoutBox(l,AW_ITEMINFO_X,AW_ITEMINFO_Y,AW_ITEMINFO_W,AW_ITEMINFO_H,AW_ITEMINFO_TITLE_H,n,w,0);
    full=l->content[2]/AW_ITEMINFO_CHAR;
    text[0]=l->content[0];text[1]=l->content[1];text[3]=l->content[3];
    text[2]=b->chars<full?l->content[2]-AW_ITEMINFO_BAR:l->content[2];   /* the scroll bar takes its width */
    if(visible)*visible=l->content[3]/AW_ITEMINFO_ROW;
}
aw_iteminfo_t *AW_ItemInfoOpen(const aw_inventory_item_t *it,const aw_iteminfo_extra_t *x,const char *action){
    aw_iteminfo_t *b;aw_layout_t l;int t[4],visible,size=2048,full,n;
    if(!it)return NULL;
    if(x && x->magic)size+=(int)strlen(x->magic);
    if(x && x->body)size+=(int)strlen(x->body);
    if(size>AW_ITEMINFO_TEXT_MAX)size=AW_ITEMINFO_TEXT_MAX;
    if(!(b=(aw_iteminfo_t *)AW_TryCalloc(1,sizeof(*b))))return NULL;
    if(!(b->text=(char *)AW_TryMalloc((unsigned long)size))){free(b);return NULL;}
    AW_ItemInfoText(it,x,b->text,size);
    snprintf(b->title,sizeof(b->title),"%s",it->name[0]?it->name:it->id);
    snprintf(b->action,sizeof(b->action),"%s",action?action:"");
    /* the width: the whole text area, or less the scroll bar when the lines do not all fit */
    b->chars=1000;AW_ItemInfoLayout(b,&l,t,&visible);
    full=t[2]/AW_ITEMINFO_CHAR;b->chars=full;
    if(wrap(b->text,full,NULL,NULL)>visible)b->chars=(t[2]-AW_ITEMINFO_BAR)/AW_ITEMINFO_CHAR;
    n=wrap(b->text,b->chars,NULL,NULL);
    b->line=(int *)AW_TryMalloc((unsigned long)(n?n:1)*sizeof(int));
    b->len=(unsigned char *)AW_TryMalloc((unsigned long)(n?n:1));
    if(!b->line || !b->len){AW_ItemInfoClose(b);return NULL;}
    b->lines=wrap(b->text,b->chars,b->line,b->len);
    return b;
}
void AW_ItemInfoClose(aw_iteminfo_t *b){
    if(!b)return;
    free(b->text);free(b->line);free(b->len);free(b);
}
static int max_top(const aw_iteminfo_t *b,int visible){return b->lines>visible?b->lines-visible:0;}
void AW_ItemInfoDraw(const aw_iteminfo_t *b,int mouse_x,int mouse_y){
    aw_layout_t l;const char *labels[2];int t[4],visible,i,w[2],n,gold=AW_UIColor(223,199,144),hit;char row[256];
    if(!b)return;
    AW_ItemInfoLayout(b,&l,t,&visible);
    n=box_buttons(b,labels,w);
    AW_UIBox(l.box[0],l.box[1],l.box[2],l.box[3]);
    AW_UISmallBegin();
    AW_UITextBox(l.title[0],l.title[1],l.title[2],l.title[3],b->title,gold);
    AW_UISmallEnd();
    for(i=0;i<visible && b->top+i<b->lines;i++){
        int k=b->top+i,m=b->len[k];
        if(!m)continue;
        memcpy(row,b->text+b->line[k],(size_t)m);row[m]=0;
        AW_SmallStringColor(t[0],t[1]+i*AW_ITEMINFO_ROW+1,t[2],row,gold);
    }
    if(b->lines>visible)AW_UIScrollbar(t[0]+t[2]+2,t[1],t[3],b->lines,visible,b->top);
    hit=AW_LayoutButtonAt(&l,mouse_x,mouse_y);
    for(i=0;i<n;i++)AW_UIButton(l.button[i][0],l.button[i][1],l.button[i][2],l.button[i][3],labels[i],hit==i,gold);
}
int AW_ItemInfoKey(aw_iteminfo_t *b,int key,int mouse_x,int mouse_y,int use_key,int info_key){
    aw_layout_t l;int t[4],visible,top,hit;
    if(!b)return AW_ITEMINFO_CLOSE;
    AW_ItemInfoLayout(b,&l,t,&visible);
    top=b->top;
    if(key==K_MOUSE1){
        hit=AW_LayoutButtonAt(&l,mouse_x,mouse_y);
        if(hit==0)return AW_ITEMINFO_CLOSE;
        if(hit==1)return AW_ITEMINFO_ACTION;
        if(b->lines>visible){
            int s=AW_UIScrollHit(mouse_x,mouse_y,t[0]+t[2]+2,t[1],t[3],b->lines,visible,b->top);
            if(s>=0){
                b->top=s;
                if(mouse_y>=t[1]+10 && mouse_y<t[1]+t[3]-10)b->drag=1;   /* the rail holds it; the arrows step */
            }
        }
        return AW_ITEMINFO_KEEP;
    }
    /* ITEM-VIEW-ENTER-UNEQUIPS-67 (decided for the project 2026-11-20): Enter is the box's OK, it only closes it and
     * never acts on the item (the window's use key is E and Enter; since the box came, 4307f71f6 v0.0.67-dev3, Enter
     * unequipped the item being looked at). The other use key (E) and the action button still do the item's action. */
    if(key==K_ESCAPE || key==K_ENTER || info_key)return AW_ITEMINFO_CLOSE;
    if(use_key)return b->action[0]?AW_ITEMINFO_ACTION:AW_ITEMINFO_CLOSE;
    if(key==K_UPARROW)top--;
    else if(key==K_DOWNARROW)top++;
    else if(key==K_PGUP)top-=visible>1?visible-1:1;
    else if(key==K_PGDN)top+=visible>1?visible-1:1;
    else if(key==K_HOME)top=0;
    else if(key==K_END)top=max_top(b,visible);
    else if(key==K_MWHEELUP)top-=3;
    else if(key==K_MWHEELDOWN)top+=3;
    if(top>max_top(b,visible))top=max_top(b,visible);
    if(top<0)top=0;
    b->top=top;
    return AW_ITEMINFO_KEEP;
}
void AW_ItemInfoDrag(aw_iteminfo_t *b,int mouse_y){
    aw_layout_t l;int t[4],visible,s,y;
    if(!b || !b->drag)return;
    AW_ItemInfoLayout(b,&l,t,&visible);
    y=mouse_y<t[1]+10?t[1]+10:mouse_y>t[1]+t[3]-11?t[1]+t[3]-11:mouse_y;
    s=AW_UIScrollHit(t[0]+t[2]+4,y,t[0]+t[2]+2,t[1],t[3],b->lines,visible,b->top);
    if(s>=0)b->top=s;
}
