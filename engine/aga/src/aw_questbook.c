/* SPDX-License-Identifier: GPL-2.0-or-later
 * The journal book's quest pages (aw_questbook.h, JOURNAL-BOOK-32-QUESTS-59). */
#include <string.h>
#include <stdlib.h>
#include "aw_questbook.h"
#include "aw_tryalloc.h"

static int fold(int c){return c>='A' && c<='Z'?c-'A'+'a':c;}
static int casecmp(const char *a,const char *b){
    while(*a && fold((unsigned char)*a)==fold((unsigned char)*b)){a++;b++;}
    return fold((unsigned char)*a)-fold((unsigned char)*b);
}
int32_t AW_QuestBookStage(const aw_ledger_t *l,const char *id){
    int32_t v=0;
    if(!l || !id || !*id || !AW_LedgerValue(l,AW_LEDGER_QUESTS,AW_LedgerNameHash(id),&v))return 0;
    return v;
}
void AW_QuestBookFree(aw_questbook_t *b){
    if(!b)return;
    free(b->group);free(b->entry);memset(b,0,sizeof(*b));
}
/* the catalogue row of ID (folded compare), -1 none: a linear look, run once per dated entry when the book opens */
static int quest_row(const aw_qb_quest_t *q,int n,const char *id){
    int i;
    for(i=0;i<n;i++)if(!casecmp(q[i].id,id))return i;
    return -1;
}
static const aw_qb_quest_t *sort_quests;
static int by_title(const void *a,const void *b){
    const aw_qb_group_t *x=(const aw_qb_group_t *)a,*y=(const aw_qb_group_t *)b;
    int c=casecmp(sort_quests[x->quest].title,sort_quests[y->quest].title);
    return c?c:x->quest-y->quest;
}
int AW_QuestBookBuild(aw_questbook_t *b,const aw_qb_quest_t *quests,int n,const aw_ledger_t *l,
                      const aw_qb_dated_t *dated,int nd,aw_qb_status_fn status,void *ctx){
    int32_t *stage=NULL;int i,j,g,*row_of=NULL,ok=0;uint8_t *fin=NULL;
    if(!b)return 0;
    AW_QuestBookFree(b);
    if(n<0 || n>AW_QB_QUESTS || nd<0 || (n && !quests) || (nd && !dated))return 0;
    fin=(uint8_t *)AW_TryCalloc((unsigned long)(n?n:1),1);
    stage=(int32_t *)AW_TryCalloc((unsigned long)(n?n:1),sizeof(int32_t));
    row_of=(int *)AW_TryMalloc((unsigned long)(nd?nd:1)*sizeof(int));
    b->group=(aw_qb_group_t *)AW_TryMalloc((unsigned long)(n?n:1)*sizeof(aw_qb_group_t));
    b->entry=(aw_qb_entry_t *)AW_TryMalloc((unsigned long)(nd+n?nd+n:1)*sizeof(aw_qb_entry_t));
    if(!fin || !stage || !row_of || !b->group || !b->entry)goto done;
    /* the stage of every quest: the kept one, else the highest dated (an older save's 32-slot journal) */
    for(i=0;i<n;i++)stage[i]=AW_QuestBookStage(l,quests[i].id);
    for(j=0;j<nd;j++){
        row_of[j]=dated[j].id?quest_row(quests,n,dated[j].id):-1;
        if(row_of[j]>=0 && !AW_QuestBookStage(l,quests[row_of[j]].id) && dated[j].stage>stage[row_of[j]])
            stage[row_of[j]]=dated[j].stage;
    }
    /* finished or active (JOURNAL-QUEST-ENDINGS-64; OpenMW 0.53 mwdialogue/quest.cpp addEntry, read, not copied):
     * the quest's entries replayed in the order earned, an entry with the finished mark finishes it, one with the
     * restart mark reopens it, any other entry and a bare index change leave it as it was; the kept stage counts as
     * the last entry when no dated entry holds it (an older save's stages without dates) */
    if(status){
        for(j=0;j<nd;j++){
            int s;
            if(row_of[j]<0 || dated[j].stage<=0)continue;
            s=status(quests[row_of[j]].id,dated[j].stage,ctx);
            if(s&AW_QB_FINISHED)fin[row_of[j]]=1;
            else if(s&AW_QB_RESTART)fin[row_of[j]]=0;
        }
        for(i=0;i<n;i++){
            int s;
            if(stage[i]<=0)continue;
            for(j=0;j<nd && !(row_of[j]==i && dated[j].stage==stage[i]);j++);
            if(j<nd)continue;
            s=status(quests[i].id,stage[i],ctx);
            if(s&AW_QB_FINISHED)fin[i]=1;
            else if(s&AW_QB_RESTART)fin[i]=0;
        }
    }
    /* the names: each once, a name finished when any of its quests is */
    for(i=0;i<n;i++){
        if(stage[i]<=0)continue;
        b->started++;
        if(fin[i])b->finished++;
        if(!quests[i].title[0])continue;
        for(g=0;g<b->groups && casecmp(quests[b->group[g].quest].title,quests[i].title);g++);
        if(g==b->groups){b->group[g].quest=i;b->group[g].finished=0;b->groups++;}
        if(fin[i])b->group[g].finished=1;
    }
    sort_quests=quests;
    if(b->groups>1)qsort(b->group,(size_t)b->groups,sizeof(aw_qb_group_t),by_title);
    sort_quests=NULL;
    /* the entries: the dated ones as recorded, then each started quest's kept stage without a dated entry */
    for(j=0;j<nd;j++){
        aw_qb_entry_t *e=&b->entry[b->entries++];
        e->quest=row_of[j];e->dated=j;e->stage=dated[j].stage;e->days=dated[j].days;e->milliseconds=dated[j].milliseconds;
        e->group=-1;
    }
    for(i=0;i<n;i++){
        if(stage[i]<=0)continue;
        for(j=0;j<nd && !(row_of[j]==i && dated[j].stage==stage[i]);j++);
        if(j<nd)continue;
        {aw_qb_entry_t *e=&b->entry[b->entries++];
         e->quest=i;e->dated=AW_QB_UNDATED;e->stage=stage[i];e->days=e->milliseconds=0;e->group=-1;}
    }
    for(j=0;j<b->entries;j++){
        aw_qb_entry_t *e=&b->entry[j];
        if(e->quest<0 || !quests[e->quest].title[0])continue;
        for(g=0;g<b->groups && casecmp(quests[b->group[g].quest].title,quests[e->quest].title);g++);
        if(g<b->groups)e->group=g;
    }
    ok=1;
 done:
    free(fin);free(stage);free(row_of);
    if(!ok)AW_QuestBookFree(b);
    return ok;
}
/* ---- the dated journal (aw_questbook.h) ---- */
/* LORE-DATE-FORMAT-62: the names are the game data's (GMSTs sMonthMorningstar .. sMonthEveningstar and sDay, written
 * by tools/prepare_levelup.py into levelup/rest.txt and set here through AW_DateNameSet); these are the same GMSTs'
 * English values, used until the image's own are read (and by the native tests). */
#define DATE_NAME 32
static char month_name[12][DATE_NAME]={"Morning Star","Sun's Dawn","First Seed","Rain's Hand","Second Seed","Mid Year",
    "Sun's Height","Last Seed","Heartfire","Frost Fall","Sun's Dusk","Evening Star"};
static char day_word[DATE_NAME]="Day";
static const char *const month_keys[12]={"sMonthMorningstar","sMonthSunsdawn","sMonthFirstseed","sMonthRainshand",
    "sMonthSecondseed","sMonthMidyear","sMonthSunsheight","sMonthLastseed","sMonthHeartfire","sMonthFrostfall",
    "sMonthSunsdusk","sMonthEveningstar"};
static const int month_days[12]={31,28,31,30,31,30,31,31,30,31,30,31};
static void name_copy(char *to,const char *text){
    int i;
    for(i=0;i<DATE_NAME-1 && text[i] && text[i]!='\r' && text[i]!='\n';i++)to[i]=(unsigned char)text[i]<32?'?':text[i];
    to[i]=0;
}
int AW_DateNameSet(const char *key,const char *text){
    int m;
    if(!key || !text || !*text)return 0;
    if(!strcmp(key,"sDay")){name_copy(day_word,text);return 1;}
    for(m=0;m<12;m++)if(!strcmp(key,month_keys[m])){name_copy(month_name[m],text);return 1;}
    return 0;
}
const char *AW_DateMonthName(int month){return month>=1 && month<=12?month_name[month-1]:"";}
/* built by hand: the C library's snprintf is not on every target this file compiles for */
static int put_text(char *s,int n,const char *t){while(*t && n<120)s[n++]=*t++;return n;}
static int put_number(char *s,int n,long v){
    char num[12];int k=0;
    if(v<0)v=0;
    do{num[k++]=(char)('0'+v%10);v/=10;}while(v);
    while(k && n<120)s[n++]=num[--k];
    return n;
}
int AW_DateText(int form,int32_t days,int hour,int minute,char *out,int capacity){
    char s[128];int32_t d;long year;int m=0,n=0,h12;
    if(!out || capacity<1)return 0;
    if(days<0)days=0;
    d=days+227;year=427+d/365;d%=365;
    while(d>=month_days[m])d-=month_days[m++];
    if(hour<0)hour=0;
    if(hour>23)hour=23;
    if(minute<0)minute=0;
    if(minute>59)minute=59;
    h12=hour%12?hour%12:12;
    if(form==AW_DATE_NUMERIC){
        /* 18/08/427: day/month/year, the debug form */
        if(d+1<10)s[n++]='0';
        n=put_number(s,n,(long)d+1);s[n++]='/';
        if(m+1<10)s[n++]='0';
        n=put_number(s,n,(long)m+1);s[n++]='/';n=put_number(s,n,year);
    }else{
        n=put_number(s,n,(long)d+1);s[n++]=' ';n=put_text(s,n,month_name[m]);
        if(form==AW_DATE_LORE){n=put_text(s,n,", 3E ");n=put_number(s,n,year);}
        if(form==AW_DATE_JOURNAL || form==AW_DATE_REST){
            s[n++]=' ';s[n++]='(';n=put_text(s,n,day_word);s[n++]=' ';n=put_number(s,n,(long)days+1);s[n++]=')';
        }
        if(form==AW_DATE_REST || form==AW_DATE_SAVE){
            s[n++]=' ';n=put_number(s,n,h12);n=put_text(s,n,hour>=12?" p.m.":" a.m.");
        }
    }
    s[n]=0;
    if(n>=capacity){out[0]=0;return 0;}
    memcpy(out,s,(size_t)n+1);
    return n;
}
int AW_JournalDate(int32_t days,char *out,int capacity){return AW_DateText(AW_DATE_JOURNAL,days,0,0,out,capacity);}
static int jv_para(aw_journalview_t *v,int kind,const char *text){
    uint32_t len=text?(uint32_t)strlen(text):0;
    if(v->paras==v->para_cap){
        int cap=v->para_cap?v->para_cap*2:32;uint32_t *p;uint8_t *k;
        p=(uint32_t *)AW_TryRealloc(v->para,(unsigned long)cap*sizeof(uint32_t));
        if(!p)return 0;
        v->para=p;
        k=(uint8_t *)AW_TryRealloc(v->para_kind,(unsigned long)cap);
        if(!k)return 0;
        v->para_kind=k;v->para_cap=cap;
    }
    if(v->used+len+1>v->cap){
        uint32_t cap=v->cap?v->cap:2048;char *t;
        while(v->used+len+1>cap)cap*=2;
        t=(char *)AW_TryRealloc(v->text,cap);
        if(!t)return 0;
        v->text=t;v->cap=cap;
    }
    v->para[v->paras]=v->used;v->para_kind[v->paras]=(uint8_t)kind;v->paras++;
    if(len)memcpy(v->text+v->used,text,len);
    v->text[v->used+len]=0;v->used+=len+1;
    return 1;
}
int AW_JournalViewAdd(aw_journalview_t *v,int32_t days,const char *text){
    char date[64];
    if(!v)return 0;
    if(!v->entries)v->last_day=-1;
    if(days>=0 && days!=v->last_day){
        if(v->paras && !jv_para(v,2,NULL))return 0;
        if(!AW_JournalDate(days,date,sizeof(date)) || !jv_para(v,1,date))return 0;
        v->last_day=days;
    }else if(v->paras && !jv_para(v,2,NULL))return 0;   /* entries of one day: a blank line between */
    if(!jv_para(v,0,text?text:""))return 0;
    v->entries++;
    return 1;
}
static int jv_line(aw_journalview_t *v,uint32_t start,int len,int heading,int blank){
    if(v->lines==v->line_cap){
        int cap=v->line_cap?v->line_cap*2:64;aw_jv_line_t *l=(aw_jv_line_t *)AW_TryRealloc(v->line,(unsigned long)cap*sizeof(aw_jv_line_t));
        if(!l)return 0;
        v->line=l;v->line_cap=cap;
    }
    v->line[v->lines].start=start;v->line[v->lines].len=(uint16_t)(len>65535?65535:len);
    v->line[v->lines].heading=(uint8_t)heading;v->line[v->lines].blank=(uint8_t)blank;v->lines++;
    return 1;
}
int AW_JournalViewLayout(aw_journalview_t *v,aw_jv_wrap_fn wrap,int width,int page_lines){
    int i,on_page=0,*pages;char out[256];const char *p,*before;
    if(!v || !wrap || page_lines<2)return 0;
    v->lines=v->pages=0;
    for(i=0;i<v->paras;i++){
        if(v->para_kind[i]==2){if(!jv_line(v,v->para[i],0,0,1))return 0;continue;}
        p=v->text+v->para[i];
        if(!*p){if(!jv_line(v,v->para[i],0,0,0))return 0;continue;}
        while(*p){
            before=p;p=wrap(p,width,out,(int)sizeof(out));
            if(p==before)break;
            if(!jv_line(v,(uint32_t)(before-v->text),(int)strlen(out),v->para_kind[i]==1,0))return 0;
        }
    }
    free(v->page);v->page=NULL;
    pages=(int *)AW_TryMalloc((unsigned long)(v->lines+1)*sizeof(int));
    if(!pages)return 0;
    v->page=pages;
    for(i=0;i<v->lines;i++){
        if(on_page==0 && v->line[i].blank)continue;            /* never a blank line at the top of a page */
        if(on_page==page_lines){on_page=0;if(v->line[i].blank)continue;}
        /* a heading starts a page when it and the first line under it do not fit on this one */
        if(on_page && v->line[i].heading && (i==0 || !v->line[i-1].heading)){
            int h=0;while(i+h<v->lines && v->line[i+h].heading)h++;
            if(h+1<=page_lines && on_page+h+1>page_lines)on_page=0;
        }
        if(!on_page)v->page[v->pages++]=i;
        on_page++;
    }
    return 1;
}
int AW_JournalViewNewest(const aw_journalview_t *v){return v && v->pages>0?((v->pages-1)&~1):0;}
void AW_JournalViewFree(aw_journalview_t *v){
    if(!v)return;
    free(v->text);free(v->para);free(v->para_kind);free(v->line);free(v->page);memset(v,0,sizeof(*v));
}
int AW_QuestBookShown(const aw_questbook_t *b,int all,int *out,int max){
    int g,n=0;
    if(!b || !out)return 0;
    for(g=0;g<b->groups && n<max;g++)if(all || !b->group[g].finished)out[n++]=g;
    return n;
}
