/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_UI_ARROW_INCLUDED
#define AW_UI_ARROW_INCLUDED
/* INVENTORY-BROWSER-ARROWS-66: the drawn scroll triangles of the race page, shared by every window that pages or
 * scrolls (the race page's rows, the class and birthsign lists, the container strip's pages). A triangle is 7 lines
 * deep and 13 wide: pointing left or right its box is 7 x 13, pointing up or down 13 x 7. Header only, drawn through
 * AW_UIFill and AW_UIColor (aw_ui.c), so every native test that already stubs those draws it into its own picture. */
int AW_UIColor(int r,int g,int b);
void AW_UIFill(int x,int y,int w,int h,int color);
enum {AW_UI_ARROW_LEFT,AW_UI_ARROW_RIGHT,AW_UI_ARROW_UP,AW_UI_ARROW_DOWN};
#define AW_UI_ARROW_DEPTH 7
#define AW_UI_ARROW_SPAN 13
/* the box of an arrow pointing DIR: width and height */
#define AW_UI_ARROW_W(dir) ((dir)<=AW_UI_ARROW_RIGHT?AW_UI_ARROW_DEPTH:AW_UI_ARROW_SPAN)
#define AW_UI_ARROW_H(dir) ((dir)<=AW_UI_ARROW_RIGHT?AW_UI_ARROW_SPAN:AW_UI_ARROW_DEPTH)
/* The states of a page arrow: GREYED (no more that way: the dim colour of the class list's marks), ON (gold), LIT
 * (under the pointer or just used: gold on the race page's row highlight colour, one line past it along its span). */
enum {AW_UI_ARROW_GREYED,AW_UI_ARROW_ON,AW_UI_ARROW_LIT};
/* The triangle pointing DIR in COLOUR, its box's top left at (X,Y): line J from the tip is 2J+1 long, centred. */
static __inline__ void AW_UIArrow(int x,int y,int dir,int colour)
{
    int j,n=AW_UI_ARROW_DEPTH;
    for(j=0;j<n;j++){
        switch(dir){
        case AW_UI_ARROW_LEFT:AW_UIFill(x+j,y+n-1-j,1,j*2+1,colour);break;
        case AW_UI_ARROW_RIGHT:AW_UIFill(x+n-1-j,y+n-1-j,1,j*2+1,colour);break;
        case AW_UI_ARROW_UP:AW_UIFill(x+n-1-j,y+j,j*2+1,1,colour);break;
        default:AW_UIFill(x+j,y+j,(n-1-j)*2+1,1,colour);break;   /* down: the wide line first */
        }
    }
}
/* A page arrow in STATE (above) */
static __inline__ void AW_UIPageArrow(int x,int y,int dir,int state)
{
    int w=AW_UI_ARROW_W(dir),h=AW_UI_ARROW_H(dir);
    if(state==AW_UI_ARROW_LIT){
        if(dir<=AW_UI_ARROW_RIGHT)AW_UIFill(x,y-1,w,h+2,AW_UIColor(54,47,32));
        else AW_UIFill(x-1,y,w+2,h,AW_UIColor(54,47,32));
    }
    AW_UIArrow(x,y,dir,state==AW_UI_ARROW_GREYED?AW_UIColor(84,76,61):AW_UIColor(223,199,144));
}
/* 1 when (PX,PY) is on the arrow's box at (X,Y), with SLACK pixels around it (an easier pointer target) */
static __inline__ int AW_UIArrowHit(int x,int y,int dir,int slack,int px,int py)
{
    return px>=x-slack && px<x+AW_UI_ARROW_W(dir)+slack && py>=y-slack && py<y+AW_UI_ARROW_H(dir)+slack;
}
#endif
