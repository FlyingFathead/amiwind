/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native face-loader oracle: compare resolved renderer geometry, UVs and samples.
 * Pointer/index addresses may change; no geometry or rendered input may change. */
#include <assert.h>
#include "../engine/aga/src/model.c"
static byte arena[16*1024*1024];
static int used;
static short same_short(short v){return v;}
static int same_long(int v){return v;}
static float same_float(float v){return v;}
short (*LittleShort)(short)=same_short;
int (*LittleLong)(int)=same_long;
float (*LittleFloat)(float)=same_float;
void *Hunk_AllocName(int size,char *name){void *p;size=(size+15)&~15;assert(size>=0 && used+size<(int)sizeof(arena));p=arena+used;used+=size;memset(p,0,size);return p;}
void Sys_Error(char *fmt,...){va_list args;va_start(args,fmt);vfprintf(stderr,fmt,args);va_end(args);abort();}
int Q_strncmp(char *a,char *b,int n){return strncmp(a,b,n);}
static unsigned long long hash;
static void bytes(const void *value,int size){const byte *p=value;int i;for(i=0;i<size;i++){hash^=p[i];hash*=1099511628211ULL;}}
static void check(const char *path){
    FILE *file;long length;byte *raw,*texlump;dheader_t *head;model_t model;
    dplane_t *planes;texinfo_t *texinfos;texture_t *textures;int *offsets;
    int i,j,k,count,index,styles,samples,edge,vertex;msurface_t *surface;float uv;
    file=fopen(path,"rb");assert(file);fseek(file,0,SEEK_END);length=ftell(file);rewind(file);
    raw=malloc(length);assert(raw && fread(raw,1,length,file)==(size_t)length);fclose(file);
    head=(dheader_t *)raw;assert(head->version==29);memset(&model,0,sizeof(model));
    loadmodel=&model;mod_base=raw;used=0;
    Mod_LoadVertexes(&head->lumps[LUMP_VERTEXES]);Mod_LoadEdges(&head->lumps[LUMP_EDGES]);Mod_LoadSurfedges(&head->lumps[LUMP_SURFEDGES]);
    model.numplanes=head->lumps[LUMP_PLANES].filelen/sizeof(dplane_t);
    model.planes=calloc(model.numplanes,sizeof(mplane_t));assert(model.planes);
    planes=(dplane_t *)(raw+head->lumps[LUMP_PLANES].fileofs);
    for(i=0;i<model.numplanes;i++){memcpy(model.planes[i].normal,planes[i].normal,12);model.planes[i].dist=planes[i].dist;model.planes[i].type=planes[i].type;}
    texlump=raw+head->lumps[LUMP_TEXTURES].fileofs;count=*(int *)texlump;offsets=(int *)(texlump+4);
    textures=calloc(count,sizeof(texture_t));assert(textures);
    for(i=0;i<count;i++)if(offsets[i]>=0){memcpy(textures[i].name,texlump+offsets[i],16);memcpy(&textures[i].width,texlump+offsets[i]+16,8);}
    model.numtexinfo=head->lumps[LUMP_TEXINFO].filelen/sizeof(texinfo_t);
    model.texinfo=calloc(model.numtexinfo,sizeof(mtexinfo_t));assert(model.texinfo);
    texinfos=(texinfo_t *)(raw+head->lumps[LUMP_TEXINFO].fileofs);
    for(i=0;i<model.numtexinfo;i++){memcpy(model.texinfo[i].vecs,texinfos[i].vecs,32);model.texinfo[i].flags=texinfos[i].flags;index=texinfos[i].miptex;assert(index>=0 && index<count);model.texinfo[i].texture=&textures[index];}
    model.lightdata=raw+head->lumps[LUMP_LIGHTING].fileofs;
    Mod_LoadFaces(&head->lumps[LUMP_FACES]);hash=1469598103934665603ULL;
    for(i=0;i<model.numsurfaces;i++){
        surface=&model.surfaces[i];bytes(&surface->numedges,sizeof(int));bytes(&surface->flags,sizeof(int));
        bytes(surface->plane->normal,12);bytes(&surface->plane->dist,4);
        bytes(surface->texturemins,4);bytes(surface->extents,4);bytes(surface->styles,MAXLIGHTMAPS);
        bytes(surface->texinfo->vecs,32);bytes(surface->texinfo->texture->name,16);
        for(j=0;j<surface->numedges;j++){
            edge=model.surfedges[surface->firstedge+j];assert(abs(edge)<model.numedges);
            /* Renderer orientation, including the reserved edge-zero case. */
            vertex=model.edges[abs(edge)].v[edge>0?0:1];assert(vertex<model.numvertexes);
            bytes(model.vertexes[vertex].position,12);
            for(k=0;k<2;k++){
                uv=model.vertexes[vertex].position[0]*surface->texinfo->vecs[k][0]+model.vertexes[vertex].position[1]*surface->texinfo->vecs[k][1]+model.vertexes[vertex].position[2]*surface->texinfo->vecs[k][2]+surface->texinfo->vecs[k][3];
                bytes(&uv,4);
            }
        }
        if(surface->samples){
            styles=0;while(styles<MAXLIGHTMAPS && surface->styles[styles]!=255)styles++;
            samples=((surface->extents[0]>>4)+1)*((surface->extents[1]>>4)+1)*styles;
            assert(samples>=0 && surface->samples>=model.lightdata && surface->samples+samples<=model.lightdata+head->lumps[LUMP_LIGHTING].filelen);
            bytes(surface->samples,samples);
        }
    }
    printf("%016llx %d %s\n",hash,model.numsurfaces,path);
    free(model.planes);free(model.texinfo);free(textures);free(raw);
}
int main(int argc,char **argv){int i;assert(argc>1);for(i=1;i<argc;i++)check(argv[i]);return 0;}
