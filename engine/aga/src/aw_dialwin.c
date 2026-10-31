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
 * Not yet (later steps of the design): result scripts and choices, disposition changes and persuasion, saving the
 * known topics, topics named in the greeting.
 */
#include "quakedef.h"
#include "aw_dial.h"
#include "aw_listbox.h"
#include "aw_statswin.h"
#include "aw_tryalloc.h"
#include "aw_talk.h"

#define BOX_X 8
#define BOX_Y 6
#define BOX_W 304
#define BOX_H 188
#define PAD 6
#define LIST_W 104                  /* the topic column: 12 characters */
#define HISTORY 6144                /* the conversation text kept while it is open (oldest paragraphs dropped) */
#define NAME_CHARS 32
#define HEADING '\001'              /* a paragraph that is a topic's name */

static const char path[]="dialogue.lut";
static aw_dial_t table;
static unsigned char *resident,*known;
static int loaded;                  /* 0 not tried, 1 usable, -1 unavailable (logged once) */

static int active,row,listed,scroll,disposition;
static aw_dial_facts_t facts;      /* the speaker's disposition facts while the conversation is open */
static edict_t *speaker;
static FILE *file;
static long file_start;
static unsigned char *buffer;
static char *names,*history;        /* names: NAME_CHARS per topic of the NPC's row */
static int history_len;
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
        fclose(f);Con_Printf("Dialogue: %s is not AWDL1\n",path);return 0;
    }
    if(!(resident=(unsigned char *)AW_TryMalloc((size_t)resident_size))){fclose(f);Con_Printf("Dialogue: no memory for %ld bytes\n",resident_size);return 0;}
    memcpy(resident,header,AW_DIAL_HEADER);
    if((long)fread(resident+AW_DIAL_HEADER,1,(size_t)(resident_size-AW_DIAL_HEADER),f)!=resident_size-AW_DIAL_HEADER ||
       !AW_DialOpen(&table,resident,resident_size,size) ||
       !(known=(unsigned char *)AW_TryMalloc((size_t)AW_DialKnownBytes(&table)))){
        fclose(f);free(resident);resident=NULL;memset(&table,0,sizeof(table));Con_Printf("Dialogue: %s is damaged\n",path);return 0;
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
static void read_string(long at,char *out,int capacity) {
    int n;
    out[0]=0;
    if(at<0 || !file || fseek(file,file_start+at,SEEK_SET))return;
    n=(int)fread(out,1,(size_t)(capacity-1),file);
    out[n<0?0:n]=0;
}

/* the conversation text: paragraphs ended by '\n', a heading starts with HEADING */
static void append(const char *text,int heading) {
    int n=(int)strlen(text)+2;
    if(n>HISTORY-1)n=HISTORY-1;
    while(history_len && history_len+n>HISTORY-1){       /* drop the oldest paragraph */
        char *end=memchr(history,'\n',(size_t)history_len);
        int cut=end?(int)(end-history)+1:history_len;
        memmove(history,history+cut,(size_t)(history_len-cut));history_len-=cut;
    }
    if(heading)history[history_len++]=HEADING;
    memcpy(history+history_len,text,(size_t)(n-2));history_len+=n-2;
    history[history_len++]='\n';history[history_len]=0;
    scroll=0;                                                  /* show the newest */
}

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
    if(r<0 || r>=listed || (k=AW_DialFind(&conv,list[r]))<0)return "";
    return names+NAME_CHARS*k;
}
static void refresh(void){
    int keep=AW_ListBoxSelected(&box),at=keep>=0 && keep<listed?list[keep]:-1,i;
    listed=AW_DialTopicList(&conv,known,&state,list,AW_DIAL_MAX_TOPICS);
    AW_ListBoxReset(&box,listed,label,NULL,shown,list_rows());
    for(i=0;i<box.shown_count;i++)if(list[box.shown[i]]==at){box.selection=i;break;}
}

static void release(void){
    if(file){fclose(file);file=NULL;}
    free(buffer);buffer=NULL;free(names);names=NULL;free(history);history=NULL;
    memset(&conv,0,sizeof(conv));active=0;speaker=NULL;listed=0;history_len=0;
}
static void closed(void){release();}

/* the lines of the conversation that fit, newest at the bottom (SCROLL lines up) */
/* one pass over the wrapped lines: count them (DRAW 0) or draw those from line FIRST on */
static int history_lines(int draw,int first){
    int cols=text_cols(),rows=text_rows(),line=0,y=body_y(),heading,n;const char *p=history,*q;
    char para[1100],out[64];
    if(cols>(int)sizeof(out)-2)cols=(int)sizeof(out)-2;
    while(*p){
        const char *end=strchr(p,'\n');
        n=end?(int)(end-p):(int)strlen(p);
        heading=n>0 && *p==HEADING;
        if(heading){p++;n--;}
        if(n>(int)sizeof(para)-1)n=(int)sizeof(para)-1;
        memcpy(para,p,(size_t)n);para[n]=0;
        for(q=para;AW_DialWrapNext(&q,cols-(heading?2:0),out,sizeof(out));line++){
            if(!draw || line<first || line>=first+rows)continue;
            if(heading){
                AW_UIFill(BOX_X+PAD,y-1,cols*char_w(),row_h(),AW_UIColor(62,53,36));
                text(BOX_X+PAD+char_w(),y,out,list_x()-6);
            }else text(BOX_X+PAD,y,out,list_x()-6);
            y+=row_h();
        }
        p=end?end+1:p+strlen(p);
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
        text(list_x()+2,y,label(NULL,box.shown[box.top+i]),right);
    }
    if(!box.shown_count)text(list_x()+2,list_y(),"(no topics)",right);
    AW_UIFill(list_x(),button_y()-1,LIST_W,row_h(),dark);
    text(list_x()+(LIST_W-7*char_w())/2,button_y(),"Goodbye",right);
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
static void ask(int r){
    int topic,k,answer,i,n;unsigned short links[64];char raw[1024],ranked[1024],filled[1024];
    if(r<0 || r>=listed)return;
    topic=list[r];k=AW_DialFind(&conv,topic);
    append(k>=0?names+NAME_CHARS*k:"",1);
    if((answer=AW_DialAnswer(&conv,topic,&state))<0){append("...",0);refresh();return;}
    read_string(AW_DialTextAt(&conv,answer),raw,sizeof(raw));
    rank_defines(raw,ranked,sizeof(ranked));
    AW_GlutFill(speaker,row,ranked,filled,sizeof(filled));
    append(filled,0);
    n=AW_DialLinks(&conv,answer,read_file,NULL,links,64);
    for(i=0;i<n;i++)AW_DialKnow(&table,known,links[i]);
    refresh();
}
static int key(int k,int mouse_x,int mouse_y){
    int r=AW_LB_NONE;
    switch(k){
    case K_UPARROW:r=AW_ListBoxKey(&box,AW_LBKEY_UP);break;
    case K_DOWNARROW:case K_TAB:r=AW_ListBoxKey(&box,AW_LBKEY_DOWN);break;
    case K_PGUP:scroll+=text_rows()-1;break;                  /* the conversation text */
    case K_PGDN:scroll-=text_rows()-1;break;
    case K_HOME:r=AW_ListBoxKey(&box,AW_LBKEY_HOME);break;
    case K_END:r=AW_ListBoxKey(&box,AW_LBKEY_END);break;
    case K_BACKSPACE:case K_DEL:r=AW_ListBoxKey(&box,AW_LBKEY_BACKSPACE);break;
    case K_ENTER:r=AW_ListBoxKey(&box,AW_LBKEY_CHOOSE);break;
    case K_MWHEELUP:if(mouse_x<list_x())scroll+=3;else r=AW_ListBoxKey(&box,AW_LBKEY_UP);break;
    case K_MWHEELDOWN:if(mouse_x<list_x())scroll-=3;else r=AW_ListBoxKey(&box,AW_LBKEY_DOWN);break;
    case K_MOUSE1:
        if(mouse_x>=list_x() && mouse_x<list_x()+LIST_W && mouse_y>=button_y()-1 && mouse_y<button_y()-1+row_h())
            return 0;                                          /* Goodbye */
        if(mouse_x>=list_x() && mouse_x<list_x()+LIST_W && mouse_y>=list_y()-1 && mouse_y<list_y()-1+list_rows()*row_h())
            r=AW_ListBoxClick(&box,(mouse_y-(list_y()-1))/row_h());
        else if(mouse_x<BOX_X || mouse_x>=BOX_X+BOX_W || mouse_y<BOX_Y || mouse_y>=BOX_Y+BOX_H)return 0;
        break;
    default:
        if(k>=32 && k<127)AW_ListBoxType(&box,k);
        break;
    }
    if(scroll<0)scroll=0;
    if(r==AW_LB_CHOSEN)ask(AW_ListBoxSelected(&box));
    return 1;
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
    }
    if(COM_FOpenFile((char *)path,&file)<0 || !file){file=NULL;return 0;}
    file_start=ftell(file);
    if(!(buffer=(unsigned char *)AW_TryMalloc(AW_DIAL_BUFFER)) || !(history=(char *)AW_TryMalloc(HISTORY))){
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
    speaker=e;history[0]=0;history_len=0;scroll=0;
    {char ranked[1024];
     rank_defines(greeting && *greeting?greeting:"...",ranked,sizeof(ranked));
     append(ranked,0);}
    memset(&box,0,sizeof(box));
    refresh();
    if(key_dest==key_console)key_dest=key_game;
    active=1;
    if(!AW_WorldUIOpenPanel(draw,key,closed)){key_dest=was;release();return 0;}
    return 1;
}
int AW_DialWindowActive(void){return active;}

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
void AW_DialWindowInit(void){}
