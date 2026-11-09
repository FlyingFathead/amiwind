/* SPDX-License-Identifier: GPL-2.0-or-later */
/* DIALOGUE-LINKS-62 (v0.0.62-dev1: a link click in the dialogue text worked once, then clicks stopped): the window's
 * link path on aw_dial_links.c, by number. A small model of aw_dialwin.c's conversation (paragraphs with link spans,
 * the newest lines at the bottom, SCROLL lines up, the hits of the visible link runs rebuilt each frame) and of its
 * refresh (the linkable set follows the topic list); the clicks go through AW_DialLinkHit and the window's ask rule.
 * Each click must ask the right topic: A, then B in the new answer, then A again, in the topic list and in the
 * barter list, and after scrolling. The rule before the fix (the set rebuilt only while the topic list shows) is run
 * too and must lose the second click, which is the reported fault. */
#include <stdio.h>
#include <string.h>
#include "aw_dial_links.h"

#define TOPICS 5
enum{A,B,C,D,E};
#define COLS 16
#define ROWS 8
#define CW 8
#define RH 9
#define BODY 20
typedef struct {const char *text;int nspans;int off[4],len[4],topic[4];} para_t;
static para_t paras[32];static int nparas,scroll,nhits,known[TOPICS],answers[TOPICS],asked[64],nasked,barter;
static unsigned char bits[TOPICS/8+1];
static aw_dial_hit_t hits[48];
static int fixed_rule=1,failures;

static void refresh(void){
    int list[TOPICS],n=0,t;
    for(t=0;t<TOPICS;t++)if(known[t] && answers[t])list[n++]=t;
    if(fixed_rule || !barter)AW_DialLinksSet(bits,TOPICS,list,n);   /* before the fix: only with the topic list */
}
static void add(const char *text,int nspans,const int *off,const int *len,const int *topic){
    para_t *p=&paras[nparas++];int k;
    p->text=text;p->nspans=nspans;
    for(k=0;k<nspans;k++){p->off[k]=off[k];p->len[k]=len[k];p->topic[k]=topic[k];}
    scroll=0;
}
static int span_at(const para_t *p,int at){
    int k;
    for(k=0;k<p->nspans;k++)if(at>=p->off[k] && at<p->off[k]+p->len[k])return AW_DialLinkOn(bits,TOPICS,p->topic[k])?k:-1;
    return -1;
}
/* one frame: count the lines, then record the visible link runs (aw_dialwin.c history_lines) */
static void frame(void){
    int total=0,i,first,line=0,y=BODY;
    for(i=0;i<nparas;i++)total+=((int)strlen(paras[i].text)+COLS-1)/COLS;
    if(scroll>total-ROWS)scroll=total-ROWS;
    if(scroll<0)scroll=0;
    first=total-ROWS-scroll;if(first<0)first=0;
    nhits=0;
    for(i=0;i<nparas;i++){
        int len=(int)strlen(paras[i].text),base,j,k;
        for(base=0;base<len;base+=COLS,line++){
            if(line<first || line>=first+ROWS)continue;
            for(j=0;j<COLS && base+j<len;j++){
                if((k=span_at(&paras[i],base+j))<0)continue;
                if(j==0 || span_at(&paras[i],base+j-1)!=k){
                    aw_dial_hit_t *h=&hits[nhits++];int e=j;
                    while(e<COLS && base+e<len && span_at(&paras[i],base+e)==k)e++;
                    h->x=(short)(j*CW);h->y=(short)y;h->w=(short)((e-j)*CW);h->topic=(unsigned short)paras[i].topic[k];
                    h->para=(short)i;h->span=(short)k;
                }
            }
            y+=RH;
        }
    }
}
/* the answers: each names the next topics; asking one learns the topics it names that the speaker answers */
static void ask(int topic){
    static const int o1[]={0},l1[]={1},t1[]={B};
    static const int o2[]={0,6},l2[]={1,1},t2[]={A,C};
    static const int o3[]={4},l3[]={1},t3[]={B};
    asked[nasked++]=topic;
    add("--heading--",0,NULL,NULL,NULL);
    if(topic==A){add("B is the next topic to ask about.",1,o1,l1,t1);known[B]=1;}
    else if(topic==B){add("A and C are both worth a question.",2,o2,l2,t2);known[C]=1;}
    else add("Ask B again, or not.",1,o3,l3,t3);
    refresh();
}
/* a click on the first visible run of TOPIC (searching the hits as the player's eye would), through the window rule */
static int click(int topic){
    int h,x=-1,y=-1,before=nasked;
    frame();
    for(h=nhits-1;h>=0;h--)if(hits[h].topic==topic){x=hits[h].x+1;y=hits[h].y;break;}
    if(x<0)return -1;                                   /* not lit */
    h=AW_DialLinkHit(hits,nhits,x,y,RH);
    if(h>=0 && AW_DialLinkOn(bits,TOPICS,hits[h].topic))ask(hits[h].topic);   /* ask_link */
    return nasked>before?asked[nasked-1]:-2;            /* -2: lit, but the click asked nothing */
}
static void expect(const char *what,int got,int want){
    printf("%s: %d (want %d)\n",what,got,want);
    if(got!=want)failures++;
}
static void start(int rule,int in_barter){
    static const int o0[]={8},l0[]={1},t0[]={A};
    memset(paras,0,sizeof(paras));memset(known,0,sizeof(known));
    nparas=scroll=nhits=nasked=0;fixed_rule=rule;barter=0;
    answers[A]=answers[B]=answers[C]=1;answers[D]=answers[E]=0;known[A]=1;
    add("Ask me: A, if you like.",1,o0,l0,t0);
    refresh();
    barter=in_barter;                                   /* the player opened the barter list before clicking */
}
int main(void){
    int t,n=0;
    for(t=0;t<2;t++){
        start(1,t);
        expect(t?"barter: click A":"topics: click A",click(A),A);
        expect(t?"barter: click B in the new answer":"topics: click B in the new answer",click(B),B);
        expect(t?"barter: click A again":"topics: click A again",click(A),A);
        expect(t?"barter: click C":"topics: click C",click(C),C);
    }
    /* scrolled: the oldest A link scrolled back into view and clicked at its new place */
    start(1,1);
    click(A);click(B);click(A);click(B);
    frame();scroll=100;frame();                         /* PgUp to the top: the greeting's A visible again */
    {int h,x=-1,y=-1;for(h=0;h<nhits;h++)if(hits[h].para==0){x=hits[h].x;y=hits[h].y;break;}
     expect("scrolled up: the greeting's A is visible",y>=0,1);
     h=AW_DialLinkHit(hits,nhits,x+1,y,RH);
     if(h>=0 && AW_DialLinkOn(bits,TOPICS,hits[h].topic))ask(hits[h].topic);
     expect("scrolled up: the click asks",asked[nasked-1],A);}
    scroll=1;frame();
    for(t=0;t<nhits;t++)if(hits[t].topic==B)n++;
    expect("scrolled one line: B still clickable",n>0,1);
    /* a topic the speaker does not answer is never lit and a click on its text asks nothing */
    expect("unanswered topic D lit",AW_DialLinkOn(bits,TOPICS,D),0);
    /* the rule before the fix: in the barter list the second click is lost (the reported fault) */
    start(0,1);
    expect("old rule, barter: click A",click(A),A);
    expect("old rule, barter: click B (lost)",click(B),-1);
    /* a multi-word topic ("know you", topic E here) in mid-sentence, wrapped across two lines: lit only when the
     * speaker answers it, and then either part asks it; unanswered it is plain and a click on it asks nothing */
    {static const int o[]={13},l[]={8},tp[]={E};int h,parts=0,x0=-1,y0=-1,x1=-1,y1=-1;
     start(1,0);answers[E]=1;known[E]=1;refresh();
     add("Do you think know you is a topic?",1,o,l,tp);   /* "know you" = characters 13..20, wrapped at 16 */
     frame();
     for(h=0;h<nhits;h++)if(hits[h].topic==E){if(!parts){x0=hits[h].x;y0=hits[h].y;}else{x1=hits[h].x;y1=hits[h].y;}parts++;}
     expect("know you: runs on two lines",parts,2);
     h=AW_DialLinkHit(hits,nhits,x0+1,y0,RH);if(h>=0 && AW_DialLinkOn(bits,TOPICS,hits[h].topic))ask(hits[h].topic);
     expect("know you: first part asks it",asked[nasked-1],E);
     frame();parts=0;                                   /* its paragraph (1) moved up under the new answer */
     for(h=0;h<nhits;h++)if(hits[h].topic==E && hits[h].para==1){x1=hits[h].x;y1=hits[h].y;parts++;}
     h=AW_DialLinkHit(hits,nhits,x1+1,y1,RH);
     expect("know you: second part still a hit after a new answer",h>=0 && parts==2,1);
     answers[E]=0;refresh();scroll=0;frame();parts=0;
     for(h=0;h<nhits;h++)if(hits[h].topic==E)parts++;
     expect("know you unanswered: not lit",parts,0);}
    /* DIALOGUE-SCROLLBARS-62: the thin bars, by number, with the mouse button and keys only (no wheel input) */
    {int pos,len,lit,grab,first;
     lit=AW_DialBar(8,12,0,100,&pos,&len);                         /* fits: dim, no thumb */
     expect("fits: lit",lit,0);expect("fits: thumb length",len,0);
     expect("dim colour is the frame brown",(int)AW_DIAL_BAR_DIM,0x3e3524);
     lit=AW_DialBar(40,10,0,100,&pos,&len);                        /* overflows: lit, thumb = 10/40 of 100 */
     expect("overflows: lit",lit,1);expect("thumb length",len,25);expect("thumb at the top",pos,0);
     AW_DialBar(40,10,30,100,&pos,&len);expect("thumb at the bottom",pos,75);
     AW_DialBar(40,10,15,100,&pos,&len);expect("thumb half way",pos,38);
     AW_DialBar(1000,10,0,100,&pos,&len);expect("thumb never under the minimum",len,AW_DIAL_BAR_MIN_THUMB);
     expect("drag: centre at 50 px",AW_DialBarFirst(40,10,100,50),15);
     expect("drag: past the top",AW_DialBarFirst(40,10,100,-9),0);
     expect("drag: past the bottom",AW_DialBarFirst(40,10,100,500),30);
     /* a 108 px bar: 4 px arrow ends and a 100 px track; 40 lines, 10 shown, first 15 (thumb 38..63 of the track) */
     expect("click the up arrow",AW_DialBarClick(40,10,15,108,1,&grab),14);
     expect("click the down arrow",AW_DialBarClick(40,10,15,108,106,&grab),16);
     expect("click above the thumb pages up",AW_DialBarClick(40,10,15,108,10,&grab),6);
     expect("click below the thumb pages down",AW_DialBarClick(40,10,15,108,100,&grab),24);
     first=AW_DialBarClick(40,10,15,108,4+50,&grab);
     expect("click on the thumb grabs it",grab,1);expect("a grab does not move",first,15);
     expect("up arrow at the top stays",AW_DialBarClick(40,10,0,108,1,&grab),0);
     expect("a click on a dim bar",AW_DialBarClick(8,12,0,108,50,&grab),0);
    }
    /* DIALOGUE-CHOICES-62: a Choice's rows in the text (the roadside robber's two options, the first wrapped on two
     * lines) under an answer with a link: a click picks by row, on either line of a wrapped row; a link is never a
     * choice; the keys step through the rows from none, wrapping; the Choice number is the row's (never matched from
     * typed letters: the window's search no longer sees the rows) */
    {aw_dial_hit_t ch[8];int n=0,numbers[2]={1,2};
     ch[n].x=0;ch[n].y=BODY;ch[n].w=5*CW;ch[n].topic=A;ch[n].para=0;ch[n].span=0;n++;            /* a link */
     ch[n].x=CW;ch[n].y=BODY+RH;ch[n].w=14*CW;ch[n].topic=0;ch[n].para=AW_DIAL_HIT_CHOICE;ch[n].span=0;n++;
     ch[n].x=CW;ch[n].y=BODY+2*RH;ch[n].w=9*CW;ch[n].topic=0;ch[n].para=AW_DIAL_HIT_CHOICE;ch[n].span=0;n++;
     ch[n].x=CW;ch[n].y=BODY+3*RH;ch[n].w=6*CW;ch[n].topic=0;ch[n].para=AW_DIAL_HIT_CHOICE;ch[n].span=1;n++;
     expect("choice: a click on the first row",AW_DialChoiceAt(ch,n,CW+3,BODY+RH,RH),0);
     expect("choice: its wrapped second line",AW_DialChoiceAt(ch,n,CW+20,BODY+2*RH+4,RH),0);
     expect("choice: the second row's number",numbers[AW_DialChoiceAt(ch,n,CW*2,BODY+3*RH,RH)],2);
     expect("choice: a link is not a choice",AW_DialChoiceAt(ch,n,2,BODY,RH),-1);
     expect("choice: past the row's text",AW_DialChoiceAt(ch,n,CW*12,BODY+3*RH,RH),-1);
     expect("choice: Down from none",AW_DialChoiceStep(2,-1,1),0);
     expect("choice: Up from none",AW_DialChoiceStep(2,-1,-1),1);
     expect("choice: Down wraps",AW_DialChoiceStep(2,1,1),0);
     expect("choice: Up wraps",AW_DialChoiceStep(2,0,-1),1);
     expect("choice: no rows",AW_DialChoiceStep(0,-1,1),-1);}
    printf(failures?"FAIL %d\n":"OK\n",failures);
    return failures!=0;
}
