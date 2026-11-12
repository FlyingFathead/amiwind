/* SPDX-License-Identifier: GPL-2.0-or-later
 * The tutorial texts' keys (aw_tutorial.h). Pure C. */
#include <string.h>
#include "aw_tutorial.h"

static const aw_tutorial_row_t rows[]={
#include "aw_tutorial_table.inc"
};
#define ROWS ((int)(sizeof(rows)/sizeof(rows[0])))

static int space(unsigned char c){return c==' ' || c=='\t' || c=='\r' || c=='\n';}
unsigned long AW_TutorialHash(const char *text){
    unsigned long h=2166136261UL;int pending=0,any=0;unsigned char c;
    if(!text)return h;
    for(;(c=(unsigned char)*text)!=0;text++){
        if(space(c)){pending=any;continue;}
        if(pending){h^=' ';h=(h*16777619UL)&0xffffffffUL;pending=0;}
        if(c>='A' && c<='Z')c=(unsigned char)(c-'A'+'a');
        h^=c;h=(h*16777619UL)&0xffffffffUL;any=1;
    }
    return h;
}
int AW_TutorialRows(void){return ROWS;}
const aw_tutorial_row_t *AW_TutorialRow(int i){return i>=0 && i<ROWS?&rows[i]:NULL;}
const char *AW_TutorialFind(unsigned long hash){
    int i;
    for(i=0;i<ROWS;i++)if(rows[i].hash==hash)return rows[i].text;
    return NULL;
}
static int put(char *out,int n,int capacity,const char *s){while(s && *s && n<capacity-1)out[n++]=*s++;return n;}
int AW_TutorialFill(const char *tmpl,const char *original,const char *(*key)(const char *command),char *out,int capacity){
    int n=0;const char *p=tmpl;char command[48];
    if(capacity<1)return 0;
    while(p && *p && n<capacity-1){
        if(!strncmp(p,"{text}",6)){n=put(out,n,capacity,original);p+=6;continue;}
        if(!strncmp(p,"{key:",5)){
            const char *end=strchr(p+5,'}'),*name;int k=end?(int)(end-(p+5)):-1;
            if(k>0 && k<(int)sizeof(command)){
                memcpy(command,p+5,(size_t)k);command[k]=0;
                name=key?key(command):NULL;
                n=put(out,n,capacity,name && *name?name:"not bound");
                p=end+1;continue;
            }
        }
        out[n++]=*p++;
    }
    out[n]=0;
    return n;
}
static int same_word(const char *a,int n,const char *b){
    int i;
    for(i=0;i<n;i++){
        int x=(unsigned char)a[i],y=(unsigned char)b[i];
        if(!y)return 0;
        if(x>='A' && x<='Z')x+='a'-'A';
        if(y>='A' && y<='Z')y+='a'-'A';
        if(x!=y)return 0;
    }
    return b[n]==0;
}
int AW_WinKeyMatch(const char *list,const char *name){
    const char *p=list;int n;
    if(!list || !name || !*name)return 0;
    while(*p){
        while(*p==' ')p++;
        for(n=0;p[n] && p[n]!=' ';n++);
        if(n && same_word(p,n,name))return 1;
        p+=n;
    }
    return 0;
}
void AW_WinKeyWords(const char *list,char *out,int capacity){
    const char *p=list;int n,k=0,words=0,i;
    if(capacity<1)return;
    out[0]=0;
    if(!list)return;
    while(*p){
        while(*p==' ')p++;
        for(n=0;p[n] && p[n]!=' ';n++);
        if(!n)break;
        /* the parenthesis form of the tutorial texts: "(E) or (Enter)" from "({key:...})" */
        if(words && k<capacity-7){memcpy(out+k,") or (",6);k+=6;}
        for(i=0;i<n && k<capacity-1;i++){
            int c=(unsigned char)p[i];
            /* a letter in upper case, a key's name as a word: ENTER -> Enter */
            if(n>1 && i>0 && c>='A' && c<='Z')c+='a'-'A';
            if(i==0 && c>='a' && c<='z')c-='a'-'A';
            out[k++]=(char)c;
        }
        words++;p+=n;
    }
    out[k]=0;
}
static unsigned char shown[ROWS];
void AW_TutorialReset(void){memset(shown,0,sizeof(shown));}
int AW_TutorialApply(const char *text,const char *(*key)(const char *command),char *out,int capacity){
    unsigned long h;int i;
    if(!text)return 0;
    h=AW_TutorialHash(text);
    for(i=0;i<ROWS;i++){
        if(rows[i].hash!=h)continue;
        if(rows[i].once==AW_TUTORIAL_HIDE)return -1;
        if(rows[i].once==AW_TUTORIAL_ONCE && shown[i])return 0;
        shown[i]=1;
        AW_TutorialFill(rows[i].text,text,key,out,capacity);
        return 1;
    }
    return 0;
}
