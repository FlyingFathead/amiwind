/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHARGEN-ABILITY-DESCRIPTIONS-65: the birthsign window and the race window's View Stats box drawn by the real
 * aw_character.c, aw_spelllist.c and aw_ui.c into a 320 x 200 screen, and measured: every ability, power and spell of
 * The Thief, The Lady and the Breton is listed with its effect lines inside its panel (never on the window's title, the
 * sign's picture, the list or the hint row), the console font's ink stays in the panel, the icons sit beside their
 * lines, a long list scrolls with the wheel and Page Down and its bar shows.
 *
 * The records are the published values of those spells, written here by hand (no game data). AW_SPELLLIST_ROOT may name
 * a built image's id1 folder (a private build output): its fonts, window skin, palette and effect icons are then used,
 * for the pictures sent for review; the checks hold either way. AW_SPELLLIST_PICS names a folder for the pictures
 * (PPM). */
#include "quakedef.h"
server_t sv;server_static_t svs;
#include <assert.h>
#include "aw_spelllist.h"
#include "aw_fxrow.h"
#include "aw_actorstate.h"
#include "aw_effects.h"
#include "aw_stats.h"
#include "aw_statswin.h"
#include "aw_inventory.h"
#include "aw_character.h"

keydest_t key_dest=key_game;
void IN_AWClearButtons(void){}
viddef_t vid;int scr_copyeverything,scr_fullupdate;double host_frametime=.02,realtime;
static byte frame[320*200],palette[768],glyphs[16384];
byte *host_basepal=palette,*draw_chars=glyphs;
void AW_HeadDraw(int x,int y,int w,int h,float angle){(void)angle;AW_UIFill(x,y,w,h,AW_UIColor(40,40,48));}
void AW_HeadClear(void){}
int AW_HeadLoad(int a,int b){(void)a;(void)b;return 1;}
/* the sign's picture: a plain 96 x 112 field where the art goes (the art is a build output) */
void AW_BirthArt(int index,int x,int y){(void)index;AW_UIFill(x,y,96,112,AW_UIColor(70,60,90));}
void Con_Printf(char *s,...){(void)s;}
void Con_DPrintf(char *s,...){(void)s;}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void Cvar_RegisterVariable(cvar_t *c){c->value=atof(c->string);}
void Cvar_SetValue(char *s,float v){(void)s;(void)v;}
void Cmd_AddCommand(char *s,void(*fn)(void)){(void)s;(void)fn;}
char *Cmd_Argv(int n){(void)n;return "";}int Cmd_Argc(void){return 0;}

/* ---- the files: from AW_SPELLLIST_ROOT when given, else a synthetic font of the shipped size ---- */
static byte font_file[2056+21];
static void make_font(void){
    int c;byte *m;
    memcpy(font_file,"AWF1",4);font_file[4]=12;font_file[5]=14;font_file[6]=21;font_file[7]=0;
    for(c=0;c<256;c++){
        m=font_file+8+c*8;
        if(c>32 && c<127){m[2]=5;m[3]=10;m[4]=0;m[5]=1;m[6]=6;}
        else m[6]=4;
    }
    memset(font_file+2056,0xFF,21);
}
static const char *root(void){return getenv("AW_SPELLLIST_ROOT");}
int COM_FOpenFile(char *s,FILE **f){
    char path[600];long n;
    *f=NULL;
    if(root()){
        snprintf(path,sizeof(path),"%s/%s",root(),s);
        if((*f=fopen(path,"rb"))!=NULL){fseek(*f,0,SEEK_END);n=ftell(*f);rewind(*f);return (int)n;}
        return -1;
    }
    if(strcmp(s,"gfx/book12.awf") && strcmp(s,"gfx/magic14.awf") && strcmp(s,"gfx/magicclear14.awf"))return -1;
    *f=fmemopen(font_file,sizeof(font_file),"rb");
    return *f?(int)sizeof(font_file):-1;
}

/* ---- the records: the published spells of The Thief, The Lady and the Breton ---- */
typedef struct {const char *name;int type;int n;aw_spell_effect_t e[2];} rec_t;
static const rec_t recs[]={
    {"Akaviri Danger-sense",1,1,{{42,-1,-1,0,0,0,10,10}}},
    {"Lady's Favor",1,1,{{79,-1,6,0,0,0,25,25}}},
    {"Lady's Grace",1,1,{{79,-1,5,0,0,0,25,25}}},
    {"Resist Magicka",1,1,{{93,-1,-1,0,0,0,50,50}}},
    {"Magicka Bonus",1,1,{{84,-1,-1,0,0,0,5,5}}},
    {"Dragon Skin",5,1,{{3,-1,-1,0,0,60,50,50}}},
    /* a long sign for the scroll: four spells of two effects each */
    {"Star-Cursed Gift",1,2,{{79,-1,0,0,0,0,10,10},{79,-1,3,0,0,0,10,10}}},
    {"Second Gift",1,2,{{93,-1,-1,0,0,0,25,25},{42,-1,-1,0,0,0,5,5}}},
    {"Night Eye",5,2,{{43,-1,-1,0,0,120,50,50},{39,-1,-1,0,0,30,0,0}}},
    {"Fireball",0,2,{{14,-1,-1,2,10,1,5,20},{90,-1,-1,2,0,10,20,20}}},
};
static const struct {int effect;const char *name;unsigned long flags;} mgefs[]={
    {3,"Shield",0},{14,"Fire Damage",0},{39,"Invisibility",AW_SL_NO_MAGNITUDE},{42,"Sanctuary",0},{43,"Night Eye",0},
    {79,"Fortify Attribute",0},{84,"Fortify Maximum Magicka",0},{90,"Weakness to Fire",0},{93,"Resist Magicka",0}};
const unsigned char *AW_AreaStatsShared(long *bytes){static const unsigned char t[4];*bytes=4;return t;}
uint32_t AW_StatIdHash(const char *id){uint32_t h=2166136261u;while(*id)h=(h^(unsigned char)tolower(*id++))*16777619u;return h?h:1;}
int AW_StatRaceSpells(const unsigned char *t,long tb,uint32_t race,int *out,int max){
    (void)t;(void)tb;
    if(race!=AW_StatIdHash("breton") || max<3)return 0;
    out[0]=5;out[1]=3;out[2]=4;return 3;   /* the power first: the window still lists the abilities first */
}
int AW_StatBirthSpells(const unsigned char *t,long tb,uint32_t birth,int *out,int max){
    (void)t;(void)tb;(void)max;
    if(birth==AW_StatIdHash("the thief")){out[0]=0;return 1;}
    if(birth==AW_StatIdHash("the lady")){out[0]=1;out[1]=2;return 2;}
    if(birth==AW_StatIdHash("long sign")){out[0]=6;out[1]=7;out[2]=8;out[3]=9;return 4;}
    return 0;
}
int AW_ActorSpellInfo(int spell,int *type,char *name,int capacity,int *cost){
    if(cost)*cost=0;
    if(spell<0 || spell>=(int)(sizeof(recs)/sizeof(recs[0])))return 0;
    if(type)*type=recs[spell].type;
    if(name)snprintf(name,(size_t)capacity,"%s",recs[spell].name);
    return 1;
}
int AW_ActorSpellEffects(int spell,aw_spell_effect_t *out,int max){
    int i;
    if(spell<0 || spell>=(int)(sizeof(recs)/sizeof(recs[0])))return 0;
    for(i=0;i<recs[spell].n && i<max;i++)out[i]=recs[spell].e[i];
    return i;
}
int AW_ActorMagicEffect(int index,aw_mgef_t *out){
    int i;
    for(i=0;i<(int)(sizeof(mgefs)/sizeof(mgefs[0]));i++)if(mgefs[i].effect==index){
        memset(out,0,sizeof(*out));out->flags=mgefs[i].flags;snprintf(out->name,sizeof(out->name),"%s",mgefs[i].name);return 1;}
    return 0;
}
int AW_EffectKind(int effect,int *group){*group=effect==79?0:effect==83?4:1;return 0;}
const char *AW_StatsAttributeName(int i){
    static const char *a[]={"Strength","Intelligence","Willpower","Agility","Speed","Endurance","Personality","Luck"};
    return i>=0 && i<8?a[i]:"";
}
const char *AW_StatsSkillName(int i){(void)i;return "Long Blade";}
/* the icons: gfx/effects.awe of the root when given (read with the engine's own directory rule), else none */
static int icon_calls;
int AW_FxSmallIcons(const short *effects,int n,unsigned char (*out)[AW_FX_HUD_ICON*AW_FX_HUD_ICON],unsigned char *ok){
    static unsigned char head[8+AW_FX_EFFECTS*AW_FX_ROW_BYTES];static aw_fx_dir_t dir[AW_FX_EFFECTS];
    FILE *f=NULL;int size,count,i,got=0;
    icon_calls++;memset(ok,0,(size_t)n);
    size=COM_FOpenFile(AW_FX_FILE,&f);
    if(!f)return 0;
    if(size<(int)sizeof(head) || fread(head,1,sizeof(head),f)!=sizeof(head)){fclose(f);return 0;}
    count=AW_FxDirectory(head,sizeof(head),(unsigned long)size,dir,AW_FX_EFFECTS);
    for(i=0;i<n;i++)if(effects[i]>=0 && effects[i]<count && dir[effects[i]].small && !fseek(f,(long)dir[effects[i]].small,SEEK_SET)
                       && fread(out[i],1,AW_FX_HUD_ICON*AW_FX_HUD_ICON,f)==AW_FX_HUD_ICON*AW_FX_HUD_ICON){ok[i]=1;got++;}
    fclose(f);return got;
}

/* ---- the measurements ---- */
static void picture(const char *name){
    const char *dir=getenv("AW_SPELLLIST_PICS");char path[512];FILE *f;int i;
    if(!dir)return;
    snprintf(path,sizeof(path),"%s/%s.ppm",dir,name);
    f=fopen(path,"wb");assert(f);
    fprintf(f,"P6\n320 200\n255\n");
    for(i=0;i<320*200;i++)fwrite(palette+frame[i]*3,1,3,f);
    fclose(f);
}
static int gold,bright,muted;
/* pixels of COLOUR inside X,Y W x H, and outside it within the window */
static int count_in(int colour,int x,int y,int w,int h){
    int i,j,n=0;
    for(j=y;j<y+h;j++)for(i=x;i<x+w;i++)if(frame[j*320+i]==colour)n++;
    return n;
}
static void draw(void){memset(frame,0,sizeof(frame));AW_CharacterDraw();}
/* UI-NO-SHARED-LAYOUT-67: the shared layout check (aw_layout.c) over what the window draws: no text or button out of
 * its box, no button against its box's bottom edge, no two texts on top of one another; the faults printed */
#include "aw_layout.h"
static int layout_faults(const char *what){
    static aw_layout_record_t record;static char why[8192];int n;
    memset(&record,0,sizeof(record));AW_LayoutRecording=&record;draw();AW_LayoutRecording=NULL;
    n=AW_LayoutCheck(&record,why,sizeof(why));
    printf("layout of %s: %d drawn, %d fault%s\n%s",what,record.count,n,n==1?"":"s",why);
    assert(record.count>10);   /* the window was recorded: its boxes, buttons and lines */
    return n;
}
/* what the panel adds: the window drawn without the panel's drawing, then with it; every changed pixel must lie in
 * X,Y W x H; returns how many changed (and how many right of the icons' column) */
extern void (*aw_chargen_spells_draw)(int x,int y,int w,int h);
static void no_panel(int x,int y,int w,int h){(void)x;(void)y;(void)w;(void)h;}
static byte base[320*200];
static int panel_only(int x,int y,int w,int h,int *text){
    void (*real)(int,int,int,int)=aw_chargen_spells_draw;int i,j,n=0;
    aw_chargen_spells_draw=no_panel;draw();memcpy(base,frame,sizeof(base));
    aw_chargen_spells_draw=real;draw();
    *text=0;
    for(j=0;j<200;j++)for(i=0;i<320;i++)if(frame[j*320+i]!=base[j*320+i]){
        if(i<x || i>=x+w || j<y || j>=y+h){printf("panel ink outside at %d,%d\n",i,j);assert(0);}
        n++;if(i>=x+2+AW_SL_ICON_W)(*text)++;
    }
    return n;
}

int main(void){
    int i,rows_ink,text;FILE *f;static byte before[320*200];
    for(i=0;i<256;i++)palette[i*3]=palette[i*3+1]=palette[i*3+2]=(byte)i;
    if(root()){char p[600];snprintf(p,sizeof(p),"%s/gfx/palette.lmp",root());f=fopen(p,"rb");if(f){assert(fread(palette,1,768,f)==768);fclose(f);}}
    make_font();
    vid.width=320;vid.height=200;vid.rowbytes=320;vid.buffer=frame;
    AW_UIInit();AW_SpellListInit();
    gold=AW_UIColor(223,199,144);bright=AW_UIColor(255,240,200);muted=AW_UIColor(150,135,104);
    aw_race_count=2;aw_birth_count=4;aw_part_count=4;aw_class_count=1;
    strcpy(aw_races[0].id,"nord");strcpy(aw_races[0].name,"Nord");
    strcpy(aw_races[1].id,"breton");strcpy(aw_races[1].name,"Breton");
    for(i=0;i<16;i++)aw_races[0].attributes[i]=aw_races[1].attributes[i]=40;
    aw_races[1].skills[13]=10;aw_races[1].skills[11]=5;aw_races[1].skills[12]=5;aw_races[1].skills[15]=10;aw_races[1].skills[16]=5;
    aw_races[1].power_count=3;strcpy(aw_races[1].powers[0],"dragon skin");
    strcpy(aw_births[0].id,"the lady");strcpy(aw_births[0].name,"The Lady");
    strcpy(aw_births[1].id,"the thief");strcpy(aw_births[1].name,"The Thief");
    strcpy(aw_births[2].id,"long sign");strcpy(aw_births[2].name,"Long Sign");
    strcpy(aw_births[3].id,"no sign");strcpy(aw_births[3].name,"No Spells");
    strcpy(aw_classes[0].id,"warrior");strcpy(aw_classes[0].name,"Warrior");
    for(i=0;i<4;i++){sprintf(aw_parts[i].id,"part%d",i);aw_parts[i].race=(byte)(i/2);aw_parts[i].female=0;aw_parts[i].kind=(byte)(i%2);}
    assert(AW_CharacterPreset("breton","warrior","the thief",0,"Tester"));

    /* the birthsign window, The Thief: Abilities, Akaviri Danger-sense, its Sanctuary line, inside the panel */
    /* the birthsign window, The Thief: Abilities, Akaviri Danger-sense and its Sanctuary line, all of it inside the
     * panel beside the picture: nothing over the title, the picture, the list or the hint row */
    assert(AW_CharacterOpen(3));
    assert(panel_only(124,32,86,130,&text)>0 && text>0);
    picture("2026_11_13_v0.0.66_birthsign_the_thief");
    assert(icon_calls==1);draw();draw();assert(icon_calls==1);   /* read once per sign shown, never while drawing */
    /* The Lady: two abilities */
    AW_CharacterKey(K_UPARROW);
    assert(panel_only(124,32,86,130,&text)>0 && text>0 && icon_calls==2);
    picture("2026_11_13_v0.0.66_birthsign_the_lady");
    /* a long sign scrolls: its bar shows; Page Down and the wheel move the list; it stays in its panel */
    AW_CharacterKey(K_DOWNARROW);AW_CharacterKey(K_DOWNARROW);
    assert(panel_only(124,32,86,130,&text)>0);
    picture("2026_11_13_v0.0.66_birthsign_long_top");
    rows_ink=count_in(AW_UIColor(210,184,121),200,32,10,130);   /* aw_ui.c AW_UIScrollbar's gold */
    assert(rows_ink>0);
    memcpy(before,frame,sizeof(before));
    AW_CharacterKey(K_PGDN);AW_CharacterKey(K_MWHEELDOWN);
    assert(panel_only(124,32,86,130,&text)>0 && memcmp(before,frame,sizeof(before)));
    picture("2026_11_13_v0.0.66_birthsign_long_scrolled");
    for(i=0;i<20;i++)AW_CharacterKey(K_PGDN);                    /* past the end: held at the last page */
    assert(panel_only(124,32,86,130,&text)>0);
    AW_CharacterKey(K_PGUP);AW_CharacterKey(K_PGUP);AW_CharacterKey(K_MWHEELUP);draw();
    /* a sign without spells: the window's own "none", no panel */
    AW_CharacterKey(K_DOWNARROW);assert(panel_only(124,32,86,130,&text)==0);
    AW_CharacterClose();

    /* the race window's View Stats box, the Breton: two abilities and a power, in the box's right column under the
     * skill bonuses, never past the box */
    assert(AW_CharacterOpen(1) && aw_character.race==1);   /* the preset's Breton */
    assert(layout_faults("the race window")==0);
    AW_CharacterKey('v');
    assert(panel_only(158,126,148,66,&text)>0 && text>0);
    picture("2026_11_13_v0.0.66_race_breton_stats");
    /* UI-RACE-STATS-RETURN-SPACING-67: the Return button under the attributes, the room under their heading */
    assert(layout_faults("the race's View Stats box")==0);
    memcpy(before,frame,sizeof(before));
    AW_CharacterKey(K_PGDN);
    assert(panel_only(158,126,148,66,&text)>0 && memcmp(before,frame,sizeof(before)));
    picture("2026_11_13_v0.0.66_race_breton_stats_scrolled");
    AW_CharacterKey(K_ESCAPE);AW_CharacterClose();
    /* UI-CHARGEN-CLASS-FONT-67: the class window and the own class window: the own class's rows in the console font no
     * longer lie on top of one another (the game font's rows did, 9 rows apart) */
    assert(AW_CharacterOpen(2));
    assert(layout_faults("the class window")==0);
    AW_CharacterKey('m');
    picture("2026_11_17_v0.0.67_make_your_own_class");
    assert(layout_faults("the own class window")==0);
    AW_CharacterClose();
    assert(AW_CharacterOpen(3));
    assert(layout_faults("the birthsign window")==0);
    AW_CharacterClose();
    printf("character spell windows: ok\n");
    return 0;
}
