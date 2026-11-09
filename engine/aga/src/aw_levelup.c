/* SPDX-License-Identifier: GPL-2.0-or-later
 * Levelling on the player (aw_levelup.h, docs/CHARACTER_CREATION.md "Levelling", LEVEL-UP-58).
 *
 * The data: levelup/settings.txt (tools/prepare_levelup.py, from the player's own master file):
 *   AWLU1
 *   set NAME VALUE                       the levelling game settings (AW_LevelupSettingName)
 *   skill INDEX ATTRIBUTE SPEC U0 U1 U2 U3   each SKIL record's governing attribute, specialization, use values
 *   sound skillraise PATH                the skill-raise sound (the SOUN record "skillraise", sound/ relative)
 *   text KEY TEXT                        the game's own lines (sNotifyMessage39, sLevelUpMsg, sLevelUpMenu1,
 *                                        sLevelUpMenu2, sNotifyMessage36), read from disk only when shown
 *   level N TEXT                         a level's own sentence (Morrowind.ini [Level Up], when the install has it)
 * levelup/<picture>.awi, levelup/coin.awi: the level-up pictures and the gold coin (AWI1), read when the box opens.
 *
 * Resident: the rules (about 600 bytes) and the sound path. The box's pictures live only while it is open. */
#include "quakedef.h"
#include "aw_story.h"
#include "aw_character.h"
#include "aw_levelup.h"
#include "aw_statswin.h"
#include "aw_clock.h"
#include "aw_tryalloc.h"
#include "aw_rest.h"
#include "aw_inventory.h"
#include "aw_listbox.h"   /* DBG-STATS-COMMANDS-62: the level prompt */
#include "aw_combat.h"    /* DBG-STATS-COMMANDS-62: the fight sheet's fatigue */

aw_levelup_rules_t aw_levelup_rules;
extern int aw_stats_level_total;        /* aw_statswin.c: the level progress bar's total (0 = no bar) */
extern int aw_worldui_panel_holds_escape;   /* aw_worldui.c: Esc goes to the open panel, which does not close */
int AW_PlayerInCombat(void);            /* aw_combat.c */
static int loaded_once,load_ok;
static char raise_sound[64];
static float run_seconds,swim_seconds;

static int read_line(FILE *f,char *line,int size)
{
    if(!fgets(line,size,f))return 0;
    line[strcspn(line,"\r\n")]=0;return 1;
}
int AW_LevelupLoad(void)
{
    FILE *f=NULL;char line[320];
    if(loaded_once)return load_ok;
    loaded_once=1;memset(&aw_levelup_rules,0,sizeof(aw_levelup_rules));raise_sound[0]=0;
    if(COM_FOpenFile("levelup/settings.txt",&f)<0 || !f)return 0;
    if(!read_line(f,line,sizeof(line)) || strcmp(line,"AWLU1")){fclose(f);return 0;}
    while(read_line(f,line,sizeof(line))){
        char name[64];float v,use[4];int sk,attribute,special;
        if(Q_sscanf(line,"set %63s %f",name,&v)==2)AW_LevelupSettingSet(&aw_levelup_rules,name,v);
        else if(Q_sscanf(line,"skill %d %d %d %f %f %f %f",&sk,&attribute,&special,&use[0],&use[1],&use[2],&use[3])==7)
            AW_LevelupSkillRow(&aw_levelup_rules,sk,attribute,special,use);
        else if(Q_sscanf(line,"sound skillraise %63s",name)==1)strcpy(raise_sound,name);
    }
    fclose(f);
    aw_levelup_rules.loaded=load_ok=AW_LevelupRulesComplete(&aw_levelup_rules);
    aw_stats_level_total=load_ok?aw_levelup_rules.total:0;
    if(!load_ok)Con_Printf("Levelling: levelup/settings.txt incomplete; skills do not rise with use.\n");
    return load_ok;
}
/* One of the game's lines from the data file: "text KEY ..." (or "level N ..." with KEY "level N"). */
static int game_text(const char *key,char *out,int size)
{
    FILE *f=NULL;char line[400];size_t n=strlen(key);int found=0;
    out[0]=0;
    if(COM_FOpenFile("levelup/settings.txt",&f)<0 || !f)return 0;
    while(read_line(f,line,sizeof(line))){
        const char *rest=!strncmp(line,"text ",5)?line+5:!strncmp(line,"level ",6)?line:NULL;
        if(!rest || strncmp(rest,key,n) || rest[n]!=' ')continue;
        strncpy(out,rest+n+1,size-1);out[size-1]=0;found=1;break;
    }
    fclose(f);return found;
}
static const aw_class_t *player_class(void)
{
    const aw_character_t *c=&aw_character;
    return c->valid && c->clas>=0 && c->clas<AW_CharacterClassCount()?&aw_classes[c->clas]:NULL;
}
/* "Your %s skill increased to %d." with the skill and its new value (the game's own line, its two fields filled in
 * order; an AmiWind line when the image has none). */
int AW_LevelupGameText(const char *key,char *out,int size){return game_text(key,out,size);}
static void raised_message(int sk,int due,int book)
{
    char form[160],line[320],rest[160];int i=0,o=0,fields=0;
    if(!game_text("sNotifyMessage39",form,sizeof(form)))strcpy(form,"Your %s skill increased to %d.");
    /* a book's raise starts with the game's own book line (OpenMW playerskillhandlers.lua: sBookSkillMessage) */
    if(book){
        if(!game_text("sBookSkillMessage",rest,sizeof(rest)))strcpy(rest,"You have learned something new.");
        o=snprintf(line,sizeof(line),"%s ",rest);
    }
    while(form[i] && o<(int)sizeof(line)-48){
        if(form[i]=='%' && form[i+1]=='s' && fields==0){o+=snprintf(line+o,sizeof(line)-o,"%s",AW_StatsSkillName(sk));i+=2;fields++;}
        else if(form[i]=='%' && form[i+1]=='d' && fields==1){o+=snprintf(line+o,sizeof(line)-o,"%ld",(long)aw_character.skills[sk]);i+=2;fields++;}
        else line[o++]=form[i++];
    }
    line[o]=0;
    if(due){
        if(!game_text("sLevelUpMsg",rest,sizeof(rest)))strcpy(rest,"You should rest and meditate on what you've learned.");
        if(o+2+(int)strlen(rest)<(int)sizeof(line)){strcat(line," ");strcat(line,rest);}
    }
    /* held for 3 s: the hit and voice lines of the same blow no longer replace it at once (SKILL-RAISE-NOT-SEEN-62) */
    AW_UIHeldNotice(line,due?6:4,3);
    if(raise_sound[0])S_LocalSoundBeside(raise_sound);
}
static int raised(int sk,int was_due,int book)
{
    raised_message(sk,!was_due && AW_LevelupDue(&aw_levelup_rules,&aw_character),book);
    return 1;
}
int AW_LevelupUse(int sk,int use,float scale)
{
    int was_due,r;
    if(!aw_character.valid || !AW_LevelupLoad())return 0;
    was_due=AW_LevelupDue(&aw_levelup_rules,&aw_character);
    r=AW_LevelupSkillUsed(&aw_levelup_rules,player_class(),&aw_character,sk,use,scale);
    return r>0?raised(sk,was_due,0):0;
}
int AW_LevelupRaise(int sk,int source)
{
    int was_due;
    if(!aw_character.valid || !AW_LevelupLoad())return 0;
    was_due=AW_LevelupDue(&aw_levelup_rules,&aw_character);
    if(!AW_LevelupSkillRaise(&aw_levelup_rules,player_class(),&aw_character,sk,source))return 0;
    return raised(sk,was_due,source==AW_RAISE_BOOK);
}
/* SKILL-BOOKS-MISSING-62: the skill books (levelup/books.txt, tools/prepare_levelup.py): "AWLB1", then one line per
 * book with a skill, "book INDEX SKILL ID" (INDEX its place in the read list, the ID folded, the rest of the line).
 * Read from disk only when a book opens: nothing resident. 1 with *index and *skill when ID is a skill book. */
static int skill_book(const char *id,int *index,int *book_skill)
{
    FILE *f=NULL;char line[96];int i,s,n,found=0;
    if(COM_FOpenFile("levelup/books.txt",&f)<0 || !f)return 0;
    if(!read_line(f,line,sizeof(line)) || strcmp(line,"AWLB1")){fclose(f);return 0;}
    while(!found && read_line(f,line,sizeof(line))){
        n=0;
        if(Q_sscanf(line,"book %d %d %n",&i,&s,&n)!=2 || !n || Q_strcasecmp(line+n,(char *)id))continue;
        if(i>=0 && i<AW_BOOKS_READ_MAX && s>=0 && s<AW_LEVELUP_SKILLS){*index=i;*book_skill=s;found=1;}
    }
    fclose(f);return found;
}
/* A book opened for reading (OpenMW 0.51 mwworld/actionread.cpp): the first read of a skill book raises its skill
 * through the skill-raise rule with the "book" source (the book's line, the sound, the level progress); the book is
 * remembered as read (saved, AWS4 feature 1024) whether or not the skill could still rise. 1 when it rose. */
int AW_LevelupBookRead(const char *id)
{
    int index,book_skill;unsigned long bit;
    if(!id || !aw_character.valid || !skill_book(id,&index,&book_skill))return 0;
    bit=1UL<<(index&31);
    if(aw_character.books_read[index>>5]&bit)return 0;
    aw_character.books_read[index>>5]|=bit;
    return AW_LevelupRaise(book_skill,AW_RAISE_BOOK);
}
/* OpenMW character.cpp: the player running on the ground (not sneaking) or swimming reports one Athletics use per
 * whole second (RunOneSecond / SwimOneSecond). */
void AW_LevelupMoveSeconds(int running,int swimming,float seconds)
{
    if(!(seconds>0) || seconds>1)return;
    if(swimming){swim_seconds+=seconds;while(swim_seconds>=1){swim_seconds-=1;AW_LevelupUse(AW_LU_ATHLETICS,AW_USE_SWIM,1);}}
    else if(running){run_seconds+=seconds;while(run_seconds>=1){run_seconds-=1;AW_LevelupUse(AW_LU_ATHLETICS,AW_USE_RUN,1);}}
}

/* ---- the level-up box (LevelupDialog), on the inventory's modal panel ---- */
#define BOX_X 34
#define BOX_Y 4
#define BOX_W 252
#define BOX_H 192
#define PIC_W 128
#define PIC_H 64
#define ROW_Y 150
#define ROW_H 9
#define COL_X(c) ((c)?178:58)
#define OK_X 248
#define OK_Y 182
typedef struct {
    aw_levelup_box_t box;
    int level,w,h,coin_w,coin_h,focus;
    char text[400],title[64];
    unsigned char picture[PIC_W*PIC_H],coin[16*16];
} box_state_t;
static box_state_t *open_box;
static int awi_load(const char *path,unsigned char *pixels,int max_w,int max_h,int *w,int *h)
{
    FILE *f=NULL;unsigned char head[8];int size;
    *w=*h=0;
    size=COM_FOpenFile((char *)path,&f);
    if(size<8 || !f){if(f)fclose(f);return 0;}
    if(fread(head,1,8,f)!=8 || memcmp(head,"AWI1",4)){fclose(f);return 0;}
    *w=head[4]|(head[5]<<8);*h=head[6]|(head[7]<<8);
    if(*w<1 || *h<1 || *w>max_w || *h>max_h || size!=8+*w**h || fread(pixels,1,*w**h,f)!=(size_t)(*w**h)){
        fclose(f);*w=*h=0;return 0;}
    fclose(f);return 1;
}
static void blit(const unsigned char *pixels,int w,int h,int x,int y)
{
    int j;
    if(!w || x<0 || y<0 || x+w>(int)vid.width || y+h>(int)vid.height)return;
    for(j=0;j<h;j++)memcpy(vid.buffer+(y+j)*vid.rowbytes+x,pixels+j*w,w);
}
static void small(int x,int y,const char *s,int colour){AW_SmallStringColor(x,y,(int)strlen(s)*4,s,colour);}
static void coin(int x,int y)
{
    if(open_box->coin_w)blit(open_box->coin,open_box->coin_w,open_box->coin_h,x,y);
    else{AW_UIFill(x+1,y,6,8,AW_UIColor(200,160,40));AW_UIFill(x,y+1,8,6,AW_UIColor(200,160,40));}
}
/* The description wrapped to whole words, 58 small characters a line, at most 6 lines. */
static void wrapped(int x,int y,const char *text,int colour)
{
    char line[64];int lines=0;
    while(*text && lines<6){
        int n=(int)strlen(text),cut=n<58?n:58;
        if(n>58){while(cut>0 && text[cut]!=' ')cut--;if(!cut)cut=58;}
        memcpy(line,text,cut);line[cut]=0;
        AW_SmallStringColor(x+(232-cut*4)/2,y+lines*7,cut*4,line,colour);
        text+=cut;while(*text==' ')text++;lines++;
    }
}
static void box_draw(void)
{
    box_state_t *s=open_box;int gold=AW_UIColor(223,199,144),muted=AW_UIColor(150,135,104),i,placed=0,x,y;char value[16];
    if(!s)return;
    AW_UIFill(BOX_X,BOX_Y,BOX_W,BOX_H,AW_UIColor(0,0,0));AW_UIBox(BOX_X,BOX_Y,BOX_W,BOX_H);
    if(s->w){x=BOX_X+(BOX_W-s->w)/2;AW_UIBox(x-1,BOX_Y+5,s->w+2,s->h+2);blit(s->picture,s->w,s->h,x,BOX_Y+6);}
    AW_UISmallBegin();AW_UITextCentred(BOX_X+4,BOX_Y+74,BOX_W-8,12,s->title,gold);AW_UISmallEnd();
    wrapped(BOX_X+10,BOX_Y+90,s->text,gold);
    /* the coins not placed yet, in a row */
    for(i=0;i<s->box.coins-s->box.count;i++)placed++;
    for(i=0;i<placed;i++)coin(BOX_X+(BOX_W-placed*20)/2+i*20+6,ROW_Y-14);
    for(i=0;i<8;i++){
        int c=i/4,mult=AW_LevelupMultiplier(&aw_levelup_rules,&aw_character,i),open=aw_character.attributes[i]<100;
        x=COL_X(c);y=ROW_Y+(i%4)*ROW_H;
        if(mult>100-aw_character.attributes[i])mult=100-aw_character.attributes[i];
        if(open && mult>1){sprintf(value,"x%ld",(long)mult);small(x,y,value,gold);}
        if(AW_LevelupBoxPicked(&s->box,i))coin(x-12,y-1);
        small(x+14,y,AW_StatsAttributeName(i),open?(s->focus==i?AW_UIColor(255,255,255):gold):muted);
        sprintf(value,"%ld",(long)AW_LevelupBoxValue(&aw_levelup_rules,&aw_character,&s->box,i));
        small(x+104-(int)strlen(value)*4,y,value,open?gold:muted);
    }
    AW_UIBox(OK_X-4,OK_Y-2,28,10);small(OK_X+4,OK_Y,"OK",s->focus==8?AW_UIColor(255,255,255):gold);
}
/* closed without OK (only the console key can do that): the level-up stays due and the next rest opens the box again */
static void box_closed(void){
    if(AW_LevelupDue(&aw_levelup_rules,&aw_character))Con_Printf("Level up: still due; the next rest opens the box again.\n");
    free(open_box);open_box=NULL;
}
static int box_ok(void)
{
    box_state_t *s=open_box;char line[160];edict_t *p=sv.active && svs.clients?svs.clients[0].edict:NULL;int level;
    if(!AW_LevelupBoxReady(&s->box)){
        if(!game_text("sNotifyMessage36",line,sizeof(line)))strcpy(line,"You have to distribute all your points.");
        AW_UISubtitle("",line,4);return 1;
    }
    if(p)aw_character.current[0]=p->v.health;      /* health lives on the player entity in play */
    level=AW_LevelupApply(&aw_levelup_rules,&aw_character,s->box.picks,s->box.count);
    if(p)p->v.health=aw_character.current[0];
    Con_Printf("Level up: level %ld, health %ld/%ld.\n",(long)level,(long)aw_character.current[0],(long)aw_character.maximum[0]);
    return 0;
}
static int box_key(int key,int mouse_x,int mouse_y)
{
    box_state_t *s=open_box;int i;
    if(!s)return 0;
    if(key==K_ESCAPE)return 1;           /* the box stays until OK */
    if(key>='1' && key<='8'){AW_LevelupBoxClick(&aw_character,&s->box,key-'1');s->focus=key-'1';return 1;}
    if(key==K_UPARROW && s->focus<8)s->focus=(s->focus/4)*4+(s->focus%4+3)%4;
    else if(key==K_DOWNARROW && s->focus<8)s->focus=(s->focus/4)*4+(s->focus%4+1)%4;
    else if(key==K_LEFTARROW || key==K_RIGHTARROW)s->focus=s->focus<8?(s->focus+4)%8:0;
    else if(key==K_TAB)s->focus=s->focus==8?0:8;
    else if(key==K_SPACE && s->focus<8)AW_LevelupBoxClick(&aw_character,&s->box,s->focus);
    else if(key==K_ENTER || (key==K_SPACE && s->focus==8))return box_ok();
    else if(key==K_MOUSE1){
        if(mouse_x>=OK_X-4 && mouse_x<OK_X+24 && mouse_y>=OK_Y-2 && mouse_y<OK_Y+8)return box_ok();
        for(i=0;i<8;i++){
            int x=COL_X(i/4),y=ROW_Y+(i%4)*ROW_H;
            if(mouse_x>=x-12 && mouse_x<x+106 && mouse_y>=y-2 && mouse_y<y+ROW_H-2){AW_LevelupBoxClick(&aw_character,&s->box,i);s->focus=i;}
        }
    }
    return 1;
}
int AW_LevelupBoxActive(void){return open_box!=NULL;}
static int box_open(void)
{
    box_state_t *s;char path[64],key[16];const aw_character_t *c=&aw_character;
    if(open_box)return 1;
    if(!c->valid || !AW_LevelupLoad() || !AW_LevelupDue(&aw_levelup_rules,c))return 0;
    if(!(s=(box_state_t *)AW_TryCalloc(1,sizeof(*s)))){Con_Printf("Level up: not enough memory for the box.\n");return 0;}
    open_box=s;
    s->level=c->level+1;
    AW_LevelupBoxOpen(c,&s->box);
    snprintf(path,sizeof(path),"levelup/%s.awi",AW_LevelupClassImage(c->special[0],c->special[1],c->special[2]));
    awi_load(path,s->picture,PIC_W,PIC_H,&s->w,&s->h);
    awi_load("levelup/coin.awi",s->coin,16,16,&s->coin_w,&s->coin_h);
    if(!game_text("sLevelUpMenu1",s->title,sizeof(s->title)-8))strcpy(s->title,"You have ascended to Level ");
    /* the game's line ends in a space the data file's trimmed line has lost: "... Level 2", never "Level2" */
    if(s->title[0] && s->title[strlen(s->title)-1]!=' ')strcat(s->title," ");
    sprintf(s->title+strlen(s->title),"%ld",(long)s->level);
    sprintf(key,"level %ld",(long)s->level);
    if(!game_text(key,s->text,sizeof(s->text)))game_text("sLevelUpMenu2",s->text,sizeof(s->text));
    if(key_dest==key_console)Con_ToggleConsole_f();
    if(!AW_WorldUIOpenPanel(box_draw,box_key,box_closed)){box_closed();Con_Printf("Level up: the box cannot open now.\n");return 0;}
    aw_worldui_panel_holds_escape=1;   /* no cancel in the original: Esc stays in the box */
    if(raise_sound[0])S_LocalSoundBeside(raise_sound);
    AW_MusicTriumph();
    return 1;
}
int AW_LevelupRested(void){return box_open();}

/* ---- dbg levelup (aw_levelup): status, uses, raises, the check, a rest ---- */
static int skill_of(const char *word)
{
    int i,n;char name[32];
    if(*word>='0' && *word<='9'){i=atoi(word);return i>=0 && i<AW_LEVELUP_SKILLS?i:-1;}
    for(i=0;i<AW_LEVELUP_SKILLS;i++){
        const char *s=AW_StatsSkillName(i);
        for(n=0;s[n] && n<31;n++)name[n]=s[n]==' ' || s[n]=='-'?'_':s[n];
        name[n]=0;
        if(!Q_strncasecmp(name,(char *)word,(int)strlen(word)) || !Q_strcasecmp(name,(char *)word))return i;
    }
    return -1;
}
static void status(void)
{
    const aw_character_t *c=&aw_character;const aw_class_t *k=player_class();int i;
    Con_Printf("Level %ld, level progress %ld/%ld%s\n",(long)c->level,(long)c->level_progress,(long)aw_levelup_rules.total,
        AW_LevelupDue(&aw_levelup_rules,c)?" (level-up due: rest)":"");
    Con_Printf("Attribute raises (multiplier):");
    for(i=0;i<8;i++)Con_Printf(" %.3s %ld (x%ld)",AW_StatsAttributeName(i),(long)c->raises[i],(long)AW_LevelupMultiplier(&aw_levelup_rules,c,i));
    Con_Printf("\nSpecialization raises: combat %ld, magic %ld, stealth %ld\n",(long)c->special[0],(long)c->special[1],(long)c->special[2]);
    for(i=0;i<AW_LEVELUP_SKILLS;i++){
        int place=AW_LevelupSkillClass(k,i);
        Con_Printf("%-13s %3ld %3ld%% of %ld.%ld %s\n",AW_StatsSkillName(i),(long)c->skills[i],(long)(c->progress[i]*100),
            (long)AW_LevelupRequirement(&aw_levelup_rules,k,i,c->skills[i]),
            (long)(AW_LevelupRequirement(&aw_levelup_rules,k,i,c->skills[i])*10)%10,place==2?"major":place==1?"minor":"misc");
    }
}
/* ---- dbg setlvl / restorestats / maxstats (DBG-STATS-COMMANDS-62), routed here by aw_console.c ----
 * The sheet before and after on the console; health lives on the player entity in play and fatigue on the fight sheet,
 * so both follow the sheet. */
static void sheet_line(const char *when)
{
    const aw_character_t *c=&aw_character;int i;
    Con_Printf("%s: level %ld, health %ld/%ld, magicka %ld/%ld, fatigue %ld/%ld; attributes",when,(long)c->level,
        (long)c->current[0],(long)c->maximum[0],(long)c->current[1],(long)c->maximum[1],(long)c->current[2],(long)c->maximum[2]);
    for(i=0;i<8;i++)Con_Printf(" %.3s %ld",AW_StatsAttributeName(i),(long)(c->attributes[i]+c->modifiers[i]-c->damage[i]));
    Con_Printf("\n");
}
static void sheet_follow(void)
{
    edict_t *p=sv.active && svs.clients?svs.clients[0].edict:NULL;
    if(p)p->v.health=aw_character.current[0];
    AW_CombatPlayerFatigueFill();      /* the fight sheet takes the fatigue (at most its maximum) */
    if(aw_character.current[2]<aw_character.maximum[2])aw_character.current[2]=aw_character.maximum[2];
}
static void stats_before(void)
{
    edict_t *p=sv.active && svs.clients?svs.clients[0].edict:NULL;
    if(p)aw_character.current[0]=p->v.health;
    sheet_line("Before");
}
static void set_level(int level)
{
    edict_t *p=sv.active && svs.clients?svs.clients[0].edict:NULL;
    stats_before();
    if(!AW_LevelupSetLevel(&aw_levelup_rules,&aw_character,level)){Con_Printf("dbg setlvl: a level from 1 to %d.\n",AW_LEVEL_MAX);return;}
    if(p)p->v.health=aw_character.current[0];
    sheet_line("After");
}
static const char *level_label(void *ctx,int row){static char s[16];(void)ctx;Q_snprintf(s,sizeof(s),"%d",row+1);return s;}
static void level_chosen(void *ctx,int row){(void)ctx;set_level(row+1);}
static void stats_command(const char *w)
{
    if(!Q_strcasecmp((char *)w,"setlevel")){
        if(Cmd_Argc()==2){
            aw_listbox_spec_t s;memset(&s,0,sizeof(s));
            s.title="Set the level: type it, Enter sets it";s.count=AW_LEVEL_MAX;s.label=level_label;s.chosen=level_chosen;
            if(!AW_ListBoxOpen(&s))Con_Printf("Usage: dbg setlvl N (1 to %d)\n",AW_LEVEL_MAX);
            return;
        }
        {const char *n=Cmd_Argv(2);int v=0;
         for(;*n;n++){if(*n<'0' || *n>'9' || v>AW_LEVEL_MAX){v=-1;break;}v=v*10+*n-'0';}
         if(Cmd_Argc()!=3 || v<1 || v>AW_LEVEL_MAX){Con_Printf("Usage: dbg setlvl N (1 to %d, the highest level the game's levelling reaches)\n",AW_LEVEL_MAX);return;}
         set_level(v);}
        return;
    }
    stats_before();
    if(!Q_strcasecmp((char *)w,"restore"))AW_LevelupRestore(&aw_character);
    else{
        const aw_race_t *r=aw_character.race>=0 && aw_character.race<aw_race_count?&aw_races[aw_character.race]:NULL;
        const aw_birth_t *b=aw_character.birth>=0 && aw_character.birth<aw_birth_count?&aw_births[aw_character.birth]:NULL;
        AW_LevelupMax(&aw_levelup_rules,&aw_character,1+((r?r->magicka:0)+(b?b->magicka:0))*.1f);
    }
    sheet_follow();
    sheet_line("After");
    AW_UISubtitle("",!Q_strcasecmp((char *)w,"restore")?"Health, magicka and fatigue restored.":"Every stat at the game's maximum.",3);
}
static void levelup_command(void)
{
    const char *w=Cmd_Argc()>1?Cmd_Argv(1):"";int sk,count,i,raised_n=0;
    if(!aw_character.valid){Con_Printf("Levelling: no character yet.\n");return;}
    if(!AW_LevelupLoad()){Con_Printf("Levelling: this image has no levelup/settings.txt.\n");return;}
    if(!*w || !Q_strcasecmp((char *)w,"show")){status();return;}
    /* DBG-STATS-COMMANDS-62: dbg setlvl [N], dbg restorestats, dbg maxstats */
    if((!Q_strcasecmp((char *)w,"setlevel") && Cmd_Argc()<=3) || ((!Q_strcasecmp((char *)w,"restore") ||
       !Q_strcasecmp((char *)w,"max")) && Cmd_Argc()==2)){stats_command(w);return;}
    if(!Q_strcasecmp((char *)w,"use") || !Q_strcasecmp((char *)w,"raise")){
        int use=Cmd_Argc()>4?atoi(Cmd_Argv(4)):0;
        sk=Cmd_Argc()>2?skill_of(Cmd_Argv(2)):-1;count=Cmd_Argc()>3?atoi(Cmd_Argv(3)):1;
        if(sk<0 || count<1 || count>1000 || use<0 || use>3){Con_Printf("Usage: dbg levelup %s SKILL [N%s]\n",w,*w=='u'?" [use type 0..3]":"");return;}
        for(i=0;i<count;i++)raised_n+=*w=='u' || *w=='U'?AW_LevelupUse(sk,use,1)>0:AW_LevelupRaise(sk,AW_RAISE_USAGE);
        Con_Printf("%s: %ld, progress %ld%%; %ld raise%s; level progress %ld/%ld\n",AW_StatsSkillName(sk),(long)aw_character.skills[sk],
            (long)(aw_character.progress[sk]*100),(long)raised_n,raised_n==1?"":"s",(long)aw_character.level_progress,(long)aw_levelup_rules.total);
        return;
    }
    if(!Q_strcasecmp((char *)w,"book")){
        /* the first read of a skill book, as opening it in the reader does (no reader shown) */
        int index,book_skill;
        if(Cmd_Argc()<3){Con_Printf("Usage: dbg levelup book BOOK_ID\n");return;}
        if(!skill_book(Cmd_Argv(2),&index,&book_skill)){Con_Printf("%s is not a skill book of this image.\n",Cmd_Argv(2));return;}
        if(!AW_LevelupBookRead(Cmd_Argv(2)))Con_Printf("%s: read before (read list bit %ld); no raise.\n",Cmd_Argv(2),(long)index);
        else Con_Printf("%s: %s %ld\n",Cmd_Argv(2),AW_StatsSkillName(book_skill),(long)aw_character.skills[book_skill]);
        return;
    }
    if(!Q_strcasecmp((char *)w,"read")){
        /* the reader on a placed book of this map by its reference, as E on it opens it (the raise comes from there) */
        unsigned long ref=Cmd_Argc()>2?(unsigned long)atol(Cmd_Argv(2)):0;
        if(!ref){Con_Printf("Usage: dbg levelup read REFERENCE\n");return;}
        if(!aw_book_reader || !aw_book_reader((unsigned)ref))Con_Printf("No readable book %lu on this map.\n",ref);
        else if(key_dest==key_console)Con_ToggleConsole_f();
        return;
    }
    if(!Q_strcasecmp((char *)w,"check")){
        if(box_open())return;
        Con_Printf("No level-up yet: level progress %ld/%ld.\n",(long)aw_character.level_progress,(long)aw_levelup_rules.total);return;
    }
    if(!Q_strcasecmp((char *)w,"rest")){
        int hours=Cmd_Argc()>2?atoi(Cmd_Argv(2)):8;
        if(hours<1 || hours>24){Con_Printf("Usage: dbg levelup rest [hours 1..24, default 8]\n");return;}
        if(AW_PlayerInCombat()){Con_Printf("You cannot rest with enemies nearby.\n");return;}
        if(!AW_ClockAdvance(hours*3600000)){Con_Printf("Clock state unavailable.\n");return;}
        Con_Printf("Rested %ld hour%s.\n",(long)hours,hours==1?"":"s");
        if(!box_open())Con_Printf("No level-up yet: level progress %ld/%ld.\n",(long)aw_character.level_progress,(long)aw_levelup_rules.total);
        return;
    }
    if(!Q_strcasecmp((char *)w,"bed")){
        /* the rest window as the bed with reference REF would open it (its ownership, rest even in a no-sleep cell) */
        unsigned long ref=Cmd_Argc()>2?(unsigned long)atol(Cmd_Argv(2)):0;
        if(!ref){Con_Printf("Usage: dbg levelup bed REFERENCE\n");return;}
        if(!AW_RestOpen(ref))Con_Printf("The bed %lu did not open the rest window.\n",ref);
        return;
    }
    Con_Printf("Usage: dbg levelup [show / use SKILL [N [TYPE]] / raise SKILL [N] / book ID / read REF / check / rest [HOURS] / bed REF]\n");
}
extern int (*aw_worldui_game_text)(const char *key,char *out,int size);   /* aw_worldui.c: the inventory's refusals */
void AW_LevelupInit(void){Cmd_AddCommand("aw_levelup",levelup_command);aw_worldui_game_text=game_text;}
