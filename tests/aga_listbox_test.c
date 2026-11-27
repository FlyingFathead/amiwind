/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_listbox_rules.c alone (TP-PICKER-57): the search (letters and digits, case ignored, as you type), the filter
 * keeping the selected row, Up/Down/PgUp/PgDn/Home/End and the scroll position, clicks, Backspace, Enter only on a
 * row; the settlements table reader (AWTP1 header and size checks, signed coordinates) and the teleport line it
 * makes (the existing dbg tp X Y [Z] path). */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_listbox.h"

static const char *const places[]={"Ald-ruhn","Balmora","Caldera","Gnisis","Khuul","Seyda Neen","Suran",
    "Tel Aruhn","Tel Branora","Tel Mora","Vivec","Vivec, Arena","Vivec, Foreign Quarter"};
#define PLACES ((int)(sizeof(places)/sizeof(places[0])))
static int label_calls;
static const char *label(void *ctx,int row){(void)ctx;label_calls++;return row>=0 && row<PLACES?places[row]:"";}
/* categories of the test rows: Balmora and Tel Branora are 3, the Vivec rows 2, the rest 1 */
static int category(void *ctx,int row){(void)ctx;return row==1 || row==8?3:row>=10?2:1;}
static int blocked_wall_table(void *ctx,const float *p,float *out){
    (void)ctx;
    if(p[0]>20)return 0;                                              /* the wall */
    if(p[0]>-25 && p[0]<25 && p[1]>15 && p[1]<65)return 0;            /* the table */
    out[0]=p[0];out[1]=p[1];out[2]=p[2];return 1;
}
static int blocked_all(void *ctx,const float *p,float *out){(void)ctx;(void)p;(void)out;return 0;}
static void type(aw_listbox_t *b,const char *s){for(;*s;s++)assert(AW_ListBoxType(b,(unsigned char)*s));}

static void put32(unsigned char *p,long v){unsigned long u=(unsigned long)v;p[0]=(unsigned char)(u>>24);p[1]=(unsigned char)(u>>16);p[2]=(unsigned char)(u>>8);p[3]=(unsigned char)u;}

int main(void){
    aw_listbox_t b;int shown[PLACES],i;char line[64];
    unsigned char table[AW_TP_HEADER+2*AW_TP_ROW];unsigned char table2[AW_TP_HEADER+2*AW_TP_ROW2];aw_tp_place_t p;

    /* matching: letters and digits only, case ignored, anywhere in the label */
    assert(AW_ListBoxMatches("Ald-ruhn","aldruhn") && AW_ListBoxMatches("Ald-ruhn","ALD RU") && AW_ListBoxMatches("Seyda Neen","neen"));
    assert(AW_ListBoxMatches("Vivec, Arena","vivecar") && !AW_ListBoxMatches("Vivec","vivecar"));
    assert(AW_ListBoxMatches("Balmora","") && AW_ListBoxMatches("Balmora","  -") && !AW_ListBoxMatches("Balmora","x"));
    assert(!AW_ListBoxMatches(NULL,"a") && AW_ListBoxMatches(NULL,NULL));

    /* everything shown at first, the first row selected */
    AW_ListBoxReset(&b,PLACES,label,NULL,shown,5);
    assert(b.shown_count==PLACES && b.selection==0 && b.top==0 && AW_ListBoxSelected(&b)==0);
    /* moving keeps the selection on screen; the ends stop */
    assert(AW_ListBoxKey(&b,AW_LBKEY_UP)==AW_LB_NONE && b.selection==0);
    for(i=0;i<6;i++)AW_ListBoxKey(&b,AW_LBKEY_DOWN);
    assert(b.selection==6 && b.top==2);
    AW_ListBoxKey(&b,AW_LBKEY_PAGEDOWN);assert(b.selection==11 && b.top==7);
    AW_ListBoxKey(&b,AW_LBKEY_END);assert(b.selection==PLACES-1 && b.top==PLACES-5);
    AW_ListBoxKey(&b,AW_LBKEY_PAGEDOWN);assert(b.selection==PLACES-1);
    AW_ListBoxKey(&b,AW_LBKEY_HOME);assert(b.selection==0 && b.top==0);
    AW_ListBoxKey(&b,AW_LBKEY_PAGEUP);assert(b.selection==0);

    /* typing filters as you type; the selected row stays selected while it is shown */
    AW_ListBoxKey(&b,AW_LBKEY_DOWN);AW_ListBoxKey(&b,AW_LBKEY_DOWN);              /* Caldera */
    type(&b,"a");assert(AW_ListBoxSelected(&b)==2);                            /* every place with an a */
    type(&b,"r");assert(b.shown_count==3 && AW_ListBoxSelected(&b)==7);        /* ar: Tel Aruhn, Vivec, Arena, Vivec, Foreign Quarter */
    assert(!strcmp(b.search,"ar"));
    type(&b,"en");assert(b.shown_count==1 && AW_ListBoxSelected(&b)==11);      /* aren: Vivec, Arena */
    assert(AW_ListBoxKey(&b,AW_LBKEY_CHOOSE)==AW_LB_CHOSEN);
    type(&b,"q");assert(b.shown_count==0 && AW_ListBoxSelected(&b)==-1);
    assert(AW_ListBoxKey(&b,AW_LBKEY_CHOOSE)==AW_LB_NONE);                       /* nothing to choose */
    assert(AW_ListBoxKey(&b,AW_LBKEY_DOWN)==AW_LB_NONE && AW_ListBoxSelected(&b)==-1);
    assert(AW_ListBoxKey(&b,AW_LBKEY_BACKSPACE)==AW_LB_NONE && b.shown_count==1);
    for(i=0;i<4;i++)AW_ListBoxKey(&b,AW_LBKEY_BACKSPACE);
    assert(!b.search[0] && b.shown_count==PLACES && AW_ListBoxSelected(&b)==11);  /* still Vivec, Arena */
    assert(AW_ListBoxKey(&b,AW_LBKEY_BACKSPACE)==AW_LB_NONE && b.shown_count==PLACES);
    /* spaces: none first, never two; control characters are not typed; the field has a limit */
    assert(AW_ListBoxType(&b,' ') && !b.search[0]);
    type(&b,"tel  m");assert(!strcmp(b.search,"tel m") && b.shown_count==1 && AW_ListBoxSelected(&b)==9);
    assert(!AW_ListBoxType(&b,'\n') && !AW_ListBoxType(&b,200));
    for(i=0;i<40;i++)AW_ListBoxType(&b,'z');
    assert(strlen(b.search)==AW_LISTBOX_SEARCH);
    for(i=0;i<40;i++)AW_ListBoxKey(&b,AW_LBKEY_BACKSPACE);
    assert(AW_ListBoxKey(&b,AW_LBKEY_CLOSE)==AW_LB_CLOSED);

    /* clicks: a row on screen chooses it, below the rows nothing; the scroll bar moves the window */
    AW_ListBoxReset(&b,PLACES,label,NULL,shown,5);
    AW_ListBoxScroll(&b,4);assert(b.top==4 && b.selection==4);
    assert(AW_ListBoxClick(&b,2)==AW_LB_CHOSEN && AW_ListBoxSelected(&b)==6);
    assert(AW_ListBoxClick(&b,5)==AW_LB_NONE && AW_ListBoxClick(&b,-1)==AW_LB_NONE);
    AW_ListBoxScroll(&b,99);assert(b.top==PLACES-5 && b.selection==PLACES-5);
    AW_ListBoxScroll(&b,-3);assert(b.top==0 && b.selection==4);
    type(&b,"khuul");assert(AW_ListBoxClick(&b,1)==AW_LB_NONE && AW_ListBoxClick(&b,0)==AW_LB_CHOSEN && AW_ListBoxSelected(&b)==4);
    /* a smaller window keeps the selection on it */
    AW_ListBoxReset(&b,PLACES,label,NULL,shown,8);AW_ListBoxKey(&b,AW_LBKEY_END);
    AW_ListBoxSetVisible(&b,3);assert(b.top==PLACES-3 && b.selection==PLACES-1);
    /* labels are asked for only when filtering (and drawing, in the game) */
    label_calls=0;AW_ListBoxKey(&b,AW_LBKEY_UP);assert(!label_calls);

    /* the category buttons (TP-MENU-CATEGORY-FILTER-66): All by default, the search filters within the chosen one */
    AW_ListBoxReset(&b,PLACES,label,NULL,shown,5);
    AW_ListBoxCategories(&b,category,4);
    assert(b.categories==4 && b.chosen==0 && b.shown_count==PLACES);
    AW_ListBoxChoose(&b,3);assert(b.shown_count==2 && b.shown[0]==1 && b.shown[1]==8);   /* Balmora, Tel Branora */
    type(&b,"tel");assert(b.shown_count==1 && AW_ListBoxSelected(&b)==8);
    AW_ListBoxKey(&b,AW_LBKEY_RIGHT);assert(b.chosen==0 && b.shown_count==3);           /* back to All: 3 Tel */
    AW_ListBoxKey(&b,AW_LBKEY_LEFT);assert(b.chosen==3);
    AW_ListBoxKey(&b,AW_LBKEY_LEFT);assert(b.chosen==2);
    AW_ListBoxChoose(&b,9);assert(b.chosen==2);                                          /* no such button */
    AW_ListBoxReset(&b,PLACES,label,NULL,shown,5);
    assert(!b.categories && AW_ListBoxKey(&b,AW_LBKEY_LEFT)==AW_LB_NONE && b.shown_count==PLACES);   /* no buttons */

    /* the free spot beside a being: the side towards the player first, then either way round, then wider rings */
    {
        float c[3]={0,0,0},from[3]={100,0,0},o[3],got[3];int n;
        AW_TpSpotCandidate(c,from,40,0,o);assert(o[0]>39.9f && o[0]<40.1f && o[1]==0);
        AW_TpSpotCandidate(c,from,40,1,o);assert(o[0]>36 && o[1]>15);
        AW_TpSpotCandidate(c,from,40,2,o);assert(o[0]>36 && o[1]<-15);
        AW_TpSpotCandidate(c,from,40,16,o);assert(o[0]>63.9f && o[0]<64.1f);
        AW_TpSpotCandidate(c,from,40,32,o);assert(o[0]>87.9f && o[0]<88.1f);
        /* a wall on the player's side (x > 20) and a table at (0, 40): the first free one is behind the being */
        n=AW_TpPickSpot(c,from,40,blocked_wall_table,NULL,got);
        assert(n>0 && got[0]<20 && !(got[0]>-25 && got[0]<25 && got[1]>15 && got[1]<65));
        assert(!AW_TpPickSpot(c,from,40,blocked_all,NULL,got));
        assert(AW_TpFacingYaw(got,c)>=0 && AW_TpFacingYaw(got,c)<360);
        {float a[3]={0,0,0},e[3]={0,10,0},w[3]={-10,0,0};
         assert(AW_TpFacingYaw(a,e)>89.9f && AW_TpFacingYaw(a,e)<90.1f);
         assert(AW_TpFacingYaw(a,w)>179.9f && AW_TpFacingYaw(a,w)<180.1f);}
        /* TP-BEING-TRIBUNAL-FALLS-THROUGH-67: 'Ten-Tongues' Weerhat's row (-7 76 -91, his feet) arrives as a door
         * does, 16.875 over his floor (the player's box bottom -16.625 plus .25), never at the feet */
        {float feet[3]={-7,76,-91},arrival[3];
         AW_TpBeingArrival(feet,-16.625f,arrival);
         assert(arrival[0]==-7 && arrival[1]==76 && arrival[2]>-74.126f && arrival[2]<-74.124f);}
    }

    /* the settlements table */
    memset(table,0,sizeof(table));
    memcpy(table,"AWTP",4);table[5]=1;table[7]=AW_TP_ROW;put32(table+8,2);
    memcpy(table+AW_TP_HEADER,"Balmora",7);put32(table+AW_TP_HEADER+32,-20536);put32(table+AW_TP_HEADER+36,-13960);
    put32(table+AW_TP_HEADER+40,378);table[AW_TP_HEADER+44]=AW_TP_HAS_Z|AW_TP_DOOR;table[AW_TP_HEADER+45]=4;
    memset(table+AW_TP_HEADER+AW_TP_ROW,'x',AW_TP_NAME1);                        /* no NUL: cut at 31 */
    put32(table+AW_TP_HEADER+AW_TP_ROW+32,12288);put32(table+AW_TP_HEADER+AW_TP_ROW+36,-36864);
    assert(AW_TpPlacesRows(table,sizeof(table))==2);
    assert(AW_TpPlacesRows(table,sizeof(table)-1)==-1 && AW_TpPlacesRows(table,8)==-1 && AW_TpPlacesRows(NULL,64)==-1);
    table[5]=2;assert(AW_TpPlacesRows(table,sizeof(table))==-1);table[5]=1;
    table[7]=40;assert(AW_TpPlacesRows(table,sizeof(table))==-1);table[7]=AW_TP_ROW;
    table[0]='X';assert(AW_TpPlacesRows(table,sizeof(table))==-1);table[0]='A';
    AW_TpPlacesRow(table,0,&p);
    assert(!strcmp(p.name,"Balmora") && p.x==-20536 && p.y==-13960 && p.z==378 && p.flags==3 && p.cells==4);
    assert(AW_TpPlacesCommand(&p,line,sizeof(line))>0 && !strcmp(line,"aw_teleport -20536 -13960 378\n"));
    AW_TpPlacesRow(table,1,&p);
    assert(strlen(p.name)==AW_TP_NAME1-1 && p.x==12288 && p.y==-36864 && p.flags==0);
    assert(AW_TpPlacesCommand(&p,line,sizeof(line))>0 && !strcmp(line,"aw_teleport 12288 -36864\n"));  /* no z: the floor below */
    assert(AW_TpPlacesCommand(&p,line,20)==-1 && AW_TpPlacesCommand(NULL,line,sizeof(line))==-1);
    p.x=-2147483647L;p.y=2147483647L;p.z=-1;p.flags=AW_TP_HAS_Z;
    assert(AW_TpPlacesCommand(&p,line,sizeof(line))>0 && !strcmp(line,"aw_teleport -2147483647 2147483647 -1\n"));
    /* an old (version 1) row never reads as a room, even with bit 8 set */
    table[AW_TP_HEADER+44]|=AW_TP_ROOM;AW_TpPlacesRow(table,0,&p);
    assert(!(p.flags&AW_TP_ROOM) && !p.map[0] && !strcmp(line,"aw_teleport -2147483647 2147483647 -1\n"));

    /* version 2 (TP-MENU-INTERIORS-63): a long name, a room row with its map, dbg tp <map> */
    memset(table2,0,sizeof(table2));
    memcpy(table2,"AWTP",4);table2[5]=2;table2[7]=AW_TP_ROW2;put32(table2+8,2);
    memcpy(table2+AW_TP_HEADER,"Andrano Ancestral Tomb (interior)",33);
    table2[AW_TP_HEADER+64+12]=AW_TP_ROOM;memcpy(table2+AW_TP_HEADER+80,"ri8c361151ce",12);
    memcpy(table2+AW_TP_HEADER+AW_TP_ROW2,"Balmora",7);put32(table2+AW_TP_HEADER+AW_TP_ROW2+64,-20536);
    put32(table2+AW_TP_HEADER+AW_TP_ROW2+68,-13960);
    assert(AW_TpPlacesRows(table2,sizeof(table2))==2 && AW_TpPlacesRows(table2,sizeof(table2)-1)==-1);
    table2[7]=AW_TP_ROW;assert(AW_TpPlacesRows(table2,sizeof(table2))==-1);table2[7]=AW_TP_ROW2;
    AW_TpPlacesRow(table2,0,&p);
    assert(!strcmp(p.name,"Andrano Ancestral Tomb (interior)") && p.flags==AW_TP_ROOM && !strcmp(p.map,"ri8c361151ce"));
    assert(AW_TpPlacesCommand(&p,line,sizeof(line))>0 && !strcmp(line,"dbg tp ri8c361151ce\n"));
    assert(AW_TpPlacesCommand(&p,line,20)==-1);
    p.map[2]=';';assert(AW_TpPlacesCommand(&p,line,sizeof(line))==-1);       /* never a second console command */
    p.map[0]=0;assert(AW_TpPlacesCommand(&p,line,sizeof(line))==-1);
    AW_TpPlacesRow(table2,1,&p);
    assert(!strcmp(p.name,"Balmora") && !p.map[0] && AW_TpPlacesCommand(&p,line,sizeof(line))>0
        && !strcmp(line,"aw_teleport -20536 -13960\n"));

    /* version 3 (DBG-TP-TO-NPC-66): a being row with its record id; a v2 row never reads as a being */
    {
        unsigned char t3[AW_TP_HEADER+AW_TP_ROW3];
        memset(t3,0,sizeof(t3));memcpy(t3,"AWTP",4);t3[5]=3;t3[7]=AW_TP_ROW3;put32(t3+8,1);
        memcpy(t3+AW_TP_HEADER,"Fargoth",7);put32(t3+AW_TP_HEADER+64,-11000);put32(t3+AW_TP_HEADER+68,-71000);
        t3[AW_TP_HEADER+76]=AW_TP_BEING|AW_TP_HAS_Z;memcpy(t3+AW_TP_HEADER+96,"fargoth",7);
        assert(AW_TpPlacesRows(t3,sizeof(t3))==1);
        AW_TpPlacesRow(t3,0,&p);
        assert(!strcmp(p.name,"Fargoth") && !strcmp(p.id,"fargoth") && (p.flags&AW_TP_BEING) && p.x==-11000);
        assert(AW_TpPlacesCategory(p.flags)==AW_TP_CAT_BEING);
        table2[AW_TP_HEADER+64+12]=AW_TP_ROOM|AW_TP_BEING;AW_TpPlacesRow(table2,0,&p);
        assert(!(p.flags&AW_TP_BEING) && !p.id[0] && AW_TpPlacesCategory(p.flags)==AW_TP_CAT_INTERIOR);
        assert(AW_TpPlacesCategory(0)==AW_TP_CAT_EXTERIOR && AW_TpPlacesCategory(AW_TP_HAS_Z|AW_TP_DOOR)==AW_TP_CAT_EXTERIOR);
    }
    /* DBG-TP-LORDVIVEC-69 (dbg tp lordvivec): the being row of a record id, read row by row from the file at its
     * offset (a pak member), case ignored; a common kind's row never, a place or room row never; a missing id, an empty
     * id, a longer id, an older table and a bad size: -1 */
    {
        unsigned char t[AW_TP_HEADER+4*AW_TP_ROW3],*r;FILE *f;long base;
        memset(t,0,sizeof(t));memcpy(t,"AWTP",4);t[5]=3;t[7]=AW_TP_ROW3;put32(t+8,4);
        /* 0: a place row carrying the id (never a being without its flag) */
        r=t+AW_TP_HEADER;memcpy(r,"Vivec",5);r[76]=AW_TP_HAS_Z;memcpy(r+96,"vivec_god",9);
        /* 1: a common kind's row (AW_TP_NEAREST) with the id in its field: never taken */
        r+=AW_TP_ROW3;memcpy(r,"Vivec",5);r[76]=AW_TP_BEING|AW_TP_NEAREST|AW_TP_HAS_Z;memcpy(r+80,"k0000",5);
        memcpy(r+96,"vivec_god",9);
        /* 2: the being, in his palace (the v0.0.69-dev6 image's row: flags 25, vpi015, 0 4 -98) */
        r+=AW_TP_ROW3;memcpy(r,"Vivec",5);put32(r+64,0);put32(r+68,4);put32(r+72,-98);
        r[76]=AW_TP_BEING|AW_TP_ROOM|AW_TP_HAS_Z;memcpy(r+80,"vpi015",6);memcpy(r+96,"vivec_god",9);
        /* 3: a 31-character id that fills its field */
        r+=AW_TP_ROW3;memcpy(r,"Long",4);r[76]=AW_TP_BEING|AW_TP_HAS_Z;memset(r+96,'a',AW_TP_ID-1);
        f=tmpfile();assert(f);fputs("PAK member before the table",f);base=ftell(f);
        assert(fwrite(t,1,sizeof(t),f)==sizeof(t));fputs("and after",f);
        memset(&p,0,sizeof(p));
        assert(AW_TpPlacesBeingRow(f,base,sizeof(t),"vivec_god",&p)==2);
        assert(!strcmp(p.name,"Vivec") && !strcmp(p.map,"vpi015") && !strcmp(p.id,"vivec_god"));
        assert(p.flags==(AW_TP_BEING|AW_TP_ROOM|AW_TP_HAS_Z) && p.x==0 && p.y==4 && p.z==-98);
        assert(AW_TpPlacesBeingRow(f,base,sizeof(t),"Vivec_GOD",&p)==2);                  /* case ignored */
        assert(AW_TpPlacesBeingRow(f,base,sizeof(t),"vivec",&p)==-1);                      /* the whole id */
        assert(AW_TpPlacesBeingRow(f,base,sizeof(t),"vivec_god_x",&p)==-1);
        assert(AW_TpPlacesBeingRow(f,base,sizeof(t),"no_such_being",&p)==-1);
        assert(AW_TpPlacesBeingRow(f,base,sizeof(t),"",&p)==-1 && AW_TpPlacesBeingRow(f,base,sizeof(t),NULL,&p)==-1);
        {char id[AW_TP_ID+1];for(i=0;i<AW_TP_ID-1;i++)id[i]='A';id[AW_TP_ID-1]=0;
         assert(AW_TpPlacesBeingRow(f,base,sizeof(t),id,&p)==3);
         id[AW_TP_ID-1]='a';id[AW_TP_ID]=0;assert(AW_TpPlacesBeingRow(f,base,sizeof(t),id,&p)==-1);}  /* longer */
        assert(AW_TpPlacesBeingRow(f,base,sizeof(t)-1,"vivec_god",&p)==-1);               /* the size exact */
        assert(AW_TpPlacesBeingRow(NULL,base,sizeof(t),"vivec_god",&p)==-1);
        fclose(f);
        /* an older table (version 2) has no ids: -1 */
        f=tmpfile();assert(f);assert(fwrite(table2,1,sizeof(table2),f)==sizeof(table2));
        assert(AW_TpPlacesBeingRow(f,0,sizeof(table2),"vivec_god",&p)==-1);
        fclose(f);
    }
    /* a common kind's placements file */
    {
        unsigned char k[AW_TPK_HEADER+2*AW_TPK_ROW];
        memset(k,0,sizeof(k));memcpy(k,"AWTK",4);k[5]=1;k[7]=AW_TPK_ROW;put32(k+8,2);
        memcpy(k+AW_TPK_HEADER,"slaughterfish",13);put32(k+AW_TPK_HEADER+48,100);
        memcpy(k+AW_TPK_HEADER+AW_TPK_ROW,"slaughterfish_small",19);memcpy(k+AW_TPK_HEADER+AW_TPK_ROW+32,"rroom1",6);
        put32(k+AW_TPK_HEADER+AW_TPK_ROW+56,-8);
        assert(AW_TpKindRows(k,sizeof(k))==2 && AW_TpKindRows(k,sizeof(k)-1)==-1);
        AW_TpKindRow(k,0,&p);assert(!strcmp(p.id,"slaughterfish") && !p.map[0] && p.x==100 && !(p.flags&AW_TP_ROOM));
        AW_TpKindRow(k,1,&p);assert(!strcmp(p.map,"rroom1") && p.z==-8 && (p.flags&AW_TP_ROOM));
        k[0]='X';assert(AW_TpKindRows(k,sizeof(k))==-1);
    }
    puts("listbox rules ok");
    return 0;
}
