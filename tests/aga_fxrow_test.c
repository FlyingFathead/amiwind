/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_fxrow_rules.c alone (HUD-ACTIVE-EFFECTS-ROW-64): one icon per effect in effect-number order, the grid of at most
 * three rows with "+N" in the last place, the places, the texts, the wrapping, the effect file's directory. */
#include <assert.h>
#include <string.h>
#include "aw_fxrow.h"

static aw_fx_entry_t entry(int effect,int arg,int from,float magnitude,float left){
    aw_fx_entry_t e;memset(&e,0,sizeof(e));e.effect=(short)effect;e.arg=(short)arg;e.from=(unsigned char)from;
    e.magnitude=magnitude;e.left=left;e.source=-1;return e;
}
static void put32(unsigned char *p,unsigned long v){p[0]=v&255;p[1]=(v>>8)&255;p[2]=(v>>16)&255;p[3]=(v>>24)&255;}

int main(void){
    aw_fx_entry_t e[8];aw_fx_group_t g[8];aw_fx_layout_t l;int n,x,y;char text[32],lines[6][AW_FX_LINE];
    /* grouping: by effect number (OpenMW's map), sources of one effect together in the order they came */
    e[0]=entry(79,0,AW_FX_FROM_SPELL,10,30);     /* Fortify Attribute: Strength, a spell, 30 s */
    e[1]=entry(41,-1,AW_FX_FROM_ITEM,20,60);     /* Light, a potion */
    e[2]=entry(79,1,AW_FX_FROM_WORN,5,-1);       /* Fortify Attribute: Intelligence, a ring */
    e[3]=entry(0,-1,AW_FX_FROM_ABILITY,1,-1);    /* Water Breathing, the race */
    e[4]=entry(79,0,AW_FX_FROM_ITEM,8,12);       /* Fortify Strength again, a potion, 12 s */
    assert(AW_FxSort(e,5)==5);
    assert(e[0].effect==0 && e[1].effect==41 && e[2].effect==79 && e[3].effect==79 && e[4].effect==79);
    assert(e[2].left==30 && e[3].left==-1 && e[4].left==12);   /* stable */
    n=AW_FxGroups(e,5,g,8);
    assert(n==3 && g[0].effect==0 && g[1].effect==41 && g[2].effect==79);
    assert(g[2].first==2 && g[2].count==3 && g[2].permanent && g[2].left==12);
    assert(g[1].count==1 && !g[1].permanent && g[1].left==60);
    assert(g[0].permanent && g[0].left<0);
    assert(AW_FxGroups(e,5,g,2)==2);                            /* at most MAX */
    e[0].effect=200;assert(AW_FxGroups(e,5,g,8)==2);            /* not one of the game's numbers: no icon */
    assert(AW_FxGroups(e,0,g,8)==0 && AW_FxSort(e,0)==0);
    /* the HUD grid at 320 x 200: from x 152 to 314 (162 pixels), 44 pixels of strip: 12 a row, 3 rows, 36 places */
    assert(AW_FxLayout(5,162,44,AW_FX_HUD_ICON,AW_FX_HUD_STEP,AW_FX_ROWS_MAX,AW_FX_HUD_MAX,&l));
    assert(l.per_row==12 && l.rows==1 && l.shown==5 && l.more==0 && l.places==5);
    assert(AW_FxLayout(12,162,44,12,13,3,48,&l) && l.rows==1 && l.shown==12);
    assert(AW_FxLayout(13,162,44,12,13,3,48,&l) && l.rows==2 && l.shown==13 && !l.more);
    assert(AW_FxLayout(36,162,44,12,13,3,48,&l) && l.rows==3 && l.shown==36 && !l.more);
    /* one more than fits: the last place is "+2" (35 icons and two behind it), never a fourth row */
    assert(AW_FxLayout(37,162,44,12,13,3,48,&l) && l.rows==3 && l.shown==35 && l.more==2 && l.places==36);
    assert(AW_FxLayout(130,162,44,12,13,3,48,&l) && l.rows==3 && l.shown==35 && l.more==95);
    /* 640 wide: 482 pixels, 37 a row; three rows would be 111 places, the picture cache caps them at 48 */
    assert(AW_FxLayout(130,482,44,12,13,3,48,&l) && l.per_row==37 && l.shown==47 && l.more==83 && l.rows==2);
    assert(AW_FxLayout(48,482,44,12,13,3,48,&l) && l.shown==48 && !l.more);
    /* a strip of one row (the Stats window: 122 x 12): 9 places */
    assert(AW_FxLayout(12,122,12,12,13,1,48,&l) && l.per_row==9 && l.rows==1 && l.shown==8 && l.more==4);
    assert(AW_FxLayout(9,122,12,12,13,3,48,&l) && l.shown==9 && !l.more);
    /* no room: nothing; no effects: nothing drawn */
    assert(!AW_FxLayout(3,11,44,12,13,3,48,&l) && !AW_FxLayout(3,100,11,12,13,3,48,&l));
    assert(AW_FxLayout(0,162,44,12,13,3,48,&l) && l.shown==0 && l.rows==0 && l.places==0);
    /* places: row 0 at the bottom, left to right, rows going up */
    AW_FxLayout(37,162,44,12,13,3,48,&l);
    AW_FxPlace(&l,0,152,186,13,&x,&y);assert(x==152 && y==186);
    AW_FxPlace(&l,11,152,186,13,&x,&y);assert(x==152+11*13 && y==186);
    AW_FxPlace(&l,12,152,186,13,&x,&y);assert(x==152 && y==173);
    AW_FxPlace(&l,35,152,186,13,&x,&y);assert(x==152+11*13 && y==160);   /* "+2" in the last place, top right */
    /* texts */
    AW_FxMoreText(92,text,sizeof(text));assert(!strcmp(text,"+92"));
    AW_FxTimeText(-1,text,sizeof(text));assert(!strcmp(text,"permanent"));
    AW_FxTimeText(12.4f,text,sizeof(text));assert(!strcmp(text,"12 s"));
    AW_FxTimeText(59.6f,text,sizeof(text));assert(!strcmp(text,"1 min"));
    AW_FxTimeText(185,text,sizeof(text));assert(!strcmp(text,"3 min 5 s"));
    AW_FxTimeText(7440,text,sizeof(text));assert(!strcmp(text,"2 h 4 min"));
    AW_FxTimeText(7200,text,sizeof(text));assert(!strcmp(text,"2 h"));
    assert(!strcmp(AW_FxFromName(AW_FX_FROM_WORN),"worn item") && !strcmp(AW_FxFromName(99),""));
    assert(AW_FxFromSpellType(1)==AW_FX_FROM_ABILITY && AW_FxFromSpellType(3)==AW_FX_FROM_DISEASE &&
           AW_FxFromSpellType(2)==AW_FX_FROM_BLIGHT && AW_FxFromSpellType(4)==AW_FX_FROM_CURSE &&
           AW_FxFromSpellType(5)==AW_FX_FROM_POWER && AW_FxFromSpellType(0)==AW_FX_FROM_SPELL);
    /* wrapping between words, a long word cut, line breaks as spaces, at most MAX lines */
    {const char *t="This effect raises\r\nthe target's Strength  for a while.";
     n=AW_FxWrap(t,(int)strlen(t),12,lines,6);
     assert(n==5 && !strcmp(lines[0],"This effect") && !strcmp(lines[1],"raises the") &&
            !strcmp(lines[2],"target's") && !strcmp(lines[3],"Strength for") && !strcmp(lines[4],"a while."));}
    {const char *t="Supercalifragilistic x";
     n=AW_FxWrap(t,(int)strlen(t),8,lines,6);
     assert(n==3 && !strcmp(lines[0],"Supercal") && !strcmp(lines[1],"ifragili") && !strcmp(lines[2],"stic x"));}
    {const char *t="a b c d e f";n=AW_FxWrap(t,5,1,lines,2);assert(n==2 && !strcmp(lines[1],"b"));}   /* only BYTES read */
    assert(AW_FxWrap("   ",3,10,lines,6)==0 && AW_FxWrap(NULL,0,10,lines,6)==0);
    /* the effect file: header, rows by effect number, offsets inside the file */
    {static unsigned char f[8+3*16+144+256+5];aw_fx_dir_t d[4];unsigned long size=sizeof(f);
     memcpy(f,"AWE1",4);f[4]=3;f[5]=0;f[6]=12;f[7]=16;
     put32(f+8+16,56);put32(f+8+16+4,56+144);put32(f+8+16+8,56+400);f[8+16+12]=5;   /* row 1: both pictures and 5 bytes */
     assert(AW_FxDirectory(f,size,size,d,4)==3);
     assert(d[0].small==0 && d[1].small==56 && d[1].large==200 && d[1].desc==456 && d[1].desc_bytes==5 && d[3].small==0);
     assert(AW_FxDirectory(f,size,size-1,d,4)==-1);              /* a row past the end */
     assert(AW_FxDirectory(f,20,size,d,4)==-1);                  /* the rows not all read */
     f[6]=16;assert(AW_FxDirectory(f,size,size,d,4)==-1);f[6]=12; /* sizes the engine does not draw */
     f[0]='X';assert(AW_FxDirectory(f,size,size,d,4)==-1);}
    return 0;
}
