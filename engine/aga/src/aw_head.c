/* SPDX-License-Identifier: GPL-2.0-or-later
 * Small UI-only mesh preview. Two fixed slots, no model cache/hunk ownership. */
#include "quakedef.h"
#include "aw_character.h"
#define HEAD_FACES 480
static byte mesh[2][6+HEAD_FACES*82];
static int faces[2],loaded[2]={-1,-1};
static short depth[108*122];
static int u16(const byte *p){return p[0]+(p[1]<<8);}
void AW_HeadClear(void){faces[0]=faces[1]=0;loaded[0]=loaded[1]=-1;}
int AW_HeadDecode(int slot,const byte *raw,int size)
{
    int n;
    if(slot<0 || slot>1)return 0;
    faces[slot]=0;loaded[slot]=-1;
    if(size<6 || memcmp(raw,"AWH1",4))return 0;
    n=u16(raw+4);
    if(n<1 || n>HEAD_FACES || size!=6+n*82)return 0;
    memmove(mesh[slot],raw,size);faces[slot]=n;return 1;
}
int AW_HeadLoad(int head,int hair)
{
    int ids[2],slot,size,n;FILE *f;char path[40];
    ids[0]=head;ids[1]=hair;
    for(slot=0;slot<2;slot++){
        if(ids[slot]<0 || ids[slot]>=384){faces[slot]=0;return 0;}
        if(loaded[slot]==ids[slot])continue;
        faces[slot]=0;loaded[slot]=-1;f=NULL;
        sprintf(path,"character/h%03ld.awh",(long)ids[slot]);size=COM_FOpenFile(path,&f);
        if(!f)return 0;
        n=size>=6 && size<=(int)sizeof(mesh[slot]) && fread(mesh[slot],1,size,f)==(size_t)size;
        fclose(f);
        if(!n || !AW_HeadDecode(slot,mesh[slot],size))return 0;
        loaded[slot]=ids[slot];
    }
    return 1;
}
void AW_HeadDraw(int x,int y,int width,int height,float angle)
{
    int slot,i,j,k,xx,yy,x0,y0,x1,y1,ix,iy,z;
    byte *p;float points[3][3],low[3],high[3],centre[3],scale,cs,sn,a,b,c,area,dx,dy,dz;
    if(width<1 || width>108 || height<1 || height>122 || x<0 || y<0 || x+width>(int)vid.width || y+height>(int)vid.height)return;
    if(!faces[0] || !faces[1]){AW_UITextBox(x,y,width,height,"Preview unavailable",-1);return;}
    for(i=0;i<3;i++){low[i]=32768;high[i]=-32768;}
    for(slot=0;slot<2;slot++)for(i=0;i<faces[slot];i++){
        p=mesh[slot]+6+i*82;
        for(j=0;j<3;j++)for(k=0;k<3;k++){
            a=(short)u16(p+(j*3+k)*2)/512.f;
            if(a<low[k])low[k]=a;
            if(a>high[k])high[k]=a;
        }
    }
    for(i=0;i<3;i++)centre[i]=(low[i]+high[i])*.5f;
    a=high[0]-low[0];b=high[1]-low[1];c=high[2]-low[2];
    a=sqrt(a*a+b*b);
    if(a<.01 || c<.01)return;
    scale=(width-8)/a;
    if(scale>(height-8)/c)scale=(height-8)/c;
    cs=cos(angle);sn=sin(angle);
    for(i=0;i<width*height;i++)depth[i]=32767;
    AW_UIFill(x,y,width,height,AW_UIColor(16,17,18));
    for(slot=0;slot<2;slot++)for(i=0;i<faces[slot];i++){
        p=mesh[slot]+6+i*82;
        for(j=0;j<3;j++){
            dx=(short)u16(p+j*6)/512.f-centre[0];dy=(short)u16(p+j*6+2)/512.f-centre[1];dz=(short)u16(p+j*6+4)/512.f-centre[2];
            points[j][0]=width*.5f+(dx*cs-dy*sn)*scale;
            points[j][1]=height*.5f-dz*scale;
            points[j][2]=(dx*sn+dy*cs)*128;
        }
        area=(points[1][0]-points[0][0])*(points[2][1]-points[0][1])-(points[1][1]-points[0][1])*(points[2][0]-points[0][0]);
        if(fabs(area)<.01f)continue;
        x0=width-1;y0=height-1;x1=y1=0;
        for(j=0;j<3;j++){
            if(points[j][0]<x0)x0=(int)floor(points[j][0]);
            if(points[j][0]>x1)x1=(int)ceil(points[j][0]);
            if(points[j][1]<y0)y0=(int)floor(points[j][1]);
            if(points[j][1]>y1)y1=(int)ceil(points[j][1]);
        }
        if(x0<0)x0=0;
        if(y0<0)y0=0;
        if(x1>=width)x1=width-1;
        if(y1>=height)y1=height-1;
        for(yy=y0;yy<=y1;yy++)for(xx=x0;xx<=x1;xx++){
            dx=xx+.5f-points[0][0];dy=yy+.5f-points[0][1];
            b=(dx*(points[2][1]-points[0][1])-dy*(points[2][0]-points[0][0]))/area;
            c=((points[1][0]-points[0][0])*dy-(points[1][1]-points[0][1])*dx)/area;a=1-b-c;
            if(a<0 || b<0 || c<0)continue;
            z=(int)(a*points[0][2]+b*points[1][2]+c*points[2][2]);
            if(z>=depth[yy*width+xx])continue;
            ix=(int)(b*7+.5f);iy=(int)(c*7+.5f);
            if(ix<0 || ix>7 || iy<0 || iy>7)continue;
            depth[yy*width+xx]=z;vid.buffer[(y+yy)*vid.rowbytes+x+xx]=p[18+iy*8+ix];
        }
    }
}
