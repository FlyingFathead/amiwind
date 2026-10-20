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
        n=0;
        if(size>=6 && size<=(int)sizeof(mesh[slot])){
            int offset=0,take;
            /* These UI meshes use fixed slots, independent of the model/SFX
             * cache. Keep ordinary music and DMA serviced between bounded reads. */
            CDAudio_Update();S_ExtraUpdate();
            while(offset<size){
                take=size-offset;if(take>4096)take=4096;
                if(fread(mesh[slot]+offset,1,take,f)!=(size_t)take)break;
                offset+=take;CDAudio_Update();S_ExtraUpdate();
            }
            n=offset==size;
        }
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
    cs=Q_CosRad(angle);sn=Q_SinRad(angle);
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

/* Full-height inventory alias preview reuses the UI mesh depth/barycentric
 * method above and AmiQuake's model cache, frame/skin/seam representation.
 * It never changes the world's refdef, renderer lists, camera or simulation. */
static short *inventory_depth;
void AW_InventoryPreviewClear(void){free(inventory_depth);inventory_depth=NULL;AW_ViewInventoryClear();}
typedef struct {
    model_t *model;int frame;float origin[3],forward[3],right[3],up[3];
} inventory_part_t;
static int inventory_alias(inventory_part_t *part,aliashdr_t **header,mdl_t **mdl,trivertx_t **verts){
    aliashdr_t *h=(aliashdr_t *)Mod_Extradata(part->model);mdl_t *m;
    if(!h)return 0;
    m=(mdl_t *)((byte *)h+h->model);
    if(part->frame<0 || part->frame>=m->numframes || m->numverts<1 || m->numtris<1)return 0;
    if(h->frames[part->frame].type==ALIAS_GROUP){
        maliasgroup_t *g=(maliasgroup_t *)((byte *)h+h->frames[part->frame].frame);
        *verts=(trivertx_t *)((byte *)h+g->frames[0].frame);
    }else *verts=(trivertx_t *)((byte *)h+h->frames[part->frame].frame);
    *header=h;*mdl=m;return 1;
}
static void inventory_point(const inventory_part_t *part,const mdl_t *m,const trivertx_t *v,float point[3]){
    float local[3];int k;
    for(k=0;k<3;k++)local[k]=v->v[k]*m->scale[k]+m->scale_origin[k];
    for(k=0;k<3;k++)point[k]=part->origin[k]+local[0]*part->forward[k]-local[1]*part->right[k]+local[2]*part->up[k];
}
int AW_InventoryPreviewDraw(model_t *model,int frame,int x,int y,int width,int height,float angle){
    inventory_part_t part[3];model_t *gear[2];float origins[2][3],angles[2][3],point[3],zero[3]={0,0,0};
    aliashdr_t *h;mdl_t *m;trivertx_t *v;mtriangle_t *tri;stvert_t *st;
    maliasskindesc_t *sd;byte *skin;int i,j,k,which,count=1,n,xx,yy,x0,y0,x1,y1,ix,iy,z;
    float low[3],high[3],centre[3],points[3][3],uv[3][2],scale,cs,sn;
    float a,b,c,area,dx,dy,dz,span;
    if(!model || model->type!=mod_alias || width<1 || width>122 || height<1 || height>168 ||
       x<0 || y<0 || x+width>(int)vid.width || y+height>(int)vid.height)return 0;
    memset(part,0,sizeof(part));part[0].model=model;part[0].frame=frame;
    AngleVectors(zero,part[0].forward,part[0].right,part[0].up);
    n=AW_ViewInventoryEquipment(gear,origins,angles);
    for(i=0;i<n && count<3;i++){
        part[count].model=gear[i];part[count].frame=0;VectorCopy(origins[i],part[count].origin);
        AngleVectors(angles[i],part[count].forward,part[count].right,part[count].up);count++;
    }
    /* The carried torch shares the torch body's frame and placement (PLAYER-TORCH-THIRDPERSON-38). */
    if(count<3 && AW_ViewInventoryHeld(&part[count].model,&part[count].frame)){
        AngleVectors(zero,part[count].forward,part[count].right,part[count].up);count++;
    }
    if(!inventory_depth)inventory_depth=(short *)malloc(122*168*sizeof(short));
    if(!inventory_depth)return 0;
    for(k=0;k<3;k++){low[k]=32768;high[k]=-32768;}
    for(which=0;which<count;which++){
        if(!inventory_alias(&part[which],&h,&m,&v))return 0;
        for(i=0;i<m->numverts;i++){
            inventory_point(&part[which],m,&v[i],point);
            for(k=0;k<3;k++){if(point[k]<low[k])low[k]=point[k];if(point[k]>high[k])high[k]=point[k];}
        }
    }
    for(k=0;k<3;k++)centre[k]=(low[k]+high[k])*.5f;
    a=high[0]-low[0];b=high[1]-low[1];span=(float)sqrt(a*a+b*b);
    c=high[2]-low[2];if(span<.01f || c<.01f)return 0;
    scale=(width-8)/span;if(scale>(height-8)/c)scale=(height-8)/c;
    cs=Q_CosRad(angle);sn=Q_SinRad(angle);
    for(i=0;i<width*height;i++)inventory_depth[i]=32767;
    for(which=0;which<count;which++){
        if(!inventory_alias(&part[which],&h,&m,&v))return 0;
        sd=(maliasskindesc_t *)((byte *)h+h->skindesc);
        if(sd->type==ALIAS_SKIN_GROUP){
            maliasskingroup_t *g=(maliasskingroup_t *)((byte *)h+sd->skin);sd=&g->skindescs[0];
        }
        skin=(byte *)h+sd->skin;st=(stvert_t *)((byte *)h+h->stverts);tri=(mtriangle_t *)((byte *)h+h->triangles);
        for(i=0;i<m->numtris;i++){
            for(j=0;j<3;j++){
                int vertex=tri[i].vertindex[j];if(vertex<0 || vertex>=m->numverts)return 0;
                inventory_point(&part[which],m,&v[vertex],point);
                dx=point[0]-centre[0];dy=point[1]-centre[1];dz=point[2]-centre[2];
                points[j][0]=width*.5f+(dx*cs-dy*sn)*scale;points[j][1]=height*.5f-dz*scale;
                points[j][2]=(dx*sn+dy*cs)*128;
                uv[j][0]=(float)st[vertex].s/65536.f;
                if(!tri[i].facesfront && st[vertex].onseam)uv[j][0]+=m->skinwidth*.5f;
                uv[j][1]=(float)st[vertex].t/65536.f;
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
                z=(int)(a*points[0][2]+b*points[1][2]+c*points[2][2]);if(z>=inventory_depth[yy*width+xx])continue;
                ix=(int)(a*uv[0][0]+b*uv[1][0]+c*uv[2][0]);iy=(int)(a*uv[0][1]+b*uv[1][1]+c*uv[2][1]);
                if(ix<0 || ix>=m->skinwidth || iy<0 || iy>=m->skinheight)continue;
                inventory_depth[yy*width+xx]=(short)z;vid.buffer[(y+yy)*vid.rowbytes+x+xx]=skin[iy*m->skinwidth+ix];
            }
        }
    }
    return 1;
}
