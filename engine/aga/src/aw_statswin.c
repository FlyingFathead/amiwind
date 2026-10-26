/* SPDX-License-Identifier: GPL-2.0-or-later
 * The Stats window (P) and the Magic window placeholder (O), on the inventory's modal.
 *
 * Stats follows the original's window (structure read from OpenMW mwgui/statswindow.cpp and
 * its stats window layout; no art or code copied): the player's name as the title; left the
 * health, magicka and fatigue bars, level, race and class, then the eight attributes; right a
 * scrolled list of Major, Minor and Misc skills as the class defines them. The birthsign sits
 * under the attributes here (the original lists it under the skills). Factions, reputation and
 * bounty are not shown: the engine has no faction state yet. Everything is read live from
 * aw_character (attributes, modifiers, damage, skills, current/maximum) every frame; nothing
 * is kept while the window is closed except the scroll position.
 *
 * Magic is a placeholder until the spell system: the original's Powers / Spells / Magic Items
 * headings, the character's race and birthsign spells by name (character/spells.aws, written
 * by tools/prepare_character.py from the SPEL records; read only while the window opens) and
 * "(Not yet implemented)" at the bottom. */
#include "quakedef.h"
#include "aw_story.h"
#include "aw_character.h"
#include "aw_statswin.h"
#include "aw_tryalloc.h"

extern int (*aw_title_bar)(int x,int y,int w,const char *title);
/* aw_worldui.c: the inventory's modal for another window; key returns 0 to close, closed runs on every close. */

#define LIST_X 140
#define LIST_Y 22
#define LIST_ROW 8
#define LIST_VISIBLE 21
#define SCROLL_X 304
#define SCROLL_H (LIST_VISIBLE*LIST_ROW)
#define CLOSE_X 8
#define CLOSE_Y 176
#define CLOSE_W 60

static const char *const attribute_names[8]={"Strength","Intelligence","Willpower","Agility","Speed","Endurance","Personality","Luck"};
/* The skill order of the original records (SKIL INDX 0..26), as aw_character.c. */
static const char *const skill_names[27]={"Block","Armorer","Medium Armor","Heavy Armor","Blunt Weapon","Long Blade","Axe","Spear",
    "Athletics","Enchant","Destruction","Alteration","Illusion","Conjuration","Mysticism","Restoration","Alchemy","Unarmored",
    "Security","Sneak","Acrobatics","Light Armor","Short Blade","Marksman","Mercantile","Speechcraft","Hand-to-hand"};
const char *AW_StatsAttributeName(int i){return i>=0 && i<8?attribute_names[i]:"";}
const char *AW_StatsSkillName(int i){return i>=0 && i<27?skill_names[i]:"";}

static int skill_top;
static aw_magic_list_t *magic;   /* only while the Magic window is open */

/* the name cut to the field (no strncpy: -O2 warns on the cut, -Wstringop-truncation) */
static void copy(char *out,int size,const char *in){int n=0;if(in)while(n<size-1 && in[n]){out[n]=in[n];n++;}out[n]=0;}
int AW_StatsSheet(aw_stats_sheet_t *s){
    const aw_character_t *c=&aw_character;int i;
    memset(s,0,sizeof(*s));
    copy(s->name,sizeof(s->name),aw_story.name);
    if(!c->valid)return 0;
    s->level=c->level>0?c->level:1;
    if(c->race>=0 && c->race<aw_race_count)copy(s->race,sizeof(s->race),aw_races[c->race].name);
    if(c->birth>=0 && c->birth<aw_birth_count)copy(s->birth,sizeof(s->birth),aw_births[c->birth].name);
    if(c->clas>=0 && c->clas<aw_class_count){
        const aw_class_t *k=&aw_classes[c->clas];
        copy(s->clas,sizeof(s->clas),k->name);
        /* CLDT skill pairs: [i][0] minor, [i][1] major (OpenMW esm::Class mSkills; AW_CharacterRebuild). */
        for(i=0;i<5;i++){s->minor[i]=k->skills[i*2];s->major[i]=k->skills[i*2+1];}
        s->classed=1;
    }
    for(i=0;i<8;i++){
        int v=c->attributes[i]+c->modifiers[i]-c->damage[i];
        s->base[i]=c->attributes[i];s->attributes[i]=(short)(v<0?0:v);
    }
    for(i=0;i<27;i++)s->skills[i]=c->skills[i];
    for(i=0;i<3;i++){s->current[i]=c->current[i];s->maximum[i]=c->maximum[i];}
    /* Health lives on the player entity while a game runs (aw_combat.c keeps the sheet in step). */
    if(sv.active && svs.clients && svs.clients[0].edict)s->current[0]=svs.clients[0].edict->v.health;
    return 1;
}
int AW_StatsRows(const aw_stats_sheet_t *s,int *rows){
    int n=0,i,j,used[27];
    memset(used,0,sizeof(used));
    if(s->classed){
        rows[n++]=-1;for(i=0;i<5;i++)if(s->major[i]<27){rows[n++]=s->major[i];used[s->major[i]]=1;}
        rows[n++]=-2;for(i=0;i<5;i++)if(s->minor[i]<27 && !used[s->minor[i]]){rows[n++]=s->minor[i];used[s->minor[i]]=1;}
    }
    rows[n++]=-3;
    /* The misc skills: the rest in skill record order (OpenMW statswindow.cpp configureSkills walks the
     * skill store; major and minor keep the class's order). */
    for(j=0;j<27;j++)if(!used[j])rows[n++]=j;
    return n;
}
static void small(int x,int y,int width,const char *value,int color){
    char clipped[96];int n=(int)strlen(value),limit=width/4;
    if(limit<1)return;
    if(limit>(int)sizeof(clipped)-1)limit=sizeof(clipped)-1;
    if(n>limit)n=limit;
    memcpy(clipped,value,n);clipped[n]=0;
    if(value[n] && n>=3)memcpy(clipped+n-3,"...",3);
    AW_SmallStringColor(x,y,width,clipped,color);
}
static void right(int x_right,int y,const char *value,int color){
    int n=(int)strlen(value);small(x_right-n*4,y,n*4,value,color);
}
static void pair(int x,int y,int x_right,const char *label,const char *value,int label_color,int value_color){
    int w=(int)strlen(value)*4,most=(x_right-x)*2/3;
    if(w>most){w=most/4*4;small(x_right-w,y,w,value,value_color);}   /* a long name ends in "..." */
    else right(x_right,y,value,value_color);
    small(x,y,x_right-x-w-4,label,label_color);
}
static void window_frame(const char *title){
    int gold=AW_UIColor(223,199,144);
    AW_UIFill(0,0,320,200,AW_UIColor(0,0,0));AW_UIBox(2,2,316,196);
    AW_UISmallBegin();
    if(!aw_title_bar || !aw_title_bar(6,6,308,title))AW_UITextCentred(6,6,308,12,title,gold);
    AW_UISmallEnd();
}
/* One original dynamic-stat bar: the label, the coloured fill and current/maximum over it. */
static void bar(int y,const char *label,float current,float maximum,int fill,int gold){
    char line[32];int x=46,w=84,filled=0;
    small(8,y+1,36,label,gold);
    AW_UIFill(x,y,w,7,AW_UIColor(48,39,22));AW_UIFill(x+1,y+1,w-2,5,AW_UIColor(10,9,7));
    if(maximum>0){filled=(int)((w-2)*(current>0?current:0)/maximum);if(filled>w-2)filled=w-2;}
    if(filled>0)AW_UIFill(x+1,y+1,filled,5,fill);
    sprintf(line,"%ld/%ld",(long)(current>0?current:0),(long)(maximum>0?maximum:0));
    small(x+(w-(int)strlen(line)*4)/2,y+1,(int)strlen(line)*4,line,AW_UIColor(255,255,255));
}
void AW_StatsDrawSheet(const aw_stats_sheet_t *s,int top){
    int gold=AW_UIColor(223,199,144),muted=AW_UIColor(150,135,104),i,y,n,rows[AW_STATS_ROWS];char line[32];
    window_frame(s->name[0]?s->name:"Stats");
    AW_UIBox(4,18,130,178);AW_UIBox(136,18,180,178);
    bar(22,"Health",s->current[0],s->maximum[0],AW_UIColor(200,40,32),gold);
    bar(31,"Magicka",s->current[1],s->maximum[1],AW_UIColor(48,72,200),gold);
    bar(40,"Fatigue",s->current[2],s->maximum[2],AW_UIColor(40,160,56),gold);
    AW_UIFill(8,50,122,1,muted);
    sprintf(line,"%ld",(long)s->level);pair(8,54,130,"Level",line,gold,gold);
    pair(8,62,130,"Race",s->race[0]?s->race:"-",gold,gold);
    pair(8,70,130,"Class",s->clas[0]?s->clas:"-",gold,gold);
    AW_UIFill(8,80,122,1,muted);
    for(i=0;i<8;i++){
        sprintf(line,"%ld",(long)s->attributes[i]);
        pair(8,84+i*8,130,attribute_names[i],line,gold,s->attributes[i]==s->base[i]?gold:AW_UIColor(120,200,120));
    }
    AW_UIFill(8,150,122,1,muted);
    pair(8,154,130,"Birthsign",s->birth[0]?s->birth:"-",gold,gold);
    AW_UIFill(8,CLOSE_Y-2,122,1,muted);
    small(CLOSE_X,CLOSE_Y,CLOSE_W,"P/Esc close",gold);
    small(8,CLOSE_Y+8,122,"Up/Down skills",gold);
    n=AW_StatsRows(s,rows);
    if(top>n-LIST_VISIBLE)top=n-LIST_VISIBLE;
    if(top<0)top=0;
    for(i=0;i<LIST_VISIBLE && top+i<n;i++){
        int r=rows[top+i],x_right=n>LIST_VISIBLE?SCROLL_X-4:312;y=LIST_Y+i*LIST_ROW;
        if(r<0)small(LIST_X,y,x_right-LIST_X,r==-1?"Major Skills":r==-2?"Minor Skills":"Misc Skills",muted);
        else{sprintf(line,"%ld",(long)s->skills[r]);pair(LIST_X+4,y,x_right,skill_names[r],line,gold,gold);}
    }
    if(n>LIST_VISIBLE)AW_UIScrollbar(SCROLL_X,LIST_Y,SCROLL_H,n,LIST_VISIBLE,top);
}
static int stats_rows(void){aw_stats_sheet_t s;int rows[AW_STATS_ROWS];AW_StatsSheet(&s);return AW_StatsRows(&s,rows);}
static void stats_draw(void){aw_stats_sheet_t s;AW_StatsSheet(&s);AW_StatsDrawSheet(&s,skill_top);}
/* The key bound to this window's command closes it too (I/J/M close theirs the same way). */
static int own_key(int key,const char *command,int fallback){
    return key==fallback || key==fallback-32 || (key>=0 && key<256 && keybindings[key] && !Q_strcasecmp(keybindings[key],(char *)command));
}
static int stats_key(int key,int mouse_x,int mouse_y){
    int n=stats_rows(),top;
    if(own_key(key,"aw_stats",'p'))return 0;
    if(key==K_UPARROW || key=='w' || key==K_MWHEELUP)skill_top--;
    if(key==K_DOWNARROW || key=='s' || key==K_MWHEELDOWN)skill_top++;
    if(key==K_PGUP)skill_top-=LIST_VISIBLE;
    if(key==K_PGDN)skill_top+=LIST_VISIBLE;
    if(key==K_HOME)skill_top=0;
    if(key==K_END)skill_top=n;
    if(key==K_MOUSE1){
        if(mouse_x>=CLOSE_X && mouse_x<CLOSE_X+CLOSE_W && mouse_y>=CLOSE_Y && mouse_y<CLOSE_Y+8)return 0;
        top=AW_UIScrollHit(mouse_x,mouse_y,SCROLL_X,LIST_Y,SCROLL_H,n,LIST_VISIBLE,skill_top);
        if(top>=0)skill_top=top;
    }
    if(skill_top>n-LIST_VISIBLE)skill_top=n-LIST_VISIBLE;
    if(skill_top<0)skill_top=0;
    return 1;
}
void AW_StatsOpen(void){
    if(!aw_character.valid){Con_Printf("Stats: no character yet.\n");return;}
    AW_WorldUIOpenPanel(stats_draw,stats_key,NULL);
}

/* character/spells.aws (tools/prepare_character.py): "AWS1", u16 count, then per spell
 * id[64] (lower case), name[48], type (the SPEL type: 0 spell, 5 power, others not listed). */
static int spell_name(const char *id,char *name,int *power){
    FILE *f=NULL;byte head[6],row[113];int size,count,i,found=0;
    size=COM_FOpenFile("character/spells.aws",&f);
    if(!f)return 0;
    if(size>=6 && fread(head,1,6,f)==6 && !memcmp(head,"AWS1",4)){
        count=head[4]|(head[5]<<8);
        if(size==6+count*113)for(i=0;i<count && fread(row,1,113,f)==113;i++){
            if(!memchr(row,0,64) || !memchr(row+64,0,48) || Q_strcasecmp((char *)row,(char *)id))continue;
            if(row[112]!=0 && row[112]!=5)break;   /* abilities, diseases, curses: not in the list */
            copy(name,48,(char *)row+64);*power=row[112]==5;found=1;break;
        }
    }
    fclose(f);return found;
}
int AW_MagicList(aw_magic_list_t *out){
    const aw_character_t *c=&aw_character;int i,k,power;char name[48];
    out->count=0;
    if(!c->valid)return 0;
    for(k=0;k<2;k++){
        int count=k?(c->birth>=0 && c->birth<aw_birth_count?aw_births[c->birth].power_count:0):
                    (c->race>=0 && c->race<aw_race_count?aw_races[c->race].power_count:0);
        for(i=0;i<count && out->count<32;i++){
            const char *id=k?aw_births[c->birth].powers[i]:aw_races[c->race].powers[i];
            if(!spell_name(id,name,&power))continue;
            copy(out->name[out->count],48,name);out->power[out->count++]=(unsigned char)power;
        }
    }
    return out->count;
}
void AW_MagicDrawList(const aw_magic_list_t *list){
    int gold=AW_UIColor(223,199,144),muted=AW_UIColor(150,135,104),y=24,section,i,any;
    static const char *const headings[3]={"Powers","Spells","Magic Items"};
    window_frame("Magic");
    AW_UIBox(4,18,312,160);
    for(section=0;section<3;section++){
        /* Rows past the box bottom are not drawn (at most a handful of starting spells). */
        if(y<=170)small(10,y,200,headings[section],muted);
        y+=8;any=0;
        for(i=0;section<2 && i<list->count;i++){
            if(list->power[i]!=(section==0))continue;
            if(y<=170)small(16,y,290,list->name[i],gold);
            y+=8;any=1;
        }
        if(!any){if(y<=170)small(16,y,100,"None",muted);y+=8;}
        y+=4;
    }
    AW_UISmallBegin();
    AW_UITextCentred(4,180,312,14,"(Not yet implemented)",gold);
    AW_UISmallEnd();
}
static void magic_draw(void){if(magic)AW_MagicDrawList(magic);}
static int magic_key(int key,int mouse_x,int mouse_y){
    (void)mouse_x;(void)mouse_y;
    return !own_key(key,"aw_magicmenu",'o');
}
static void magic_closed(void){free(magic);magic=NULL;}
void AW_MagicMenuOpen(void){
    if(!aw_character.valid){Con_Printf("Magic: no character yet.\n");return;}
    free(magic);magic=(aw_magic_list_t *)AW_TryCalloc(1,sizeof(*magic));
    if(!magic){Con_Printf("Magic: not enough memory.\n");return;}
    AW_MagicList(magic);
    if(!AW_WorldUIOpenPanel(magic_draw,magic_key,magic_closed))magic_closed();
}
void AW_StatsWindowInit(void){
    Cmd_AddCommand("aw_stats",AW_StatsOpen);
    Cmd_AddCommand("aw_magicmenu",AW_MagicMenuOpen);
}
