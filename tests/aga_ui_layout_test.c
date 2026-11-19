/* SPDX-License-Identifier: GPL-2.0-or-later
 * UI-NO-SHARED-LAYOUT-67: the shared layout (engine/aga/src/aw_layout.c) and THE CHECK that fails the gate. What a screen
 * draws through aw_ui.c is recorded (every box, button and line of text, the text by its painted pixels) and measured:
 * a text or button that touches or leaves its box, a button closer than the bottom margin to its box's bottom edge, two
 * texts on top of one another (the HUD included). The faults the maintainer saw in v0.0.67-dev1 are drawn as they were
 * drawn then and must be caught (the OK against the bottom edge, the two names on one spot under the view); the screens
 * on the helper must show none. The font is one of the shipped size (14 on a 16-pixel line). Runs in seconds. */
#include "aw_intro.c"
#include <assert.h>
#include "aw_msgbox.h"
#include "aw_layout.h"
#include "aw_iteminfo.h"

server_t sv;server_static_t svs;client_static_t cls;client_state_t cl;
keydest_t key_dest=key_game;viddef_t vid;refdef_t r_refdef;aw_story_t aw_story;
double host_frametime=.02,realtime;int scr_fullupdate,scr_copyeverything;
static byte palette[768],glyphs[16384],frame[64000];
byte *host_basepal=palette,*draw_chars=glyphs;
static byte font_file[2056+21];
int AW_CharacterActive(void){return 0;}int AW_ReaderActive(void){return 0;}
int AW_GalleryModal(void){return 0;}int AW_MovieActive(void){return 0;}
int AW_ReaderKey(int key){return 0;}int AW_CharacterKey(int key){return 0;}
void AW_CharacterDraw(void){}void AW_ReaderDraw(void){}
int AW_NavStart(edict_t *e,float *p){return 1;}
void IN_AWClearButtons(void){}
int COM_FOpenFile(char *s,FILE **f){
    *f=NULL;
    if(strcmp(s,"gfx/magicclear14.awf") && strcmp(s,"gfx/magic14.awf"))return -1;
    *f=fmemopen(font_file,sizeof(font_file),"rb");
    return *f?(int)sizeof(font_file):-1;
}
void Con_Printf(char *s,...){}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
static cvar_t *pickup_setting;   /* aw_pickup_message (PICKUP-NAME-ONLY-BOX-67) */
void Cvar_RegisterVariable(cvar_t *c){c->value=atof(c->string);if(!strcmp(c->name,"aw_pickup_message"))pickup_setting=c;}
void Cvar_SetValue(char *s,float v){}
void Cmd_AddCommand(char *s,void(*fn)(void)){}
char *Cmd_Argv(int n){return "";}int Cmd_Argc(void){return 0;}
int AW_PhotoModeActive(void){return 0;}

static void make_font(void){
    int c;byte *m;
    memcpy(font_file,"AWF1",4);font_file[4]=14;font_file[5]=16;font_file[6]=21;font_file[7]=0;
    for(c=0;c<256;c++){
        m=font_file+8+c*8;
        if(c>32 && c<127){m[2]=6;m[3]=13;m[4]=0;m[5]=1;m[6]=7;}   /* ink rows 1..13 of the 16-pixel line */
        else m[6]=4;
    }
    memset(font_file+2056,0xFF,21);
}
static aw_layout_record_t record;
static void begin(void){memset(&record,0,sizeof(record));memset(frame,0,sizeof(frame));AW_LayoutRecording=&record;}
/* the faults of what was drawn since begin(), printed */
static int faults(const char *what){
    static char why[8192];int n;
    AW_LayoutRecording=NULL;
    n=AW_LayoutCheck(&record,why,sizeof(why));
    printf("%-46s %3d drawn, %d fault%s\n%s",what,record.count,n,n==1?"":"s",why);
    return n;
}
static const char *text_of(int n){
    static char out[256];int i;out[0]=0;
    for(i=0;i<n;i++)strcat(out,i?"\nThe next line of the box.":"The first line of the box.");
    return out;
}
/* the message box as aw_msgbox.c AW_MsgBoxDraw draws it: the frame, the text, the buttons sized to their labels */
static void message_box(int lines,int count){
    static const char *labels[3]={"Ok","Cancel","A longer answer"};int f[4],r[4],w[3],i,lh=AW_UIHeight();
    for(i=0;i<count;i++)w[i]=AW_UIWidth(labels[i]);
    AW_MsgBoxLayout(count,320,200,lines*lh,f);
    AW_UIBox(f[0],f[1],f[2],f[3]);
    AW_UICenteredLinesUpTo(f[0]+6,f[1]+4,f[2]-12,lines*lh+8,text_of(lines),lines);
    for(i=0;i<count;i++){AW_MsgBoxButtonRectSized(count,i,f,w,r);AW_UIButton(r[0],r[1],r[2],r[3],labels[i],i==0,-1);}
}

int main(void){
    int i,n;char label[64];
    for(i=0;i<256;i++)palette[i*3]=palette[i*3+1]=palette[i*3+2]=i;
    make_font();
    vid.width=320;vid.height=200;vid.rowbytes=320;vid.buffer=frame;
    r_refdef.vrect.height=152;AW_UIInit();
    assert(AW_UIHeight()==16 && AW_UIButtonThick());   /* the shipped size; the regular thick button frame by default */
    sv.active=true;svs.maxclients=1;cls.state=ca_connected;cls.signon=SIGNONS;

    /* 1. THE HELPER, by number: a 300 x 100 box with a title row and two buttons */
    {
        aw_layout_t l;int w[2],h,bottom;
        w[0]=AW_UIWidth("OK");w[1]=AW_UIWidth("Cancel");
        AW_LayoutBox(&l,10,20,300,100,16,2,w,0);
        bottom=20+100-aw_layout_metrics.edge;                 /* the frame's inner bottom edge */
        assert(l.inner[0]==18 && l.inner[1]==28 && l.inner[2]==284 && l.inner[3]==84);
        assert(l.title[1]==28 && l.title[3]==16 && l.buttons==2);
        for(i=0;i<2;i++){
            assert(l.button[i][3]==aw_layout_metrics.button_h);
            assert(bottom-(l.button[i][1]+l.button[i][3])==aw_layout_metrics.bottom_margin);
            assert(l.button[i][2]>=aw_layout_metrics.button_min && l.button[i][2]>=w[i]+2*aw_layout_metrics.button_pad);
        }
        /* centred, the gap between them */
        assert(l.button[1][0]-(l.button[0][0]+l.button[0][2])==aw_layout_metrics.button_gap);
        n=(l.button[0][0]-10)-(10+300-(l.button[1][0]+l.button[1][2]));assert(n>=-1 && n<=1);
        /* the content between the title and the row, the gap kept */
        assert(l.content[1]==28+16+aw_layout_metrics.content_gap);
        assert(l.content[1]+l.content[3]==l.button[0][1]-aw_layout_metrics.content_gap);
        /* the height a box needs for its content gives exactly that content */
        h=AW_LayoutBoxHeight(50,16,1,0);AW_LayoutBox(&l,0,0,200,h,16,1,w,0);assert(l.content[3]==50);
        h=AW_LayoutBoxHeight(50,0,0,0);AW_LayoutBox(&l,0,0,200,h,0,0,NULL,0);assert(l.content[3]==50 && !l.buttons);
        /* the hit test is the drawing's rectangles */
        AW_LayoutBox(&l,10,20,300,100,16,2,w,0);
        assert(AW_LayoutButtonAt(&l,l.button[1][0],l.button[1][1])==1 && AW_LayoutButtonAt(&l,l.button[0][0]-1,l.button[0][1])==-1);
        /* a row wider than the box: equal shares inside it */
        {int wide[3]={200,200,200};AW_LayoutBox(&l,0,0,200,100,0,3,wide,0);
         assert(l.button[0][0]>=0 && l.button[2][0]+l.button[2][2]<=200);}
        printf("the helper: box, title, content and a centred button row %d rows above the bottom edge ok\n",
               aw_layout_metrics.bottom_margin);
    }

    /* 2. THE CHECK CATCHES EACH FAULT, drawn as v0.0.67-dev1 drew it */
    /* a. the message box's OK against the bottom edge (the layout before: the button's foot on the frame's inner edge) */
    begin();AW_UIBox(10,20,300,60);AW_UIButton(136,20+60-4-22,48,22,"Ok",1,-1);
    assert(faults("before: the OK against the bottom edge")==1);
    /* b. a line wider than its box */
    begin();AW_UIBox(10,10,100,30);AW_UIText(18,18,"A line far wider than its box",-1);
    assert(faults("before: a line out of its box")==1);
    /* c. the maintainer's picture: the person's name and the door's drawn on one spot under the view */
    begin();AW_UIObjectName("Sellus Gravius",1);AW_UIObjectName("Seyda Neen",1);
    assert(faults("before: two names on one spot under the view")==1);
    /* d. a text under a box drawn over it is hidden, not on top of the box's text */
    begin();AW_UIText(40,60,"Under the box",-1);AW_UIBox(20,40,280,80);AW_UIText(40,60,"On the box",-1);
    assert(faults("a box over a text hides it")==0);

    /* 3. THE SCREENS ON THE HELPER SHOW NONE */
    /* the message box: 1 to 6 lines, 1 to 3 buttons (aw_msgbox_rules.c on the shared metrics) */
    for(n=1;n<=6;n++)for(i=1;i<=3;i++){
        sprintf(label,"message box, %d line%s, %d button%s",n,n==1?"":"s",i,i==1?"":"s");
        begin();message_box(n,i);assert(faults(label)==0);
    }
    /* a box laid out by the helper: its title, three lines of content, two buttons */
    {
        aw_layout_t l;int w[2];
        w[0]=AW_UIWidth("OK");w[1]=AW_UIWidth("Cancel");
        AW_LayoutBox(&l,20,30,280,AW_LayoutBoxHeight(3*AW_UIHeight()+8,AW_UIHeight(),2,0),AW_UIHeight(),2,w,0);
        begin();AW_UIBox(l.box[0],l.box[1],l.box[2],l.box[3]);
        AW_UITextCentred(l.title[0],l.title[1],l.title[2],l.title[3],"The title",-1);
        AW_UICenteredLinesUpTo(l.content[0],l.content[1],l.content[2],l.content[3],text_of(3),3);
        AW_UIButton(l.button[0][0],l.button[0][1],l.button[0][2],l.button[0][3],"OK",1,-1);
        AW_UIButton(l.button[1][0],l.button[1][1],l.button[1][2],l.button[1][3],"Cancel",0,-1);
        assert(faults("a box on the helper: title, lines, two buttons")==0);
    }
    /* DIALOGUE-GOODBYE-BLOCKED-HINT-67: the dialogue window's hint over its box (aw_dialwin.c: BOX 8,6 304x188), laid
     * out by the helper: centred, one line wide enough for its text, the frame's edge and padding kept, no fault */
    {
        static const char hint[]="Continue the conversation first.";
        int h,bx,by,bw;
        begin();AW_UIBox(8,6,304,188);h=AW_UIHintBox(8,6,304,188,hint,2);
        assert(faults("the dialogue's hint box over the window")==0);
        assert(record.count>=3 && record.rect[1].kind==AW_LAYOUT_BOX);
        bx=record.rect[1].x;by=record.rect[1].y;bw=record.rect[1].w;
        assert(record.rect[1].h==h && h==AW_LayoutBoxHeight(record.rect[2].h,0,0,0));   /* one line of ink */
        assert(bw==AW_UIWidth(hint)+2*(aw_layout_metrics.edge+aw_layout_metrics.pad)+2);
        n=(bx-8)-(8+304-(bx+bw));assert(n>=-1 && n<=1);n=(by-6)-(6+188-(by+h));assert(n>=-1 && n<=1);
        printf("hint box: %dx%d at %d,%d, centred over the dialogue window ok\n",bw,h,bx,by);
        /* a text wider than the area wraps inside it and keeps every rule */
        begin();AW_UIBox(8,6,120,188);h=AW_UIHintBox(8,6,120,188,hint,3);
        assert(faults("the hint box in a narrow area")==0 && h>0 && record.rect[1].w==120);
        assert(AW_UIHintBox(8,6,304,188,"",2)==0);
    }
    /* INVENTORY-ITEM-INFO-67: the item information box (aw_iteminfo.c) on the helper: a sword's properties (no scroll
     * bar, OK and Equip), a Cast Once scroll with its effect and a long text (the scroll bar, at the top and at the
     * end), an item with OK alone; the text of each kind as the original's tooltip words it */
    {
        aw_inventory_item_t it;aw_iteminfo_extra_t x;aw_iteminfo_t *b;static char body[6000];int k,lines;
        memset(&it,0,sizeof(it));strcpy(it.id,"steel longsword");strcpy(it.name,"Steel Longsword");
        it.category=AW_INV_WEAPON;it.weapon=2;it.damage[0]=2;it.damage[1]=15;it.damage[2]=1;it.damage[3]=12;
        it.damage[4]=1;it.damage[5]=10;it.health=600;it.weight=24;it.value=96;it.flags=AW_INV_EQUIP;
        memset(&x,0,sizeof(x));x.condition_known=1;x.condition=.5f;
        b=AW_ItemInfoOpen(&it,&x,"Equip");
        assert(b && b->lines<15 && strstr(b->text,"Type: Long Blade, One Handed") && strstr(b->text,"Chop: 2 - 15"));
        assert(strstr(b->text,"Slash: 1 - 12") && strstr(b->text,"Thrust: 1 - 10") && strstr(b->text,"Condition: 300/600"));
        assert(strstr(b->text,"Weight: 24\nValue: 96"));
        begin();AW_ItemInfoDraw(b,0,0);assert(faults("item information: a sword, OK and Equip")==0);
        assert(AW_ItemInfoKey(b,K_ESCAPE,0,0,0,0)==AW_ITEMINFO_CLOSE && AW_ItemInfoKey(b,'e',0,0,1,0)==AW_ITEMINFO_ACTION);
        AW_ItemInfoClose(b);
        /* a Cast Once scroll: its enchantment, its effect line and its text, which needs the scroll bar */
        memset(&it,0,sizeof(it));strcpy(it.id,"sc_icarianflight");strcpy(it.name,"Scroll of Icarian Flight");
        it.category=AW_INV_BOOK;it.weight=.2f;it.value=50;it.enchant_kind=AW_ENCH_ONCE;strcpy(it.enchantment,"icarian");
        for(k=0,body[0]=0;k<60;k++)strcat(body,"The words of the scroll run on, line after line, past the box's height. ");
        memset(&x,0,sizeof(x));x.magic="Jump 1000 pts for 3 secs on Self\nSlowfall 1 pt for 9 secs on Self";x.body=body;
        b=AW_ItemInfoOpen(&it,&x,"Use");
        assert(b && b->lines>15 && strstr(b->text,"Weight: 0.2\nValue: 50\n\nCast Once\nJump 1000 pts"));
        begin();AW_ItemInfoDraw(b,0,0);assert(faults("item information: a scroll at the top, scroll bar")==0);
        lines=b->lines;
        AW_ItemInfoKey(b,K_END,0,0,0,0);assert(b->top>0 && b->top<lines);
        begin();AW_ItemInfoDraw(b,0,0);assert(faults("item information: the scroll at its end")==0);
        AW_ItemInfoKey(b,K_HOME,0,0,0,0);assert(b->top==0);
        AW_ItemInfoKey(b,K_PGDN,0,0,0,0);assert(b->top>0);
        AW_ItemInfoClose(b);
        /* armour: its rating, condition, the weight's class; nothing to do with it: OK alone */
        memset(&it,0,sizeof(it));strcpy(it.id,"iron_cuirass");strcpy(it.name,"Iron Cuirass");it.category=AW_INV_ARMOUR;
        it.slots=1U<<AW_SLOT_CUIRASS;it.armor=15;it.health=500;it.shield_class=2;it.weight=30;it.value=50;
        b=AW_ItemInfoOpen(&it,NULL,NULL);
        assert(b && strstr(b->text,"Armor Rating: 15\nCondition: 500/500\nWeight: 30 (Heavy)\nValue: 50"));
        begin();AW_ItemInfoDraw(b,0,0);assert(faults("item information: armour, OK alone")==0);
        assert(AW_ItemInfoKey(b,'e',0,0,1,0)==AW_ITEMINFO_CLOSE);   /* no action: the use key is OK */
        AW_ItemInfoClose(b);
        printf("item information box: properties, effects and text by kind, scroll bar, buttons on the helper ok\n");
    }
    /* the HUD with ONE focus title (HUD-TEXTS-OVERLAP-67: aw_scene.c AW_SceneDraw draws one) */
    begin();AW_UIObjectName("Sellus Gravius",1);assert(faults("after: one title under the view")==0);
    /* PICKUP-NAME-ONLY-BOX-67: a pick-up says what happened, as the plants' harvest line does (the default); the
     * original's silence is the setting aw_pickup_message 0 */
    assert(pickup_setting && pickup_setting->value==1);
    AW_UIPickupTaken("Bottle",1,3);assert(AW_UISubtitleIs("Picked up Bottle."));
    AW_UIPickupTaken("Bottle",3,3);assert(AW_UISubtitleIs("Picked up 3 Bottle."));
    pickup_setting->value=0;AW_UIPickupTaken("Candle",1,3);assert(AW_UISubtitleIs("Picked up 3 Bottle."));
    pickup_setting->value=1;
    printf("pick-up line: Picked up NAME. / Picked up COUNT NAME.; none with aw_pickup_message 0 ok\n");
    printf("ui layout ok\n");
    return 0;
}
