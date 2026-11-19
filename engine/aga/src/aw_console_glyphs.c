/* SPDX-License-Identifier: GPL-2.0-or-later
 * Original compact 3x5 diagnostic glyphs in 4x6 cells. No extra atlas buffer.
 * Normal console mode keeps the existing 8x8 readable/retro font untouched.
 */
#include "quakedef.h"
#include "aw_layout.h"
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
/* UI-CONSOLE-FONT-SPECIAL-LETTERS-67: both console fonts have the 95 printable ASCII characters only, while the game's
 * texts are Windows-1252 (the data's own encoding: "gro-Muzgúb", "protégé", "He’ll"). A character past 127 is drawn as
 * the nearest one the font has (a letter without its accent, a curly quote straight), never as the one its low seven
 * bits name (before: ú drew z, é i, ’ the large font's coloured digit). The game prints no coloured console line (Quake's
 * \1 and \2 prefixes, the high bit in the console text), so the console's own text is unchanged. 128 bytes, one look-up
 * a character. tests/test_dialogue_text_variables.py checks the table against the code page; tests/aga_console_test.c
 * draws through it. */
static const char cp1252_plain[129]=
    "E?,f\".++^%S<O?Z?"     /* 0x80-0x8F: euro, -, low quote, florin, low double quote, ellipsis, daggers, ... */
    "?''\"\"*--~Ts>o?zY"    /* 0x90-0x9F: curly quotes, bullet, dashes, tilde, trademark, s caron, ... */
    " !cLoY|S\"ca<--R-"     /* 0xA0-0xAF: no-break space, inverted !, cent, pound, ... soft hyphen, (R), macron */
    "o+23'uP.,1o>????"      /* 0xB0-0xBF: degree, plus-minus, superscripts, acute, micro, ... fractions, inverted ? */
    "AAAAAAACEEEEIIII"      /* 0xC0-0xCF */
    "DNOOOOOxOUUUUYTs"      /* 0xD0-0xDF */
    "aaaaaaaceeeeiiii"      /* 0xE0-0xEF */
    "dnooooo/ouuuuyty";     /* 0xF0-0xFF */
int AW_ConsoleTextGlyph(int c) {c&=255;return c<128?c:(unsigned char)cp1252_plain[c-128];}
void AW_ConsoleSetSmall(int value) {small=value!=0;}
int AW_ConsoleCharWidth(void) {return small?4:8;}
int AW_ConsoleCharHeight(void) {return small?6:8;}
void AW_SmallString(int x,int y,const char *text) {
    int r,col,c,bits;byte *p;
    for(;*text && x<(int)vid.width;text++,x+=4){
        c=AW_ConsoleTextGlyph((unsigned char)*text);if(c<32 || c>126)continue;
        for(r=0;r<5;r++){
            if(y+r<0 || y+r>=(int)vid.height)continue;
            bits=glyphs[c-32][r];p=vid.buffer+(y+r)*vid.rowbytes;
            for(col=0;col<3;col++)if(x+col>=0 && x+col<(int)vid.width && (bits&(4>>col)))p[x+col]=254;
        }
    }
}
/* Inventory reuses the console glyphs, with its own ink and strict field
 * bounds. It never changes the console size or allocates another atlas. */
void AW_SmallStringColor(int x,int y,int width,const char *text,int color) {
    int r,col,c,bits,right=x+width;byte *p;
    if(width<4 || !text)return;
    /* UI-NO-SHARED-LAYOUT-67: the line as the layout check measures it (the 3x5 letters of the characters that fit) */
    if(AW_LayoutRecording){int n=(int)strlen(text);if(n>width/4)n=width/4;if(n>0)AW_LayoutRecord(AW_LAYOUT_TEXT,x,y,4*n-1,5,text);}
    for(;*text && x+4<=right;text++,x+=4){
        c=AW_ConsoleTextGlyph((unsigned char)*text);if(c<32 || c>126)c='?';
        for(r=0;r<5;r++){
            if(y+r<0 || y+r>=(int)vid.height)continue;
            bits=glyphs[c-32][r];p=vid.buffer+(y+r)*vid.rowbytes;
            for(col=0;col<3;col++)
                if(x+col>=0 && x+col<(int)vid.width && (bits&(4>>col)))p[x+col]=(byte)color;
        }
    }
}
/* STEAL-PROMPT-58: a console character in a warning colour (the red "E: Steal" prompt): the small font in palette
 * index RED, the large font from the character set's coloured half (Quake's conchars, characters 128-255). */
void AW_ConsoleCharacterRed(int x,int y,int c,int red) {
    int r,col,bits;byte *p;c=AW_ConsoleTextGlyph(c);
    if(!small){Draw_Character(x,y,c|128);return;}
    if(c<32 || c>126)return;
    for(r=0;r<5;r++) {
        if(y+r<0 || y+r>=(int)vid.conheight)continue;
        bits=glyphs[c-32][r];p=vid.conbuffer+(y+r)*vid.conrowbytes;
        for(col=0;col<3;col++)if(x+col>=0 && x+col<(int)vid.conwidth && (bits&(4>>col)))p[x+col]=(byte)red;
    }
}
void AW_ConsoleCharacter(int x,int y,int c) {
    int r,col,bits;byte *p;c=AW_ConsoleTextGlyph(c);
    if(!small){Draw_Character(x,y,c);return;}
    if(c==10)c='>';else if(c==11)c='_';
    if(c<32 || c>126)return;
    for(r=0;r<5;r++) {
        if(y+r<0 || y+r>=(int)vid.conheight)continue;
        bits=glyphs[c-32][r];p=vid.conbuffer+(y+r)*vid.conrowbytes;
        for(col=0;col<3;col++)if(x+col>=0 && x+col<(int)vid.conwidth && (bits&(4>>col)))p[x+col]=254;
    }
}
