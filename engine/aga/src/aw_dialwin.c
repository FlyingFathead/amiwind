/* SPDX-License-Identifier: GPL-2.0-or-later
 * The dialogue window (DIALOGUE-57 step 3; docs/DIALOGUE_DESIGN.md "The window"): Talk (E) on an NPC with a dialogue
 * row opens it with the greeting; the topics the player knows and this NPC answers are listed on the right (the list
 * box rules of aw_listbox_rules.c: search as you type, Up/Down/PgUp/PgDn/Home/End, Enter, the mouse); a chosen
 * topic's answer goes into the conversation on the left under the topic's name, and the topics its text names become
 * known; Goodbye (the button, Escape or F10) ends it. Drawn in the console font on the world windows' modal
 * (aw_worldui.c: the world waits).
 *
 *   +--------------------------------------------+
 *   |                 Fargoth                    |
 *   | Hello, outlander...         | Find: _      |
 *   |                             |  Background  |
 *   | [my trade]                  |  my trade    |
 *   | I work the fields...        |  ...         |
 *   |                             |   Goodbye    |
 *   +--------------------------------------------+
 *
 * Memory: the table's resident index once per session (about 25 KB on Morrowind.esm) and the known-topic set (one
 * bit per topic); while a conversation is open, its buffer (AW_DIAL_BUFFER), the shown topics' names and the
 * conversation text; all freed when it ends. The file stays open while the conversation does.
 * The greeting is picked when the conversation opens (Greeting 0..9 of the table, with the derived disposition), its
 * links made known and its result script run; the known topics follow the set the scripts save (AddTopic, AWKT).
 */
#include "quakedef.h"
#include "aw_dial.h"
#include "aw_travel.h"
#include "aw_clock.h"
#include "aw_inventory.h"
#include "aw_listbox.h"
#include "aw_statswin.h"
#include "aw_tryalloc.h"
#include "aw_talk.h"
#include "aw_msgbox.h"

#define BOX_X 8
#define BOX_Y 6
#define BOX_W 304
#define BOX_H 188
#define PAD 6
#define LIST_W 104                  /* the topic column: 12 characters */
#define HISTORY 6144                /* the conversation text kept while it is open (oldest paragraphs dropped) */
#define PARAS 48                    /* its paragraphs (oldest dropped) */
#define PARA_SPANS 24               /* the links kept per paragraph */
#define HITS 48                     /* the links on screen this frame (clicks, Tab) */
#define NAME_CHARS 32
typedef struct {short start,len;unsigned char heading,spans;aw_dial_span_t span[PARA_SPANS];} para_t;
typedef struct {short x,y,w;unsigned short topic;short para,span;} hit_t;

static const char path[]="dialogue.lut";
static aw_dial_t table;
static unsigned char *resident,*known;
static int loaded;                  /* 0 not tried, 1 usable, -1 unavailable (logged once) */

static int active,row,listed,scroll,disposition;
static aw_dial_facts_t facts;      /* the speaker's disposition facts while the conversation is open */
/* the list's fixed entries above the topics (negative codes in list[]) and the persuasion page */
#define CODE_PERSUASION (-1)
#define CODE_BACK (-2)
#define CODE_TRAVEL (-3)
#define CODE_SERVICE(k) (-30-(k))     /* k an index of services_shown[] */
#define CODE_ACTION(k) (-10-(k))
static int mode,fight_started,travel_after;
static unsigned long services;      /* the speaker's service flags (AW_DialServices), read when the conversation opens */
/* the service entries in OpenMW's order (DialogueWindow::updateTopicsPane), Travel between Spells and Spellmaking */
static const unsigned long services_mask[]={AW_DIAL_SERVICE_BARTER,AW_DIAL_SERVICE_SPELLS,0,AW_DIAL_SERVICE_SPELLMAKING,
                                            AW_DIAL_SERVICE_ENCHANTING,AW_DIAL_SERVICE_TRAINING,AW_DIAL_SERVICE_REPAIR};
static const char *const services_shown[]={"Barter","Spells","Travel","Spellmaking","Enchanting","Training","Repair"};
#define SERVICE_TRAVEL 2
#define SERVICE_TRAINING 5
#define CODE_TRAIN(k) (-50-(k))      /* the training page's rows: k an index of train_skill[] */
static const char *const skill_names[AW_DIAL_SKILLS]={"Block","Armorer","Medium Armor","Heavy Armor","Blunt Weapon",
    "Long Blade","Axe","Spear","Athletics","Enchant","Destruction","Alteration","Illusion","Conjuration","Mysticism",
    "Restoration","Alchemy","Unarmored","Security","Sneak","Acrobatics","Light Armor","Short Blade","Marksman",
    "Mercantile","Speechcraft","Hand-to-hand"};
static int train_count,train_skill[3],train_price[3];static float train_npc[AW_DIAL_SKILLS];
static char train_label[3][48];
static int leave_after;
#define SERVICE_SPELLS 1
#define SERVICE_BARTER 0
#define SERVICE_REPAIR 6
/* the result scripts' Choice and Goodbye (OpenMW DialogueWindow: choices replace the topics until one is picked; after
 * Goodbye only the Goodbye button is left) */
#define CHOICES 10
#define RESULT_TEXT 3072             /* the longest result text of the three masters is far shorter */
#define CODE_CHOICE(k) (-800-(k))
static int choice_count,choice_number[CHOICES],choice_topic=-1,goodbye_only;static char choice_text[CHOICES][64];
#define SERVICE_SPELLMAKING 3
/* Spellmaking (OpenMW SpellCreationDialog): page 7 the spell being made, page 8 the effects to add */
#define CODE_SM_NAME (-5)
#define CODE_SM_ADD (-6)
#define CODE_SM_REMOVE (-7)
#define CODE_SM_BUY (-8)
#define CODE_SM_EFFECT(k) (-200-(k))   /* one of the spell's effects: k its index (it becomes the one edited) */
#define CODE_SM_FIELD(k) (-220-(k))    /* a field of the edited effect: 0 magnitude min, 1 max, 2 duration, 3 area, 4 range */
#define CODE_SM_PICK(k) (-300-(k))     /* an effect the player may add: k an index of sm_known[] */
#define SM_KNOWN 48
static aw_made_spell_t *sm;static aw_spell_effect_t *sm_known;static int sm_known_count,sm_edit;
static char (*sm_label)[64];          /* labels: 0 name, 1..8 effects, 9..13 fields, 14 buy, 16.. picks */
#define SM_LABELS (16+SM_KNOWN)
/* Enchanting (OpenMW EnchantingDialog): page 9 the enchantment being made, 10 the item, 11 the soul gem, 12 an effect */
#define SERVICE_ENCHANTING 4
#define CODE_EN_NAME (-9)
#define CODE_EN_ITEM (-10)
#define CODE_EN_GEM (-11)
#define CODE_EN_STYLE (-12)
#define CODE_EN_ADD (-13)
#define CODE_EN_REMOVE (-14)
#define CODE_EN_BUY (-15)
#define CODE_EN_EFFECT(k) (-400-(k))
#define CODE_EN_FIELD(k) (-420-(k))
#define CODE_EN_PICKITEM(k) (-500-(k))
#define CODE_EN_PICKGEM(k) (-600-(k))
#define CODE_EN_PICK(k) (-700-(k))
#define EN_ITEMS 24
static aw_made_item_t *en;static int en_item=-1,en_gem=-1,en_edit=-1,en_items,en_points[EN_ITEMS],en_kind[EN_ITEMS];
static aw_dial_ware_t *en_wares;static char (*en_label)[64];   /* 0 name 1 item 2 gem 3 style 4..11 effects 12..16 fields
                                                                * 17 buy 18 info 20.. items 44.. gems */
#define EN_LABELS (44+64)
#define WARE_ROWS 32
#define CODE_SWITCH (-4)             /* the barter pages' Buy / Sell switch */
#define CODE_WARE(k) (-100-(k))      /* a ware row: k an index of wares[] */
static aw_dial_ware_t *wares;static int ware_count,ware_price[WARE_ROWS],ware_max[WARE_ROWS],ware_now[WARE_ROWS];static char (*ware_label)[64];
#define SPELL_ROWS 24
#define CODE_SPELL(k) (-60-(k))      /* the spells page's rows: k an index of sale_spell[] */
static int sale_count,sale_spell[SPELL_ROWS],sale_cost[SPELL_ROWS],sale_price[SPELL_ROWS];
static char sale_name[SPELL_ROWS][48],sale_label[SPELL_ROWS][64];
static char *ui_texts;              /* the window's words from the table (AW_DialUiTexts), while a conversation is open */
static const char *T(int i,const char *fallback){
    const char *s=ui_texts?ui_texts+AW_DIAL_UI_TEXT*i:NULL;
    return s && *s?s:fallback;
}
static const int service_text[]={AW_DIAL_TEXT_BARTER,AW_DIAL_TEXT_SPELLS,AW_DIAL_TEXT_TRAVEL,AW_DIAL_TEXT_SPELLMAKING,
                                 AW_DIAL_TEXT_ENCHANTING,AW_DIAL_TEXT_TRAINING,AW_DIAL_TEXT_REPAIR};             /* a service is done and the conversation ends with it (training) */
#define SERVICES 7                    /* 0 the topics, 1 the persuasion page */
static const char *const actions[AW_PERSUADE_KINDS]={"Admire","Intimidate","Taunt","Bribe 10 Gold","Bribe 100 Gold",
                                                     "Bribe 1000 Gold"};
static const char *const answer_topic[AW_PERSUADE_KINDS]={"admire","intimidate","taunt","bribe","bribe","bribe"};
static const int bribe_gold[AW_PERSUADE_KINDS]={0,0,0,10,100,1000};
/* OpenMW's bookkeeping of a conversation's disposition (DialogueManager): the speaker's own disposition when it opened,
 * now (with the temporary changes) and the permanent change, written back at Goodbye */
static int original_base,current_base,permanent_change;
static char speaker_record[64];static unsigned long speaker_reference;
static edict_t *speaker;
static FILE *file;
static long file_start;
static unsigned char *buffer;
static char *names,*history;        /* names: NAME_CHARS per topic of the NPC's row */
static int history_len,nparas,nhits,focus=-1;   /* focus: the Tab-chosen link (an index into hits), -1 none */
static para_t *paras;
static hit_t hits[HITS];
static aw_dial_conv_t conv;
static aw_glut_state_t state;
static aw_listbox_t box;
static int list[AW_DIAL_MAX_TOPICS],shown[AW_DIAL_MAX_TOPICS];

static int load(void) {
    FILE *f=NULL;long size,resident_size;unsigned char header[AW_DIAL_HEADER];
    if(loaded)return loaded>0;
    loaded=-1;
    size=COM_FOpenFile((char *)path,&f);
    if(size<AW_DIAL_HEADER || !f){if(f)fclose(f);Con_DPrintf("Dialogue: %s not in this build\n",path);return 0;}
    if(fread(header,1,AW_DIAL_HEADER,f)!=AW_DIAL_HEADER || (resident_size=AW_DialResidentSize(header,size))<0){
        int version;const char *why=AW_DialRefusal(header,size,&version);
        fclose(f);
        if(version && version!=AW_DIAL_VERSION)
            Con_Printf("Dialogue: %s is format version %d, this engine reads version %d: no dialogue (rebuild the image)\n",
                       path,version,AW_DIAL_VERSION);
        else Con_Printf("Dialogue: %s refused (%s): no dialogue\n",path,*why?why:"short file");
        return 0;
    }
    if(!(resident=(unsigned char *)AW_TryMalloc((size_t)resident_size))){fclose(f);Con_Printf("Dialogue: no memory for %ld bytes\n",resident_size);return 0;}
    memcpy(resident,header,AW_DIAL_HEADER);
    if((long)fread(resident+AW_DIAL_HEADER,1,(size_t)(resident_size-AW_DIAL_HEADER),f)!=resident_size-AW_DIAL_HEADER ||
       !AW_DialOpen(&table,resident,resident_size,size) ||
       !(known=(unsigned char *)AW_TryMalloc((size_t)AW_DialKnownBytes(&table)))){
        fclose(f);free(resident);resident=NULL;memset(&table,0,sizeof(table));Con_Printf("Dialogue: %s is damaged (its sections do not add up to the file): no dialogue\n",path);return 0;
    }
    fclose(f);
    AW_DialKnownStart(&table,known);
    Con_DPrintf("Dialogue: %ld topics, %ld NPC rows, %ld bytes resident\n",table.topics,table.npcs,resident_size);
    loaded=1;
    return 1;
}
static int read_file(void *user,long offset,void *out,long bytes) {
    (void)user;
    if(!file || offset<0 || bytes<0 || fseek(file,file_start+offset,SEEK_SET))return 0;
    return bytes==0 || (long)fread(out,1,(size_t)bytes,file)==bytes;
}
/* The known topics saved with the game (DIALOGUE-COMPLETE-58): the scripts keep them by their topic rows (AddTopic;
 * the save's AWKT, aw_mwhost.c); TOPIC_MAP (2 bytes per table topic, made once, with the file open) gives each Topic
 * kind topic its row by name. Each conversation opens with the set the scripts hold (a loaded game, AddTopic since);
 * a topic learned here joins it. Without the scripts' file: this session's set only, as before. */
int AW_MwscriptTopicKnown(int row);
void AW_MwscriptTopicLearn(int row);
int AW_MwscriptTopicHashes(unsigned long *out,int max);
static unsigned short *topic_map;static int map_state;   /* 0 not tried, 1 made, -1 none */
static void topics_sync(void) {
    if(!map_state){
        unsigned long *hashes;int rows=AW_MwscriptTopicHashes(NULL,0);
        if(rows<=0)return;           /* the scripts' file not loaded (yet): tried again at the next conversation */
        map_state=-1;
        if(rows>0 && rows<(int)AW_DIAL_NO_ROW && (hashes=(unsigned long *)AW_TryMalloc(sizeof(unsigned long)*(size_t)rows))!=NULL){
            if((rows=AW_MwscriptTopicHashes(hashes,rows))>0 &&
               (topic_map=(unsigned short *)AW_TryMalloc(sizeof(unsigned short)*(size_t)(table.topics>0?table.topics:1)))!=NULL){
                int mapped=AW_DialTopicMap(&table,read_file,NULL,hashes,rows,topic_map);
                if(mapped>0){map_state=1;Con_DPrintf("Dialogue: %d topics follow the saved known-topic set\n",mapped);}
                else{free(topic_map);topic_map=NULL;}
            }
            free(hashes);
        }
    }
    if(map_state>0)AW_DialKnownSync(&table,known,topic_map,AW_MwscriptTopicKnown);
}
static void know(int topic) {
    AW_DialKnow(&table,known,topic);
    if(map_state>0 && topic>=0 && topic<table.topics && topic_map[topic]!=(unsigned short)AW_DIAL_NO_ROW)AW_MwscriptTopicLearn(topic_map[topic]);
}
static void read_string(long at,char *out,int capacity) {
    int n;
    out[0]=0;
    if(at<0 || !file || fseek(file,file_start+at,SEEK_SET))return;
    n=(int)fread(out,1,(size_t)(capacity-1),file);
    out[n<0?0:n]=0;
}

/* the conversation: paragraphs in one text block, a heading paragraph is a topic's name, each with its link spans */
static void drop_oldest(void) {
    int i,cut=paras[0].len;
    memmove(history,history+cut,(size_t)(history_len-cut));history_len-=cut;
    memmove(paras,paras+1,sizeof(para_t)*(size_t)(nparas-1));nparas--;
    for(i=0;i<nparas;i++)paras[i].start=(short)(paras[i].start-cut);
}
static void append_spans(const char *text,int heading,const aw_dial_span_t *spans,int n) {
    int len=(int)strlen(text),k;para_t *p;
    if(len>HISTORY/2)len=HISTORY/2;
    while(nparas && (history_len+len>HISTORY || nparas>=PARAS))drop_oldest();
    p=&paras[nparas++];
    p->start=(short)history_len;p->len=(short)len;p->heading=(unsigned char)heading;p->spans=0;
    memcpy(history+history_len,text,(size_t)len);history_len+=len;
    for(k=0;k<n && p->spans<PARA_SPANS;k++)
        if(spans[k].offset+spans[k].length<=len)p->span[p->spans++]=spans[k];
    scroll=0;focus=-1;                                         /* show the newest */
}
static void append(const char *text,int heading) {append_spans(text,heading,NULL,0);}

static int char_w(void){int w=AW_ConsoleCharWidth();return w<1?8:w;}
static int char_h(void){int h=AW_ConsoleCharHeight();return h<1?8:h;}
static int row_h(void){return char_h()+2;}
static int bar_y(void){return BOX_Y+PAD+char_h()+4;}
static int body_y(void){return bar_y()+char_h()+8;}
static int list_x(void){return BOX_X+BOX_W-PAD-LIST_W;}
static int list_y(void){return body_y()+char_h()+6;}
static int button_y(void){return BOX_Y+BOX_H-PAD-row_h();}
static int list_rows(void){int r=(button_y()-4-list_y())/row_h();return r<1?1:r;}
static int text_cols(void){return (list_x()-8-(BOX_X+PAD))/char_w();}
static int text_rows(void){return (BOX_Y+BOX_H-PAD-body_y())/row_h();}

static void text(int x,int y,const char *s,int right){
    int w=char_w();
    for(;s && *s && x+w<=right;s++,x+=w)AW_ConsoleCharacter(x,y,(unsigned char)*s);
}
static const char *label(void *ctx,int r){
    int k;(void)ctx;
    if(r<0 || r>=listed)return "";
    if(list[r]==CODE_PERSUASION)return T(AW_DIAL_TEXT_PERSUASION,"Persuasion");
    if(list[r]==CODE_BACK)return T(AW_DIAL_TEXT_BACK,"Back");
    if(list[r]==CODE_TRAVEL)return T(AW_DIAL_TEXT_TRAVEL,"Travel");
    if(list[r]<=CODE_CHOICE(0) && list[r]>CODE_CHOICE(CHOICES))return choice_text[CODE_CHOICE(0)-list[r]];
    if(en_label){
        if(list[r]==CODE_EN_NAME)return en_label[0];
        if(list[r]==CODE_EN_ITEM)return en_label[1];
        if(list[r]==CODE_EN_GEM)return en_label[2];
        if(list[r]==CODE_EN_STYLE)return en_label[3];
        if(list[r]==CODE_EN_ADD)return "+";
        if(list[r]==CODE_EN_REMOVE)return "-";
        if(list[r]==CODE_EN_BUY)return en_label[17];
        if(list[r]<=CODE_EN_EFFECT(0) && list[r]>CODE_EN_EFFECT(AW_MADE_EFFECTS))return en_label[4+CODE_EN_EFFECT(0)-list[r]];
        if(list[r]<=CODE_EN_FIELD(0) && list[r]>CODE_EN_FIELD(5))return en_label[12+CODE_EN_FIELD(0)-list[r]];
        if(list[r]<=CODE_EN_PICKITEM(0) && list[r]>CODE_EN_PICKITEM(EN_ITEMS))return en_label[20+CODE_EN_PICKITEM(0)-list[r]];
        if(list[r]<=CODE_EN_PICKGEM(0) && list[r]>CODE_EN_PICKGEM(64))return en_label[44+CODE_EN_PICKGEM(0)-list[r]];
        if(list[r]<=CODE_EN_PICK(0) && list[r]>CODE_EN_PICK(SM_KNOWN) && sm_label)return sm_label[16+CODE_EN_PICK(0)-list[r]];
    }
    if(sm_label){
        if(list[r]==CODE_SM_NAME)return sm_label[0];
        if(list[r]==CODE_SM_ADD)return "+";
        if(list[r]==CODE_SM_REMOVE)return "-";
        if(list[r]==CODE_SM_BUY)return sm_label[14];
        if(list[r]<=CODE_SM_EFFECT(0) && list[r]>CODE_SM_EFFECT(AW_MADE_EFFECTS))return sm_label[1+CODE_SM_EFFECT(0)-list[r]];
        if(list[r]<=CODE_SM_FIELD(0) && list[r]>CODE_SM_FIELD(5))return sm_label[9+CODE_SM_FIELD(0)-list[r]];
        if(list[r]<=CODE_SM_PICK(0) && list[r]>CODE_SM_PICK(SM_KNOWN))return sm_label[16+CODE_SM_PICK(0)-list[r]];
    }
    if(list[r]==CODE_SWITCH)return mode==4?T(AW_DIAL_TEXT_SELL,"Sell"):T(AW_DIAL_TEXT_BUY,"Buy");
    if(list[r]<=CODE_WARE(0) && list[r]>CODE_WARE(WARE_ROWS))return ware_label?ware_label[CODE_WARE(0)-list[r]]:"";
    if(list[r]<=CODE_TRAIN(0) && list[r]>CODE_TRAIN(3))return train_label[CODE_TRAIN(0)-list[r]];
    if(list[r]<=CODE_SPELL(0) && list[r]>CODE_SPELL(SPELL_ROWS))return sale_label[CODE_SPELL(0)-list[r]];
    if(list[r]<=CODE_SERVICE(0) && list[r]>CODE_SERVICE(SERVICES))return T(service_text[CODE_SERVICE(0)-list[r]],services_shown[CODE_SERVICE(0)-list[r]]);
    if(list[r]<=CODE_ACTION(0) && list[r]>CODE_ACTION(AW_PERSUADE_KINDS))return T(AW_DIAL_TEXT_ADMIRE+CODE_ACTION(0)-list[r],actions[CODE_ACTION(0)-list[r]]);
    if((k=AW_DialFind(&conv,list[r]))<0)return "";
    return names+NAME_CHARS*k;
}
/* Exhausted topics (OpenMW DialogueWindow::updateTopicFormat via the journal): the answer this NPC would give now is
 * on its topic's journal page already, and none of the topics it names is unknown to the player. Drawn dimmer, still
 * chosen as any topic. Worked out once per list (the spans read the answer from disk), not per drawn frame. */
static unsigned char spent[AW_DIAL_MAX_TOPICS];
static int topic_spent(int topic){
    int refused=0,answer,i,n;aw_dial_span_t spans[PARA_SPANS];
    if(AW_DialTopicKind(&table,topic)!=AW_DIAL_KIND_TOPIC)return 0;
    if((answer=AW_DialPick(&conv,topic,&state,&refused))<0 || refused)return 0;
    if(!AW_DialHeardHas((int)conv.answer[answer].entry))return 0;
    n=AW_DialSpans(&conv,answer,read_file,NULL,spans,PARA_SPANS);
    for(i=0;i<n;i++)if(!AW_DialKnows(&table,known,spans[i].topic))return 0;
    return 1;
}
static void refresh(void){
    int keep=AW_ListBoxSelected(&box),at=keep>=0 && keep<listed?list[keep]:-99,i,j;
    if(goodbye_only){listed=0;}
    else if(choice_count){for(i=0;i<choice_count;i++)list[i]=CODE_CHOICE(i);listed=choice_count;}
    else if(mode==1){
        for(i=0;i<AW_PERSUADE_KINDS;i++)list[i]=CODE_ACTION(i);
        list[AW_PERSUADE_KINDS]=CODE_BACK;listed=AW_PERSUADE_KINDS+1;
    }else if(mode==2){
        for(i=0;i<train_count;i++)list[i]=CODE_TRAIN(i);
        list[train_count]=CODE_BACK;listed=train_count+1;
    }else if(mode==7 && sm){
        int k=0;
        list[k++]=CODE_SM_NAME;
        for(i=0;i<sm->effects;i++){
            list[k++]=CODE_SM_EFFECT(i);
            if(i==sm_edit)for(j=0;j<5;j++)list[k++]=CODE_SM_FIELD(j);
        }
        if(sm->effects<AW_MADE_EFFECTS)list[k++]=CODE_SM_ADD;
        if(sm->effects>0)list[k++]=CODE_SM_REMOVE;
        list[k++]=CODE_SM_BUY;list[k++]=CODE_BACK;listed=k;
    }else if(mode==9 && en){
        int k=0;
        list[k++]=CODE_EN_NAME;list[k++]=CODE_EN_ITEM;list[k++]=CODE_EN_GEM;list[k++]=CODE_EN_STYLE;
        for(i=0;i<en->effects;i++){
            list[k++]=CODE_EN_EFFECT(i);
            if(i==en_edit)for(j=0;j<5;j++)list[k++]=CODE_EN_FIELD(j);
        }
        if(en->effects<AW_MADE_EFFECTS)list[k++]=CODE_EN_ADD;
        if(en->effects>0)list[k++]=CODE_EN_REMOVE;
        list[k++]=CODE_EN_BUY;list[k++]=CODE_BACK;listed=k;
    }else if(mode==10){
        for(i=0;i<en_items;i++)list[i]=CODE_EN_PICKITEM(i);
        list[en_items]=CODE_BACK;listed=en_items+1;
    }else if(mode==11){
        for(i=0;i<AW_GemCount() && i<64;i++)list[i]=CODE_EN_PICKGEM(i);
        list[i]=CODE_BACK;listed=i+1;
    }else if(mode==12){
        for(i=0;i<sm_known_count;i++)list[i]=CODE_EN_PICK(i);
        list[sm_known_count]=CODE_BACK;listed=sm_known_count+1;
    }else if(mode==8){
        for(i=0;i<sm_known_count;i++)list[i]=CODE_SM_PICK(i);
        list[sm_known_count]=CODE_BACK;listed=sm_known_count+1;
    }else if(mode==6){
        for(i=0;i<ware_count;i++)list[i]=CODE_WARE(i);
        list[ware_count]=CODE_BACK;listed=ware_count+1;
    }else if(mode==4 || mode==5){
        list[0]=CODE_SWITCH;
        for(i=0;i<ware_count;i++)list[1+i]=CODE_WARE(i);
        list[1+ware_count]=CODE_BACK;listed=ware_count+2;
    }else if(mode==3){
        for(i=0;i<sale_count;i++)list[i]=CODE_SPELL(i);
        list[sale_count]=CODE_BACK;listed=sale_count+1;
    }else{
        int fixed=0;
        list[fixed++]=CODE_PERSUASION;
        for(i=0;i<SERVICES;i++){
            if(i==SERVICE_TRAVEL){if(AW_SceneTravelOffers(speaker))list[fixed++]=CODE_TRAVEL;}
            else if(services&services_mask[i])list[fixed++]=CODE_SERVICE(i);
        }
        listed=fixed+AW_DialTopicList(&conv,known,&state,list+fixed,AW_DIAL_MAX_TOPICS-fixed);
    }
    for(i=0;i<listed;i++)spent[i]=(unsigned char)(list[i]>=0 && mode==0 && !choice_count && topic_spent(list[i]));
    AW_ListBoxReset(&box,listed,label,NULL,shown,list_rows());
    for(i=0;i<box.shown_count;i++)if(list[box.shown[i]]==at){box.selection=i;break;}
}
/* the conversation's derived disposition again, after a change of the speaker's own */
static void dispose(void){
    facts.base=current_base;
    conv.cond.disposition=disposition=AW_DialDisposition(&table,&facts,1);
}
/* the NPC's topic of that name (the Persuasion answers: "Admire Success" ...), -1 none */
static int named_topic(const char *name){
    int k;
    for(k=0;k<conv.topics;k++)if(!Q_strcasecmp(names+NAME_CHARS*k,(char *)name))return conv.topic[k].topic;
    return -1;
}
static void answer_of(int topic,const char *heading);
/* One persuasion (OpenMW DialogueManager::persuade): the rule with a roll, the disposition changes kept for the
 * conversation, Fight and Flee written at once, the bribe's gold paid on success, the answer from "<Kind> Success" or
 * "<Kind> Fail". A bribe the player cannot pay does nothing (OpenMW greys it out). */
static int affordable(int kind){return !bribe_gold[kind] || AW_MwscriptPlayerGold(0)>=bribe_gold[kind];}
/* a row the player cannot choose now: a bribe of more gold than he has (OpenMW greys those buttons out) */
static int greyed(int r){
    if(r<0 || r>=listed)return 0;
    if(list[r]<=CODE_TRAIN(0) && list[r]>CODE_TRAIN(3))return AW_MwscriptPlayerGold(0)<train_price[CODE_TRAIN(0)-list[r]];
    if(list[r]<=CODE_SPELL(0) && list[r]>CODE_SPELL(SPELL_ROWS))return AW_MwscriptPlayerGold(0)<sale_price[CODE_SPELL(0)-list[r]];
    if(list[r]<=CODE_WARE(0) && list[r]>CODE_WARE(WARE_ROWS))return (mode==4 || mode==6) && AW_MwscriptPlayerGold(0)<ware_price[CODE_WARE(0)-list[r]];
    return list[r]<=CODE_ACTION(0) && list[r]>CODE_ACTION(AW_PERSUADE_KINDS) && !affordable(CODE_ACTION(0)-list[r]);
}
static void persuade(int kind){
    aw_dial_person_t player,npc;aw_dial_persuasion_t r;int fight,flee;char name[48];
    if(!affordable(kind))return;
    AW_MwscriptPersons(speaker_record,speaker_reference,&player,&npc,&fight,&flee);
    AW_DialPersuade(&table,kind,&player,&npc,disposition,rand()%100,fight,flee,&r);
    if(r.temp>0 && r.perm>0 && original_base+r.perm+permanent_change<0)r.perm=-(original_base+permanent_change);
    current_base+=r.temp;permanent_change+=r.perm;
    dispose();
    if(r.fight!=fight || r.flee!=flee)AW_MwscriptSetSpeaker(speaker_record,speaker_reference,-1,r.fight,r.flee);
    if(r.success && bribe_gold[kind])AW_MwscriptPlayerGold(-bribe_gold[kind]);
    Q_snprintf(name,sizeof(name),"%s %s",answer_topic[kind],r.success?"success":"fail");
    answer_of(named_topic(name),T(AW_DIAL_TEXT_ADMIRE+kind,actions[kind]));
    /* Fight from disposition (DIALOGUE-FIGHT-DISPOSITION-57): a taunt or a failed intimidation can bring the Fight
     * rating to 100; the speaker attacks and the conversation ends (OpenMW: the actor turns hostile) */
    if(AW_MwscriptSpeakerAggro(speaker,disposition)>0)fight_started=1;
}
/* Goodbye (OpenMW DialogueManager::goodbyeSelected): the speaker's own disposition becomes what it was plus the
 * permanent change, clamped so the derived disposition stays within 0..100 */
static void goodbye(void){
    int zero,v;
    if(!permanent_change && original_base==current_base)return;
    facts.base=0;zero=AW_DialDisposition(&table,&facts,0);
    v=original_base+permanent_change;
    if(v<-zero)v=-zero;
    if(v>100-zero)v=100-zero;
    AW_MwscriptSetSpeaker(speaker_record,speaker_reference,v,-1,-1);
}

static void release(void){
    if(file){fclose(file);file=NULL;}
    free(buffer);buffer=NULL;free(names);names=NULL;free(history);history=NULL;free(paras);paras=NULL;free(ui_texts);ui_texts=NULL;
    free(wares);wares=NULL;free(ware_label);ware_label=NULL;ware_count=0;
    free(sm);sm=NULL;free(sm_known);sm_known=NULL;free(sm_label);sm_label=NULL;sm_known_count=0;
    free(en);en=NULL;free(en_wares);en_wares=NULL;free(en_label);en_label=NULL;en_items=0;en_item=en_gem=en_edit=-1;
    memset(&conv,0,sizeof(conv));active=0;speaker=NULL;listed=0;history_len=0;nparas=0;nhits=0;focus=-1;
}
static void closed(void){
    edict_t *e=speaker;int travel=travel_after;
    if(active)goodbye();
    release();
    if(travel && e)AW_SceneTravelWith(e);      /* the menu opens once the window has gone (aw_scene.c AW_SceneTick) */
}

/* A console character in COLOR: drawn as usual, then the pixels it changed take the colour (any console font). */
static void char_in(int x,int y,int c,int color){
    byte keep[16*16];int w=char_w(),h=char_h(),i,j;
    if(w>16 || h>16 || x<0 || y<0 || x+w>(int)vid.conwidth || y+h>(int)vid.conheight){AW_ConsoleCharacter(x,y,c);return;}
    for(j=0;j<h;j++)memcpy(keep+16*j,vid.conbuffer+(y+j)*vid.conrowbytes+x,(size_t)w);
    AW_ConsoleCharacter(x,y,c);
    for(j=0;j<h;j++)for(i=0;i<w;i++){
        byte *p=vid.conbuffer+(y+j)*vid.conrowbytes+x+i;
        if(*p!=keep[16*j+i])*p=(byte)color;
    }
}
/* the link (span index) holding character AT of paragraph P, -1 none */
static int span_at(const para_t *p,int at){
    int k;
    for(k=0;k<p->spans;k++)if(at>=p->span[k].offset && at<p->span[k].offset+p->span[k].length)return k;
    return -1;
}
/* the lines of the conversation that fit, newest at the bottom (SCROLL lines up): one pass over the wrapped lines,
 * counting them (DRAW 0) or drawing those from line FIRST on, the links in link blue (the focused one on a band) and
 * each visible run of a link recorded in hits[] for the mouse and Tab */
static int history_lines(int draw,int first){
    int cols=text_cols(),rows=text_rows(),line=0,y=body_y(),i,j,k,x0,blue=AW_UIColor(112,126,207);
    char text_[1100],out[64];const char *q;
    if(cols>(int)sizeof(out)-2)cols=(int)sizeof(out)-2;
    if(draw)nhits=0;
    for(i=0;i<nparas;i++){
        const para_t *p=&paras[i];int n=p->len<(int)sizeof(text_)-1?p->len:(int)sizeof(text_)-1,indent=p->heading?1:0;
        memcpy(text_,history+p->start,(size_t)n);text_[n]=0;
        for(q=text_;;line++){
            int base=(int)(q-text_),len;
            if(!AW_DialWrapNext(&q,cols-indent*2,out,sizeof(out)))break;
            if(!draw || line<first || line>=first+rows)continue;
            x0=BOX_X+PAD+indent*char_w();
            if(p->heading)AW_UIFill(BOX_X+PAD,y-1,cols*char_w(),row_h(),AW_UIColor(62,53,36));
            len=(int)strlen(out);
            for(j=0;j<len;j++){
                int x=x0+j*char_w();
                if(x+char_w()>list_x()-6)break;
                k=span_at(p,base+j);
                if(k<0){AW_ConsoleCharacter(x,y,(unsigned char)out[j]);continue;}
                /* a new run of this link on this line: a hit */
                if((j==0 || span_at(p,base+j-1)!=k) && nhits<HITS){
                    hit_t *h=&hits[nhits++];int e=j;
                    while(e<len && span_at(p,base+e)==k)e++;
                    h->x=(short)x;h->y=(short)y;h->w=(short)((e-j)*char_w());h->topic=p->span[k].topic;
                    h->para=(short)i;h->span=(short)k;
                    if(focus==nhits-1)AW_UIFill(x,y-1,h->w,row_h(),AW_UIColor(46,46,92));
                }
                char_in(x,y,(unsigned char)out[j],blue);
            }
            y+=row_h();
        }
    }
    return line;
}
static void draw_history(void){
    int rows=text_rows(),total=history_lines(0,0),first;
    if(scroll>total-rows)scroll=total-rows;
    if(scroll<0)scroll=0;
    first=total-rows-scroll;
    history_lines(1,first<0?0:first);
}
static void draw(void){
    char line[64];int i,y,rows=list_rows(),right=BOX_X+BOX_W-PAD,dark=AW_UIColor(29,23,17),pick=AW_UIColor(62,53,36);
    const char *who=speaker?pr_strings+speaker->v.netname:"";int w=(int)strlen(who)*char_w();
    AW_ListBoxSetVisible(&box,rows);
    AW_UIBox(BOX_X,BOX_Y,BOX_W,BOX_H);
    text(BOX_X+(BOX_W-w)/2,BOX_Y+PAD,who,right);
    {   /* the disposition bar: the NPC's disposition toward the player, 0..100, blue, its number in the middle */
        int bw=BOX_W-2*PAD,fill=bw*disposition/100;
        Q_snprintf(line,sizeof(line),"%d",disposition);
        AW_UIFill(BOX_X+PAD,bar_y()-1,bw,char_h()+2,dark);
        if(fill>0)AW_UIFill(BOX_X+PAD,bar_y()-1,fill,char_h()+2,AW_UIColor(38,56,170));
        text(BOX_X+(BOX_W-(int)strlen(line)*char_w())/2,bar_y(),line,right);
    }
    AW_UIFill(list_x()-4,body_y()-2,1,BOX_Y+BOX_H-PAD-body_y(),pick);    /* the column rule */
    draw_history();
    AW_UIFill(list_x(),body_y()-2,LIST_W,char_h()+4,dark);
    Q_snprintf(line,sizeof(line),"Find: %s_",box.search);
    text(list_x()+2,body_y(),line,right);
    for(i=0;i<rows && box.top+i<box.shown_count;i++){
        y=list_y()+i*row_h();
        if(box.top+i==box.selection)AW_UIFill(list_x(),y-1,LIST_W,row_h(),pick);
        if(greyed(box.shown[box.top+i]) || (box.shown[box.top+i]<listed && spent[box.shown[box.top+i]])){
            const char *s=label(NULL,box.shown[box.top+i]);int x=list_x()+2,g=AW_UIColor(96,90,80);
            for(;*s && x+char_w()<=right;s++,x+=char_w())char_in(x,y,(unsigned char)*s,g);
        }else text(list_x()+2,y,label(NULL,box.shown[box.top+i]),right);
    }
    if(!box.shown_count)text(list_x()+2,list_y(),"(no topics)",right);
    AW_UIFill(list_x(),button_y()-1,LIST_W,row_h(),dark);
    {const char *g=T(AW_DIAL_TEXT_GOODBYE,"Goodbye");int glyphs=(int)strlen(g);
     if(glyphs>LIST_W/char_w())glyphs=LIST_W/char_w();
     text(list_x()+(LIST_W-glyphs*char_w())/2,button_y(),g,right);}
}
/* %PCRank, %NextPCRank and %Cell of this conversation (aw_dial.c AW_DialFillDefines) */
static void rank_defines(const char *in,char *out,int capacity){
    char pc[AW_DIAL_FACTION_ID]="%",next[AW_DIAL_FACTION_ID]="%",cell[64];const char *slash;int rank=-1,expelled=0;
    if(facts.faction && facts.rank){
        rank=facts.rank(facts.faction,&expelled);
        read_string(AW_DialRankAt(&table,facts.faction,rank<0?0:rank),pc,sizeof(pc));
        read_string(AW_DialRankAt(&table,facts.faction,rank+1>AW_DIAL_RANKS-1?AW_DIAL_RANKS-1:rank+1),next,sizeof(next));
    }
    /* the player's cell: the place name the HUD shows (the map's message, "AmiWind / Seyda Neen") */
    slash=strrchr(cl.levelname,'/');
    strncpy(cell,slash?slash+1+(slash[1]==' '):cl.levelname,sizeof(cell)-1);cell[sizeof(cell)-1]=0;
    AW_DialFillDefines(in,out,capacity,pc,next,cell);
}
/* Ask TOPIC (a row of the list or a link): its name as a heading, the answer under it with its links (the spans kept
 * through the define filling), the topics it names made known. A link to a topic this NPC does not answer: nothing. */
static void result_choice(const char **texts,int ntexts,const aw_mwcell_t *numbers,int count){
    int i;
    if(!texts){goodbye_only=1;choice_count=0;return;}
    for(i=0;i<ntexts && i<count && choice_count<CHOICES;i++){
        Q_snprintf(choice_text[choice_count],sizeof(choice_text[0]),"%s",texts[i]);choice_number[choice_count++]=numbers[i].i;}
}
/* ClearInfoActor (OpenMW clearInfoActor: the last entry this speaker added to the topic's journal page goes) */
static void result_clear(void){
    if(choice_topic>=0)AW_DialHeardRemoveLast(choice_topic,speaker?pr_strings+speaker->v.netname:"");
}
/* the answer's result script, run once it is shown (OpenMW DialogueManager::executeScript after the text) */
static void run_result(int answer,int topic){
    static char script[RESULT_TEXT];long at=AW_DialScriptAt(&conv,answer);int n;   /* static: the 68k stack is small */
    if(at<0)return;
    read_string(at,script,sizeof(script));
    if((n=(int)strlen(script))<=0)return;
    choice_count=0;choice_topic=topic;
    aw_dial_result_choice=result_choice;aw_dial_result_clear=result_clear;
    AW_MwscriptRunResult(speaker_record,speaker_reference,script,n);
    aw_dial_result_choice=NULL;aw_dial_result_clear=NULL;
    dispose();                       /* a result may change the disposition (ModDisposition, SetDisposition) */
}
/* an answer's text into the conversation with its links (the spans kept through the define filling), the topics it
 * names made known */
static void show_answer(int answer){
    int i,n,found;static char raw[1024],marked[1100],ranked[1100],filled[1100],plain[1100];   /* static: small stack */
    aw_dial_span_t spans[PARA_SPANS],kept[PARA_SPANS];
    read_string(AW_DialTextAt(&conv,answer),raw,sizeof(raw));
    n=AW_DialSpans(&conv,answer,read_file,NULL,spans,PARA_SPANS);
    AW_DialMarkSpans(raw,spans,n,marked,sizeof(marked));
    rank_defines(marked,ranked,sizeof(ranked));
    AW_GlutFill(speaker,row,ranked,filled,sizeof(filled));
    AW_DialTakeSpans(filled,spans,n,plain,sizeof(plain),kept,&found);
    append_spans(plain,0,kept,found);
    for(i=0;i<n;i++)know(spans[i].topic);
}
/* The greeting (OpenMW DialogueManager::startDialogue): the first Greeting topic's answer this speaker passes now,
 * shown, its topics made known and its result script run. 0 when the table has none for this speaker (then the
 * voice table's line is shown, as before). */
static int greet(void){
    int topic,answer;
    conv.cond.choice=-1;
    if((answer=AW_DialGreeting(&conv,&state,&topic))<0)return 0;
    show_answer(answer);
    {   /* the spoken greeting follows the picked one (VOICE-COVERAGE-58): that INFO's voice from the voice table */
        static char raw[1024];
        read_string(AW_DialTextAt(&conv,answer),raw,sizeof(raw));
        AW_GlutGreetVoice(speaker,raw);
    }
    run_result(answer,topic);
    conv.cond.choice=-1;
    topics_sync();                   /* the result's AddTopic */
    return 1;
}
static void answer_of(int topic,const char *heading){
    int k=AW_DialFind(&conv,topic),answer;
    char name[NAME_CHARS];
    if(k<0 || (answer=AW_DialAnswer(&conv,topic,&state))<0){if(heading)append(heading,1);return;}
    Q_snprintf(name,sizeof(name),"%s",heading?heading:names+NAME_CHARS*k);
    append(name,1);
    show_answer(answer);
    {   /* the journal's topic page (OpenMW Journal::addTopic): a Topic answer, not the Info Refusal one */
        int refused=0;
        if(AW_DialTopicKind(&table,topic)==AW_DIAL_KIND_TOPIC && AW_DialPick(&conv,topic,&state,&refused)==answer){
            int got=AW_DialHeardAdd((int)conv.answer[answer].entry,topic,speaker?pr_strings+speaker->v.netname:"");
            if(got==2)Con_DPrintf("Journal: the topic pages are full (12000 entries); the oldest entry of a topic with a newer one gave way\n");
            else if(!got)Con_DPrintf("Journal: no memory for a topic page entry\n");
        }
    }
    run_result(answer,topic);
    conv.cond.choice=-1;             /* a choice holds for the one answer it picks */
    topics_sync();                   /* the result's AddTopic */
    refresh();
}
static void ask_topic(int topic){answer_of(topic,NULL);}
/* Training (OpenMW TrainingWindow): the speaker's three best skills, each at iTrainingMod x the player's base
 * skill, then the barter offer; one that costs more than the player's gold is greyed out */
static void training_open(void){
    aw_dial_person_t player,npc;int fight,flee,i;
    AW_MwscriptPersons(speaker_record,speaker_reference,&player,&npc,&fight,&flee);
    AW_MwscriptNpcSkills(speaker_record,speaker_reference,train_npc);
    train_count=AW_DialTrainingPicks(train_npc,AW_DIAL_SKILLS,train_skill);
    for(i=0;i<train_count;i++){
        train_price[i]=AW_DialTrainingPrice(&table,AW_MwscriptPlayerSkill(train_skill[i],0),&player,&npc,disposition);
        Q_snprintf(train_label[i],sizeof(train_label[i]),"%s - %d%s",
                   T(AW_DIAL_TEXT_SKILL0+train_skill[i],skill_names[train_skill[i]]),train_price[i],T(AW_DIAL_TEXT_GP,"gp"));
    }
    mode=2;refresh();
}
/* Barter, the plain pages (OpenMW's full trade window, with an offer to change, a running total and the merchant's
 * gold, is its own tracker row): PAGE 4 the merchant's stock at the buying offer, 5 the player's things at the selling
 * offer, each only of the kinds the merchant's service flags trade (OpenMW Class::canSell: the kind's bit, or an
 * enchanted thing with Magic Items); one thing a click. */
static int trades(int category,int enchanted){
    unsigned long bit;
    switch(category){
    case AW_INV_WEAPON:bit=0x1;break;
    case AW_INV_ARMOUR:bit=0x2;break;
    case AW_INV_CLOTHING:bit=0x4;break;
    case AW_INV_BOOK:bit=0x8;break;
    case AW_INV_INGREDIENT:bit=0x10;break;
    case AW_INV_POTION:bit=0x2000;break;
    default:bit=0x20|0x40|0x80|0x100|0x200|0x400;break;   /* picks, probes, lights, apparatus, repair, misc */
    }
    return (services&bit)!=0 || (enchanted && (services&0x1000));
}
static void barter_open(int page){
    aw_dial_person_t player,npc;int fight,flee,i,n,k=0;
    if(!wares && !(wares=(aw_dial_ware_t *)AW_TryMalloc(sizeof(aw_dial_ware_t)*WARE_ROWS)))return;
    if(!ware_label && !(ware_label=(char (*)[64])AW_TryMalloc(64*WARE_ROWS)))return;
    AW_MwscriptPersons(speaker_record,speaker_reference,&player,&npc,&fight,&flee);
    n=page==4?AW_MwscriptStock(speaker_record,speaker_reference,wares,WARE_ROWS):AW_MwscriptPlayerWares(wares,WARE_ROWS);
    for(i=0;i<n;i++){
        if(!trades(wares[i].category,wares[i].enchanted))continue;
        wares[k]=wares[i];
        ware_price[k]=AW_DialBarterOffer(&table,wares[k].value,page==4,&player,&npc,disposition);
        Q_snprintf(ware_label[k],64,"%s (%d) - %d%s",wares[k].name,wares[k].count,ware_price[k],T(AW_DIAL_TEXT_GP,"gp"));
        k++;
    }
    ware_count=k;mode=page;refresh();
}
static void trade(int k){
    if(k<0 || k>=ware_count)return;
    if(mode==4 && AW_MwscriptPlayerGold(0)<ware_price[k])return;
    if(AW_MwscriptTrade(speaker_record,speaker_reference,&wares[k],mode==4,ware_price[k]))barter_open(mode);
    else if(mode==5)append("(The merchant cannot take more kinds of things in this build.)",0);
}
/* Repair (OpenMW MerchantRepair): the player's weapons and armour below full health, by name, each at the game's
 * price for the missing points through the offer; mending sets it to full */
static void repair_open(void){
    aw_dial_person_t player,npc;int fight,flee,i,j,n;
    if(!wares && !(wares=(aw_dial_ware_t *)AW_TryMalloc(sizeof(aw_dial_ware_t)*WARE_ROWS)))return;
    if(!ware_label && !(ware_label=(char (*)[64])AW_TryMalloc(64*WARE_ROWS)))return;
    AW_MwscriptPersons(speaker_record,speaker_reference,&player,&npc,&fight,&flee);
    n=AW_MwscriptRepairables(wares,ware_max,ware_now,WARE_ROWS);
    for(i=1;i<n;i++)for(j=i;j>0 && Q_strcasecmp(wares[j-1].name,wares[j].name)>0;j--){   /* by name (any case) */
        aw_dial_ware_t w=wares[j];int a=ware_max[j],b=ware_now[j];
        wares[j]=wares[j-1];ware_max[j]=ware_max[j-1];ware_now[j]=ware_now[j-1];wares[j-1]=w;ware_max[j-1]=a;ware_now[j-1]=b;
    }
    for(i=0;i<n;i++){
        ware_price[i]=AW_DialRepairPrice(&table,wares[i].value,ware_max[i],ware_now[i],&player,&npc,disposition);
        Q_snprintf(ware_label[i],64,"%s - %d%s",wares[i].name,ware_price[i],T(AW_DIAL_TEXT_GP,"gp"));
    }
    ware_count=n;mode=6;refresh();
}
static void mend(int k){
    if(k<0 || k>=ware_count || AW_MwscriptPlayerGold(0)<ware_price[k])return;
    if(AW_MwscriptMend(wares[k].id)){AW_MwscriptPlayerGold(-ware_price[k]);repair_open();}
}
/* the effect EFFECT's record: its name, flags and base cost (AMGE); a fallback name when the table has none */
static int sm_effect_info(int effect,aw_mgef_t *m,char *name,int capacity){
    int ok=AW_ActorMagicEffect(effect,m);
    Q_snprintf(name,capacity,"%s",ok && m->name[0]?m->name:"Effect");
    if(!ok){memset(m,0,sizeof(*m));Q_snprintf(name,capacity,"Effect %d",effect);}
    return ok;
}
/* the ranges an effect allows (MGEF CastSelf 0x40, CastTouch 0x80, CastTarget 0x100); the first allowed */
static int sm_range_ok(const aw_mgef_t *m,int range){return (m->flags&(0x40u<<range))!=0 || !(m->flags&0x1C0u);}
static void sm_effects(aw_dial_effect_t *out){
    int i;aw_mgef_t m;char name[32];
    for(i=0;i<sm->effects;i++){
        const aw_spell_effect_t *e=&sm->effect[i];
        sm_effect_info(e->effect,&m,name,sizeof(name));
        out[i].base_cost=m.base_cost;out[i].flags=(int)m.flags;out[i].magnitude_min=e->magnitude_min;
        out[i].magnitude_max=e->magnitude_max;out[i].duration=e->duration;out[i].area=e->area;out[i].range=e->range;
    }
}
static const char *sm_range_word(int r){
    return r==0?T(AW_DIAL_TEXT_RANGE_SELF,"Self"):r==1?T(AW_DIAL_TEXT_RANGE_TOUCH,"Touch"):T(AW_DIAL_TEXT_RANGE_TARGET,"Target");
}
static void sm_labels(void){
    aw_dial_person_t player,npc;int fight,flee,i,cost,price;aw_dial_effect_t e[AW_MADE_EFFECTS];aw_mgef_t m;char name[32];
    Q_snprintf(sm_label[0],64,"%s: %s_",T(AW_DIAL_TEXT_NAME,"Name"),sm->name);
    for(i=0;i<sm->effects;i++){
        const aw_spell_effect_t *x=&sm->effect[i];
        sm_effect_info(x->effect,&m,name,sizeof(name));
        Q_snprintf(sm_label[1+i],64,"%s%s %u-%u %u %u %s",i==sm_edit?"> ":"",name,x->magnitude_min,x->magnitude_max,
                   x->duration,x->area,sm_range_word(x->range));
    }
    if(sm_edit>=0 && sm_edit<sm->effects){
        const aw_spell_effect_t *x=&sm->effect[sm_edit];
        Q_snprintf(sm_label[9],64,"  %s min: %u",T(AW_DIAL_TEXT_MAGNITUDE,"Magnitude"),x->magnitude_min);
        Q_snprintf(sm_label[10],64,"  %s max: %u",T(AW_DIAL_TEXT_MAGNITUDE,"Magnitude"),x->magnitude_max);
        Q_snprintf(sm_label[11],64,"  %s: %u %s",T(AW_DIAL_TEXT_DURATION,"Duration"),x->duration,T(AW_DIAL_TEXT_SECONDS,"secs"));
        Q_snprintf(sm_label[12],64,"  %s: %u %s",T(AW_DIAL_TEXT_AREA,"Area"),x->area,T(AW_DIAL_TEXT_FEET,"ft"));
        Q_snprintf(sm_label[13],64,"  %s: %s",T(AW_DIAL_TEXT_RANGE,"Range"),sm_range_word(x->range));
    }
    sm_effects(e);
    AW_MwscriptPersons(speaker_record,speaker_reference,&player,&npc,&fight,&flee);
    cost=AW_DialSpellmakingCost(&table,e,sm->effects);price=AW_DialSpellmakingPrice(&table,e,sm->effects,&player,&npc,disposition);
    Q_snprintf(sm_label[14],64,"%s (%s %d, %d%s)",T(AW_DIAL_TEXT_BUY,"Buy"),T(AW_DIAL_TEXT_POINT_COST,"Point Cost"),cost,price,
               T(AW_DIAL_TEXT_GP,"gp"));
    for(i=0;i<sm_known_count;i++){
        sm_effect_info(sm_known[i].effect,&m,name,sizeof(name));
        Q_snprintf(sm_label[16+i],64,"%s",name);
    }
}
static void spellmaking_open(void){
    if(!sm && !(sm=(aw_made_spell_t *)AW_TryCalloc(1,sizeof(aw_made_spell_t))))return;
    if(!sm_known && !(sm_known=(aw_spell_effect_t *)AW_TryMalloc(sizeof(aw_spell_effect_t)*SM_KNOWN)))return;
    if(!sm_label && !(sm_label=(char (*)[64])AW_TryMalloc(64*SM_LABELS)))return;
    sm_known_count=AW_MwscriptKnownEffects(sm_known,SM_KNOWN);
    sm_edit=sm->effects?sm->effects-1:-1;
    sm_labels();mode=7;refresh();
}
/* Left and Right on a field change it by one (choosing it: up by one); a range steps through the allowed ones */
static void sm_change(int field,int step){
    aw_spell_effect_t *x;aw_mgef_t m;char name[32];int v,i;
    if(!sm || sm_edit<0 || sm_edit>=sm->effects)return;
    x=&sm->effect[sm_edit];sm_effect_info(x->effect,&m,name,sizeof(name));
    if(field==4){
        for(i=0;i<3;i++){x->range=(unsigned char)((x->range+(step>0?1:2))%3);if(sm_range_ok(&m,x->range))break;}
    }else{
        unsigned short *p=field==0?&x->magnitude_min:field==1?&x->magnitude_max:field==2?&x->duration:&x->area;
        if((field<2 && (m.flags&AW_DIAL_MGEF_NO_MAGNITUDE)) || (field==2 && (m.flags&AW_DIAL_MGEF_NO_DURATION)))return;
        /* the limits of the original's effect editor (no game setting holds them; its sliders, as OpenMW 0.51 keeps
         * them in files/data/mygui/openmw_edit_effect.layout): magnitude 1..100, duration 1..1440, area 0..50 */
        v=(int)*p+step;if(v<(field==3?0:1))v=field==3?0:1;if(v>(field==3?50:field==2?1440:100))v=field==3?50:field==2?1440:100;
        *p=(unsigned short)v;
        if(x->magnitude_max<x->magnitude_min){if(field==0)x->magnitude_max=x->magnitude_min;else x->magnitude_min=x->magnitude_max;}
    }
    sm_labels();
}
static void sm_add(int k){
    aw_spell_effect_t *x;aw_mgef_t m;char name[32];
    if(!sm || k<0 || k>=sm_known_count || sm->effects>=AW_MADE_EFFECTS)return;
    x=&sm->effect[sm->effects];*x=sm_known[k];
    sm_effect_info(x->effect,&m,name,sizeof(name));
    x->magnitude_min=x->magnitude_max=1;x->duration=(m.flags&AW_DIAL_MGEF_NO_DURATION)?0:1;x->area=0;x->range=0;
    while(x->range<2 && !sm_range_ok(&m,x->range))x->range++;
    sm_edit=sm->effects++;
    sm_labels();mode=7;refresh();
}
/* Buy (OpenMW onBuyButtonClicked): an effect, a name, a cost above 0 and the gold; then the spell is the player's */
static void sm_buy(void){
    aw_dial_person_t player,npc;int fight,flee,price;aw_dial_effect_t e[AW_MADE_EFFECTS];
    if(!sm->effects){append(T(AW_DIAL_TEXT_NEED_EFFECT,"You have to add at least one effect to a spell."),0);return;}
    if(!sm->name[0]){append(T(AW_DIAL_TEXT_NEED_NAME,"You have to name the spell before buying it."),0);return;}
    sm_effects(e);
    if(AW_DialSpellmakingCost(&table,e,sm->effects)<=0){append(T(AW_DIAL_TEXT_ZERO_COST,"You cannot buy a spell that has a zero point cost."),0);return;}
    AW_MwscriptPersons(speaker_record,speaker_reference,&player,&npc,&fight,&flee);
    price=AW_DialSpellmakingPrice(&table,e,sm->effects,&player,&npc,disposition);
    if(AW_MwscriptPlayerGold(0)<price){append(T(AW_DIAL_TEXT_NO_GOLD_SPELL,"You do not have enough gold to buy this spell."),0);return;}
    if(AW_MadeSpellAdd(sm)<0){append("(No room for another made spell in this build.)",0);return;}
    AW_MwscriptPlayerGold(-price);
    memset(sm,0,sizeof(*sm));sm_edit=-1;mode=0;refresh();
}
static int en_soul(void){return en_gem>=0?AW_GemSoul(en_gem):0;}
static int en_constant(void){return en && en->cast_type==3;}
static void en_effects(aw_dial_effect_t *out){
    int i;aw_mgef_t m;char name[32];
    for(i=0;i<en->effects;i++){
        const aw_spell_effect_t *e=&en->effect[i];
        sm_effect_info(e->effect,&m,name,sizeof(name));
        out[i].base_cost=m.base_cost;out[i].flags=(int)m.flags;out[i].magnitude_min=e->magnitude_min;
        out[i].magnitude_max=e->magnitude_max;out[i].duration=e->duration;out[i].area=e->area;out[i].range=e->range;
    }
}
static const char *en_style_word(int s){
    return s==0?T(AW_DIAL_TEXT_CAST_ONCE,"Cast Once"):s==1?T(AW_DIAL_TEXT_CAST_STRIKES,"Cast When Strikes"):
           s==2?T(AW_DIAL_TEXT_CAST_USED,"Cast When Used"):T(AW_DIAL_TEXT_CAST_CONSTANT,"Constant Effect");
}
static void en_labels(void){
    aw_dial_person_t player,npc;int fight,flee,i,cost,price,chance,capacity;aw_dial_effect_t e[AW_MADE_EFFECTS];
    aw_mgef_t m;char name[32];float points;
    Q_snprintf(en_label[0],64,"%s: %s_",T(AW_DIAL_TEXT_NAME,"Name"),en->name);
    capacity=en_item>=0?AW_DialEnchantCapacity(&table,(float)en_points[en_item]):0;
    Q_snprintf(en_label[1],64,"%s: %s (%d)",T(AW_DIAL_TEXT_ITEM,"Item"),en_item>=0?en_wares[en_item].name:"-",capacity);
    {char gem[40];int creature;
     if(en_gem>=0 && AW_GemAt(en_gem,gem,sizeof(gem),&creature))Q_snprintf(en_label[2],64,"%s: %s (%d)",T(AW_DIAL_TEXT_SOUL,"Soul"),gem,en_soul());
     else Q_snprintf(en_label[2],64,"%s: -",T(AW_DIAL_TEXT_SOUL,"Soul"));}
    Q_snprintf(en_label[3],64,"%s",en_style_word(en->cast_type));
    for(i=0;i<en->effects;i++){
        const aw_spell_effect_t *x=&en->effect[i];
        sm_effect_info(x->effect,&m,name,sizeof(name));
        Q_snprintf(en_label[4+i],64,"%s%s %u-%u %u %u %s",i==en_edit?"> ":"",name,x->magnitude_min,x->magnitude_max,
                   x->duration,x->area,sm_range_word(x->range));
    }
    if(en_edit>=0 && en_edit<en->effects){
        const aw_spell_effect_t *x=&en->effect[en_edit];
        Q_snprintf(en_label[12],64,"  %s min: %u",T(AW_DIAL_TEXT_MAGNITUDE,"Magnitude"),x->magnitude_min);
        Q_snprintf(en_label[13],64,"  %s max: %u",T(AW_DIAL_TEXT_MAGNITUDE,"Magnitude"),x->magnitude_max);
        Q_snprintf(en_label[14],64,"  %s: %u %s",T(AW_DIAL_TEXT_DURATION,"Duration"),x->duration,T(AW_DIAL_TEXT_SECONDS,"secs"));
        Q_snprintf(en_label[15],64,"  %s: %u %s",T(AW_DIAL_TEXT_AREA,"Area"),x->area,T(AW_DIAL_TEXT_FEET,"ft"));
        Q_snprintf(en_label[16],64,"  %s: %s",T(AW_DIAL_TEXT_RANGE,"Range"),sm_range_word(x->range));
    }
    en_effects(e);
    AW_MwscriptPersons(speaker_record,speaker_reference,&player,&npc,&fight,&flee);
    points=AW_DialEnchantPoints(&table,e,en->effects,en_constant(),0);
    cost=AW_DialEnchantCastCost(&table,e,en->effects,en_constant(),AW_MwscriptPlayerSkill(9,0));
    price=AW_DialEnchantPrice(&table,e,en->effects,en_constant(),&player,&npc,disposition);
    chance=AW_DialEnchantChance(&table,e,en->effects,en_constant(),AW_MwscriptSpeakerStat(speaker_record,speaker_reference,AWA_SKILL+9),
                                AW_MwscriptSpeakerStat(speaker_record,speaker_reference,AWA_ATTRIBUTE+1),npc.luck,npc.fatigue);
    Q_snprintf(en_label[17],64,"%s (%s %d/%d, %s %d, %s %d, %d%s)",T(AW_DIAL_TEXT_BUY,"Buy"),T(AW_DIAL_TEXT_POINT_COST,"Point Cost"),
               (int)points,capacity,T(AW_DIAL_TEXT_CAST_COST,"Cast Cost"),cost,T(AW_DIAL_TEXT_CHANCE,"Chance"),chance,price,
               T(AW_DIAL_TEXT_GP,"gp"));
    for(i=0;i<en_items;i++)Q_snprintf(en_label[20+i],64,"%s (%d)",en_wares[i].name,AW_DialEnchantCapacity(&table,(float)en_points[i]));
    for(i=0;i<AW_GemCount() && i<64;i++){char gem[40];int creature;
        AW_GemAt(i,gem,sizeof(gem),&creature);Q_snprintf(en_label[44+i],64,"%s (%d)",gem,AW_GemSoul(i));}
}
static void enchanting_open(void){
    if(!en && !(en=(aw_made_item_t *)AW_TryCalloc(1,sizeof(aw_made_item_t))))return;
    if(!en_wares && !(en_wares=(aw_dial_ware_t *)AW_TryMalloc(sizeof(aw_dial_ware_t)*EN_ITEMS)))return;
    if(!en_label && !(en_label=(char (*)[64])AW_TryMalloc(64*EN_LABELS)))return;
    if(!sm_known && !(sm_known=(aw_spell_effect_t *)AW_TryMalloc(sizeof(aw_spell_effect_t)*SM_KNOWN)))return;
    if(!sm_label && !(sm_label=(char (*)[64])AW_TryMalloc(64*SM_LABELS)))return;
    if(!sm && !(sm=(aw_made_spell_t *)AW_TryCalloc(1,sizeof(aw_made_spell_t))))return;
    sm_known_count=AW_MwscriptKnownEffects(sm_known,SM_KNOWN);sm_labels();   /* the effect names for page 12 */
    en_items=AW_MwscriptEnchantables(en_wares,en_points,en_kind,EN_ITEMS);
    if(en_item>=en_items)en_item=-1;
    if(en_gem>=AW_GemCount())en_gem=-1;
    en_labels();mode=9;refresh();
}
static void en_change(int field,int step){
    aw_spell_effect_t *x;aw_mgef_t m;char name[32];int v,i;
    if(!en || en_edit<0 || en_edit>=en->effects)return;
    x=&en->effect[en_edit];sm_effect_info(x->effect,&m,name,sizeof(name));
    if(field==4){
        if(en_constant())return;                                   /* a constant effect is on the wearer */
        for(i=0;i<3;i++){x->range=(unsigned char)((x->range+(step>0?1:2))%3);if(sm_range_ok(&m,x->range))break;}
    }else{
        unsigned short *p=field==0?&x->magnitude_min:field==1?&x->magnitude_max:field==2?&x->duration:&x->area;
        if((field<2 && (m.flags&AW_DIAL_MGEF_NO_MAGNITUDE)) || (field==2 && ((m.flags&AW_DIAL_MGEF_NO_DURATION) || en_constant())))return;
        /* the original editor's limits (as for Spellmaking) */
        v=(int)*p+step;if(v<(field==3?0:1))v=field==3?0:1;if(v>(field==3?50:field==2?1440:100))v=field==3?50:field==2?1440:100;
        *p=(unsigned short)v;
        if(x->magnitude_max<x->magnitude_min){if(field==0)x->magnitude_max=x->magnitude_min;else x->magnitude_min=x->magnitude_max;}
    }
    en_labels();
}
static void en_set_style(void){
    if(en_item<0)return;
    en->cast_type=(unsigned char)AW_DialNextCastStyle(en_kind[en_item],en->cast_type,en_soul(),&table);
    if(en_constant()){int i;for(i=0;i<en->effects;i++)en->effect[i].range=0;}
    en_labels();
}
static void en_add(int k){
    aw_spell_effect_t *x;aw_mgef_t m;char name[32];
    if(k<0 || k>=sm_known_count || en->effects>=AW_MADE_EFFECTS)return;
    x=&en->effect[en->effects];*x=sm_known[k];sm_effect_info(x->effect,&m,name,sizeof(name));
    x->magnitude_min=x->magnitude_max=1;x->duration=(m.flags&AW_DIAL_MGEF_NO_DURATION)?0:1;x->area=0;x->range=0;
    while(!en_constant() && x->range<2 && !sm_range_ok(&m,x->range))x->range++;
    en_edit=en->effects++;en_labels();mode=9;refresh();
}
/* Buy (OpenMW onBuyButtonClicked): an effect, a name, a soul, an item, the points within the item, the gold; at an
 * enchanter it always succeeds (OpenMW Enchanting::create: only self-enchanting rolls the chance) */
static void en_buy(void){
    aw_dial_person_t player,npc;int fight,flee,price;aw_dial_effect_t e[AW_MADE_EFFECTS];
    if(!en->effects){append(T(AW_DIAL_TEXT_NEED_ENCH_EFFECT,"You must add at least one effect to an enchantment"),0);return;}
    if(!en->name[0]){append(T(AW_DIAL_TEXT_NEED_NAME,"You have to name the spell before buying it."),0);return;}
    if(en_gem<0){append(T(AW_DIAL_TEXT_NEED_SOUL,"You must have a soul gem with a soul to make an Enchanted Item"),0);return;}
    if(en_item<0){append(T(AW_DIAL_TEXT_NEED_ITEM,"You have to have an item to enchant."),0);return;}
    en_effects(e);
    if((int)AW_DialEnchantPoints(&table,e,en->effects,en_constant(),0)>AW_DialEnchantCapacity(&table,(float)en_points[en_item])){
        append(T(AW_DIAL_TEXT_TOO_MUCH,"You cannot add more enchantment to an object than it can hold."),0);return;}
    AW_MwscriptPersons(speaker_record,speaker_reference,&player,&npc,&fight,&flee);
    price=AW_DialEnchantPrice(&table,e,en->effects,en_constant(),&player,&npc,disposition);
    if(AW_MwscriptPlayerGold(0)<price){append(T(AW_DIAL_TEXT_NO_GOLD_SPELL,"You do not have enough gold."),0);return;}
    Q_snprintf(en->base,sizeof(en->base),"%s",en_wares[en_item].id);
    en->charge=en->charge_max=en_constant()?0:(float)en_soul();
    if(!AW_MwscriptEnchant(en,en_gem)){append("(No room for another enchanted item in this build.)",0);return;}
    AW_MwscriptPlayerGold(-price);
    append(T(AW_DIAL_TEXT_ENCHANT_DONE,"You have successfully created an enchanted item"),0);
    memset(en,0,sizeof(*en));en_item=en_gem=en_edit=-1;mode=0;refresh();
}
/* Spells (OpenMW SpellBuyingWindow): the speaker's plain spells the player does not know, by name, each at
 * max(1, cost x fSpellValueMult) through the barter offer; what the player cannot pay is greyed out */
static void spells_open(void){
    aw_dial_person_t player,npc;int fight,flee,i;
    AW_MwscriptPersons(speaker_record,speaker_reference,&player,&npc,&fight,&flee);
    sale_count=AW_MwscriptSpellsForSale(speaker_record,speaker_reference,sale_spell,SPELL_ROWS,sale_name,sale_cost);
    for(i=0;i<sale_count;i++){
        sale_price[i]=AW_DialSpellPrice(&table,sale_cost[i],&player,&npc,disposition);
        Q_snprintf(sale_label[i],sizeof(sale_label[i]),"%s - %d%s",sale_name[i],sale_price[i],T(AW_DIAL_TEXT_GP,"gp"));
    }
    mode=3;refresh();
}
/* buying: the gold, the spell added to the player (a full list of spell changes refuses), the page made again */
static void buy_spell(int k){
    if(AW_MwscriptPlayerGold(0)<sale_price[k])return;
    if(!AW_MwscriptBuySpell(sale_spell[k])){append("(No room for another spell in this build.)",0);return;}
    AW_MwscriptPlayerGold(-sale_price[k]);
    spells_open();
}
/* one session: the gold, the NPC must know the skill better, the skill not past its governing attribute; then the skill
 * goes up by one, two hours pass and the conversation ends (OpenMW onTrainingSelected, onTrainingFinished) */
static void train(int k){
    int which=train_skill[k],base=AW_MwscriptPlayerSkill(which,0),attribute;
    if(AW_MwscriptPlayerGold(0)<train_price[k])return;
    if(train_npc[which]<=(float)base){append(T(AW_DIAL_TEXT_TRAINING_WORDS,"I cannot teach you any more of that."),0);return;}
    attribute=AW_DialSkillAttribute(&table,which,read_file,NULL);
    if(attribute>=0 && base>=AW_MwscriptPlayerAttribute(attribute)){
        append(T(AW_DIAL_TEXT_TRAINING_ATTRIBUTE,"You cannot train a skill above its governing attribute."),0);return;}
    /* LEVEL-UP-58: a trained skill counts toward level progress (OpenMW skillLevelUp with the "trainer" source: the
     * level progress and the governing attribute's counter). When levelling lands, call it here instead of the bare
     * raise; tests/test_dialogue_features.py test_training_waits_for_level_up keeps this note until then. */
    AW_MwscriptPlayerSkill(which,1);
    AW_MwscriptPlayerGold(-train_price[k]);
    AW_ClockAdvance(2*3600000);
    leave_after=1;
}
/* Service Refusal (OpenMW DialogueManager::checkServiceRefused): before a service opens, the speaker's "Service
 * Refusal" answer under this conversation's conditions; one that holds is said and the service stays shut */
static int service_refused(void){
    int topic=named_topic("service refusal");
    if(topic<0 || AW_DialPick(&conv,topic,&state,NULL)<0)return 0;
    answer_of(topic,"Service Refusal");return 1;
}
/* a row of the list: a topic, or the persuasion page's entries */
static void ask(int r){
    if(r<0 || r>=listed)return;
    if(list[r]<=CODE_CHOICE(0) && list[r]>CODE_CHOICE(CHOICES)){   /* the topic again, with this choice */
        int k=CODE_CHOICE(0)-list[r],topic=choice_topic;
        append(choice_text[k],0);
        conv.cond.choice=choice_number[k];choice_count=0;
        if(topic>=0)answer_of(topic,"");else refresh();
        return;
    }
    if(list[r]==CODE_PERSUASION){mode=1;refresh();return;}
    if(list[r]==CODE_BACK){mode=mode==8?7:mode>=10 && mode<=12?9:0;refresh();return;}
    if(list[r]==CODE_EN_ITEM){mode=10;refresh();return;}
    if(list[r]==CODE_EN_GEM){mode=11;refresh();return;}
    if(list[r]==CODE_EN_STYLE){en_set_style();refresh();return;}
    if(list[r]==CODE_EN_ADD){mode=12;refresh();return;}
    if(list[r]==CODE_EN_REMOVE){if(en && en->effects){en->effects--;en_edit=en->effects-1;en_labels();}refresh();return;}
    if(list[r]==CODE_EN_BUY){en_buy();return;}
    if(list[r]==CODE_EN_NAME)return;
    if(list[r]<=CODE_EN_EFFECT(0) && list[r]>CODE_EN_EFFECT(AW_MADE_EFFECTS)){en_edit=CODE_EN_EFFECT(0)-list[r];en_labels();refresh();return;}
    if(list[r]<=CODE_EN_FIELD(0) && list[r]>CODE_EN_FIELD(5)){en_change(CODE_EN_FIELD(0)-list[r],1);return;}
    if(list[r]<=CODE_EN_PICKITEM(0) && list[r]>CODE_EN_PICKITEM(EN_ITEMS)){
        en_item=CODE_EN_PICKITEM(0)-list[r];en->cast_type=(unsigned char)AW_DialNextCastStyle(en_kind[en_item],3,en_soul(),&table);
        en_labels();mode=9;refresh();return;}
    if(list[r]<=CODE_EN_PICKGEM(0) && list[r]>CODE_EN_PICKGEM(64)){en_gem=CODE_EN_PICKGEM(0)-list[r];en_labels();mode=9;refresh();return;}
    if(list[r]<=CODE_EN_PICK(0) && list[r]>CODE_EN_PICK(SM_KNOWN)){en_add(CODE_EN_PICK(0)-list[r]);return;}
    if(list[r]==CODE_SM_ADD){mode=8;refresh();return;}
    if(list[r]==CODE_SM_REMOVE){if(sm && sm->effects){sm->effects--;sm_edit=sm->effects-1;sm_labels();}refresh();return;}
    if(list[r]==CODE_SM_BUY){sm_buy();return;}
    if(list[r]==CODE_SM_NAME)return;
    if(list[r]<=CODE_SM_EFFECT(0) && list[r]>CODE_SM_EFFECT(AW_MADE_EFFECTS)){sm_edit=CODE_SM_EFFECT(0)-list[r];sm_labels();refresh();return;}
    if(list[r]<=CODE_SM_FIELD(0) && list[r]>CODE_SM_FIELD(5)){sm_change(CODE_SM_FIELD(0)-list[r],1);return;}
    if(list[r]<=CODE_SM_PICK(0) && list[r]>CODE_SM_PICK(SM_KNOWN)){sm_add(CODE_SM_PICK(0)-list[r]);return;}
    if(list[r]<=CODE_TRAIN(0) && list[r]>CODE_TRAIN(3)){train(CODE_TRAIN(0)-list[r]);return;}
    if(list[r]<=CODE_SPELL(0) && list[r]>CODE_SPELL(SPELL_ROWS)){buy_spell(CODE_SPELL(0)-list[r]);return;}
    if(list[r]==CODE_SWITCH){barter_open(mode==4?5:4);return;}
    if(list[r]<=CODE_WARE(0) && list[r]>CODE_WARE(WARE_ROWS)){
        if(mode==6)mend(CODE_WARE(0)-list[r]);else trade(CODE_WARE(0)-list[r]);
        return;
    }
    if(list[r]==CODE_TRAVEL){if(!service_refused())travel_after=1;return;}
    if(list[r]<=CODE_SERVICE(0) && list[r]>CODE_SERVICE(SERVICES)){
        /* the service windows come one by one (docs/DIALOGUE_FEATURES.md, services row); the refusal already holds */
        char line[80];
        if(service_refused())return;
        if(CODE_SERVICE(0)-list[r]==SERVICE_TRAINING){training_open();return;}
        if(CODE_SERVICE(0)-list[r]==SERVICE_SPELLS){spells_open();return;}
        if(CODE_SERVICE(0)-list[r]==SERVICE_BARTER){barter_open(4);return;}
        if(CODE_SERVICE(0)-list[r]==SERVICE_REPAIR){repair_open();return;}
        if(CODE_SERVICE(0)-list[r]==SERVICE_SPELLMAKING){spellmaking_open();return;}
        if(CODE_SERVICE(0)-list[r]==SERVICE_ENCHANTING){enchanting_open();return;}
        Q_snprintf(line,sizeof(line),"(%s: not in this build yet.)",services_shown[CODE_SERVICE(0)-list[r]]);
        append(line,0);return;
    }
    if(list[r]<=CODE_ACTION(0) && list[r]>CODE_ACTION(AW_PERSUADE_KINDS)){persuade(CODE_ACTION(0)-list[r]);refresh();return;}
    ask_topic(list[r]);
}
static int key(int k,int mouse_x,int mouse_y){
    int r=AW_LB_NONE;
    switch(k){
    case K_UPARROW:r=AW_ListBoxKey(&box,AW_LBKEY_UP);break;
    case K_DOWNARROW:r=AW_ListBoxKey(&box,AW_LBKEY_DOWN);break;
    case K_TAB:focus=nhits?(focus+1)%nhits:-1;return 1;      /* the next link on screen; Enter asks it */
    case K_PGUP:scroll+=text_rows()-1;break;                  /* the conversation text */
    case K_PGDN:scroll-=text_rows()-1;break;
    case K_HOME:r=AW_ListBoxKey(&box,AW_LBKEY_HOME);break;
    case K_END:r=AW_ListBoxKey(&box,AW_LBKEY_END);break;
    case K_BACKSPACE:case K_DEL:
        if(mode==7 && sm){size_t n=strlen(sm->name);if(n){sm->name[n-1]=0;sm_labels();}return 1;}   /* the name */
        if(mode==9 && en){size_t n=strlen(en->name);if(n){en->name[n-1]=0;en_labels();}return 1;}
        r=AW_ListBoxKey(&box,AW_LBKEY_BACKSPACE);break;
    case K_LEFTARROW:case K_RIGHTARROW:
        if(mode==7){int s=AW_ListBoxSelected(&box);
            if(s>=0 && s<listed && list[s]<=CODE_SM_FIELD(0) && list[s]>CODE_SM_FIELD(5))
                sm_change(CODE_SM_FIELD(0)-list[s],k==K_LEFTARROW?-1:1);}
        if(mode==9){int s=AW_ListBoxSelected(&box);
            if(s>=0 && s<listed && list[s]<=CODE_EN_FIELD(0) && list[s]>CODE_EN_FIELD(5))
                en_change(CODE_EN_FIELD(0)-list[s],k==K_LEFTARROW?-1:1);}
        return 1;
    case K_ENTER:
        if(focus>=0 && focus<nhits){ask_topic(hits[focus].topic);return 1;}
        r=AW_ListBoxKey(&box,AW_LBKEY_CHOOSE);break;
    case K_MWHEELUP:if(mouse_x<list_x())scroll+=3;else r=AW_ListBoxKey(&box,AW_LBKEY_UP);break;
    case K_MWHEELDOWN:if(mouse_x<list_x())scroll-=3;else r=AW_ListBoxKey(&box,AW_LBKEY_DOWN);break;
    case K_MOUSE1:
        if(mouse_x>=list_x() && mouse_x<list_x()+LIST_W && mouse_y>=button_y()-1 && mouse_y<button_y()-1+row_h())
            return 0;                                          /* Goodbye */
        {int h;for(h=0;h<nhits;h++)           /* a link in the conversation: ask its topic */
            if(mouse_x>=hits[h].x && mouse_x<hits[h].x+hits[h].w && mouse_y>=hits[h].y-1 && mouse_y<hits[h].y-1+row_h()){
                ask_topic(hits[h].topic);return 1;}}
        if(mouse_x>=list_x() && mouse_x<list_x()+LIST_W && mouse_y>=list_y()-1 && mouse_y<list_y()-1+list_rows()*row_h())
            r=AW_ListBoxClick(&box,(mouse_y-(list_y()-1))/row_h());
        else if(mouse_x<BOX_X || mouse_x>=BOX_X+BOX_W || mouse_y<BOX_Y || mouse_y>=BOX_Y+BOX_H)return 0;
        break;
    default:
        if(mode==9 && en && k>=32 && k<127){   /* typing names the enchanted item */
            size_t n=strlen(en->name);
            if(n<sizeof(en->name)-1){en->name[n]=(char)k;en->name[n+1]=0;en_labels();}
            return 1;
        }
        if(mode==7 && sm && k>=32 && k<127){   /* typing names the spell (up to 31 characters) */
            size_t n=strlen(sm->name);
            if(n<sizeof(sm->name)-1){sm->name[n]=(char)k;sm->name[n+1]=0;sm_labels();}
            return 1;
        }
        if(k>=32 && k<127)AW_ListBoxType(&box,k);
        break;
    }
    if(scroll<0)scroll=0;
    if(r==AW_LB_CHOSEN)ask(AW_ListBoxSelected(&box));
    return !fight_started && !travel_after && !leave_after;    /* the speaker attacks, or a service opens: the conversation ends */
}

int AW_DialWindowOpen(edict_t *e,const char *greeting,int again){
    aw_glut_cond_t cond;int k;keydest_t was=key_dest;
    if(active || !e || !load())return 0;
    if((row=AW_GlutSpeaker(e,again,&cond,&state))<0 || row>=table.npcs)return 0;
    {   /* the derived disposition: the bar, and what every Disposition test of this conversation reads */
        eval_t *id=GetEdictFieldValue(e,"aw_source_id"),*ref=GetEdictFieldValue(e,"aw_ref");
        AW_MwscriptDispositionFacts(id && id->string?pr_strings+id->string:NULL,ref?(uint32_t)ref->_float:0,
                                    cond.disposition,cond.faction,&facts);
        cond.disposition=disposition=AW_DialDisposition(&table,&facts,1);
        Q_snprintf(speaker_record,sizeof(speaker_record),"%s",id && id->string?pr_strings+id->string:"");
        speaker_reference=ref?(unsigned long)ref->_float:0;
        original_base=current_base=facts.base;permanent_change=0;mode=0;fight_started=travel_after=leave_after=0;
        choice_count=0;choice_topic=-1;goodbye_only=0;train_count=sale_count=0;
    }
    if(COM_FOpenFile((char *)path,&file)<0 || !file){file=NULL;return 0;}
    file_start=ftell(file);
    services=AW_DialServices(&table,row,read_file,NULL);     /* one read: the speaker's service flags */
    if((ui_texts=(char *)AW_TryMalloc((size_t)AW_DIAL_UI_TEXT*AW_DIAL_TEXTS))!=NULL &&
       !AW_DialUiTexts(&table,read_file,NULL,ui_texts)){free(ui_texts);ui_texts=NULL;}   /* else the fallback words */
    if(!(buffer=(unsigned char *)AW_TryMalloc(AW_DIAL_BUFFER)) || !(history=(char *)AW_TryMalloc(HISTORY)) ||
       !(paras=(para_t *)AW_TryMalloc(sizeof(para_t)*PARAS))){
        Con_Printf("Dialogue: not enough memory.\n");release();return 0;
    }
    if(!AW_DialConverse(&conv,&table,row,&cond,read_file,NULL,buffer,AW_DIAL_BUFFER)){
        Con_Printf("Dialogue: the conversation could not be read.\n");release();return 0;
    }
    if(!(names=(char *)AW_TryCalloc((size_t)(conv.topics>0?conv.topics:1),NAME_CHARS))){release();return 0;}
    for(k=0;k<conv.topics;k++){
        int length;long at=AW_DialTopicName(&table,conv.topic[k].topic,&length);
        if(length>NAME_CHARS-1)length=NAME_CHARS-1;
        if(at>=0 && read_file(NULL,at,names+NAME_CHARS*k,length))names[NAME_CHARS*k+length]=0;
    }
    speaker=e;history_len=0;nparas=0;nhits=0;focus=-1;scroll=0;
    topics_sync();                   /* the saved known topics: a loaded game, AddTopic since the last conversation */
    if(!greet()){                    /* the voice table's line when the dialogue table has no greeting for this speaker */
        char ranked[1024];
        rank_defines(greeting && *greeting?greeting:"...",ranked,sizeof(ranked));
        append(ranked,0);
    }
    memset(&box,0,sizeof(box));
    refresh();
    if(key_dest==key_console)key_dest=key_game;
    active=1;
    if(!AW_WorldUIOpenPanel(draw,key,closed)){key_dest=was;release();return 0;}
    return 1;
}
int AW_DialWindowActive(void){return active;}
/* RankRequirement (FACTION-RANK-58, aw_mwhost.c's live conditions): the faction's requirement row read from the
 * table (the open conversation's file, else opened for the read), the last row kept (116 bytes for the session) so a
 * greeting's or a topic's conditions read the disk once per faction in a row. */
static long rank_req_at=-1;static unsigned char rank_req_row[AW_DIAL_RANK_REQ];
static int read_rank_req(void *user,long offset,void *out,long bytes){
    FILE *f=file;long start=file_start;int ok;
    (void)user;
    if(bytes!=AW_DIAL_RANK_REQ || offset<0)return 0;
    if(offset!=rank_req_at){
        if(!f){if(COM_FOpenFile((char *)path,&f)<=0 || !f){if(f)fclose(f);return 0;}start=ftell(f);}
        ok=!fseek(f,start+offset,SEEK_SET) && fread(rank_req_row,1,AW_DIAL_RANK_REQ,f)==AW_DIAL_RANK_REQ;
        if(f!=file)fclose(f);
        if(!ok){rank_req_at=-1;return 0;}
        rank_req_at=offset;
    }
    memcpy(out,rank_req_row,AW_DIAL_RANK_REQ);
    return 1;
}
int AW_DialWindowRankRequirement(const char *faction,int rank,const short *attributes,const short *skills,int reputation){
    if(!load())return 0;
    return AW_DialRankRequirement(&table,faction,rank,attributes,skills,reputation,read_rank_req,NULL);
}
/* The journal's topic pages (aw_worldui.c): a topic's name and a heard entry's text from the table, the file opened
 * for the read when no conversation holds it. 1 read. */
static int read_journal(long at,char *out,int capacity){
    FILE *f=file;long start=file_start;int n;
    out[0]=0;
    if(at<0)return 0;
    if(!f){if(COM_FOpenFile((char *)path,&f)<=0 || !f){if(f)fclose(f);return 0;}start=ftell(f);}
    n=fseek(f,start+at,SEEK_SET)?0:(int)fread(out,1,(size_t)(capacity-1),f);
    if(f!=file)fclose(f);
    out[n<0?0:n]=0;
    return n>0;
}
int AW_DialWindowTopicName(int topic,char *out,int capacity){
    int length;long at;
    out[0]=0;
    if(!load() || (at=AW_DialTopicName(&table,topic,&length))<0)return 0;
    if(!read_journal(at,out,capacity))return 0;
    if(length<capacity)out[length]=0;
    return 1;
}
int AW_DialWindowEntryText(int entry,char *out,int capacity){
    unsigned char entry_row[AW_DIAL_ENTRY_ROW+1];char raw[1024];long text;int i,k=0;
    out[0]=0;
    if(!load() || entry<0 || entry>=table.entries || !read_journal(table.at_entries+(long)AW_DIAL_ENTRY_ROW*entry,(char *)entry_row,sizeof(entry_row)))return 0;
    text=((long)entry_row[0]<<24)|((long)entry_row[1]<<16)|((long)entry_row[2]<<8)|entry_row[3];
    if(text==(long)AW_DIAL_NONE32 || !read_journal(table.at_texts+text,raw,sizeof(raw)))return 0;
    for(i=0;raw[i] && k<capacity-1;i++)if(raw[i]!=0x40 && raw[i]!=0x23)out[k++]=raw[i];   /* the link markers dropped */
    out[k]=0;
    return 1;
}
/* the NPC's own facts into C, once, when its slot is made (the cell's load): the only reads of the aggro's disposition */
void AW_DialNpcPrepare(edict_t *e,aw_dial_npc_cache_t *c){
    aw_dial_facts_t f;eval_t *id,*ref;aw_glut_cond_t cond;aw_glut_state_t s;
    memset(c,0,sizeof(*c));c->ready=-1;
    if(!e || !load() || AW_GlutSpeaker(e,0,&cond,&s)<0)return;
    id=GetEdictFieldValue(e,"aw_source_id");ref=GetEdictFieldValue(e,"aw_ref");
    AW_MwscriptDispositionFacts(id && id->string?pr_strings+id->string:NULL,ref?(uint32_t)ref->_float:0,cond.disposition,
                                cond.faction,&f);
    c->same_race=(signed char)f.same_race;c->base=(short)cond.disposition;
    Q_snprintf(c->faction,sizeof(c->faction),"%s",cond.faction?cond.faction:"");
    c->actor_row=AW_MwscriptActorRow(id && id->string?pr_strings+id->string:NULL);
    c->ready=1;
}
/* on the engage tick: no file read (only the cached facts, the actor record in memory and the player's side) */
int AW_DialNpcDisposition(edict_t *e,const aw_dial_npc_cache_t *c){
    aw_dial_facts_t f;eval_t *ref;
    if(!e || !c || c->ready<=0 || !resident)return 50;
    ref=GetEdictFieldValue(e,"aw_ref");
    memset(&f,0,sizeof(f));
    AW_MwscriptDispositionNow(c->actor_row,ref?(unsigned long)ref->_float:0,c->base,&f);
    f.same_race=c->same_race;f.faction=c->faction[0]?c->faction:NULL;
    return AW_DialDisposition(&table,&f,1);
}

/* dbg npcs talk [record id] (aw_debug.c): Talk with the nearest NPC that can be talked to (or the named record), as E does on
 * the one under the crosshair, the player turned to face it; for checks and pictures (the window is the same). */
void AW_DialWindowTalk(const char *want){
    edict_t *p,*e,*best=NULL;int i;float best_d=1e9f,d;vec3_t delta;char text[1024];
    eval_t *v,*count;
    if(!sv.active || svs.maxclients<1 || !(p=svs.clients[0].edict)){Con_Printf("Not in a game.\n");return;}
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);
        if(e->free || strcmp(pr_strings+e->v.classname,"aw_npc") || !AW_CanTalk(e) || AW_GlutNpcOf(e)<0)continue;
        if(want){v=GetEdictFieldValue(e,"aw_source_id");if(!v || !v->string || Q_strcasecmp(pr_strings+v->string,(char *)want))continue;}
        VectorSubtract(e->v.origin,p->v.origin,delta);d=Length(delta);
        if(d<best_d){best_d=d;best=e;}
    }
    if(!best){Con_Printf("No NPC to talk to%s%s.\n",want?" named ":"",want?want:"");return;}
    VectorSubtract(best->v.origin,p->v.origin,delta);delta[2]=0;
    p->v.angles[0]=0;p->v.angles[1]=(float)(atan2(delta[1],delta[0])*180/M_PI);p->v.angles[2]=0;p->v.fixangle=1;
    count=GetEdictFieldValue(best,"aw_manual_count");
    v=GetEdictFieldValue(best,count && count->_float>0?"aw_greeting_again":"aw_greeting");
    if((!v || !v->string || !pr_strings[v->string]) && count && count->_float>0)v=GetEdictFieldValue(best,"aw_greeting");
    if(v && v->string && pr_strings[v->string])AW_ExpandDialogue(text,sizeof(text),pr_strings+v->string);
    else if(!AW_GlutConverse(best,count && count->_float>0,text,sizeof(text)))text[0]=0;
    if(count)count->_float+=1;
    Con_Printf("Talk: %s (%.0f units)\n",pr_strings+best->v.netname,best_d);
    if(!AW_DialWindowOpen(best,text,count && count->_float>1))Con_Printf("Talk: no dialogue window for this NPC.\n");
}
static int journal_entry_filled(int entry,char *out,int capacity){   /* the entry with its %-values filled */
    char said[1024];
    if(!AW_DialWindowEntryText(entry,said,sizeof(said)))return 0;
    AW_ExpandDialogue(out,capacity,said);
    return 1;
}
static int journal_read(void *user,long offset,void *out,long bytes){   /* aw_dial_read_t over read_journal */
    char buf[AW_DIAL_ENTRY_ROW+AW_DIAL_LINK_ROW+2];
    (void)user;
    if(bytes<=0 || bytes>(long)sizeof(buf)-1 || !read_journal(offset,buf,(int)bytes+1))return 0;
    memcpy(out,buf,(size_t)bytes);
    return 1;
}
/* The journal's links (OpenMW JournalWindow: the topic names in a page are links to their topic pages): the entry with
 * AW_DIAL_LINK_OPEN/CLOSE around each of its builder-made spans, its %-values filled, the spans' topics into TOPICS in
 * the same order. The number of links, -1 when the entry cannot be read. Read from disk; nothing kept. */
static int journal_entry_marked(int entry,char *out,int capacity,unsigned short *topics,int max){
    unsigned char entry_row[AW_DIAL_ENTRY_ROW+1];char raw[1024],marked[1100],plain[1100];aw_dial_span_t spans[PARA_SPANS];
    long text;int n,i,k=0;
    out[0]=0;
    if(!load() || entry<0 || entry>=table.entries || !read_journal(table.at_entries+(long)AW_DIAL_ENTRY_ROW*entry,(char *)entry_row,sizeof(entry_row)))return -1;
    text=((long)entry_row[0]<<24)|((long)entry_row[1]<<16)|((long)entry_row[2]<<8)|entry_row[3];
    if(text==(long)AW_DIAL_NONE32 || !read_journal(table.at_texts+text,raw,sizeof(raw)))return -1;
    n=AW_DialEntrySpans(&table,entry_row,journal_read,NULL,spans,PARA_SPANS);
    AW_DialMarkSpans(raw,spans,n,marked,sizeof(marked));
    for(i=0;marked[i] && k<(int)sizeof(plain)-1;i++)if(marked[i]!=0x40 && marked[i]!=0x23)plain[k++]=marked[i];
    plain[k]=0;
    AW_ExpandDialogue(out,capacity,plain);
    for(i=0;i<n && i<max;i++)topics[i]=spans[i].topic;
    return n<max?n:max;
}
/* "Your journal has been updated." (OpenMW Journal::addEntry: messageBox #{sJournalEntry}, no sound of its own): the
 * game's own GMST from the table's words, shown as a timed notice; 1 read, nothing kept */
static void journal_updated(void){
    char words[AW_DIAL_UI_TEXT+1];
    if(!load() || !read_journal(table.at_ui_texts+(long)AW_DIAL_UI_TEXT*AW_DIAL_TEXT_JOURNAL_ENTRY,words,sizeof(words)))return;
    words[AW_DIAL_UI_TEXT-1]=0;
    if(words[0])AW_MsgBoxShow(words,NULL,0);
}
void AW_DialWindowInit(void){   /* the journal book's topic pages read through these (aw_worldui.c) */
    aw_journal_heard_count=AW_DialHeardCount;aw_journal_heard_at=AW_DialHeardAt;
    aw_journal_topic_name=AW_DialWindowTopicName;aw_journal_entry_text=journal_entry_filled;
    aw_journal_entry_marked=journal_entry_marked;aw_journal_updated=journal_updated;
}
