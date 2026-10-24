/* SPDX-License-Identifier: GPL-2.0-or-later
 * The Stats window (P) and the Magic window placeholder (O), aw_statswin.c: a fixture
 * character sheet drawn with the real 3x5 glyphs into a 320x200 frame; the content rows,
 * the live update, the skill grouping and scroll, the keys (own key, rebinding) and the
 * Magic window's sections. AW_STATS_PPM=<file> writes the drawn Stats frame (and
 * <file>.magic.ppm the Magic one) for a look; the gate does not set it. */
#include "quakedef.h"
#include "aw_story.h"
#include "aw_character.h"
#include "aw_statswin.h"
#include <assert.h>

viddef_t vid;server_t sv;server_static_t svs;char *keybindings[256];
aw_story_t aw_story;aw_character_t aw_character;
aw_race_t aw_races[16];aw_class_t aw_classes[32];aw_birth_t aw_births[16];
int aw_race_count,aw_class_count,aw_birth_count;
int (*aw_title_bar)(int x,int y,int w,const char *title);
static byte frame[320*200];
static byte palette[256][3];static int colours;
int AW_UIColor(int r,int g,int b){
    int i;for(i=1;i<colours;i++)if(palette[i][0]==r && palette[i][1]==g && palette[i][2]==b)return i;
    assert(colours<256);palette[colours][0]=(byte)r;palette[colours][1]=(byte)g;palette[colours][2]=(byte)b;return colours++;
}
void AW_UIFill(int x,int y,int w,int h,int c){
    int i,j;assert(x>=0 && y>=0 && x+w<=320 && y+h<=200);
    for(j=y;j<y+h;j++)for(i=x;i<x+w;i++)frame[j*320+i]=(byte)c;
}
static int boxes;
void AW_UIBox(int x,int y,int w,int h){
    int c=AW_UIColor(150,135,104);boxes++;
    AW_UIFill(x,y,w,1,c);AW_UIFill(x,y+h-1,w,1,c);AW_UIFill(x,y,1,h,c);AW_UIFill(x+w-1,y,1,h,c);
}
static int small_depth;
void AW_UISmallBegin(void){small_depth++;}
void AW_UISmallEnd(void){small_depth--;}
static int scroll_total,scroll_top,scroll_calls;
void AW_UIScrollbar(int x,int y,int h,int total,int visible,int top){
    assert(x==304 && y==22 && h==168 && visible==21);scroll_calls++;scroll_total=total;scroll_top=top;
    AW_UIFill(x,y,8,h,AW_UIColor(48,39,22));AW_UIFill(x,y+top*(h-10)/(total-visible),8,10,AW_UIColor(223,199,144));
}
int AW_UIScrollHit(int mx,int my,int x,int y,int h,int total,int visible,int top){
    (void)top;if(mx<x || mx>=x+10 || my<y || my>=y+h || total<=visible)return -1;
    return (my-y)*(total-visible)/(h-1);
}
/* Every text the windows paint, with its place. */
typedef struct {int x,y,width,colour,centred;char value[96];} text_t;
static text_t texts[160];static int text_count;
void __real_AW_SmallStringColor(int x,int y,int width,const char *value,int colour);
void __wrap_AW_SmallStringColor(int x,int y,int width,const char *value,int colour){
    text_t *t;assert(text_count<160);t=&texts[text_count++];
    t->x=x;t->y=y;t->width=width;t->colour=colour;t->centred=0;
    strncpy(t->value,value,sizeof(t->value)-1);t->value[sizeof(t->value)-1]=0;
    assert(x>=4 && x+width<=316 && y>=4 && y+5<=196);
    __real_AW_SmallStringColor(x,y,width,value,colour);
}
void AW_UITextCentred(int x,int y,int w,int h,const char *value,int colour){
    int n=(int)strlen(value)*4;text_t *t;
    assert(small_depth==1);   /* the window titles' font, at the titles' size */
    __real_AW_SmallStringColor(x+(w-n)/2,y+(h-5)/2,n,value,colour);
    assert(text_count<160);t=&texts[text_count++];t->x=x;t->y=y;t->width=w;t->colour=colour;t->centred=1;
    strncpy(t->value,value,sizeof(t->value)-1);t->value[sizeof(t->value)-1]=0;
}
void Draw_Character(int x,int y,int c){(void)x;(void)y;(void)c;}
void Con_Printf(char *fmt,...){(void)fmt;}
static xcommand_t stats_command,magic_command;
void Cmd_AddCommand(char *name,xcommand_t f){
    if(!strcmp(name,"aw_stats"))stats_command=f;else if(!strcmp(name,"aw_magicmenu"))magic_command=f;else assert(0);
}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
int COM_FOpenFile(char *name,FILE **file){
    long size;*file=NULL;
    if(strcmp(name,"character/spells.aws"))return -1;
    if(!(*file=fopen("spells.aws","rb")))return -1;
    fseek(*file,0,SEEK_END);size=ftell(*file);fseek(*file,0,SEEK_SET);return (int)size;
}
static void (*panel_draw)(void);static int (*panel_key)(int,int,int);static void (*panel_closed)(void);static int opens;
int AW_WorldUIOpenPanel(void (*draw)(void),int (*key)(int,int,int),void (*closed)(void)){
    panel_draw=draw;panel_key=key;panel_closed=closed;opens++;return 1;
}

static void draw(void){
    text_count=0;memset(frame,0,sizeof(frame));vid.buffer=frame;vid.rowbytes=vid.width=320;vid.height=200;
    panel_draw();assert(!small_depth);
}
static const text_t *find(const char *value){
    int i;for(i=0;i<text_count;i++)if(!strcmp(texts[i].value,value))return &texts[i];
    return NULL;
}
/* A label and its value on one row, the value right-aligned at x_right. */
static void row(const char *label,const char *value,int x_right){
    const text_t *a=find(label),*b;int i;
    assert(a);
    for(i=0;i<text_count;i++){
        b=&texts[i];
        if(b!=a && b->y==a->y && !strcmp(b->value,value) && b->x>a->x){assert(b->x+b->width==x_right);return;}
    }
    fprintf(stderr,"no value %s for %s\n",value,label);assert(0);
}
static void write_ppm(const char *path){
    FILE *f=fopen(path,"wb");int i;
    assert(f);fprintf(f,"P6\n320 200\n255\n");
    for(i=0;i<320*200;i++)fwrite(palette[frame[i]],1,3,f);
    fclose(f);
}
static void spells_file(void){
    static const struct {const char *id,*name;int type;} rows[]={
        {"ancestor guardian","Ancestor Guardian",5},{"resist fire_75","Resist Fire",1},
        {"mages_spell","Fay's Light",0},{"wombburn","Wombburned",5}};
    FILE *f=fopen("spells.aws","wb");byte head[6]={'A','W','S','1',4,0},row[113];int i;
    assert(f);fwrite(head,1,6,f);
    for(i=0;i<4;i++){
        memset(row,0,sizeof(row));strcpy((char *)row,rows[i].id);strcpy((char *)row+64,rows[i].name);row[112]=(byte)rows[i].type;
        fwrite(row,1,113,f);
    }
    fclose(f);
}
int main(void){
    static const char *const attributes[8]={"Strength","Intelligence","Willpower","Agility","Speed","Endurance","Personality","Luck"};
    char line[32],*path=getenv("AW_STATS_PPM");int i,j,seen[27],major_rows;
    aw_character_t *c=&aw_character;
    /* Fixture: a Dark Elf Battlemage under the Mage (names and numbers made up for the test). */
    strcpy(aw_story.name,"Tester");
    aw_race_count=aw_class_count=aw_birth_count=1;
    strcpy(aw_races[0].name,"Dark Elf");aw_races[0].power_count=2;
    strcpy(aw_races[0].powers[0],"ancestor guardian");strcpy(aw_races[0].powers[1],"resist fire_75");
    strcpy(aw_classes[0].name,"Battlemage");
    {static const unsigned char pairs[10]={8,10,6,11,3,13,24,14,5,16};memcpy(aw_classes[0].skills,pairs,10);}
    strcpy(aw_births[0].name,"The Mage");aw_births[0].power_count=2;
    strcpy(aw_births[0].powers[0],"mages_spell");strcpy(aw_births[0].powers[1],"missing_spell");
    c->valid=1;c->level=3;c->race=c->clas=c->birth=0;
    for(i=0;i<8;i++)c->attributes[i]=(short)(30+i);
    c->modifiers[1]=10;c->damage[4]=5;
    for(i=0;i<27;i++)c->skills[i]=(short)(5+i);
    c->maximum[0]=52;c->current[0]=40;c->maximum[1]=120;c->current[1]=99.5f;c->maximum[2]=210;c->current[2]=180;

    AW_StatsWindowInit();assert(stats_command && magic_command);
    stats_command();assert(opens==1 && panel_draw && panel_key && !panel_closed);
    draw();
    /* Title: the player's name, in the title band, centred in the window title font. */
    assert(find("Tester") && find("Tester")->centred && find("Tester")->y==6);
    assert(boxes==3);
    assert(find("40/52") && find("99/120") && find("180/210"));
    assert(find("Health") && find("Magicka") && find("Fatigue"));
    row("Level","3",130);row("Race","Dark Elf",130);row("Class","Battlemage",130);row("Birthsign","The Mage",130);
    /* The eight attributes: base + modifiers - damage. */
    for(i=0;i<8;i++){
        int v=30+i+(i==1?10:0)-(i==4?5:0);sprintf(line,"%d",v);row(attributes[i],line,130);
        assert(find(attributes[i])->y==84+i*8);
    }
    /* The skill list: Major (the class's odd CLDT slots), Minor (even slots), then Misc. */
    assert(scroll_calls==1 && scroll_total==30 && scroll_top==0);
    assert(find("Major Skills")->y==22);
    {static const int major[5]={10,11,13,14,16},minor[5]={8,6,3,24,5};
     for(i=0;i<5;i++){
        const text_t *t=find(AW_StatsSkillName(major[i]));assert(t && t->y==30+i*8);
        sprintf(line,"%d",5+major[i]);row(AW_StatsSkillName(major[i]),line,300);
     }
     assert(find("Minor Skills")->y==70);
     for(i=0;i<5;i++)assert(find(AW_StatsSkillName(minor[i]))->y==78+i*8);
    }
    assert(find("Misc Skills")->y==118);
    if(path)write_ppm(path);
    /* Every skill exactly once over the scroll; misc rows in skill record order. */
    memset(seen,0,sizeof(seen));major_rows=0;
    for(j=0;j<2;j++){
        if(j){for(i=0;i<40;i++)assert(panel_key(K_DOWNARROW,0,0));draw();assert(scroll_top==9);}
        for(i=0;i<27;i++)if(find(AW_StatsSkillName(i)))seen[i]=1;
    }
    for(i=0;i<27;i++)assert(seen[i]);
    {aw_stats_sheet_t s;int rows[AW_STATS_ROWS],n;
     AW_StatsSheet(&s);n=AW_StatsRows(&s,rows);assert(n==30);
     assert(rows[12]==-3 && rows[13]==0);
     for(i=14;i<n;i++)assert(rows[i]>rows[i-1]);   /* misc: skill record order */
     major_rows=rows[1];assert(major_rows==10);}
    assert(panel_key(K_HOME,0,0));draw();assert(scroll_top==0);
    assert(panel_key(K_END,0,0));draw();assert(scroll_top==9);
    assert(panel_key(K_MWHEELUP,0,0));draw();assert(scroll_top==8);
    /* Live: a change on the sheet shows on the next frame. */
    c->current[0]=12;c->skills[10]=77;assert(panel_key(K_HOME,0,0));draw();assert(find("12/52"));row("Destruction","77",300);
    /* Without a class the list is Misc only (never invented groups). */
    aw_class_count=0;draw();assert(!find("Major Skills") && find("Misc Skills") && find("Class"));aw_class_count=1;
    /* Keys: P (either case) and the key bound to aw_stats close; others do not. */
    assert(!panel_key('p',0,0) && !panel_key('P',0,0) && panel_key('k',0,0) && panel_key('i',0,0));
    keybindings['k']="aw_stats";assert(!panel_key('k',0,0));keybindings['k']=NULL;
    /* The close hint closes with the mouse, as the inventory's does. */
    assert(!panel_key(K_MOUSE1,10,177) && panel_key(K_MOUSE1,200,100));

    /* Magic (O): Powers / Spells / Magic Items; the race's and birthsign's spells by name
     * from character/spells.aws, abilities and unknown ids left out; the footer. */
    spells_file();
    magic_command();assert(opens==2 && panel_closed);
    draw();
    assert(find("Magic") && find("Magic")->centred);
    assert(find("Powers") && find("Spells") && find("Magic Items"));
    assert(find("Ancestor Guardian") && find("Fay's Light") && !find("Resist Fire") && !find("missing_spell"));
    assert(find("Powers")->y<find("Ancestor Guardian")->y && find("Ancestor Guardian")->y<find("Spells")->y);
    assert(find("Spells")->y<find("Fay's Light")->y && find("Fay's Light")->y<find("Magic Items")->y);
    assert(find("None") && find("None")->y>find("Magic Items")->y);
    assert(find("(Not yet implemented)") && find("(Not yet implemented)")->centred && find("(Not yet implemented)")->y>=176);
    if(path){char other[512];snprintf(other,sizeof(other),"%s.magic.ppm",path);write_ppm(other);}
    assert(!panel_key('o',0,0) && !panel_key('O',0,0) && panel_key('p',0,0));
    panel_closed();
    /* Without the spell table: every heading lists None. */
    remove("spells.aws");magic_command();draw();
    for(i=j=0;i<text_count;i++)if(!strcmp(texts[i].value,"None"))j++;
    assert(j==3);panel_closed();
    /* No character: neither window opens. */
    c->valid=0;stats_command();magic_command();assert(opens==3);
    puts("Stats and Magic windows: content rows, grouping, scroll, keys, live update ok");
    return 0;
}
