/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
server_t sv;server_static_t svs;
#include "aw_save.h"
#include "aw_maps.h"
#include <assert.h>
#include <stdint.h>
#include "aw_clock.h"
keydest_t key_dest=key_game;
void IN_AWClearButtons(void){}
viddef_t vid;int scr_copyeverything;double host_frametime=.02;
static byte frame[340*207+2];
static float head_angle;static int black_background=1,ui_mode=1,ok_drawn,ok_focused;
int AW_UIMode(void){return ui_mode;}
int AW_ModalBlackBackground(void){return black_background;}
void AW_HeadDraw(int x,int y,int w,int h,float angle){head_angle=angle;}
int AW_UIColor(int r,int g,int b){return r==0 && g==0 && b==0?0:1;}
void AW_UIFill(int x,int y,int w,int h,int color){
    int row;if(x==251 && y==169 && w==54 && h==16)ok_focused++;assert(x>=0 && y>=0 && x+w<=vid.width && y+h<=vid.height);
    for(row=y;row<y+h;row++)memset(vid.buffer+row*vid.rowbytes+x,color,w);
}
void AW_UIBox(int x,int y,int w,int h){}
void AW_UITextBox(int x,int y,int w,int h,const char *s,int color){if(!strcmp(s,"OK")){assert(x==248 && y==166 && w==60 && h==22);ok_drawn++;}}
void AW_UISmallBegin(void){}void AW_UISmallEnd(void){}
void AW_BirthArt(int index,int x,int y){}
static void draw_covered(void){
    int x,y;memset(frame,0x5a,sizeof(frame));scr_copyeverything=0;
    AW_CharacterDraw();assert(scr_copyeverything && frame[0]==0x5a && frame[sizeof(frame)-1]==0x5a);
    for(y=0;y<vid.height;y++)for(x=0;x<vid.rowbytes;x++){
        byte value=vid.buffer[y*vid.rowbytes+x];
        if(x>=vid.width)assert(value==0x5a);
        else if(x<2 || x>=318 || y<2 || y>=198)assert(value==0);
        else assert(value!=0x5a);
    }
    /* Switchback restores the original exposed background around the panel. */
    black_background=0;memset(frame,0x5a,sizeof(frame));AW_CharacterDraw();
    assert(vid.buffer[0]==0x5a && vid.buffer[(vid.height-1)*vid.rowbytes]==0x5a);
    black_background=1;
}
void AW_HeadClear(void){}
int AW_HeadLoad(int a,int b){return 1;}
void Con_Printf(char *s,...){}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
int COM_FOpenFile(char *s,FILE **f){*f=NULL;return -1;}
static void legacy_header(byte *raw,int size,int version)
{
    uint32_t crc=0xffffffffU;int i,j;
    memcpy(raw,"AWS1",4);raw[3]=(byte)version;
    for(i=12;i<size;i++){crc^=raw[i];for(j=0;j<8;j++)crc=(crc>>1)^((crc&1)?0xedb88320U:0);}
    crc^=0xffffffffU;
    for(i=0;i<4;i++){raw[4+i]=(size>>(8*i))&255;raw[8+i]=(crc>>(8*i))&255;}
}
static void setup(void)
{
    int i;
    aw_race_count=aw_class_count=aw_birth_count=1;aw_part_count=4;
    strcpy(aw_races[0].id,"test race");strcpy(aw_classes[0].id,"test class");strcpy(aw_births[0].id,"test sign");
    for(i=0;i<16;i++)aw_races[0].attributes[i]=40+(i&1)*10;
    aw_races[0].skills[0]=10;aw_classes[0].attributes[0]=0;aw_classes[0].attributes[1]=5;
    for(i=0;i<10;i++)aw_classes[0].skills[i]=i;
    aw_births[0].modifiers[5]=25;aw_races[0].magicka=5;
    for(i=0;i<4;i++){sprintf(aw_parts[i].id,"part%d",i);aw_parts[i].race=0;aw_parts[i].female=i/2;aw_parts[i].kind=i%2;}
}
int main(void)
{
    aw_character_t c;aw_save_t source,decoded,unchanged;byte raw[AW_SAVE_BYTES];int n,i;char out[64];
    vid.width=333;vid.height=207;vid.rowbytes=340;vid.buffer=frame+1;
    setup();assert(!AW_CharacterHors());
    strcpy(aw_races[0].id,"Nord");strcpy(aw_classes[0].id,"Barbarian");strcpy(aw_births[0].id,"Charioteer");
    assert(AW_CharacterHors());assert(!strcmp(aw_story.name,"Hors") && aw_character.valid && !aw_character.female);
    assert(aw_story.stage==AW_STAGE_RELEASED && !AW_StoryRestricted() && AW_Ring() && AW_Package());
    assert(AW_StateGet(&aw_state,AW_ITEM,"gold_001")==87 && aw_character.maximum[0]==50);
    /* A direct start's ready-made character (tools/direct_start.py --quick-character):
     * catalogue IDs (any case), sex and name; the opening is done, so saving is allowed
     * once the player walks (AW_SaveAllowed: released stage, valid character). */
    assert(!AW_CharacterPreset("Nord","Barbarian","Charioteer",0,""));
    assert(!AW_CharacterPreset("Dremora","Barbarian","Charioteer",0,"X"));
    assert(!AW_CharacterPreset("Nord","Barbarian","Charioteer",2,"X"));
    assert(!AW_CharacterPreset("Nord","Barbarian","Charioteer",0,"A name far too long for the story buffer"));
    assert(AW_CharacterPreset("nord","BARBARIAN","charioteer",1,"Ilmeni"));
    assert(!strcmp(aw_story.name,"Ilmeni") && aw_character.valid && aw_character.female);
    assert(aw_character.head==2 && aw_character.hair==3);
    assert(aw_story.stage==AW_STAGE_RELEASED && !AW_StoryRestricted() && aw_story.ship_disabled);
    assert(AW_CharacterHors() && !strcmp(aw_story.name,"Hors") && !aw_character.female);
    memset(&c,0,sizeof(c));c.head=0;c.hair=1;
    assert(AW_CharacterRebuild(&c));assert(c.attributes[0]==50 && c.attributes[5]==50);
    assert(c.modifiers[5]==25 && c.maximum[0]==50 && c.maximum[1]==60 && c.maximum[2]==205);
    assert(c.skills[0]==30 && c.skills[1]==35);
    c.female=1;c.head=2;c.hair=3;assert(AW_CharacterRebuild(&c));assert(c.maximum[0]==60);
    c.head=0;assert(!AW_CharacterRebuild(&c));c.head=2;
    aw_character=c;assert(AW_CharacterOpen(1));AW_CharacterMouse(0,0);
    draw_covered();assert(head_angle>0);{float before=head_angle;draw_covered();assert(head_angle>before);}
    for(i=0;i<5;i++)AW_CharacterKey(K_ENTER);
    draw_covered();
    assert(AW_CharacterActive() && !AW_CharacterDone());
    AW_CharacterKey('n');assert(AW_CharacterActive() && !AW_CharacterDone());
    AW_CharacterKey(K_ENTER);AW_CharacterKey('y');
    assert(!AW_CharacterActive() && AW_CharacterDone()==1);
    assert(AW_CharacterOpen(4));
    for(i=0;i<5;i++){draw_covered();AW_CharacterKey(K_RIGHTARROW);}
    AW_CharacterKey(K_ENTER);draw_covered();assert(AW_CharacterActive() && !AW_CharacterDone());
    AW_CharacterKey(K_ESCAPE);assert(AW_CharacterActive() && !AW_CharacterDone());
    AW_CharacterKey(K_ENTER);AW_CharacterKey(K_LEFTARROW);AW_CharacterKey(K_ENTER);
    assert(AW_CharacterActive() && !AW_CharacterDone());
    AW_CharacterKey(K_ENTER);AW_CharacterKey(K_ENTER);
    assert(!AW_CharacterActive() && AW_CharacterDone()==4 && !AW_CharacterDone());
    for(i=1;i<=3;i++){
        int presses;assert(AW_CharacterOpen(i));draw_covered();
        for(presses=0;presses<(i==1?5:1);presses++)AW_CharacterKey(K_ENTER);
        assert(AW_CharacterActive());draw_covered();AW_CharacterKey(K_ENTER);
        assert(!AW_CharacterActive() && AW_CharacterDone()==i);
    }
    /* Birthsign arrows and WASD cycle values; pointer motion cannot consume keys. */
    aw_birth_count=3;aw_births[1]=aw_births[0];aw_births[2]=aw_births[0];
    aw_character.birth=0;assert(AW_CharacterOpen(3));
    AW_CharacterKey(K_RIGHTARROW);AW_CharacterMouse(7,0);
    AW_CharacterKey(K_ENTER);AW_CharacterKey(K_ENTER);assert(aw_character.birth==1);
    assert(AW_CharacterOpen(3));AW_CharacterKey(K_LEFTARROW);
    AW_CharacterKey(K_ENTER);AW_CharacterKey(K_ENTER);assert(aw_character.birth==0);
    assert(AW_CharacterOpen(3));AW_CharacterKey('d');
    AW_CharacterKey(K_ENTER);AW_CharacterKey(K_ENTER);assert(aw_character.birth==1);
    assert(AW_CharacterOpen(3));AW_CharacterKey('a');
    AW_CharacterKey(K_ENTER);AW_CharacterKey(K_ENTER);assert(aw_character.birth==0);
    /* Click the right Sex arrow, then Choose; no keyboard row assumptions. */
    aw_character.female=0;aw_character.head=0;aw_character.hair=1;
    assert(AW_CharacterOpen(1));AW_CharacterMouse(85,22);AW_CharacterKey(K_MOUSE1);
    AW_CharacterMouse(-85,106);AW_CharacterKey(K_MOUSE1);AW_CharacterKey(K_ENTER);
    assert(aw_character.female==1 && !AW_CharacterActive());
    /* V1 above retains its broad footer. V2 adds an exact visible hit box. */
    ui_mode=2;
    for(i=1;i<=4;i++){
        assert(AW_CharacterOpen(i));ok_drawn=0;draw_covered();assert(ok_drawn);
        /* Footer hints are not an invisible accept button in V2. */
        AW_CharacterMouse(0,i==1?128:0);AW_CharacterKey(K_MOUSE1);
        assert(AW_CharacterActive() && !AW_CharacterDone());
        AW_CharacterMouse(160,0);AW_CharacterKey(K_MOUSE1);
        assert(AW_CharacterActive() && !AW_CharacterDone()); /* Confirmation, not a bypass. */
        AW_CharacterKey(K_ENTER);assert(!AW_CharacterActive() && AW_CharacterDone()==i);
    }
    assert(AW_CharacterOpen(1));
    for(i=0;i<4;i++)AW_CharacterKey(K_ENTER);
    ok_focused=0;draw_covered();assert(ok_focused && AW_CharacterActive());
    AW_CharacterKey(K_ENTER);AW_CharacterKey('n');assert(AW_CharacterActive());
    AW_CharacterKey(K_ENTER);AW_CharacterKey(K_ENTER);assert(AW_CharacterDone()==1);
    /* Mouse right/bottom borders are exclusive; only the visible OK accepts. */
    assert(AW_CharacterOpen(2));AW_CharacterMouse(208,0);AW_CharacterKey(K_MOUSE1);
    AW_CharacterMouse(-1,12);AW_CharacterKey(K_MOUSE1);
    assert(AW_CharacterActive() && !AW_CharacterDone());
    AW_CharacterMouse(0,-1);AW_CharacterKey(K_MOUSE1);AW_CharacterKey(K_ENTER);
    assert(AW_CharacterDone()==2);
    /* Review's subedit returns to review, with no premature final acceptance. */
    assert(AW_CharacterOpen(4));AW_CharacterKey('r');
    AW_CharacterMouse(160,128);AW_CharacterKey(K_MOUSE1);
    assert(AW_CharacterActive() && !AW_CharacterDone());
    AW_CharacterKey(K_ENTER);AW_CharacterKey(K_ENTER);assert(AW_CharacterDone()==4);
    /* Switching back uses the original footer without losing selection. */
    assert(AW_CharacterOpen(1));ui_mode=1;ok_drawn=0;draw_covered();assert(!ok_drawn);
    AW_CharacterMouse(0,128);AW_CharacterKey(K_MOUSE1);AW_CharacterKey(K_ENTER);
    assert(AW_CharacterDone()==1);
    AW_StoryReset(1);assert(AW_StoryRestricted());assert(!AW_StoryTransition(AW_STAGE_OFFICE));
    assert(AW_CourtyardRingAvailable() && AW_CourtyardTakeRing());
    assert(AW_Ring()==1 && !AW_CourtyardTakeRing());
    assert(AW_ItemAdd(&aw_state,"ring_keley",-1));
    assert(!AW_CourtyardRingAvailable() && !AW_CourtyardTakeRing());
    strcpy(aw_story.name,"%PCName %%n");AW_ExpandPlayerName(out,sizeof(out),"Hello %PCName!");assert(!strcmp(out,"Hello %PCName %%n!"));
    AW_ExpandPlayerName(out,3,"%PCName");assert(!strcmp(out,"%P"));
    assert(AW_StateGet(&aw_state,AW_JOURNAL,"A1_1_FindSpymaster")==0);
    assert(AW_CaptainDuties());assert(AW_StateGet(&aw_state,AW_ITEM,"GOLD_001")==87);
    assert(AW_ItemAdd(&aw_state,"bk_a1_1_caiuspackage",-1));assert(!AW_CaptainDuties());
    assert(AW_StateGet(&aw_state,AW_ITEM,"gold_001")==87); /* Item loss is not quest reset. */
    assert(AW_JournalAdd(&aw_state,"A1_1_FindSpymaster",12));
    assert(AW_JournalAdd(&aw_state,"A1_1_FindSpymaster",1));
    assert(AW_StateTest(&aw_state,AW_JOURNAL,"a1_1_findspymaster",AW_GE,12));
    assert(AW_StateSet(&aw_state,AW_JOURNAL,"a1_1_findspymaster",5)); /* Explicit branch/index update. */
    assert(AW_StateTest(&aw_state,AW_JOURNAL,"a1_1_findspymaster",AW_EQ,5));
    assert(!AW_ItemAdd(&aw_state,"gold_001",-88));
    assert(AW_StateSet(&aw_state,AW_ITEM,"overflow",INT32_MAX));assert(!AW_ItemAdd(&aw_state,"overflow",1));
    memset(&source,0,sizeof(source));source.sequence=3;source.profile=4;
    source.character=c;source.story=aw_story;source.story.stage=AW_STAGE_RELEASED;
    source.story.hall=1;source.story.ship_disabled=1;source.story.captain=-1;
    assert(AW_StateSet(&aw_state,AW_GLOBAL,"CharGenState",-1));assert(AW_ClockEnsure() && AW_ClockAdvance(86400000));
    assert(AW_ClockSetTime(23,59) && AW_ClockAdvance(12345));source.state=aw_state;
    strcpy(source.scene,"seyda");strcpy(source.label,"Manual 1");source.position[0]=12.25;
    n=AW_SaveEncode(raw,sizeof(raw),&source);assert(n>500 && n<2000);
    memset(&decoded,0x5a,sizeof(decoded));unchanged=decoded;
    for(i=0;i<n;i++){assert(!AW_SaveDecode(raw,i,&decoded));assert(!memcmp(&decoded,&unchanged,sizeof(decoded)));}
    assert(AW_SaveDecode(raw,n,&decoded));assert(decoded.state.journal_count==2 && decoded.state.journal[0].stage==1 && decoded.state.journal[1].stage==12);assert(AW_StateGet(&decoded.state,AW_GLOBAL,"amiwind:clock:days")==1);assert(decoded.position[0]==12.25 && decoded.character.maximum[0]==60);
    AW_StateReset();aw_state=decoded.state;
    assert(AW_ClockEnsure() && AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:ms")==86352345);
    assert(AW_ClockAdvance(47655) && AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:days")==2 && AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:ms")==0);
    assert(decoded.story.hall==1 && AW_StateGet(&decoded.state,AW_GLOBAL,"amiwind:ref:172851:ring_taken")==1);
    assert(AW_StateGet(&decoded.state,AW_JOURNAL,"a1_1_findspymaster")==5);
    assert(!AW_StateGet(&decoded.state,AW_ITEM,"bk_a1_1_caiuspackage")); /* Released saves may lack a former quest item. */
    for(i=12;i<n;i++){raw[i]^=1;assert(!AW_SaveDecode(raw,n,&decoded));raw[i]^=1;}
    /* Legacy bytes have indices, no dates; decoding must not invent history. */
    /* AWS4 appends feature/equipment words to this no-harvest sample.
     * Retain explicit AWS2 and AWS1 reader acceptance, with independent CRCs. */
    assert(!memcmp(raw,"AWS4",4));
    i=n-8;legacy_header(raw,i,'2');
    assert(AW_SaveDecode(raw,i,&decoded) && decoded.state.journal_count==2 && !decoded.equipment);
    i-=4+source.state.journal_count*16;legacy_header(raw,i,'1');
    assert(AW_SaveDecode(raw,i,&decoded) && !decoded.state.journal_count);
    assert(AW_StateGet(&decoded.state,AW_JOURNAL,"a1_1_findspymaster")==5);
    strcpy(source.scene,"addamasartus");source.actor_count=1;
    source.actors[0].reference=42;source.actors[0].scene=15;
    n=AW_SaveEncode(raw,sizeof(raw),&source);assert(n>0);
    assert(AW_SaveDecode(raw,n,&decoded));assert(!strcmp(decoded.scene,"addamasartus"));
    assert(decoded.actors[0].scene==15 && decoded.actors[0].reference==42);
    strcpy(source.scene,"balmora");source.actors[0].scene=16;
    n=AW_SaveEncode(raw,sizeof(raw),&source);assert(n>0);
    assert(AW_SaveDecode(raw,n,&decoded));assert(!strcmp(decoded.scene,"balmora"));
    assert(decoded.actors[0].scene==16);
    strcpy(source.scene,"bmastius");source.actors[0].scene=17;
    n=AW_SaveEncode(raw,sizeof(raw),&source);assert(n>0 && AW_SaveDecode(raw,n,&decoded));
    assert(!strcmp(decoded.scene,"bmastius") && decoded.actors[0].scene==17);
    strcpy(source.scene,"tharystomb");source.actor_count=AW_SAVE_ACTORS;
    for(i=0;i<AW_SAVE_ACTORS;i++){source.actors[i]=source.actors[0];source.actors[i].scene=AW_MAP_COUNT-1;source.actors[i].reference=i+1;}
    n=AW_SaveEncode(raw,sizeof(raw),&source);assert(n>0 && AW_SaveDecode(raw,n,&decoded));
    assert(decoded.actor_count==AW_SAVE_ACTORS && decoded.actors[AW_SAVE_ACTORS-1].reference==AW_SAVE_ACTORS);
    for(i=0;i<AW_JOURNAL_ENTRIES;i++){
        source.state.journal[i].quest=0;source.state.journal[i].stage=1000+i;
        source.state.journal[i].days=i;source.state.journal[i].milliseconds=43200000;
    }
    source.state.journal_count=AW_JOURNAL_ENTRIES;
    n=AW_SaveEncode(raw,sizeof(raw),&source);assert(n>0 && n<AW_SAVE_BYTES && AW_SaveDecode(raw,n,&decoded));
    assert(decoded.state.journal_count==AW_JOURNAL_ENTRIES && decoded.state.journal[255].stage==1255);
    source.state.journal[0].quest=AW_STATE_VALUES;assert(!AW_SaveEncode(raw,sizeof(raw),&source));
    source.state.journal[0].quest=0;source.state.journal[1]=source.state.journal[0];
    assert(!AW_SaveEncode(raw,sizeof(raw),&source));source.state.journal_count=0;
    source.actors[0].scene=AW_MapId("vf2525");
    n=AW_SaveEncode(raw,sizeof(raw),&source);assert(n>0 && AW_SaveDecode(raw,n,&decoded));
    assert(decoded.actors[0].scene==AW_MapId("vf2525"));
    source.actors[0].scene=AW_SCENE_COUNT;assert(!AW_SaveEncode(raw,sizeof(raw),&source));source.actor_count=0;
    strcpy(source.scene,"../bad");assert(!AW_SaveEncode(raw,sizeof(raw),&source));strcpy(source.scene,"seyda");
    source.character.head=384;assert(!AW_SaveEncode(raw,sizeof(raw),&source));source.character=c;
    source.character.current[0]=NAN;assert(!AW_SaveEncode(raw,sizeof(raw),&source));
    return 0;
}
