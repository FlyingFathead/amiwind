/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_story.h"
#include "aw_character.h"
#include "aw_tryalloc.h"

aw_character_t aw_character;
aw_race_t aw_races[16];
aw_class_t aw_classes[32];
aw_birth_t aw_births[16];
aw_part_t aw_parts[384];
int aw_race_count,aw_class_count,aw_birth_count,aw_part_count;
byte aw_character_source[32];
static byte specialization[27];
static const byte *cursor,*limit;
static int decode_error;
static unsigned short eye_heights[16][2];
static int default_eye_race,default_eye_female;
static int menu,accepted,row,review_return,page;
static int confirming,confirm_yes;
/* Quick character screen (aw_quickchar.c): pages before its last one are
 * accepted with Enter, without the "Really choose" box. */
static int skip_confirm;
static int mouse_x=160,mouse_y=90,mouse_visible;
static aw_character_t choice;
static float rotation;
/* Version 1 retains the original footer and hit strip. Version 2 shares this
 * one rectangle between drawing, focus and pointer activation. */
#define OK_X 248
#define OK_Y 166
#define OK_W 60
#define OK_H 22
static int over_ok(void) {
    return mouse_x>=OK_X && mouse_x<OK_X+OK_W &&
        mouse_y>=OK_Y && mouse_y<OK_Y+OK_H;
}
/* RACE-STATS-57: the race page's "View Stats" button (row STATS_ROW, between Hair and OK) opens a box with the
 * race's base attributes for the chosen sex, its skill bonuses and its specials, from the catalogue the builder
 * made from the game's RACE records (character/catalog.awc, already loaded for this screen: nothing more held).
 * The original's race menu lists skill bonuses and specials (OpenMW 0.51 apps/openmw/mwgui/race.cpp
 * updateSkills, updateSpellPowers); the base attributes are the record's own (ESM RADT), shown here too. */
#define STATS_ROW 5
#define STATS_X 10
#define STATS_Y 133
#define STATS_W 92
#define STATS_H 23
static int stats_open;
static int over_stats(void) {
    return mouse_x>=STATS_X && mouse_x<STATS_X+STATS_W && mouse_y>=STATS_Y && mouse_y<STATS_Y+STATS_H;
}
/* CHARGEN-CENSUS-57 (a): the class page is a list (CLASS_ROWS names, scrolled with the selection) beside the
 * chosen class's specialization, favored attributes and major/minor skills (the original's class menu, as
 * OpenMW 0.51 apps/openmw/mwgui/class.cpp PickClassDialog shows it). Rows are clicked to choose. */
#define CLASS_ROWS 7
#define CLASS_X 10
#define CLASS_Y 34
#define CLASS_W 112
#define CLASS_H 16
/* CHARGEN-CENSUS-57 (b): the birthsign page uses the same list, beside the sign's abilities, powers and spells by
 * their names (character/spells.aws, read once per sign shown, never while drawing) and its picture (OpenMW 0.51
 * mwgui/birth.cpp BirthDialog). */
static int class_top;
static int list_count(void){return menu==3?aw_birth_count:aw_class_count;}
static int over_class_row(void) {
    int r=(mouse_y-CLASS_Y)/CLASS_H;
    if(mouse_x<CLASS_X || mouse_x>=CLASS_X+CLASS_W || mouse_y<CLASS_Y || r>=CLASS_ROWS || class_top+r>=list_count())return -1;
    return class_top+r;
}
/* CHARGEN-CENSUS-57 (c): the class page's other two ways, as in the original's registration: the ten questions
 * (character/questions.awq from the install's Morrowind.ini, held only while they are asked) and the player's own
 * class. class_way: 0 the list, 1 the questions, 2 the own class. */
static int class_way;
static int custom_valid(const aw_class_t *k);
#define QUIZ_TEXT 400
#define QUIZ_BYTES 6144
static char *quiz;                 /* NUL-ended strings, 4 per question; NULL when not asking */
static int quiz_at,quiz_answer,quiz_counts[3],quiz_offsets[10][4];
static int quiz_available=-1;      /* -1 not looked at yet; 0 the build has no questions; 1 it has */
static void quiz_free(void){if(quiz)free(quiz);quiz=NULL;}
/* Reads character/questions.awq ("AWQ1", u8 count, then u16 length + text per string); 1 when ten questions. */
static int quiz_load(void)
{
    FILE *f=NULL;byte *raw=NULL;int size,ok=0,at=5,used=0,q,s,n;
    quiz_free();
    size=COM_FOpenFile("character/questions.awq",&f);
    if(!f)return quiz_available=0;
    if(size>=5 && size<=QUIZ_BYTES && (raw=AW_TryMalloc(size)) && fread(raw,1,size,f)==(size_t)size &&
       !memcmp(raw,"AWQ1",4) && raw[4]==10 && (quiz=AW_TryMalloc(size+40))){
        ok=1;
        for(q=0;q<10 && ok;q++)for(s=0;s<4 && ok;s++){
            if(at+2>size){ok=0;break;}
            n=raw[at]|(raw[at+1]<<8);at+=2;
            if(n<1 || n>QUIZ_TEXT || at+n>size || memchr(raw+at,0,n)){ok=0;break;}
            memcpy(quiz+used,raw+at,n);quiz[used+n]=0;quiz_offsets[q][s]=used;used+=n+1;at+=n;
        }
        if(at!=size)ok=0;
    }
    fclose(f);if(raw)free(raw);
    if(!ok)quiz_free();
    return quiz_available=ok;
}
/* Draws text word-wrapped into lines of h pixels inside w (the small font: at most WRAP_CHAR pixels a letter);
 * at most lines lines. */
#define WRAP_CHAR 5
static void wrap(int x,int y,int w,int h,int lines,const char *text,int color)
{
    char line[128];int n,most=w/WRAP_CHAR;
    if(most>(int)sizeof(line)-1)most=sizeof(line)-1;
    while(*text && lines-->0){
        int fit=0,last_space=-1;
        while(*text==' ')text++;
        for(n=0;text[n] && n<most;n++){
            if(text[n]==' ')last_space=n;
            fit=n+1;
        }
        if(text[fit] && last_space>0)fit=last_space;
        if(fit<1)fit=1;
        memcpy(line,text,fit);line[fit]=0;
        AW_UITextBox(x,y,w,h,line,color);y+=h;text+=fit;
    }
}
static aw_class_t custom;          /* the own class being made */
static int custom_row;             /* 0 specialization, 1-2 favored, 3-7 major, 8-12 minor, 13 OK */
#define CUSTOM_ROWS 14
static int custom_skill(int at){return at<8?(at-3)*2+1:(at-8)*2;}  /* CLDT: odd major, even minor */
static void custom_change(int direction)
{
    int i,j,value,used;
    if(custom_row==0){custom.special=(custom.special+direction+3)%3;return;}
    if(custom_row<3){
        value=custom.attributes[custom_row-1];
        do value=(value+direction+8)%8;while(value==custom.attributes[2-custom_row]);
        custom.attributes[custom_row-1]=value;return;
    }
    if(custom_row>12)return;
    i=custom_skill(custom_row);value=custom.skills[i];
    for(j=0;j<27;j++){
        int k;value=(value+direction+27)%27;used=0;
        for(k=0;k<10;k++)if(k!=i && custom.skills[k]==value)used=1;
        if(!used)break;
    }
    custom.skills[i]=value;
}
static void custom_start(void)
{
    int i;
    /* starts from the class now chosen, so a change is one step away */
    custom=aw_classes[choice.clas];
    if(!custom_valid(&custom)){memset(&custom,0,sizeof(custom));custom.attributes[1]=1;for(i=0;i<10;i++)custom.skills[i]=i;}
    custom_row=0;class_way=2;
}
/* the class page's two buttons beside the list: "Questions" and "Make your own" */
#define QWAY_Y 132
#define QWAY_H 18
/* A button that cannot be used: every other pixel inside its frame black, the usual greyed-out look */
static void greyed(int x,int y,int w,int h)
{
    int i,j,black=AW_UIColor(0,0,0);
    for(j=y+3;j<y+h-3;j++)for(i=x+3+(j&1);i<x+w-3;i+=2)AW_UIFill(i,j,1,1,black);
}
#define SIGN_SPELLS 6
static int sign_loaded=-1,sign_spell_count;
static char sign_spell[SIGN_SPELLS][48];
static byte sign_kind[SIGN_SPELLS]; /* the SPEL type: 0 spell, 1 ability, 5 power, others as given */
/* character/spells.aws: "AWS1", u16 count, then id[64], name[48], type per spell. A missing file or spell
 * shows the record ID, so the page never goes blank. */
static void copy_name(char *out,const char *in){int k=0;while(k<47 && in[k]){out[k]=in[k];k++;}out[k]=0;}
static void sign_spells(int birth)
{
    FILE *f=NULL;byte head[6],entry[113];int size=-1,count=0,i,j,n;aw_birth_t *b;
    if(birth==sign_loaded || birth<0 || birth>=aw_birth_count)return;
    b=&aw_births[birth];n=b->power_count<SIGN_SPELLS?b->power_count:SIGN_SPELLS;
    for(j=0;j<n;j++){copy_name(sign_spell[j],b->powers[j]);sign_kind[j]=255;}
    size=COM_FOpenFile("character/spells.aws",&f);
    if(f){
        if(size>=6 && fread(head,1,6,f)==6 && !memcmp(head,"AWS1",4))count=head[4]|(head[5]<<8);
        if(size!=6+count*113)count=0;
        for(i=0;i<count && fread(entry,1,113,f)==113;i++){
            if(!memchr(entry,0,64) || !memchr(entry+64,0,48))break;
            for(j=0;j<n;j++)if(!Q_strcasecmp((char *)entry,b->powers[j])){copy_name(sign_spell[j],(char *)entry+64);sign_kind[j]=entry[112];}
        }
        fclose(f);
    }
    sign_spell_count=n;sign_loaded=birth;
}
static const char *specializations[]={"Combat","Magic","Stealth"};
static const char *attributes[]={"Strength","Intelligence","Willpower","Agility","Speed","Endurance","Personality","Luck"};
static const char *skills[]={"Block","Armorer","Medium armor","Heavy armor","Blunt weapon","Long blade","Axe","Spear","Athletics","Enchant","Destruction","Alteration","Illusion","Conjuration","Mysticism","Restoration","Alchemy","Unarmored","Security","Sneak","Acrobatics","Light armor","Short blade","Marksman","Mercantile","Speechcraft","Hand to hand"};

static int take(void *out,int count)
{
    if(count<0 || count>limit-cursor){decode_error=1;return 0;}
    memcpy(out,cursor,count);cursor+=count;return 1;
}
static int number(void){byte b[2]={0,0};take(b,2);return b[0]+(b[1]<<8);}
static void name(char *out,int size)
{
    int i;
    if(!take(out,size))return;
    if(!out[0] || !memchr(out,0,size)){decode_error=1;return;}
    for(i=0;out[i];i++)if((unsigned char)out[i]<32)decode_error=1;
}
static int powers(char out[16][64])
{
    byte n=0;int i;take(&n,1);
    if(n>16){decode_error=1;return 0;}
    for(i=0;i<n;i++)name(out[i],64);
    return n;
}

int AW_CharacterDecode(const byte *data,int size)
{
    int nr,nc,nb,np,i,j;byte pad=0;
    aw_race_t *r;aw_class_t *c;aw_birth_t *b;aw_part_t *p;
    aw_race_count=aw_class_count=aw_birth_count=aw_part_count=0;sign_loaded=-1;memset(aw_classes,0,sizeof(aw_classes));
    memset(eye_heights,0,sizeof(eye_heights));default_eye_race=default_eye_female=0;
    if(size<72 || size>98304 || memcmp(data,"AWC1",4))return 0;
    cursor=data+4;limit=data+size;decode_error=0;
    nr=number();nc=number();nb=number();np=number();
    if(nr<1 || nr>16 || nc<1 || nc>32 || nb<1 || nb>16 || np<1 || np>384)return 0;
    take(specialization,27);take(&pad,1);take(aw_character_source,32);
    if(pad)return 0;
    for(i=0;i<27;i++)if(specialization[i]>2)return 0;
    for(i=0;i<nr && !decode_error;i++){
        r=&aw_races[i];name(r->id,64);name(r->name,48);
        take(r->attributes,16);take(r->skills,27);
        for(j=0;j<8;j++){r->modifiers[j]=(short)number();
        if(abs(r->modifiers[j])>1000)decode_error=1;}
        r->magicka=number();
        if(r->magicka>1000)decode_error=1;
        r->power_count=powers(r->powers);
    }
    for(i=0;i<nc && !decode_error;i++){
        c=&aw_classes[i];name(c->id,64);name(c->name,48);
        take(c->attributes,2);take(&c->special,1);take(c->skills,10);
        if(c->attributes[0]>7 || c->attributes[1]>7 || c->special>2)decode_error=1;
        for(j=0;j<10;j++)if(c->skills[j]>26)decode_error=1;
    }
    for(i=0;i<nb && !decode_error;i++){
        b=&aw_births[i];name(b->id,64);name(b->name,48);
        for(j=0;j<8;j++){b->modifiers[j]=(short)number();
        if(abs(b->modifiers[j])>1000)decode_error=1;}
        b->magicka=number();
        if(b->magicka>1000)decode_error=1;
        b->power_count=powers(b->powers);
    }
    for(i=0;i<np && !decode_error;i++){
        p=&aw_parts[i];name(p->id,64);take(&p->race,1);take(&p->female,1);take(&p->kind,1);take(&pad,1);
        if(pad || p->race>=nr || p->female>1 || p->kind>1)decode_error=1;
    }
    if(!decode_error && cursor<limit){
        byte header[6];
        if(limit-cursor!=6+nr*4 || !take(header,6) || memcmp(header,"AWE1",4) ||
           header[4]>=nr || header[5]>1)return 0;
        default_eye_race=header[4];default_eye_female=header[5];
        for(i=0;i<nr;i++)for(j=0;j<2;j++){
            int height=number();if(height<8000 || height>60000)return 0;
            eye_heights[i][j]=height;
        }
    }
    if(decode_error || cursor!=limit)return 0;
    /* Reject duplicate IDs and missing race/sex choices before selectors use it. */
    for(i=0;i<np;i++)for(j=0;j<i;j++)if(!strcmp(aw_parts[i].id,aw_parts[j].id))return 0;
    for(i=0;i<nr*4;i++){
        for(j=0;j<np;j++)if(aw_parts[j].race==i/4 && aw_parts[j].female==(i/2)%2 && aw_parts[j].kind==i%2)break;
        if(j==np)return 0;
    }
    aw_race_count=nr;aw_class_count=nc;aw_birth_count=nb;aw_part_count=np;
    return 1;
}

int AW_CharacterLoad(void)
{
    FILE *f=NULL;byte *raw;int size,ok;
    if(aw_race_count)return 1;
    size=COM_FOpenFile("character/catalog.awc",&f);
    if(!f)return 0;
    if(size<72 || size>98304){fclose(f);return 0;}
    raw=AW_TryMalloc(size);
    if(!raw){fclose(f);return 0;}
    ok=fread(raw,1,size,f)==(size_t)size;fclose(f);
    if(ok)ok=AW_CharacterDecode(raw,size);
    free(raw);return ok;
}

float AW_CharacterEyeHeight(void)
{
    int race=default_eye_race,sex=default_eye_female;
    if(!aw_race_count)return 0;
    if(aw_character.valid && (aw_story.stage==AW_STAGE_DEMO || aw_story.stage>=AW_STAGE_OFFICE)){
        race=aw_character.race;sex=aw_character.female;
    }
    if(race<0 || race>=aw_race_count || sex<0 || sex>1)return 0;
    return eye_heights[race][sex]*.001f;
}

static void apply_eye(void)
{
    float height;edict_t *p;
    if(!aw_character.valid || aw_character.race<0 || aw_character.race>=aw_race_count || aw_character.female<0 || aw_character.female>1)return;
    height=eye_heights[aw_character.race][aw_character.female]*.001f;
    if(height<=0 || !sv.active || svs.maxclients!=1 || !svs.clients || !(p=svs.clients[0].edict))return;
    p->v.view_ofs[2]=height+p->v.mins[2];
}

static int part_next(int current,int race,int sex,int kind,int direction)
{
    int i,index=current;
    for(i=0;i<aw_part_count;i++){
        index=(index+direction+aw_part_count)%aw_part_count;
        if(aw_parts[index].race==race && aw_parts[index].female==sex && aw_parts[index].kind==kind)return index;
    }
    return -1;
}
static int part_valid(int index,aw_character_t *c,int kind)
{
    return index>=0 && index<aw_part_count && aw_parts[index].race==c->race &&
        aw_parts[index].female==c->female && aw_parts[index].kind==kind;
}
/* CHARGEN-CENSUS-57 (c): the player's own class lives in the slot after the catalogue's classes (aw_classes[
 * aw_class_count]), named "Custom class". Its ID carries its whole definition, so a save names it like any other
 * class and needs no new field: "~" specialization, two favored attributes (one digit each), then ten skills (two
 * digits each, the CLDT order: minor, major, minor, major...). */
/* The slot holds the player's class when its ID is a valid definition (written by AW_CharacterCustomDefine, or by
 * the save reader, aw_save_codec.c, which copies a saved "~" ID there); its fields are filled from the ID. */
static int custom_slot(void)
{
    aw_class_t k;aw_class_t *slot;const char *id;int i;
    if(aw_class_count<1 || aw_class_count>=32)return 0;
    slot=&aw_classes[aw_class_count];id=slot->id;
    if(id[0]!='~' || !memchr(id,0,64) || strlen(id)!=24)return 0;
    for(i=1;i<24;i++)if(id[i]<'0' || id[i]>'9')return 0;
    memset(&k,0,sizeof(k));
    k.special=id[1]-'0';k.attributes[0]=id[2]-'0';k.attributes[1]=id[3]-'0';
    for(i=0;i<10;i++)k.skills[i]=(id[4+i*2]-'0')*10+id[5+i*2]-'0';
    if(!custom_valid(&k))return 0;
    slot->special=k.special;memcpy(slot->attributes,k.attributes,2);memcpy(slot->skills,k.skills,10);
    strcpy(slot->name,"Custom class");
    return 1;
}
int AW_CharacterClassCount(void){return aw_class_count+custom_slot();}
static int custom_valid(const aw_class_t *k)
{
    int i,j;
    if(k->special>2 || k->attributes[0]>7 || k->attributes[1]>7 || k->attributes[0]==k->attributes[1])return 0;
    for(i=0;i<10;i++){
        if(k->skills[i]>26)return 0;
        for(j=0;j<i;j++)if(k->skills[i]==k->skills[j])return 0;
    }
    return 1;
}
int AW_CharacterCustomDefine(const aw_class_t *k)
{
    aw_class_t *slot;int i;
    if(!k || aw_class_count<1 || aw_class_count>=32 || !custom_valid(k))return -1;
    slot=&aw_classes[aw_class_count];memset(slot,0,sizeof(*slot));
    sprintf(slot->id,"~%d%d%d",(int)k->special,(int)k->attributes[0],(int)k->attributes[1]);
    for(i=0;i<10;i++)sprintf(slot->id+4+i*2,"%02d",(int)k->skills[i]);
    return custom_slot()?aw_class_count:-1;
}
/* The class the ten questions give (OpenMW 0.51 charactercreation.cpp, the original's rule; written here as a
 * table): a count of 8 or more in one specialization gives its class; else the combat count, then the magic
 * count, then the stealth count picks it, some cases split by another count. Returns a catalogue index or -1. */
static int quiz_class(int combat,int magic,int stealth)
{
    const char *name;
    if(combat>7)name="warrior";
    else if(magic>7)name="mage";
    else if(stealth>7)name="thief";
    else if(combat==4)name="rogue";
    else if(combat==5)name=stealth==3?"scout":"archer";
    else if(combat==6)name=stealth==1?"barbarian":stealth==3?"crusader":"knight";
    else if(combat==7)name="warrior";
    else if(magic==4)name="spellsword";
    else if(magic==5)name="witchhunter";
    else if(magic==6)name=combat==2?"sorcerer":combat==3?"healer":"battlemage";
    else if(magic==7)name="mage";
    else if(stealth==3)name=magic==3?"bard":"warrior";
    else if(stealth==5)name=magic==3?"monk":"pilgrim";
    else if(stealth==6)name=magic==1?"agent":magic==3?"assassin":"acrobat";
    else if(stealth==7)name="thief";
    else name="warrior";
    {int i;for(i=0;i<aw_class_count;i++)if(!Q_strcasecmp(aw_classes[i].id,(char *)name))return i;}
    return -1;
}
int AW_CharacterQuizClass(int combat,int magic,int stealth){return quiz_class(combat,magic,stealth);}

int AW_CharacterRebuild(aw_character_t *c)
{
    int i;aw_race_t *r;aw_class_t *k;aw_birth_t *b;
    if(c->race<0 || c->race>=aw_race_count || c->female<0 || c->female>1 ||
       c->clas<0 || c->clas>=AW_CharacterClassCount() || c->birth<0 || c->birth>=aw_birth_count ||
       !part_valid(c->head,c,0) || !part_valid(c->hair,c,1))return 0;
    r=&aw_races[c->race];k=&aw_classes[c->clas];b=&aw_births[c->birth];
    for(i=0;i<8;i++){
        c->attributes[i]=r->attributes[i*2+c->female];
        c->modifiers[i]=r->modifiers[i]+b->modifiers[i];c->damage[i]=0;
    }
    for(i=0;i<2;i++)c->attributes[k->attributes[i]]+=10;
    for(i=0;i<27;i++)c->skills[i]=5+r->skills[i]+(specialization[i]==k->special?5:0);
    for(i=0;i<10;i++)c->skills[k->skills[i]]+=(i&1)?25:10;
    /* Starting health uses base Strength/Endurance; permanent Fortify Attribute
     * effects modify fatigue/magicka, without granting retroactive health. */
    c->maximum[0]=(c->attributes[0]+c->attributes[5])*.5f;
    c->maximum[1]=(c->attributes[1]+c->modifiers[1])*(1+(r->magicka+b->magicka)*.1f);
    c->maximum[2]=0;
    for(i=0;i<6;i++)if(i!=1 && i!=4)c->maximum[2]+=c->attributes[i]+c->modifiers[i];
    for(i=0;i<3;i++)c->current[i]=c->maximum[i];
    c->level=1;c->valid=1;return 1;
}

void AW_CharacterReset(void)
{
    memset(&aw_character,0,sizeof(aw_character));menu=accepted=review_return=confirming=skip_confirm=0;
    AW_HeadClear();
    if(!AW_CharacterLoad())return;
    aw_character.head=part_next(-1,0,0,0,1);aw_character.hair=part_next(-1,0,0,1,1);
    AW_CharacterRebuild(&aw_character);
}

/* Explicit development restart. Resolve catalogue IDs and use the ordinary
 * stat builder; never invent a second set of Nord/class/birthsign values. */
int AW_CharacterPreset(const char *race,const char *clas,const char *birth,int female,const char *name)
{
    aw_character_t c;int i;
    if(!race || !clas || !birth || !name || !*name || strlen(name)>=sizeof(aw_story.name) || female<0 || female>1)return 0;
    if(!AW_CharacterLoad())return 0;
    memset(&c,0,sizeof(c));c.race=c.clas=c.birth=-1;c.female=female;
    for(i=0;i<aw_race_count;i++)if(!Q_strcasecmp(aw_races[i].id,(char *)race))c.race=i;
    for(i=0;i<aw_class_count;i++)if(!Q_strcasecmp(aw_classes[i].id,(char *)clas))c.clas=i;
    for(i=0;i<aw_birth_count;i++)if(!Q_strcasecmp(aw_births[i].id,(char *)birth))c.birth=i;
    if(c.race<0 || c.clas<0 || c.birth<0)return 0;
    c.head=part_next(-1,c.race,female,0,1);c.hair=part_next(-1,c.race,female,1,1);
    if(!AW_CharacterRebuild(&c))return 0;
    AW_StoryReset(0);strcpy(aw_story.name,name);
    AW_CourtyardTakeRing();AW_CaptainDuties();
    AW_StateSet(&aw_state,AW_GLOBAL,"CharGenState",-1);
    aw_story.stage=AW_STAGE_RELEASED;aw_story.ship_disabled=1;
    aw_story.hall=aw_story.hall_open=1;aw_story.captain=-1;
    aw_story.dock=aw_story.census=-1;
    aw_character=c;menu=accepted=review_return=confirming=0;AW_HeadClear();apply_eye();
    return 1;
}
/* Explicit development restart. Resolve catalogue IDs and use the ordinary
 * stat builder; never invent a second set of Nord/class/birthsign values. */
int AW_CharacterHors(void){return AW_CharacterPreset("nord","barbarian","charioteer",0,"Hors");}

#define LOWER(c) ((c)>='A' && (c)<='Z'?(c)+32:(c))
/* Case-insensitive match that ignores spaces: "longblade" names "Long blade". */
static int same_name(const char *a,const char *b)
{
    for(;;){
        while(*a==' ')a++;
        while(*b==' ')b++;
        if(!*a || !*b)return !*a && !*b;
        if(LOWER(*a)!=LOWER(*b))return 0;
        a++;b++;
    }
}
static int catalogue_find(const char *value,int kind)
{
    int i,n=kind==0?aw_race_count:kind==1?aw_class_count:kind==2?aw_birth_count:kind==3?8:27;
    for(i=0;i<n;i++){
        const char *id=kind==0?aw_races[i].id:kind==1?aw_classes[i].id:kind==2?aw_births[i].id:NULL;
        const char *label=kind==0?aw_races[i].name:kind==1?aw_classes[i].name:kind==2?aw_births[i].name:kind==3?attributes[i]:skills[i];
        if((id && same_name(id,value)) || same_name(label,value))return i;
    }
    return -1;
}
/* One field of a scripted character (aw_quickchar_set, aw_quickchar.c): race, class,
 * birthsign and sex rebuild the stats with the ordinary builder (so set them first);
 * attribute NAME N, skill NAME N and level N then override single values. 1 when set. */
int AW_CharacterSet(aw_character_t *c,const char *field,const char *value,const char *number)
{
    int i,n=0;aw_character_t trial;
    if(!c || !field || !value || !AW_CharacterLoad())return 0;
    trial=*c;
    if(!Q_strcasecmp((char *)field,"race") || !Q_strcasecmp((char *)field,"class") ||
       !Q_strcasecmp((char *)field,"birthsign") || !Q_strcasecmp((char *)field,"birth")){
        int kind=!Q_strcasecmp((char *)field,"race")?0:!Q_strcasecmp((char *)field,"class")?1:2;
        if((i=catalogue_find(value,kind))<0)return 0;
        if(kind==0){trial.race=i;trial.head=part_next(-1,i,trial.female,0,1);trial.hair=part_next(-1,i,trial.female,1,1);}
        else if(kind==1)trial.clas=i;else trial.birth=i;
    }else if(!Q_strcasecmp((char *)field,"sex")){
        if(Q_strcasecmp((char *)value,"m") && Q_strcasecmp((char *)value,"f"))return 0;
        trial.female=LOWER(value[0])=='f';
        trial.head=part_next(-1,trial.race,trial.female,0,1);trial.hair=part_next(-1,trial.race,trial.female,1,1);
    }else if(!Q_strcasecmp((char *)field,"level")){
        n=Q_atoi((char *)value);if(n<1 || n>100)return 0;
        c->level=n;return 1;
    }else if(!Q_strcasecmp((char *)field,"attribute") || !Q_strcasecmp((char *)field,"skill")){
        int kind=!Q_strcasecmp((char *)field,"attribute")?3:4;
        if(!number || (i=catalogue_find(value,kind))<0)return 0;
        n=Q_atoi((char *)number);if(n<0 || n>255)return 0;
        if(kind==3){c->attributes[i]=(short)(n-c->modifiers[i]);c->current[0]=c->maximum[0]=(c->attributes[0]+c->attributes[5])*.5f;}
        else c->skills[i]=(short)n;
        return 1;
    }else return 0;
    if(!AW_CharacterRebuild(&trial))return 0;
    *c=trial;return 1;
}

int AW_CharacterOpen(int kind){return AW_CharacterOpenQuick(kind,1);}
int AW_CharacterOpenQuick(int kind,int confirm)
{
    skip_confirm=0;
    if(kind<1 || kind>4 || !AW_CharacterLoad() || !aw_character.valid)return 0;
    skip_confirm=!confirm;
    choice=aw_character;menu=kind;row=page=accepted=review_return=mouse_visible=confirming=stats_open=0;rotation=0;class_top=0;
    mouse_x=100;mouse_y=kind==1?48:176;
    IN_AWClearButtons();
    if(kind==1 && !AW_HeadLoad(choice.head,choice.hair)){menu=0;return 0;}
    if(kind==3)sign_spells(choice.birth);
    class_way=0;quiz_free();
    if(kind==2 && quiz_available<0){quiz_load();quiz_free();}  /* whether the build has the questions */
    custom_slot();
    return 1;
}
int AW_CharacterActive(void){return menu!=0;}
void AW_CharacterClose(void){quiz_free();class_way=0;menu=confirming=accepted=review_return=skip_confirm=stats_open=0;AW_HeadClear();IN_AWClearButtons();}
int AW_CharacterDone(void){int result=accepted;accepted=0;return result;}

static void change(int direction)
{
    if(menu==1){
        if(row==0)choice.race=(choice.race+direction+aw_race_count)%aw_race_count;
        if(row==1)choice.female=1-choice.female;
        if(row<2){choice.head=part_next(-1,choice.race,choice.female,0,1);choice.hair=part_next(-1,choice.race,choice.female,1,1);}
        if(row==2)choice.head=part_next(choice.head,choice.race,choice.female,0,direction);
        if(row==3)choice.hair=part_next(choice.hair,choice.race,choice.female,1,direction);
        if(row<4 && !AW_HeadLoad(choice.head,choice.hair))Con_Printf("Head preview missing or invalid.\n");
    }else if(menu==2)choice.clas=(choice.clas+direction+aw_class_count)%aw_class_count;
    else if(menu==3){choice.birth=(choice.birth+direction+aw_birth_count)%aw_birth_count;sign_spells(choice.birth);}
    else page=(page+direction+5)%5;
    AW_CharacterRebuild(&choice);
}
void AW_CharacterMouse(int dx,int dy)
{
    if(!menu || (!dx && !dy))return;
    mouse_visible=1;mouse_x+=dx;mouse_y+=dy;
    if(mouse_x<0)mouse_x=0;
    if(mouse_x>319)mouse_x=319;
    if(mouse_y<0)mouse_y=0;
    if(mouse_y>199)mouse_y=199;
    if(confirming){if(mouse_y>=143 && mouse_y<166)confirm_yes=mouse_x>=160;return;}
    if(stats_open)return;
    if(menu==2 && class_way==1){
        if(mouse_x>=12 && mouse_x<308 && mouse_y>=92 && mouse_y<92+3*24)quiz_answer=(mouse_y-92)/24;
        return;
    }
    if(menu==2 && class_way==2)return;
    if(menu==1 && mouse_x<198 && mouse_y>=38 && mouse_y<126)row=(mouse_y-38)/22;
    if(menu==1 && over_stats())row=STATS_ROW;
    if(AW_UIMode()==2?over_ok():mouse_y>=166)row=4;
}
int AW_CharacterKey(int key)
{
    if(!menu || key_dest!=key_game)return 0;
    if(confirming){
        if(key==K_ESCAPE || key=='n' || key=='N'){confirming=0;return 1;}
        if(key==K_LEFTARROW || key==K_RIGHTARROW || key==K_TAB)confirm_yes=!confirm_yes;
        if(key==K_MOUSE1 && (mouse_y<143 || mouse_y>=166 || mouse_x<44 || mouse_x>=276))return 1;
        if(key=='y' || key=='Y')confirm_yes=1;
        if(key==K_ENTER || key==K_MOUSE1 || key=='y' || key=='Y'){
            confirming=0;
            if(confirm_yes){aw_character=choice;accepted=menu;menu=0;AW_HeadClear();IN_AWClearButtons();apply_eye();}
        }
        return 1;
    }
    if(stats_open){
        /* the race's stats box: Enter, Escape, V or a click closes it (back on the button) */
        if(key==K_ENTER || key==K_ESCAPE || key==K_MOUSE1 || key=='v' || key=='V'){stats_open=0;row=STATS_ROW;}
        return 1;
    }
    if(menu==1 && (key=='v' || key=='V' || (key==K_MOUSE1 && over_stats()) || (key==K_ENTER && row==STATS_ROW))){
        stats_open=1;row=STATS_ROW;return 1;
    }
    if(menu==2 && class_way){
        int up=key==K_UPARROW || key=='w' || key=='W',down=key==K_DOWNARROW || key=='s' || key=='S' || key==K_TAB;
        int left=key==K_LEFTARROW || key=='a' || key=='A',right=key==K_RIGHTARROW || key=='d' || key=='D';
        if(key==K_ESCAPE){quiz_free();class_way=0;return 1;}   /* back to the list, nothing changed */
        if(class_way==1){
            if(key==K_MOUSE1){
                if(mouse_x<12 || mouse_x>=308 || mouse_y<92 || mouse_y>=92+3*24)return 1;
                quiz_answer=(mouse_y-92)/24;key=K_ENTER;
            }
            if(key>='1' && key<='3'){quiz_answer=key-'1';key=K_ENTER;}
            if(up)quiz_answer=(quiz_answer+2)%3;
            if(down)quiz_answer=(quiz_answer+1)%3;
            if(key==K_ENTER){
                /* the first answer counts toward combat, the second magic, the third stealth */
                quiz_counts[quiz_answer]++;quiz_at++;quiz_answer=0;
                if(quiz_at>=10){
                    int pick=quiz_class(quiz_counts[0],quiz_counts[1],quiz_counts[2]);
                    if(pick>=0){choice.clas=pick;AW_CharacterRebuild(&choice);}
                    quiz_free();class_way=0;
                }
            }
            return 1;
        }
        if(key==K_MOUSE1){
            if(AW_UIMode()==2 && over_ok()){custom_row=CUSTOM_ROWS-1;key=K_ENTER;}
            else if(mouse_y>=34 && mouse_y<34+(CUSTOM_ROWS-1)*9 && mouse_x>=12 && mouse_x<308){
                custom_row=(mouse_y-34)/9;
                if(mouse_x>=116 && mouse_x<132)custom_change(-1);
                else if(mouse_x>=290)custom_change(1);
                return 1;
            }else return 1;
        }
        if(up)custom_row=(custom_row+CUSTOM_ROWS-1)%CUSTOM_ROWS;
        if(down)custom_row=(custom_row+1)%CUSTOM_ROWS;
        if(left || right)custom_change(left?-1:1);
        if(key==K_ENTER){
            if(custom_row<CUSTOM_ROWS-1){custom_row++;return 1;}
            {int made=AW_CharacterCustomDefine(&custom);
            if(made>=0){choice.clas=made;AW_CharacterRebuild(&choice);class_way=0;}}
        }
        return 1;
    }
    if(menu==2 && (key=='q' || key=='Q' || (key==K_MOUSE1 && mouse_y>=QWAY_Y && mouse_y<QWAY_Y+QWAY_H && mouse_x>=128 && mouse_x<216))){
        if(quiz_load()){class_way=1;quiz_at=quiz_answer=0;quiz_counts[0]=quiz_counts[1]=quiz_counts[2]=0;}
        return 1;
    }
    if(menu==2 && (key=='m' || key=='M' || (key==K_MOUSE1 && mouse_y>=QWAY_Y && mouse_y<QWAY_Y+QWAY_H && mouse_x>=220 && mouse_x<308))){
        if(aw_class_count<32)custom_start();
        return 1;
    }
    if(key==K_ESCAPE)return 0; /* Pause menu, retaining the unfinished choice. */
    if(key=='a' || key=='A')key=K_LEFTARROW;
    if(key=='d' || key=='D')key=K_RIGHTARROW;
    if(key=='w' || key=='W')key=K_UPARROW;
    if(key=='s' || key=='S')key=K_DOWNARROW;
    if(key==K_MOUSE1){
        if(menu==1 && mouse_x<198 && mouse_y>=38 && mouse_y<126){
            row=(mouse_y-38)/22;
            if(mouse_x>=12 && mouse_x<=33)change(-1);
            else if(mouse_x>=171 && mouse_x<=193)change(1);
            return 1;
        }
        if(AW_UIMode()==2 && over_ok()){row=4;key=K_ENTER;}
        else if(AW_UIMode()==2 && mouse_y>=166)return 1;
        else if(AW_UIMode()!=2 && mouse_y>=166 && mouse_y<187){if(menu==1)row=4;key=K_ENTER;}
        else if(menu==1 && mouse_x>=200){rotation+=.4f;return 1;}
        else if(menu==1)return 1;
        else if(menu==2 || menu==3){
            int pick=over_class_row();
            if(pick>=0){if(menu==2)choice.clas=pick;else {choice.birth=pick;sign_spells(pick);}AW_CharacterRebuild(&choice);}
            return 1;
        }
        else {change(mouse_x<100?-1:1);return 1;}
    }
    if(menu==4 && (key=='r' || key=='c' || key=='b')){
        review_return=1;menu=key=='r'?1:key=='c'?2:3;row=0;
        mouse_visible=0;mouse_x=100;mouse_y=menu==1?48:176;
        if(menu==1)AW_HeadLoad(choice.head,choice.hair);
        if(menu==3)sign_spells(choice.birth);
        return 1;
    }
    if(key==K_LEFTARROW || key==K_RIGHTARROW)change(key==K_LEFTARROW?-1:1);
    if(key=='[')rotation-=.2f;
    if(key==']')rotation+=.2f;
    if(key==K_UPARROW || key==K_DOWNARROW || key==K_TAB){
        if(menu==1){
            /* Race, Sex, Face, Hair, View Stats, OK, then round again */
            static const unsigned char order[6]={0,1,2,3,STATS_ROW,4};
            int at=0;
            while(at<5 && order[at]!=row)at++;
            row=order[(at+(key==K_UPARROW?5:1))%6];
        }
        else if(AW_UIMode()==2 && key==K_TAB)row=row==4?0:4;
        else {row=0;change(key==K_UPARROW?-1:1);}
    }
    if(key==K_ENTER){
        if(menu==1 && row<4){row++;return 1;}
        if(!AW_CharacterRebuild(&choice))return 1;
        if(review_return){menu=4;review_return=0;page=0;return 1;}
        if(skip_confirm){aw_character=choice;accepted=menu;menu=0;skip_confirm=0;AW_HeadClear();IN_AWClearButtons();apply_eye();return 1;}
        confirming=1;confirm_yes=1;mouse_visible=0;mouse_x=220;mouse_y=154;return 1;
    }
    return 1;
}
void AW_CharacterDraw(void)
{
    int i,j,y,index,gold,muted;char line[160];
    if(!menu || key_dest!=key_game)return;
    /* All head/race/class/review pages and confirmations share blackout. */
    if(AW_ModalBlackBackground())
        AW_UIFill(0,0,vid.width,vid.height,AW_UIColor(0,0,0));
    scr_copyeverything=1;
    gold=AW_UIColor(223,199,144);muted=AW_UIColor(120,109,87);
    AW_UIBox(2,2,316,196);
    if(menu==4)sprintf(line,"Review your character (page %ld/5)",(long)page+1);
    if(menu==2 && class_way==1)sprintf(line,"Class questions (%ld/10)",(long)quiz_at+1);
    if(menu==2 && class_way==2)strcpy(line,"Make your own class");
    AW_UITextBox(10,8,300,20,menu==1?"Choose your appearance":menu==2 && !class_way?"Choose your class":menu==3?"Choose your birthsign":line,gold);
    if(menu==1){
        const char *labels[]={"Race","Sex","Face","Hair"};
        for(i=0;i<4;i++){
            if(i==0)sprintf(line,"%s",aw_races[choice.race].name);
            else if(i==1)sprintf(line,"%s",choice.female?"Female":"Male");
            else {
                int n=0,selected=0;
                for(index=0;index<aw_part_count;index++)if(part_valid(index,&choice,i-2)){
                    n++;
                    if(index==(i==2?choice.head:choice.hair))selected=n;
                }
                sprintf(line,"%s: %ld / %ld",labels[i],(long)selected,(long)n);
            }
            y=38+i*22;
            if(row==i)AW_UIFill(9,y,186,21,AW_UIColor(54,47,32));
            for(j=0;j<=6;j++){
                AW_UIFill(16+j,y+10-j,1,j*2+1,gold);
                AW_UIFill(188-j,y+10-j,1,j*2+1,gold);
            }
            AW_UITextBox(34,y,136,21,line,gold);
        }
        AW_UIBox(STATS_X,STATS_Y,STATS_W,STATS_H);
        if(row==STATS_ROW || (mouse_visible && over_stats()))
            AW_UIFill(STATS_X+3,STATS_Y+3,STATS_W-6,STATS_H-6,AW_UIColor(54,47,32));
        AW_UISmallBegin();
        AW_UITextBox(STATS_X,STATS_Y,STATS_W,STATS_H,"View Stats",gold);
        AW_UITextBox(STATS_X+STATS_W+4,STATS_Y,195-STATS_X-STATS_W-4,STATS_H,"Arrows: choose",muted);
        AW_UISmallEnd();
        rotation+=host_frametime*.35f;AW_HeadDraw(201,34,108,122,rotation);
    }else if(menu==2 && class_way==1 && quiz){
        /* CHARGEN-CENSUS-57 (c): one question, its three answers; Enter, 1-3 or a click answers */
        AW_UISmallBegin();
        wrap(12,34,296,11,5,quiz+quiz_offsets[quiz_at][0],gold);
        for(i=0;i<3;i++){
            y=92+i*24;
            AW_UIBox(12,y,296,22);
            if(i==quiz_answer)AW_UIFill(15,y+3,290,16,AW_UIColor(54,47,32));
            wrap(16,y+1,288,10,2,quiz+quiz_offsets[quiz_at][i+1],gold);
        }
        AW_UISmallEnd();
    }else if(menu==2 && class_way==2){
        /* CHARGEN-CENSUS-57 (c): the own class: specialization, two favored attributes, five major and five minor
         * skills, all different; arrows change the marked row, Enter goes on, OK makes the class */
        AW_UISmallBegin();
        for(i=0;i<CUSTOM_ROWS-1;i++){
            const char *label=i==0?"Specialization":i<3?"Favored attribute":i<8?"Major skill":"Minor skill";
            const char *value=i==0?specializations[custom.special]:i<3?attributes[custom.attributes[i-1]]:
                skills[custom.skills[custom_skill(i)]];
            y=34+i*9;
            if(i==custom_row)AW_UIFill(12,y,296,9,AW_UIColor(54,47,32));
            AW_UITextBox(12,y,100,9,label,muted);
            AW_UITextBox(116,y,16,9,"<",gold);
            AW_UITextBox(134,y,154,9,value,gold);
            AW_UITextBox(290,y,16,9,">",gold);
        }
        AW_UITextBox(12,34+13*9,296,11,"Arrows: change  Enter: next  Esc: back",muted);
        AW_UISmallEnd();
    }else if(menu==2 || menu==3){
        const aw_class_t *k=&aw_classes[choice.clas];
        int selected=menu==2?choice.clas:choice.birth,count=list_count();
        if(selected<class_top)class_top=selected;
        if(selected>=class_top+CLASS_ROWS)class_top=selected-CLASS_ROWS+1;
        AW_UISmallBegin();
        for(i=0;i<CLASS_ROWS && class_top+i<count;i++){
            y=CLASS_Y+i*CLASS_H;
            if(class_top+i==selected)AW_UIFill(CLASS_X,y,CLASS_W,CLASS_H-1,AW_UIColor(54,47,32));
            AW_UITextBox(CLASS_X,y,CLASS_W,CLASS_H,menu==2?aw_classes[class_top+i].name:aw_births[class_top+i].name,gold);
        }
        if(class_top)AW_UITextBox(CLASS_X,CLASS_Y-9,CLASS_W,8,"more above",muted);
        if(class_top+CLASS_ROWS<count)AW_UITextBox(CLASS_X,CLASS_Y+CLASS_ROWS*CLASS_H,CLASS_W,8,"more below",muted);
        if(menu==3){
            static const char *kinds[]={"Spell","Ability","Power"};
            sign_spells(choice.birth); /* already loaded when the page opened or changed: no file read here */
            AW_BirthArt(choice.birth,212,34);
            for(i=0;i<sign_spell_count;i++){
                int kind=sign_kind[i]==0?0:sign_kind[i]==1?1:sign_kind[i]==5?2:-1;
                if(kind>=0)AW_UITextBox(126,34+i*22,84,10,kinds[kind],muted);
                AW_UITextBox(126,44+i*22,84,11,sign_spell[i],gold);
            }
            if(!sign_spell_count)AW_UITextBox(126,34,84,11,"none",gold);
            AW_UISmallEnd();
        }else{
        sprintf(line,"Specialization: %s",specializations[k->special]);
        AW_UITextBox(128,34,180,11,line,gold);
        sprintf(line,"Favored: %s, %s",attributes[k->attributes[0]],attributes[k->attributes[1]]);
        AW_UITextBox(128,46,180,11,line,gold);
        AW_UITextBox(128,60,88,11,"Major skills",muted);
        AW_UITextBox(220,60,88,11,"Minor skills",muted);
        for(i=0;i<5;i++){
            AW_UITextBox(128,72+i*11,88,11,skills[k->skills[i*2+1]],gold);
            AW_UITextBox(220,72+i*11,88,11,skills[k->skills[i*2]],gold);
        }
        if(choice.clas>=aw_class_count)AW_UITextBox(CLASS_X,156,CLASS_W,9,"Custom class",gold);
        /* the other two ways: the questions (when the build has them) and the own class */
        AW_UIBox(128,QWAY_Y,88,QWAY_H);AW_UIBox(220,QWAY_Y,88,QWAY_H);
        AW_UITextBox(128,QWAY_Y,88,QWAY_H,"Questions (Q)",quiz_available>0?gold:muted);
        AW_UITextBox(220,QWAY_Y,88,QWAY_H,"Make own (M)",aw_class_count<32?gold:muted);
        /* the muted colour alone recolours only a glyph's brightest shade, so an unusable button read as usable
         * (CHARGEN-BIRTHSIGN-REVIEW-58: an image built without Morrowind.ini has no questions): grey it out */
        if(quiz_available<=0)greyed(128,QWAY_Y,88,QWAY_H);
        if(aw_class_count>=32)greyed(220,QWAY_Y,88,QWAY_H);
        AW_UISmallEnd();
        }
    }else{
        /* CHARGEN-CENSUS-57 (a): the review sheet as the original's (OpenMW 0.51 mwgui/review.cpp): name, level,
         * race, class and sign, the attributes, health/magicka/fatigue (AW_CharacterRebuild), then the skills
         * grouped major, minor and miscellaneous. Page 0 attributes; 1 major; 2 minor; 3-4 miscellaneous. */
        byte order[37];int n=0,first=0,count=8,rows=page?5:4;
        const aw_class_t *k=&aw_classes[choice.clas];
        for(i=0;i<5;i++)order[n++]=k->skills[i*2+1];
        for(i=0;i<5;i++)order[n++]=k->skills[i*2];
        for(i=0;i<27;i++){for(j=0;j<10 && k->skills[j]!=i;j++);if(j==10)order[n++]=(byte)i;}
        if(page==1){first=0;count=5;}
        else if(page==2){first=5;count=5;}
        else if(page==3){first=10;count=10;}
        else if(page==4){first=20;count=n-20>10?10:n-20;}
        if(!page){
            /* no name yet (a review opened before any name page): never a bare ", level 1" */
            if(aw_story.name[0])sprintf(line,"%s, level %ld",aw_story.name,(long)choice.level);
            else sprintf(line,"Level %ld",(long)choice.level);
            AW_UITextBox(12,31,296,20,line,gold);
        }else AW_UITextBox(12,31,296,20,page==1?"Major skills":page==2?"Minor skills":"Miscellaneous skills",muted);
        for(i=0;i<count;i++){
            if(!page)sprintf(line,"%s: %ld",attributes[i],(long)(choice.attributes[i]+choice.modifiers[i]));
            else sprintf(line,"%s: %ld",skills[order[first+i]],(long)choice.skills[order[first+i]]);
            AW_UITextBox(12+(i/rows)*148,53+(i%rows)*17,144,17,line,gold);
        }
        AW_UISmallBegin();
        if(!page){
            sprintf(line,"%s  %s  %s",aw_races[choice.race].name,k->name,aw_births[choice.birth].name);
            AW_UITextBox(12,124,296,11,line,gold);
            sprintf(line,"Health %ld  Magicka %ld  Fatigue %ld",(long)choice.maximum[0],(long)choice.maximum[1],(long)choice.maximum[2]);
            AW_UITextBox(12,136,296,11,line,gold);
        }
        AW_UITextBox(12,152,296,11,"R: race  C: class  B: birthsign",muted);
        AW_UISmallEnd();
    }
    if(AW_UIMode()==2){
        AW_UISmallBegin();
        AW_UITextBox(10,166,230,22,menu==4?"Arrows: pages  Enter: OK":menu==1?"Enter: next/OK  LMB: rotate":"Arrows: choose  Enter: OK",gold);
        AW_UISmallEnd();
        AW_UIBox(OK_X,OK_Y,OK_W,OK_H);
        if(row==4 || (mouse_visible && over_ok()))
            AW_UIFill(OK_X+3,OK_Y+3,OK_W-6,OK_H-6,AW_UIColor(54,47,32));
        AW_UITextBox(OK_X,OK_Y,OK_W,OK_H,"OK",gold);
    }else {
    AW_UITextBox(10,166,300,22,menu==4?"Enter: accept  Arrows/WASD: pages":menu==1?"Enter: next / accept   LMB: rotate":"Arrows/WASD: Choose  Enter: accept",gold);
    }
    if(stats_open && menu==1){
        /* RACE-STATS-57: base attributes (the chosen sex), skill bonuses and specials of the race */
        const aw_race_t *r=&aw_races[choice.race];int n=0;
        AW_UIBox(8,26,304,170);
        sprintf(line,"%s - %s",r->name,choice.female?"Female":"Male");
        AW_UITextBox(14,30,292,18,line,gold);
        AW_UISmallBegin();
        AW_UITextBox(16,49,136,11,"Attributes",muted);
        for(i=0;i<8;i++){
            sprintf(line,"%s %ld",attributes[i],(long)r->attributes[i*2+choice.female]);
            AW_UITextBox(16,61+i*11,136,11,line,gold);
        }
        AW_UITextBox(160,49,144,11,"Skill bonus",muted);
        for(i=0;i<27 && n<7;i++)if(r->skills[i]){
            sprintf(line,"%s +%ld",skills[i],(long)r->skills[i]);
            AW_UITextBox(160,61+n*11,144,11,line,gold);n++;
        }
        if(!n)AW_UITextBox(160,61,144,11,"none",gold);
        AW_UITextBox(160,61+7*11,144,11,"Specials",muted);
        for(i=0;i<r->power_count && i<3;i++){
            /* the catalogue holds the spells' IDs ("resist magicka_25", "orc_beserk"): shown with spaces, as the small
             * font has no underscore or percent sign (the spells' own names are not in the catalogue yet) */
            const char *s=r->powers[i];int k=0;
            while(*s && k<(int)sizeof(line)-1){if(*s!='%')line[k++]=*s=='_'?' ':*s;s++;}
            line[k]=0;
            AW_UITextBox(160,72+7*11+i*11,144,11,line,gold);
        }
        if(!r->power_count)AW_UITextBox(160,72+7*11,144,11,"none",gold);
        AW_UISmallEnd();
    }
    if(confirming){
        AW_UIBox(16,48,288,126);AW_UISmallBegin();
        AW_UITextBox(24,53,272,20,"Really choose this character?",gold);
        sprintf(line,"%s - %s",aw_races[choice.race].name,choice.female?"Female":"Male");
        AW_UITextBox(24,75,272,18,line,gold);
        if(menu==1){
            int faces=0,hairs=0;
            for(i=0;i<=choice.head;i++)if(part_valid(i,&choice,0))faces++;
            for(i=0;i<=choice.hair;i++)if(part_valid(i,&choice,1))hairs++;
            sprintf(line,"Face %ld / Hair %ld",(long)faces,(long)hairs);
            AW_UITextBox(24,96,272,18,line,gold);
        }else{
            AW_UITextBox(24,96,272,18,aw_classes[choice.clas].name,gold);
            /* Class comes before birthsign in the original registration flow.
             * The default table index is not a choice the player has made. */
            if(menu==3 || menu==4)
                AW_UITextBox(24,117,272,18,aw_births[choice.birth].name,gold);
        }
        if(AW_UIMode()==2){
            AW_UIBox(44,143,112,23);AW_UIBox(164,143,112,23);
            AW_UIFill((confirm_yes?164:44)+3,146,106,17,AW_UIColor(54,47,32));
        }else AW_UIFill(confirm_yes?164:44,143,112,23,AW_UIColor(54,47,32));
        AW_UITextBox(44,143,112,23,"Go back",gold);
        AW_UITextBox(164,143,112,23,"Choose",gold);AW_UISmallEnd();
    }
    if(mouse_visible && !AW_UICursor(mouse_x,mouse_y)){AW_UIFill(mouse_x,mouse_y,2,6,gold);AW_UIFill(mouse_x,mouse_y,6,2,gold);}
}
