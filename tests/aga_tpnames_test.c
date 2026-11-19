/* SPDX-License-Identifier: GPL-2.0-or-later
 * dbg tp's names list (aw_listbox_rules.c AW_TpNames*, v0.0.66): the whole list and the low-memory path that reads
 * the labels from the file in chunks give the same rows; and the HEAP TEST: on a first-fit heap that splits and
 * merges blocks (as exec's does), opening and closing the list 100 times, whole and paged, and once across an area
 * change, leaves the total free memory AND the largest free block exactly as they were, to the byte. Built with
 * AW_TP_ALLOC=test_alloc AW_TP_FREE=test_free. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_listbox.h"

/* ---- a first-fit heap with splitting and merging */
#define HEAP (1024L*1024L)
#define BLOCKS 256
static unsigned char heap[HEAP];
static struct {long at,size;int used;} block[BLOCKS];
static int blocks;
static long refuse_over=-1;            /* a request larger than this fails (the low-memory path) */
static void heap_reset(void){blocks=1;block[0].at=0;block[0].size=HEAP;block[0].used=0;}
void *test_alloc(unsigned long size){
    long want=(long)((size+7)&~7ul);int i,k;
    if(!want || (refuse_over>=0 && want>refuse_over))return NULL;
    for(i=0;i<blocks;i++){
        if(block[i].used || block[i].size<want)continue;
        if(block[i].size>want){
            assert(blocks<BLOCKS);
            for(k=blocks;k>i+1;k--)block[k]=block[k-1];
            blocks++;
            block[i+1].at=block[i].at+want;block[i+1].size=block[i].size-want;block[i+1].used=0;
            block[i].size=want;
        }
        block[i].used=1;
        return heap+block[i].at;
    }
    return NULL;
}
void test_free(void *p){
    long at=(long)((unsigned char *)p-heap);int i,k;
    for(i=0;i<blocks && block[i].at!=at;i++);
    assert(i<blocks && block[i].used);
    block[i].used=0;
    if(i+1<blocks && !block[i+1].used){
        block[i].size+=block[i+1].size;
        for(k=i+1;k<blocks-1;k++)block[k]=block[k+1];
        blocks--;
    }
    if(i>0 && !block[i-1].used){
        block[i-1].size+=block[i].size;
        for(k=i;k<blocks-1;k++)block[k]=block[k+1];
        blocks--;
    }
}
static void heap_state(long *total,long *largest){
    int i;*total=0;*largest=0;
    for(i=0;i<blocks;i++)if(!block[i].used){*total+=block[i].size;if(block[i].size>*largest)*largest=block[i].size;}
}

/* ---- a names list file: ROWS rows, labels of varied length, categories 1..3 */
#define ROWS 3000
static void label_of(int i,char *out){
    static const char *const words[]={"Balmora","Dagoth Ur, Facility Cavern","Slaughterfish","Raven Rock (Bloodmoon)",
        "Mournhold, Great Bazaar (Tribunal) (interior)","Fargoth","Vivec","A"};
    sprintf(out,"%s %d",words[i%8],i);
}
static FILE *names_file(long *size){
    FILE *f=tmpfile();unsigned char head[16];long bytes=0;int i;char label[80];
    assert(f);
    for(i=0;i<ROWS;i++){label_of(i,label);bytes+=2+(long)strlen(label);}
    memcpy(head,"AWTN",4);head[4]=0;head[5]=1;head[6]=head[7]=0;
    head[8]=0;head[9]=0;head[10]=(unsigned char)(ROWS>>8);head[11]=(unsigned char)ROWS;
    head[12]=(unsigned char)(bytes>>24);head[13]=(unsigned char)(bytes>>16);head[14]=(unsigned char)(bytes>>8);
    head[15]=(unsigned char)bytes;
    fwrite(head,1,16,f);
    for(i=0;i<ROWS;i++){
        label_of(i,label);
        fputc(1+i%3,f);fputc((int)strlen(label),f);fwrite(label,1,strlen(label),f);
    }
    fflush(f);
    *size=16+bytes;
    return f;
}

/* ---- a typed name (dbg tp TEXT, DBG-TP-EXPANSION-ARRIVALS-66): the row the box would take, read row by row */
static const char *const typed[]={"Balmora","Balmora, Hlaalo Manor (interior)",
    "Mournhold, Royal Palace: Reception Area (Tribunal) (interior)",
    "Mournhold, Royal Palace: Courtyard (Tribunal) (interior)","Seyda Neen","Seyda Neen (interior)","Fargoth"};
#define TYPED 7
static FILE *typed_file(long *size){
    FILE *f=tmpfile();unsigned char head[16];long bytes=0;int i;
    assert(f);
    for(i=0;i<TYPED;i++)bytes+=2+(long)strlen(typed[i]);
    memset(head,0,sizeof(head));memcpy(head,"AWTN",4);head[5]=1;head[11]=TYPED;
    head[14]=(unsigned char)(bytes>>8);head[15]=(unsigned char)bytes;
    fwrite(head,1,16,f);
    for(i=0;i<TYPED;i++){fputc(i==6?3:i==0||i==4?1:2,f);fputc((int)strlen(typed[i]),f);fwrite(typed[i],1,strlen(typed[i]),f);}
    fflush(f);
    *size=16+bytes;
    return f;
}
static void typed_names(void){
    FILE *f;long size,matches;char list[200],small[40];
    /* the name rule: the label without its trailing " (...)" parts, letters and digits, case ignored */
    assert(AW_ListBoxNames(typed[2],"Mournhold, Royal Palace: Reception Area"));
    assert(AW_ListBoxNames(typed[2],"mournhold royal palace reception area"));
    assert(!AW_ListBoxNames(typed[2],"reception area") && !AW_ListBoxNames(typed[2],"mournhold royal palace"));
    assert(AW_ListBoxNames("Ald-ruhn","aldruhn") && !AW_ListBoxNames("Ald-ruhn","ald") && !AW_ListBoxNames("Ald-ruhn",""));
    assert(!AW_ListBoxNames("Ald-ruhn"," ,:") && !AW_ListBoxNames(NULL,"a") && !AW_ListBoxNames("a",NULL));
    f=typed_file(&size);
    /* named exactly: the room by its cell's name (the picker's label carries the tags) */
    assert(AW_TpNamesFind(f,0,size,"Mournhold, Royal Palace: Reception Area",&matches,list,sizeof(list))==2 && matches==1);
    /* one row holds it: that row */
    assert(AW_TpNamesFind(f,0,size,"reception",&matches,list,sizeof(list))==2 && matches==1);
    assert(AW_TpNamesFind(f,0,size,"fargoth",&matches,list,sizeof(list))==6);
    /* several hold it, one is named: the named one (the first, the outdoor place before its room) */
    assert(AW_TpNamesFind(f,0,size,"balmora",&matches,list,sizeof(list))==0);
    assert(AW_TpNamesFind(f,0,size,"Seyda Neen",&matches,list,sizeof(list))==4);
    /* several hold it, none is named: how many, and the first labels */
    assert(AW_TpNamesFind(f,0,size,"royal palace",&matches,list,sizeof(list))==-2 && matches==2);
    assert(!strcmp(list,"Mournhold, Royal Palace: Reception Area (Tribunal) (interior); "
                        "Mournhold, Royal Palace: Courtyard (Tribunal) (interior)"));
    assert(AW_TpNamesFind(f,0,size,"royal palace",&matches,small,sizeof(small))==-2 && matches==2 && !small[0]);
    /* none holds it, no letters, a bad file */
    assert(AW_TpNamesFind(f,0,size,"dagoth",&matches,list,sizeof(list))==-1 && matches==0 && !list[0]);
    assert(AW_TpNamesFind(f,0,size," ,: ",&matches,list,sizeof(list))==-1);
    assert(AW_TpNamesFind(f,0,size-1,"balmora",&matches,list,sizeof(list))==-1);
    assert(AW_TpNamesFind(NULL,0,size,"balmora",NULL,NULL,0)==-1);
    fclose(f);
    puts("typed names ok");
}

int main(void){
    aw_tp_names_t n;FILE *f;long size,total0,largest0,total,largest,held_whole,held_paged;int i,k,c;
    char got[AW_TP_NAME],want[80];void *area;
    typed_names();
    f=names_file(&size);
    heap_reset();heap_state(&total0,&largest0);

    /* the whole list and the paged one give the same rows */
    assert(AW_TpNamesOpen(&n,f,0,size,1)==ROWS);
    held_whole=AW_TpNamesHeld(&n);
    for(i=0;i<ROWS;i++){
        label_of(i,want);
        assert(AW_TpNamesGet(&n,i,got,sizeof(got),&c) && !strcmp(got,want) && c==1+i%3);
    }
    AW_TpNamesClose(&n);
    assert(AW_TpNamesOpen(&n,f,0,size,0)==ROWS);
    held_paged=AW_TpNamesHeld(&n);
    for(k=0;k<2;k++)                                 /* forwards, then backwards (every chunk read again) */
        for(i=0;i<ROWS;i++){
            int r=k?ROWS-1-i:i;
            label_of(r,want);
            assert(AW_TpNamesGet(&n,r,got,sizeof(got),&c) && !strcmp(got,want) && c==1+r%3);
        }
    assert(!AW_TpNamesGet(&n,ROWS,got,sizeof(got),&c) && !AW_TpNamesGet(&n,-1,got,sizeof(got),&c));
    AW_TpNamesClose(&n);
    assert(held_paged==ROWS*(long)sizeof(unsigned long) && held_whole==held_paged+size-16);
    printf("names list: %d rows, %ld bytes held whole, %ld paged (+%d chunk)\n",ROWS,held_whole,held_paged,AW_TPN_CHUNK);

    /* low memory: the whole block is refused, the paged one fits */
    refuse_over=held_paged+64;
    assert(AW_TpNamesOpen(&n,f,0,size,1)==-1 && !n.block);
    assert(AW_TpNamesOpen(&n,f,0,size,0)==ROWS);
    label_of(1234,want);assert(AW_TpNamesGet(&n,1234,got,sizeof(got),NULL) && !strcmp(got,want));
    AW_TpNamesClose(&n);
    refuse_over=-1;

    /* THE HEAP TEST: 100 opens and closes, whole and paged: the heap is back to the byte */
    for(i=0;i<100;i++){
        assert(AW_TpNamesOpen(&n,f,0,size,i&1)==ROWS);
        AW_TpNamesGet(&n,i*29%ROWS,got,sizeof(got),NULL);
        AW_TpNamesClose(&n);
        heap_state(&total,&largest);
        assert(total==total0 && largest==largest0);
    }
    /* across an area change: the area's memory taken while the list is open, the list closed, the area freed */
    assert(AW_TpNamesOpen(&n,f,0,size,1)==ROWS);
    assert((area=test_alloc(300000))!=NULL);
    AW_TpNamesClose(&n);
    test_free(area);
    heap_state(&total,&largest);assert(total==total0 && largest==largest0);
    /* and the other order: an area loaded before the open, unloaded while it is open */
    assert((area=test_alloc(300000))!=NULL);
    assert(AW_TpNamesOpen(&n,f,0,size,1)==ROWS);
    test_free(area);
    AW_TpNamesClose(&n);
    heap_state(&total,&largest);assert(total==total0 && largest==largest0);
    /* a bad file holds nothing */
    assert(AW_TpNamesOpen(&n,f,0,size-1,1)==-1 && !n.block);
    heap_state(&total,&largest);assert(total==total0 && largest==largest0);
    fclose(f);
    printf("heap test: 102 opens, free %ld, largest %ld, unchanged\n",total0,largest0);
    puts("tp names ok");
    return 0;
}
