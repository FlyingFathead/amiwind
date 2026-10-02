/* SPDX-License-Identifier: GPL-2.0-or-later
 * Build-selected first-person sprite path. Original 3D path remains available.
 * Bounded AWS1 spans are validated once; no disk I/O during animation playback.
 */
#include "quakedef.h"
#ifndef AMIWIND_SPRITE_HANDS
#define AMIWIND_SPRITE_HANDS 0
#endif
#if AMIWIND_SPRITE_HANDS
static byte *data,*torch_data;
static unsigned long offsets[33];
static int frames;
static unsigned int u16(byte *p){return ((unsigned int)p[0]<<8)|p[1];}
static unsigned long u32(byte *p){return ((unsigned long)p[0]<<24)|((unsigned long)p[1]<<16)|((unsigned long)p[2]<<8)|p[3];}
int AW_HandSpritesValidate(byte *p,unsigned long bytes) {
    unsigned long at,end,start;int f,y,r,n,x,len;
    if(bytes<20 || bytes>524288 || memcmp(p,"AWS1",4) || u16(p+4)!=160 || u16(p+6)!=100 || u16(p+10))return 0;
    n=u16(p+8);if(n<1||n>32 || bytes<12+4*(n+1))return 0;
    if(u32(p+12)!=12+4*(n+1) || u32(p+12+4*n)!=bytes)return 0;
    for(f=0;f<n;f++) {
        at=u32(p+12+4*f);end=u32(p+16+4*f);if(at>end || end>bytes)return 0;
        for(y=0;y<100;y++) {
            if(at+2>end)return 0;r=u16(p+at);at+=2;start=0;
            if(r>80)return 0;
            while(r--) {
                if(at+4>end)return 0;x=u16(p+at);len=u16(p+at+2);at+=4;
                if(!len || x<start || x+len>160 || at+len>end)return 0;
                start=x+len;at+=len;
            }
        }
        if(at!=end)return 0;
    }
    return 1;
}
void AW_HandSpritesInit(void) {
    int i,hands_bytes;extern int com_filesize;
    data=COM_LoadHunkFile("gfx/hands.aws");
    if(!data || !AW_HandSpritesValidate(data,com_filesize))Sys_Error("Invalid first-person sprite bake; rebuild with --hands sprites");
    hands_bytes=com_filesize;frames=u16(data+8);for(i=0;i<=frames;i++)offsets[i]=u32(data+12+4*i);
    torch_data=COM_LoadHunkFile("gfx/torch.aws");
    if(!torch_data || !AW_HandSpritesValidate(torch_data,com_filesize) || u16(torch_data+8)!=8)Sys_Error("Invalid original torch sprite bake");
    Con_Printf("First-person sprites: %ld bytes, %ld frames\n",(long)hands_bytes,(long)frames);
}
void AW_HandSpritesDraw(void) {
    byte *p,*dst;int frame=cl.stats[STAT_WEAPONFRAME],y,r,x,n,k,xx,yy,sx,sy,scale,left,top;
    if(!data || frame<0 || frame>=frames)return;
    scale=r_refdef.vrect.width>=320?2:1;
    left=r_refdef.vrect.x+(r_refdef.vrect.width-160*scale)/2;
    top=r_refdef.vrect.y+r_refdef.vrect.height-100*scale;
    if(AW_TorchEquipped()){frame=AW_TorchFrame();p=torch_data+u32(torch_data+12+4*frame);}
    else p=data+offsets[frame];
    for(y=0;y<100;y++) {
        r=u16(p);p+=2;
        while(r--) {
            x=u16(p);n=u16(p+2);p+=4;
            for(sy=0;sy<scale;sy++) {
                yy=top+y*scale+sy;
                if(yy<r_refdef.vrect.y || yy>=r_refdef.vrect.y+r_refdef.vrect.height)continue;
                dst=vid.buffer+yy*vid.rowbytes;
                for(k=0;k<n;k++)for(sx=0;sx<scale;sx++) {
                    xx=left+(x+k)*scale+sx;
                    if(xx>=r_refdef.vrect.x && xx<r_refdef.vrect.x+r_refdef.vrect.width)dst[xx]=p[k];
                }
            }
            p+=n;
        }
    }
}
#else
void AW_HandSpritesInit(void) {}
void AW_HandSpritesDraw(void) {}
#endif
