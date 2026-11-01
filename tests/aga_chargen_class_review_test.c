/* SPDX-License-Identifier: GPL-2.0-or-later */
/* CHARGEN-CENSUS-57 (a): the class page is a clickable, scrolled list with the class's specialization,
 * favored attributes and major/minor skills; the review sheet shows level, race/class/sign, health, magicka
 * and fatigue, and the skills grouped major, minor and miscellaneous. */
#include "quakedef.h"
server_t sv;server_static_t svs;
#include "aw_save.h"
#include <assert.h>
keydest_t key_dest=key_game;
void IN_AWClearButtons(void){}
viddef_t vid;int scr_copyeverything;double host_frametime=.02;
static byte frame[340*207];
int AW_UIMode(void){return 2;}
int AW_ModalBlackBackground(void){return 1;}
void AW_HeadDraw(int x,int y,int w,int h,float angle){}
int AW_UIColor(int r,int g,int b){return 1;}
static int grey_dots;   /* single black dots over the Questions button (128,132 88x18): the greyed-out look */
void AW_UIFill(int x,int y,int w,int h,int color){
    assert(x>=0 && y>=0 && x+w<=320 && y+h<=200);
    if(w==1 && h==1 && x>=128 && x<216 && y>=132 && y<150)grey_dots++;
}
void AW_UIBox(int x,int y,int w,int h){assert(x>=0 && y>=0 && x+w<=320 && y+h<=200);}
static char seen[64][96];static int seen_count;
void AW_UITextBox(int x,int y,int w,int h,const char *s,int color){
    assert(x>=0 && y>=0 && x+w<=320 && y+h<=200 && strlen(s)<96);
    if(seen_count<64)strcpy(seen[seen_count++],s);
}
static int shown(const char *s){int i;for(i=0;i<seen_count;i++)if(!strcmp(seen[i],s))return 1;return 0;}
static void draw(void){seen_count=0;AW_CharacterDraw();}
void AW_UISmallBegin(void){}void AW_UISmallEnd(void){}
void AW_BirthArt(int index,int x,int y){}
void AW_HeadClear(void){}
int AW_HeadLoad(int a,int b){return 1;}
void Con_Printf(char *s,...){}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
/* character/spells.aws for step (b): two named spells (an ability and a power); "unnamed" is not in it */
static int opens,have_questions;
/* character/questions.awq for step (c): ten questions "Qn", answers "An-1".."An-3" */
static int questions_file(FILE **f)
{
    static byte raw[2048];int n=5,q,s;
    memcpy(raw,"AWQ1",4);raw[4]=10;
    for(q=0;q<10;q++)for(s=0;s<4;s++){
        char text[128];int len;
        if(!s)sprintf(text,"Q%d is a question long enough to need more than one line of text in the box",q+1);
        else sprintf(text,"A%d-%d",q+1,s);
        len=(int)strlen(text);raw[n]=len;raw[n+1]=0;memcpy(raw+n+2,text,len);n+=2+len;
    }
    *f=fmemopen(raw,n,"rb");return n;
}
int COM_FOpenFile(char *s,FILE **f){
    static byte raw[6+2*113];long n=sizeof(raw);
    *f=NULL;
    if(!strcmp(s,"character/questions.awq"))return have_questions?questions_file(f):-1;
    if(strcmp(s,"character/spells.aws"))return -1;
    opens++;memset(raw,0,sizeof(raw));memcpy(raw,"AWS1",4);raw[4]=2;
    strcpy((char *)raw+6,"steed_power");strcpy((char *)raw+6+64,"Speed of the Steed");raw[6+112]=1;
    strcpy((char *)raw+119,"lady_power");strcpy((char *)raw+119+64,"Lady's Grace");raw[119+112]=5;
    *f=fmemopen(raw,n,"rb");return (int)n;
}
int main(void)
{
    int i;
    vid.width=320;vid.height=200;vid.rowbytes=340;vid.buffer=frame;
    aw_race_count=1;aw_birth_count=1;aw_part_count=4;aw_class_count=12;
    strcpy(aw_races[0].id,"nord");strcpy(aw_races[0].name,"Nord");
    strcpy(aw_births[0].id,"charioteer");strcpy(aw_births[0].name,"The Steed");
    for(i=0;i<16;i++)aw_races[0].attributes[i]=40;
    for(i=0;i<aw_class_count;i++){
        int j;sprintf(aw_classes[i].id,"class%d",i);sprintf(aw_classes[i].name,"Class %d",i);
        aw_classes[i].attributes[0]=0;aw_classes[i].attributes[1]=5;aw_classes[i].special=i%3;
        for(j=0;j<10;j++)aw_classes[i].skills[j]=(byte)((i+j)%27);
    }
    for(i=0;i<4;i++){sprintf(aw_parts[i].id,"part%d",i);aw_parts[i].race=0;aw_parts[i].female=i/2;aw_parts[i].kind=i%2;}
    assert(AW_CharacterPreset("nord","class0","charioteer",0,"Hors"));
    /* class page: list rows, details of the chosen class */
    assert(AW_CharacterOpen(2));draw();
    assert(shown("Class 0") && shown("Class 6") && !shown("Class 7") && shown("more below"));
    assert(shown("Specialization: Combat") && shown("Favored: Strength, Endurance"));
    assert(shown("Major skills") && shown("Minor skills") && shown("Armorer") && shown("Block"));
    /* a click on the fourth row picks Class 3 (mouse starts at 100,176) */
    AW_CharacterMouse(-50,-176+34+3*16+4);AW_CharacterKey(K_MOUSE1);draw();
    assert(shown("Specialization: Combat") && shown("Favored: Strength, Endurance"));
    for(i=0;i<8;i++)AW_CharacterKey(K_DOWNARROW);
    draw();assert(shown("Class 11") && !shown("Class 0") && shown("more above") && shown("Specialization: Stealth"));
    AW_CharacterKey(K_ENTER);AW_CharacterKey(K_ENTER);
    assert(!AW_CharacterActive() && AW_CharacterDone()==2 && aw_character.clas==11);
    /* review sheet: level, names, derived stats, then grouped skills */
    assert(AW_CharacterOpen(4));draw();
    assert(shown("Hors, level 1") && shown("Nord  Class 11  The Steed"));
    {char want[96];sprintf(want,"Health %ld  Magicka %ld  Fatigue %ld",(long)aw_character.maximum[0],
        (long)aw_character.maximum[1],(long)aw_character.maximum[2]);assert(shown(want));}
    /* favored Strength and Endurance +10: health (50+50)/2, magicka Intelligence x1, fatigue Str+Wil+Agi+End */
    assert(aw_character.maximum[0]==50 && aw_character.maximum[1]==40 && aw_character.maximum[2]==180);
    AW_CharacterKey(K_RIGHTARROW);draw();assert(shown("Major skills"));
    /* class 11's majors are skills 12,14,16,18,20 (5 + 25), its minors 11,13,15,17,19 (5 + 10) */
    assert(shown("Illusion: 30") && aw_character.skills[12]==30);
    AW_CharacterKey(K_RIGHTARROW);draw();assert(shown("Minor skills"));
    assert(shown("Alteration: 15") && aw_character.skills[11]==15);
    AW_CharacterKey(K_RIGHTARROW);draw();assert(shown("Miscellaneous skills") && shown("Block: 5"));
    AW_CharacterKey(K_RIGHTARROW);draw();assert(shown("Miscellaneous skills"));
    for(i=0;i<5;i++){AW_CharacterKey(K_RIGHTARROW);draw();}
    AW_CharacterClose();
    /* (b) birthsign page: a list of the signs, the chosen sign's spells by name and kind, read once per sign */
    aw_birth_count=10;
    for(i=1;i<10;i++){aw_births[i]=aw_births[0];sprintf(aw_births[i].id,"sign%d",i);sprintf(aw_births[i].name,"Sign %d",i);}
    aw_births[0].power_count=1;strcpy(aw_births[0].powers[0],"steed_power");
    aw_births[2].power_count=2;strcpy(aw_births[2].powers[0],"lady_power");strcpy(aw_births[2].powers[1],"unnamed");
    opens=0;assert(AW_CharacterOpen(3) && opens==1);draw();draw();assert(opens==1);
    assert(shown("The Steed") && shown("Sign 6") && !shown("Sign 7") && shown("more below"));
    assert(shown("Ability") && shown("Speed of the Steed"));
    AW_CharacterMouse(-50,-176+34+2*16+4);AW_CharacterKey(K_MOUSE1);draw();
    assert(opens==2 && shown("Power") && shown("Lady's Grace") && shown("unnamed") && !shown("Speed of the Steed"));
    for(i=0;i<7;i++)AW_CharacterKey(K_DOWNARROW);
    draw();assert(shown("Sign 9") && shown("more above") && shown("none"));
    AW_CharacterKey(K_ENTER);AW_CharacterKey(K_ENTER);
    assert(!AW_CharacterActive() && AW_CharacterDone()==3 && aw_character.birth==9);
    /* review's B goes to the signs and back to review */
    assert(AW_CharacterOpen(4));AW_CharacterKey('b');AW_CharacterKey(K_UPARROW);draw();assert(shown("Sign 8"));
    AW_CharacterKey(K_ENTER);assert(AW_CharacterActive());draw();assert(shown("Hors, level 1"));
    AW_CharacterClose();
    {
    /* (c) the answer-to-class rule (OpenMW 0.51 behaviour) on the real class IDs */
    static const char *ids[]={"acrobat","agent","archer","assassin","barbarian","bard","battlemage","crusader","healer",
        "knight","mage","monk","nightblade","pilgrim","rogue","scout","sorcerer","spellsword","thief","warrior","witchhunter"};
    static const struct {int c,m,s;const char *want;} rule[]={
        {8,1,1,"warrior"},{1,8,1,"mage"},{1,1,8,"thief"},{4,3,3,"rogue"},{5,2,3,"scout"},{5,3,2,"archer"},
        {6,3,1,"barbarian"},{6,1,3,"crusader"},{6,2,2,"knight"},{7,2,1,"warrior"},{3,4,3,"spellsword"},
        {2,5,3,"witchhunter"},{2,6,2,"sorcerer"},{3,6,1,"healer"},{1,6,3,"battlemage"},{2,7,1,"mage"},
        {3,2,5,"pilgrim"},{2,3,5,"monk"},{3,1,6,"agent"},{1,3,6,"assassin"},{2,2,6,"acrobat"},{2,1,7,"thief"},
        {0,0,10,"thief"},{3,3,4,"warrior"}};
    aw_class_t saved[32];int saved_count=aw_class_count,k;
    memcpy(saved,aw_classes,sizeof(saved));
    aw_class_count=21;
    for(i=0;i<21;i++){strcpy(aw_classes[i].id,ids[i]);strcpy(aw_classes[i].name,ids[i]);}
    for(k=0;k<(int)(sizeof(rule)/sizeof(rule[0]));k++){
        int got=AW_CharacterQuizClass(rule[k].c,rule[k].m,rule[k].s);
        assert(got>=0 && !strcmp(aw_classes[got].id,rule[k].want));
    }
    memcpy(aw_classes,saved,sizeof(saved));aw_class_count=saved_count;
    }
    /* (c) without questions in the build: the button is muted and Q does nothing */
    have_questions=0;assert(AW_CharacterOpen(2));grey_dots=0;draw();assert(shown("Questions (Q)") && shown("Make own (M)"));
    assert(grey_dots>100);   /* CHARGEN-BIRTHSIGN-REVIEW-58: greyed out, not only a colour its glyphs barely show */
    AW_CharacterKey('q');draw();assert(shown("Choose your class"));AW_CharacterClose();
    /* the review sheet before any name: no bare ", level 1" */
    {char kept[32];strcpy(kept,aw_story.name);aw_story.name[0]=0;
     assert(AW_CharacterOpen(4));draw();assert(shown("Level 1") && !shown(", level 1"));AW_CharacterClose();
     strcpy(aw_story.name,kept);}
    /* (c) the questions: ten answers, all the first (combat) -> Warrior's rule; here class ids are classN, so the
     * rule finds no "warrior" and the class stays as it was; then Escape leaves the questions unchanged */
    {
    int before=aw_character.clas;
    strcpy(aw_classes[4].id,"Warrior");
    have_questions=1;
    AW_CharacterOpen(2);AW_CharacterKey('q');draw();
    assert(shown("Class questions (1/10)") && shown("A1-1") && shown("A1-3"));
    {int found=0;for(i=0;i<seen_count;i++)if(!strncmp(seen[i],"Q1 is a",7))found=1;assert(found);}
    for(i=0;i<9;i++)AW_CharacterKey(K_ENTER);
    draw();assert(shown("Class questions (10/10)"));
    grey_dots=0;AW_CharacterKey(K_ENTER);draw();assert(shown("Choose your class") && shown("Class 4"));
    assert(!grey_dots);   /* questions in the build: the button is live */
    AW_CharacterKey(K_ENTER);AW_CharacterKey(K_ENTER);assert(AW_CharacterDone()==2 && aw_character.clas==4);
    AW_CharacterOpen(2);AW_CharacterKey('q');AW_CharacterKey('3');AW_CharacterKey(K_ESCAPE);
    assert(AW_CharacterActive());draw();assert(shown("Choose your class"));AW_CharacterClose();
    (void)before;
    }
    /* (c) the own class: Long blade cannot be taken twice; OK makes "Custom class", and it rebuilds and saves */
    {
    aw_save_t source,decoded;static byte raw[AW_SAVE_BYTES];int n,slot;
    assert(AW_CharacterOpen(2));AW_CharacterKey('m');draw();assert(shown("Make your own class") && shown("Specialization"));
    AW_CharacterKey(K_RIGHTARROW);                                  /* from Class 4's Magic to Stealth */
    AW_CharacterKey(K_DOWNARROW);AW_CharacterKey(K_RIGHTARROW);     /* first favored: next attribute */
    for(i=0;i<12;i++)AW_CharacterKey(K_ENTER);                      /* to OK */
    AW_CharacterKey(K_ENTER);
    draw();assert(shown("Choose your class") && shown("Custom class") && shown("Specialization: Stealth"));
    slot=aw_class_count;
    AW_CharacterKey(K_ENTER);AW_CharacterKey(K_ENTER);assert(AW_CharacterDone()==2 && aw_character.clas==slot);
    assert(AW_CharacterClassCount()==aw_class_count+1 && aw_classes[slot].id[0]=='~' && strlen(aw_classes[slot].id)==24);
    {aw_class_t k=aw_classes[slot];int a,b;for(a=0;a<10;a++)for(b=0;b<a;b++)assert(k.skills[a]!=k.skills[b]);
     assert(k.special==2 && k.attributes[0]==1 && k.attributes[1]==5);}
    assert(AW_CharacterRebuild(&aw_character));
    memset(&source,0,sizeof(source));source.sequence=1;source.profile=1;source.character=aw_character;
    source.story=aw_story;source.story.stage=AW_STAGE_RELEASED;strcpy(source.scene,"seyda");strcpy(source.label,"x");
    source.story.hall=1;source.story.ship_disabled=1;source.story.captain=-1;source.state=aw_state;
    n=AW_SaveEncode(raw,sizeof(raw),&source);assert(n>0);
    memset(aw_classes[slot].id,0,64);assert(AW_CharacterClassCount()==aw_class_count);
    assert(AW_SaveDecode(raw,n,&decoded) && decoded.character.clas==slot && AW_CharacterClassCount()==aw_class_count+1);
    assert(aw_classes[slot].special==2 && !strcmp(aw_classes[slot].name,"Custom class"));
    /* a broken own-class ID is no class */
    strcpy(aw_classes[slot].id,"~911000102030405060708");assert(AW_CharacterClassCount()==aw_class_count);
    }
    return 0;
}
