/* SPDX-License-Identifier: GPL-2.0-or-later
 * Bounded single-skin aliases stream into the final relocatable cache block.
 * Multiple ordinary frames are supported. Other legal formats retain the
 * generic loader. Validate the complete member before admitting a cache.
 * Loading callbacks may move/evict cache blocks: use offsets across reads and
 * abort cleanly on eviction, never retain a pointer across a callback. */
typedef struct {
    FILE *file;
    long left;
    model_t *mod;
    int allocated, total, used;
} aw_alias_stream_t;

static void AW_AliasStreamError(aw_alias_stream_t *s, const char *why) {
    if(s->file){fclose(s->file);s->file=NULL;}
    if(s->allocated && s->mod->cache.data)Cache_Free(&s->mod->cache);
    s->allocated=0;s->mod->needload=NL_NEEDS_LOADED;
    Sys_Error("Mod_TryStreamAlias: %s: %s",s->mod->name,why);
}
static byte *AW_AliasStreamData(aw_alias_stream_t *s) {
    if(!s->mod->cache.data)AW_AliasStreamError(s,"cache evicted during load");
    return (byte *)s->mod->cache.data;
}
static void AW_AliasStreamRead(aw_alias_stream_t *s, void *out, size_t n) {
    if(n>(size_t)s->left || AW_LoadRead(out,n,s->file)!=n)
        AW_AliasStreamError(s,"truncated member");
    s->left-=(long)n;
}
/* offset < 0 validates/skips data without retaining it. The scratch buffer
 * also prevents a loading callback from invalidating fread's destination. */
static void AW_AliasStreamCopy(aw_alias_stream_t *s, int offset, size_t n) {
    byte scratch[4096];size_t take;
    while(n){
        take=n>sizeof(scratch)?sizeof(scratch):n;
        AW_AliasStreamRead(s,scratch,take);
        if(offset>=0){
            if(offset>s->total || take>(size_t)(s->total-offset))AW_AliasStreamError(s,"cache extent");
            memcpy(AW_AliasStreamData(s)+offset,scratch,take);offset+=(int)take;
        }
        n-=take;
    }
}
static int AW_AliasStreamAlloc(aw_alias_stream_t *s,size_t n) {
    size_t block=0;int offset=s->used;
    if(!AW_AliasBlock(&block,n) || block>(size_t)(s->total-s->used))AW_AliasStreamError(s,"cache size mismatch");
    s->used+=(int)block;return offset;
}
static void AW_AliasStreamTriangle(aw_alias_stream_t *s,dtriangle_t *tri,int vertices) {
    int i;
    tri->facesfront=LittleLong(tri->facesfront);
    for(i=0;i<3;i++){
        tri->vertindex[i]=LittleLong(tri->vertindex[i]);
        if(tri->vertindex[i]<0 || tri->vertindex[i]>=vertices)AW_AliasStreamError(s,"triangle vertex");
    }
}
static void AW_AliasStreamTriangles(aw_alias_stream_t *s,int count,int vertices,int offset) {
    dtriangle_t batch[64];int take,i;
    while(count){
        take=count>64?64:count;AW_AliasStreamRead(s,batch,(size_t)take*sizeof(batch[0]));
        for(i=0;i<take;i++)AW_AliasStreamTriangle(s,&batch[i],vertices);
        if(offset>=0){memcpy(AW_AliasStreamData(s)+offset,batch,(size_t)take*sizeof(batch[0]));offset+=take*sizeof(batch[0]);}
        count-=take;
    }
}
int Mod_TryStreamAlias(model_t *mod) {
    aw_alias_stream_t s;mdl_t disk,check,*m;daliasskintype_t kind;
    daliasframetype_t framekind;daliasframe_t frame;
    aliashdr_t *h;maliasskindesc_t *skin;stvert_t *uv;
    long base;int bytes,nv,nt,nf,width,height,i,j,headeroff,modeloff,uvoff,trioff,skinoff,pixeloff,frameoff;
    size_t total=0,head=0,skinbytes=0;
    memset(&s,0,sizeof(s));s.mod=mod;
    if(r_pixbytes!=1 || strlen(mod->name)<4 || strcmp(mod->name+strlen(mod->name)-4,".mdl"))return 0;
    bytes=COM_FOpenFile(mod->name,&s.file);
    if(!s.file)return 0;
    base=ftell(s.file);s.left=bytes;
    if(base<0 || bytes<(int)sizeof(disk) || bytes>AW_ALIAS_STAGING_LIMIT){fclose(s.file);return 0;}
    AW_AliasStreamRead(&s,&disk,sizeof(disk));
    if(LittleLong(disk.ident)!=IDPOLYHEADER){fclose(s.file);return 0;}
    nv=LittleLong(disk.numverts);nt=LittleLong(disk.numtris);nf=LittleLong(disk.numframes);
    width=LittleLong(disk.skinwidth);height=LittleLong(disk.skinheight);
    /* Extended models must still pass the exact-file exception reader. */
    if(LittleLong(disk.numskins)!=1 || nv>2000){fclose(s.file);return 0;}
    if(LittleLong(disk.version)!=ALIAS_VERSION || nv<1 || nt<1 || nf<1 ||
       width<1 || (width&3) || height<1 || height>MAX_LBM_HEIGHT ||
       !AW_AliasSum(&skinbytes,height,(size_t)width))AW_AliasStreamError(&s,"invalid header");
    if(!AW_AliasSum(&head,1,sizeof(aliashdr_t)) || !AW_AliasSum(&head,nf-1,sizeof(maliasframedesc_t)) ||
       !AW_AliasSum(&head,1,sizeof(mdl_t)) || !AW_AliasSum(&head,nv,sizeof(stvert_t)) ||
       !AW_AliasSum(&head,nt,sizeof(mtriangle_t)) || !AW_AliasBlock(&total,head) ||
       !AW_AliasBlock(&total,sizeof(maliasskindesc_t)) || !AW_AliasBlock(&total,skinbytes))
        AW_AliasStreamError(&s,"size overflow");
    /* A frame consumes at least 28 + 4*nv bytes. Bound loops before parsing. */
    if((size_t)nf>(size_t)bytes/(28+(size_t)nv*4))AW_AliasStreamError(&s,"frame count");
    for(i=0;i<nf;i++)if(!AW_AliasBlock(&total,(size_t)nv*sizeof(trivertx_t)))AW_AliasStreamError(&s,"size overflow");
    if(total>AW_ALIAS_STAGING_LIMIT){fclose(s.file);return 0;}
    s.total=(int)total;
    AW_AliasStreamRead(&s,&kind,sizeof(kind));
    if(LittleLong(kind.type)==ALIAS_SKIN_GROUP){fclose(s.file);return 0;}
    if(LittleLong(kind.type)!=ALIAS_SKIN_SINGLE)AW_AliasStreamError(&s,"skin type");
    AW_AliasStreamCopy(&s,-1,skinbytes);
    AW_AliasStreamCopy(&s,-1,(size_t)nv*sizeof(stvert_t));
    AW_AliasStreamTriangles(&s,nt,nv,-1);
    for(i=0;i<nf;i++){
        AW_AliasStreamRead(&s,&framekind,sizeof(framekind));
        if(LittleLong(framekind.type)==ALIAS_GROUP){fclose(s.file);return 0;}
        if(LittleLong(framekind.type)!=ALIAS_SINGLE)AW_AliasStreamError(&s,"frame type");
        AW_AliasStreamRead(&s,&frame,sizeof(frame));
        if(!memchr(frame.name,0,sizeof(frame.name)))AW_AliasStreamError(&s,"frame name");
        AW_AliasStreamCopy(&s,-1,(size_t)nv*sizeof(trivertx_t));
    }
    if(s.left)AW_AliasStreamError(&s,"trailing member data");
    if(fseek(s.file,base,SEEK_SET))AW_AliasStreamError(&s,"member rewind");
    s.left=bytes;AW_AliasStreamRead(&s,&check,sizeof(check));
    if(memcmp(&disk,&check,sizeof(disk)))AW_AliasStreamError(&s,"header changed");
    COM_FileBase(mod->name,loadname);
    Cache_Alloc(&mod->cache,s.total,loadname);s.allocated=1;
    memset(AW_AliasStreamData(&s),0,(size_t)s.total);
    headeroff=AW_AliasStreamAlloc(&s,head); /* zero, same padding as generic */
    modeloff=headeroff+sizeof(aliashdr_t)+(nf-1)*sizeof(maliasframedesc_t);
    uvoff=modeloff+sizeof(mdl_t);trioff=uvoff+nv*sizeof(stvert_t);
    h=(aliashdr_t *)AW_AliasStreamData(&s);m=(mdl_t *)((byte *)h+modeloff);
    h->model=modeloff;h->stverts=uvoff;h->triangles=trioff;
    m->boundingradius=LittleFloat(disk.boundingradius);m->numskins=1;m->skinwidth=width;m->skinheight=height;
    m->numverts=nv;m->numtris=nt;m->numframes=nf;m->size=LittleFloat(disk.size)*ALIAS_BASE_SIZE_RATIO;
    for(i=0;i<3;i++){m->scale[i]=LittleFloat(disk.scale[i]);m->scale_origin[i]=LittleFloat(disk.scale_origin[i]);m->eyeposition[i]=LittleFloat(disk.eyeposition[i]);}
    skinoff=AW_AliasStreamAlloc(&s,sizeof(maliasskindesc_t));pixeloff=AW_AliasStreamAlloc(&s,skinbytes);
    h->skindesc=skinoff;skin=(maliasskindesc_t *)((byte *)h+skinoff);skin->type=ALIAS_SKIN_SINGLE;skin->skin=pixeloff;
    AW_AliasStreamRead(&s,&kind,sizeof(kind));
    if(LittleLong(kind.type)!=ALIAS_SKIN_SINGLE)AW_AliasStreamError(&s,"skin changed");
    AW_AliasStreamCopy(&s,pixeloff,skinbytes);
    AW_AliasStreamCopy(&s,uvoff,(size_t)nv*sizeof(stvert_t));
    uv=(stvert_t *)(AW_AliasStreamData(&s)+uvoff);
    for(i=0;i<nv;i++){
        uv[i].onseam=LittleLong(uv[i].onseam);
        uv[i].s=(int)((unsigned int)LittleLong(uv[i].s)<<16);uv[i].t=(int)((unsigned int)LittleLong(uv[i].t)<<16);
    }
    AW_AliasStreamTriangles(&s,nt,nv,trioff);
    for(i=0;i<nf;i++){
        AW_AliasStreamRead(&s,&framekind,sizeof(framekind));AW_AliasStreamRead(&s,&frame,sizeof(frame));
        if(LittleLong(framekind.type)!=ALIAS_SINGLE || !memchr(frame.name,0,sizeof(frame.name)))AW_AliasStreamError(&s,"frame changed");
        frameoff=AW_AliasStreamAlloc(&s,(size_t)nv*sizeof(trivertx_t));
        h=(aliashdr_t *)AW_AliasStreamData(&s);h->frames[i].type=ALIAS_SINGLE;h->frames[i].frame=frameoff;
        strcpy(h->frames[i].name,frame.name);
        for(j=0;j<3;j++){h->frames[i].bboxmin.v[j]=frame.bboxmin.v[j];h->frames[i].bboxmax.v[j]=frame.bboxmax.v[j];}
        AW_AliasStreamCopy(&s,frameoff,(size_t)nv*sizeof(trivertx_t));
    }
    if(s.left || s.used!=s.total)AW_AliasStreamError(&s,"decoded size mismatch");
    h=(aliashdr_t *)AW_AliasStreamData(&s);m=(mdl_t *)((byte *)h+modeloff);
    mod->flags=LittleLong(disk.flags);mod->synctype=LittleLong(disk.synctype);mod->numframes=nf;
    for(i=0;i<3;i++){mod->mins[i]=m->scale_origin[i];mod->maxs[i]=m->scale_origin[i]+m->scale[i]*255;}
    mod->radius=RadiusFromBounds(mod->mins,mod->maxs)+0.125f;
    mod->type=mod_alias;mod->needload=NL_PRESENT;fclose(s.file);return 1;
}
