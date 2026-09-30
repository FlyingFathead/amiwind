/* SPDX-License-Identifier: GPL-2.0-or-later
 * Original compact 3x5 diagnostic glyphs in 4x6 cells. No extra atlas buffer.
 * Normal console mode keeps the existing 8x8 readable/retro font untouched.
 */
#include "quakedef.h"
static int small=1;
static const byte glyphs[95][5]={
{0,0,0,0,0},
{2,2,2,0,2},
{5,5,0,0,0},
{5,7,5,7,5},
{3,6,2,3,6},
{5,1,2,4,5},
{2,5,2,5,3},
{2,2,0,0,0},
{1,2,2,2,1},
{4,2,2,2,4},
{0,5,2,5,0},
{0,2,7,2,0},
{0,0,0,2,4},
{0,0,7,0,0},
{0,0,0,0,2},
{1,1,2,4,4},
{7,5,5,5,7},
{2,6,2,2,7},
{6,1,2,4,7},
{6,1,2,1,6},
{5,5,7,1,1},
{7,4,6,1,6},
{3,4,7,5,7},
{7,1,2,2,2},
{7,5,7,5,7},
{7,5,7,1,6},
{0,2,0,2,0},
{0,2,0,2,4},
{1,2,4,2,1},
{0,7,0,7,0},
{4,2,1,2,4},
{6,1,2,0,2},
{7,5,7,4,3},
{2,5,7,5,5},
{6,5,6,5,6},
{3,4,4,4,3},
{6,5,5,5,6},
{7,4,6,4,7},
{7,4,6,4,4},
{3,4,5,5,3},
{5,5,7,5,5},
{7,2,2,2,7},
{1,1,1,5,2},
{5,5,6,5,5},
{4,4,4,4,7},
{5,7,7,5,5},
{5,7,7,7,5},
{2,5,5,5,2},
{6,5,6,4,4},
{2,5,5,7,3},
{6,5,6,5,5},
{3,4,2,1,6},
{7,2,2,2,2},
{5,5,5,5,7},
{5,5,5,5,2},
{5,5,7,7,5},
{5,5,2,5,5},
{5,5,2,2,2},
{7,1,2,4,7},
{3,2,2,2,3},
{4,4,2,1,1},
{6,2,2,2,6},
{2,5,0,0,0},
{0,0,0,0,7},
{4,2,0,0,0},
{0,3,5,5,3},
{4,4,6,5,6},
{0,3,4,4,3},
{1,1,3,5,3},
{0,2,5,6,3},
{3,2,7,2,2},
{0,3,5,3,6},
{4,4,6,5,5},
{2,0,2,2,2},
{1,0,1,5,2},
{4,5,6,6,5},
{6,2,2,2,3},
{0,7,7,5,5},
{0,6,5,5,5},
{0,2,5,5,2},
{0,6,5,6,4},
{0,3,5,3,1},
{0,5,6,4,4},
{0,3,6,1,6},
{2,7,2,2,3},
{0,5,5,5,3},
{0,5,5,5,2},
{0,5,5,7,7},
{0,5,2,2,5},
{0,5,5,3,6},
{0,7,1,4,7},
{3,2,6,2,3},
{2,2,2,2,2},
{6,2,3,2,6},
{0,3,6,0,0}
};
void AW_ConsoleSetSmall(int value) {small=value!=0;}
int AW_ConsoleCharWidth(void) {return small?4:8;}
int AW_ConsoleCharHeight(void) {return small?6:8;}
void AW_SmallString(int x,int y,const char *text) {
    int r,col,c,bits;byte *p;
    for(;*text && x<vid.width;text++,x+=4){
        c=*text&127;if(c<32 || c>126)continue;
        for(r=0;r<5;r++){
            if(y+r<0 || y+r>=vid.height)continue;
            bits=glyphs[c-32][r];p=vid.buffer+(y+r)*vid.rowbytes;
            for(col=0;col<3;col++)if(x+col>=0 && x+col<vid.width && (bits&(4>>col)))p[x+col]=254;
        }
    }
}
void AW_ConsoleCharacter(int x,int y,int c) {
    int r,col,bits;byte *p;c&=127;
    if(!small){Draw_Character(x,y,c);return;}
    if(c==10)c='>';else if(c==11)c='_';
    if(c<32 || c>126)return;
    for(r=0;r<5;r++) {
        if(y+r<0 || y+r>=vid.conheight)continue;
        bits=glyphs[c-32][r];p=vid.conbuffer+(y+r)*vid.conrowbytes;
        for(col=0;col<3;col++)if(x+col>=0 && x+col<vid.conwidth && (bits&(4>>col)))p[x+col]=254;
    }
}
