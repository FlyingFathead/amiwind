/*
Copyright (C) 1996-1997 Id Software, Inc.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

*/
// models.c -- model loading and caching

// models are the only shared resource between a client and server running
// on the same machine.

#include "quakedef.h"
#include "aw_log.h"
#include "r_local.h"
#include <limits.h>
#include <stddef.h>
#include <setjmp.h>

#define AW_STREAM_SPRITES 1

static cvar_t aw_allow_poly_budget_over={"aw_allow_poly_budget_over","1",true};
static cvar_t aw_poly_budget_over_cap={"aw_poly_budget_over_cap","auto",true};
static cvar_t aw_gallery_defaults={"aw_gallery_defaults","0",true};
/* Upgrade the previously disabled shipped setting once, after config.cfg.
 * Later explicit opt-outs remain effective on subsequent launches. */
static void AW_GalleryDefaults(void) {
    if(aw_gallery_defaults.value>=1)return;
    Cvar_SetValue("aw_allow_poly_budget_over",1);
    Cvar_Set("aw_poly_budget_over_cap","auto");
    Cvar_SetValue("aw_gallery_defaults",1);
}
/* Existing shared-vertex models retain their original 2000-vertex allowance.
 * Only the extension is governed by this converted-triangle cap. */
int AW_AliasBudgetAllows(int vertices,int triangles) {
    int cap;
    if(vertices<1 || vertices>MAXALIASVERTS || triangles<1)return 0;
    if(vertices<=2000)return 1;
    if(!aw_allow_poly_budget_over.value)return 0;
    if(!Q_strcasecmp(aw_poly_budget_over_cap.string,"auto"))cap=1024;
    else {
        if(!(aw_poly_budget_over_cap.value>=666 && aw_poly_budget_over_cap.value<=1024))return 0;
        cap=(int)aw_poly_budget_over_cap.value;if(aw_poly_budget_over_cap.value!=cap)return 0;
    }
    return triangles<=cap && vertices<=cap*3;
}
/* Only extended models read this disk table, once at load. The CRC binds the
 * allowance to the packaged bytes; the host inspection ledger retains SHA-256.
 * It is an integrity check, not an authentication mechanism. */
int AW_AliasExceptionAllows(const char *name,int vertices,int triangles,const byte *raw,int bytes) {
    FILE *f=NULL;char line[160],path[64],extra;int nv,nt,length,i,bit;unsigned long expected;
    unsigned int crc=0xffffffffU;
    if(!AW_AliasBudgetAllows(vertices,triangles))return 0;
    if(vertices<=2000)return 1;
    if(!raw || bytes<84 || COM_FOpenFile("model-budgets.txt",&f)<0 || !f)return 0;
    if(!fgets(line,sizeof(line),f) || strcmp(line,"AWPB1\n")){fclose(f);return 0;}
    while(fgets(line,sizeof(line),f)){
        if(Q_sscanf(line,"%63s %d %d %d %lx %c",path,&nv,&nt,&length,&expected,&extra)!=5){fclose(f);return 0;}
        if(strcmp(path,name))continue;
        fclose(f);
        if(vertices!=nv || triangles!=nt || bytes!=length)return 0;
        for(i=0;i<bytes;i++){
            crc^=raw[i];for(bit=0;bit<8;bit++)crc=(crc>>1)^(0xedb88320U&-(crc&1));
        }
        return (crc^0xffffffffU)==expected;
    }
    fclose(f);return 0;
}
model_t	*loadmodel;
char	loadname[COM_FILEBASE_SIZE];	// for hunk tags
/* Optional main-task music service; unset in asset-free loader tests. */
void (*aw_load_audio_tick)(void);
size_t (*aw_load_prefetch_copy)(const char *,long,byte *,size_t);
double (*aw_load_clock)(void);
/* Optional Hunk low+high bytes in use; recorded per streamed BSP section. */
int (*aw_load_hunk_used)(void);
long aw_load_disk_bytes,aw_load_disk_calls;
double aw_load_disk_seconds,aw_load_decode_seconds;
static void AW_LoadAudioTick(void) {
    if(aw_load_audio_tick)aw_load_audio_tick();
}
static size_t AW_LoadRead(byte *data,size_t bytes,FILE *file) {
    size_t done=0,take,got,limit;double started;
    while(done<bytes) {
        AW_LoadAudioTick();
        /* The OST also needs disk time between asset reads. Keep loading
         * slices within one music refill; ordinary reads retain their size. */
        limit=aw_loading_music?4096:16384;
        take=bytes-done;if(take>limit)take=limit;
        started=aw_load_clock?aw_load_clock():0;
        got=fread(data+done,1,take,file);done+=got;
        if(aw_load_clock)aw_load_disk_seconds+=aw_load_clock()-started;
        aw_load_disk_bytes+=got;aw_load_disk_calls++;
        if(got!=take)break;
    }
    AW_LoadAudioTick();
    return done;
}

void Mod_LoadSpriteModel (model_t *mod, void *buffer);
int Mod_TryStreamSprite (model_t *mod);
void Mod_LoadBrushModel (model_t *mod, void *buffer);
void Mod_LoadAliasModel (model_t *mod, void *buffer, int bytes);
int Mod_TryStreamAlias (model_t *mod);
/* Small converted aliases use transient host heap for their file image.
 * Holding the file in the high hunk while decoding into the low hunk evicts
 * other visible actors from the cache between them. No resident RAM increase. */
static int aw_alias_file_bytes;
static void *AW_AliasFile(char *name) {
    FILE *f=NULL;byte *data;int size;
    if(strlen(name)<4 || strcmp(name+strlen(name)-4,".mdl"))return NULL;
    aw_alias_file_bytes=0;size=COM_FOpenFile(name,&f);if(!f)return NULL;
    if(size<84 || size>512*1024){fclose(f);return NULL;}
    data=malloc(size);if(!data){fclose(f);return NULL;}
    Draw_BeginDisc();
    if(AW_LoadRead(data,size,f)!=(size_t)size || memcmp(data,"IDPO",4)){free(data);data=NULL;}
    fclose(f);Draw_EndDisc();if(data)aw_alias_file_bytes=size;return data;
}

model_t *Mod_LoadModel (model_t *mod, qboolean crash);

byte	mod_novis[MAX_MAP_LEAFS/8];

#define	MAX_MOD_KNOWN	AW_EDGE_CACHE_MODEL_LIMIT
model_t	mod_known[MAX_MOD_KNOWN];
int		mod_numknown;

// values for model_t's needload
#define NL_PRESENT		0
#define NL_NEEDS_LOADED	1
#define NL_UNREFERENCED	2

/*
===============
Mod_Init
===============
*/
void Mod_Init (void)
{
    Cvar_RegisterVariable(&aw_allow_poly_budget_over);Cvar_RegisterVariable(&aw_poly_budget_over_cap);
    Cvar_RegisterVariable(&aw_gallery_defaults);Cmd_AddCommand("aw_gallery_migrate",AW_GalleryDefaults);
    memset (mod_novis, 0xff, sizeof(mod_novis));
}

/*
===============
Mod_Extradata

Caches the data if needed
===============
*/
void *Mod_Extradata (model_t *mod)
{
    void	*r;

    r = Cache_Check (&mod->cache);
    if (r)
        return r;

    Mod_LoadModel (mod, true);

    if (!mod->cache.data)
        Sys_Error ("Mod_Extradata: caching failed");
    return mod->cache.data;
}

/*
===============
Mod_PointInLeaf
===============
*/
mleaf_t *Mod_PointInLeaf (float *p, model_t *model)
{
    mnode_t		*node;
    float		d;
    mplane_t	*plane;

    if (!model || !model->nodes)
        Sys_Error ("Mod_PointInLeaf: bad model");

    node = model->nodes;
    while (1)
    {
        if (node->contents < 0)
            return (mleaf_t *)node;
        plane = node->plane;
        d = DotProduct (p,plane->normal) - plane->dist;
        if (d > 0)
            node = node->children[0];
        else
            node = node->children[1];
    }

    return NULL;	// never reached
}


/*
===================
Mod_DecompressVis
===================
*/
byte *Mod_DecompressVis (byte *in, model_t *model)
{
    static byte	decompressed[MAX_MAP_LEAFS/8];
    int		c;
    byte	*out;
    int		row;

    row = (model->numleafs+7)>>3;
    out = decompressed;

    if (!in)
    {	// no vis info, so make all visible
        while (row)
        {
            *out++ = 0xff;
            row--;
        }
        return decompressed;
    }

    do
    {
        if (*in)
        {
            *out++ = *in++;
            continue;
        }

        c = in[1];
        in += 2;
        while (c)
        {
            *out++ = 0;
            c--;
        }
    } while (out - decompressed < row);

    return decompressed;
}

byte *Mod_LeafPVS (mleaf_t *leaf, model_t *model)
{
    if (leaf == model->leafs)
        return mod_novis;
    return Mod_DecompressVis (leaf->compressed_vis, model);
}

/*
===================
Mod_ClearAll
===================
*/
void Mod_ClearAll (void)
{
    int		i;
    model_t	*mod;


    for (i=0 , mod=mod_known ; i<mod_numknown ; i++, mod++) {
        /* Inspection visits release the previous actor and footprint payloads. */
        if (mod->type == mod_alias && !strncmp(mod->name,"gallery/",8) && mod->cache.data)
            Cache_Free (&mod->cache);
        mod->needload = NL_UNREFERENCED;
//FIX FOR CACHE_ALLOC ERRORS:
        if (mod->type == mod_sprite) mod->cache.data = NULL;
    }
}

/*
==================
Mod_FindName

==================
*/
/* Read-only admission query for bounded optional shared assets. This must use
 * the same reuse rule as Mod_FindName and must not touch the cache LRU. */
qboolean Mod_CanFindName(const char *name)
{
    int i;
    if(!name || !name[0])return false;
    if(mod_numknown<MAX_MOD_KNOWN)return true;
    for(i=0;i<mod_numknown;i++)
        if(!strcmp(mod_known[i].name,name) || mod_known[i].needload==NL_UNREFERENCED)return true;
    return false;
}
void Mod_ReleaseAlias(model_t *mod)
{
    /* Optional render-only models (aw_npc_lod.c): free the data now, and mark the
     * slot unreferenced like Mod_ClearAll so a later Mod_FindName can reuse it. */
    if(!mod || mod->type!=mod_alias)return;
    if(mod->cache.data)Cache_Free(&mod->cache);
    mod->needload=NL_UNREFERENCED;
}
model_t *Mod_FindName (char *name)
{
    int		i;
    model_t	*mod;
    model_t	*avail = NULL;

    if (!name[0])
        Sys_Error ("Mod_ForName: NULL name");

//
// search the currently loaded models
//
    for (i=0 , mod=mod_known ; i<mod_numknown ; i++, mod++)
    {
        if (!strcmp (mod->name, name) )
            break;
        if (mod->needload == NL_UNREFERENCED)
            if (!avail || mod->type != mod_alias)
                avail = mod;
    }

    if (i == mod_numknown)
    {
        if (mod_numknown == MAX_MOD_KNOWN)
        {
            if (avail)
            {
                mod = avail;
                if (mod->type == mod_alias)
                    if (Cache_Check (&mod->cache))
                        Cache_Free (&mod->cache);
            }
            else
                Sys_Error ("mod_numknown == MAX_MOD_KNOWN");
        }
        else
            mod_numknown++;
        strcpy (mod->name, name);
        mod->needload = NL_NEEDS_LOADED;
    }

    return mod;
}

/*
==================
Mod_TouchModel

==================
*/
void Mod_TouchModel (char *name)
{
    model_t	*mod;

    if (!name || !name[0] || strlen (name) >= MAX_QPATH)
        return;
    mod = Mod_FindName (name);

    if (mod->needload == NL_PRESENT)
    {
        if (mod->type == mod_alias)
            Cache_Check (&mod->cache);
    }
}

/*
==================
Mod_LoadModel

Loads a model into the cache
==================
*/
/* AmiWind: decode loose BSP sections one at a time. The decoded world stays
 * resident; this bounds temporary loading memory, not world-cell residency. */
static FILE *aw_bsp_file;
static long aw_bsp_bytes, aw_bsp_base;
static int aw_bsp_peak, aw_bsp_reads, aw_bsp_slice_peak;
/* File position relative to aw_bsp_base after the last read, or -1. */
static long aw_bsp_position;
/* Hunk in use at the end of each section (its temporary slice included),
 * before the first section and after the post-section allocations. */
static lump_t *aw_bsp_lumps;
static int aw_bsp_used[HEADER_LUMPS+2],aw_bsp_slices[HEADER_LUMPS];
static const char *const aw_bsp_lump_names[HEADER_LUMPS]={"entities","planes","textures",
    "vertexes","visibility","nodes","texinfo","faces","lighting","clipnodes","leafs",
    "marksurfaces","edges","surfedges","models"};
static void AW_RecordSection(lump_t *l,int slice)
{
    int index;
    if(!aw_bsp_lumps || !aw_load_hunk_used || l<aw_bsp_lumps || l>=aw_bsp_lumps+HEADER_LUMPS)return;
    index=(int)(l-aw_bsp_lumps);
    aw_bsp_used[index]=aw_load_hunk_used();aw_bsp_slices[index]=slice;
}
static int AW_TryStreamBrush(model_t *mod) {
    dheader_t header;int filebytes;
    /* Use the same search order as ordinary loads, including world volumes.
     * Pack-file offsets remain relative to this member's starting position. */
    filebytes=COM_FOpenFile(mod->name,&aw_bsp_file);
    if(!aw_bsp_file || filebytes<(int)sizeof(header)) {
        if(aw_bsp_file)fclose(aw_bsp_file);
        aw_bsp_file=NULL;return 0;
    }
    aw_bsp_base=ftell(aw_bsp_file);aw_bsp_bytes=filebytes;
    if(aw_bsp_base<0){fclose(aw_bsp_file);aw_bsp_file=NULL;return 0;}
    if(fread(&header,1,sizeof(header),aw_bsp_file)!=sizeof(header) || LittleLong(header.version)!=BSPVERSION) {
        fclose(aw_bsp_file);aw_bsp_file=NULL;return 0;
    }
    aw_bsp_peak=aw_bsp_reads=aw_bsp_slice_peak=0;aw_bsp_position=sizeof(header);
    memset(aw_bsp_used,0,sizeof(aw_bsp_used));memset(aw_bsp_slices,0,sizeof(aw_bsp_slices));
    if(aw_load_hunk_used)aw_bsp_used[HEADER_LUMPS]=aw_load_hunk_used();
    COM_FileBase(mod->name,loadname);loadmodel=mod;mod->needload=NL_PRESENT;
    aw_bsp_lumps=header.lumps;
    Mod_LoadBrushModel(mod,&header);
    aw_bsp_lumps=NULL;
    fclose(aw_bsp_file);aw_bsp_file=NULL;
    /* In memory unless aw_logs_live (aw_log.c, BOOT-VOLUME-NOT-VALIDATED-33). */
    AW_LogBegin(AW_LOG_BSP_LOAD);
    {
        int i;
        AW_LogPrintf(AW_LOG_BSP_LOAD,"map=%s\nfile_bytes=%ld\nmax_input_section_bytes=%d\nmax_slice_bytes=%d\nsection_reads=%d\nhunk_before=%d\nhunk_after=%d\n",
            mod->name,aw_bsp_bytes,aw_bsp_peak,aw_bsp_slice_peak,aw_bsp_reads,aw_bsp_used[HEADER_LUMPS],aw_bsp_used[HEADER_LUMPS+1]);
        /* Mod_LoadBrushModel byte-swapped the header lumps in place. */
        for(i=0;i<HEADER_LUMPS;i++)AW_LogPrintf(AW_LOG_BSP_LOAD,"section=%s bytes=%d slice=%d hunk_end=%d\n",
            aw_bsp_lump_names[i],header.lumps[i].filelen,aw_bsp_slices[i],aw_bsp_used[i]);
    }
    AW_LogEnd(AW_LOG_BSP_LOAD);
    return 1;
}

model_t *Mod_LoadModel (model_t *mod, qboolean crash)
{
    unsigned *buf;
    byte	stackbuf[1024];		// avoid dirtying the cache heap
    void *alias_file;
    int alias_bytes;

    if (mod->type == mod_alias)
    {
        if (Cache_Check (&mod->cache))
        {
            mod->needload = NL_PRESENT;
            return mod;
        }
    }
    else
    {
        if (mod->needload == NL_PRESENT)
            return mod;
    }

//
// because the world is so huge, load it one piece at a time
//

//
// load the file
//
    if(AW_TryStreamBrush(mod))return mod;
#if AW_STREAM_SPRITES
    if(Mod_TryStreamSprite(mod))return mod;
#endif
    if(Mod_TryStreamAlias(mod))return mod;
    alias_file=AW_AliasFile(mod->name);
    buf=alias_file?alias_file:(unsigned *)COM_LoadStackFile (mod->name, stackbuf, sizeof(stackbuf));
    if (!buf)
    {
        /* A missing model file ends the session, never the program
           (ENGINE-MODEL-NAME-SYSERROR-35). */
        if (crash)
            Host_Error ("Model %s not found", mod->name);
        return NULL;
    }

//
// allocate a new model
//
    alias_bytes=alias_file?aw_alias_file_bytes:com_filesize;
    COM_FileBase (mod->name, loadname);

    loadmodel = mod;

//
// fill it in
//

// call the apropriate loader
    mod->needload = NL_PRESENT;

    switch (LittleLong(*(unsigned *)buf))
    {
    case IDPOLYHEADER:
        if(!AW_AliasExceptionAllows(mod->name,LittleLong(((mdl_t *)buf)->numverts),LittleLong(((mdl_t *)buf)->numtris),(byte *)buf,alias_file?aw_alias_file_bytes:com_filesize)){
            Con_Printf("Model %s needs a matching model-budgets.txt exception and an adequate active polygon cap.\n",mod->name);
            mod->needload=NL_NEEDS_LOADED;if(alias_file)free(alias_file);
            if(crash)Host_Error("Model exceeds the active polygon budget");
            return NULL;
        }
        Mod_LoadAliasModel (mod, buf, alias_bytes);
        break;

    case IDSPRITEHEADER:
        Mod_LoadSpriteModel (mod, buf);
        break;

    default:
        Mod_LoadBrushModel (mod, buf);
        break;
    }

    if(alias_file)free(alias_file);
    return mod;
}

/*
==================
Mod_ForName

Loads in a model for the given name
==================
*/
model_t *Mod_ForName (char *name, qboolean crash)
{
    model_t	*mod;

    /* mod->name holds MAX_QPATH: a longer or empty name (QuakeC strings, map
       "model" keys) is a model that does not load (ENGINE-MODEL-NAME-SYSERROR-35). */
    if (!name || !name[0] || strlen (name) >= MAX_QPATH)
    {
        if (crash)
            Host_Error ("Model name empty or too long");
        Con_Printf ("Model name empty or too long\n");
        return NULL;
    }
    AW_LoadAudioTick();
    mod = Mod_FindName (name);

    return Mod_LoadModel (mod, crash);
}


/*
===============================================================================

                    BRUSHMODEL LOADING

===============================================================================
*/

byte	*mod_base;

/* AmiWind: Quake's Mod_Load* decoders walk one complete file image. Streamed
 * BSPs instead hand each decoder its lump in bounded slices that are decoded
 * straight into the final Hunk structures, so no complete second copy of a
 * lump sits beside its decoded form. A file image (aw_bsp_file NULL) is still
 * decoded in place from mod_base. Both use the same decoders.
 *
 * The file is read exactly as a staged lump was: consecutive 16 KiB chunks from
 * the lump's start, each into the window at the same aligned address. A record
 * split by a chunk boundary is completed in the prefix just before the window;
 * for textures the prefix holds the directory while the window moves on. */
#define AW_BSP_SLICE_BYTES 16384
#define AW_BSP_RECORD_PREFIX 64 /* >= every disk record; dmodel_t is largest */
#define AW_BSP_DIRECTORY_BYTES (4+4*MAX_MAP_TEXTURES)
/* A CHIM loading buffer (model.h) holds the largest window plus prefix. */
typedef char aw_brush_slice_fits[AW_BRUSH_SLICE_BYTES>=AW_BSP_SLICE_BYTES+((AW_BSP_DIRECTORY_BYTES+15)&~15)?1:-1];
static byte *aw_bsp_slice;
static int aw_bsp_slice_bytes,aw_bsp_slice_prefix,aw_bsp_window_start,aw_bsp_window_bytes;
typedef struct { lump_t *lump; int size, count, done, next; byte *tail; } aw_records_t;

/* CHIM: the arena that brush decoders allocate from (model.h). NULL for every
 * legacy load, which keeps the Hunk calls exactly as before. */
static aw_brush_arena_t *aw_brush_arena;
/* CHIM: bad data in an arena decode (a damaged or truncated sector file)
 * ends that load, not the game. The decoders below say Sys_Error; while an
 * arena entry point (AW_BrushImage, AW_BrushStreamStep) runs, that returns
 * to it and the load fails with the reason on the console. Legacy (Hunk)
 * loads are unchanged: aw_brush_catch is set only around arena decodes
 * (CHIM-BRUSH-BAD-DATA-35). */
static jmp_buf *aw_brush_catch;
static char aw_brush_why[128];
static void AW_BrushError(char *fmt,...)
{
    va_list args;
    va_start(args,fmt);vsnprintf(aw_brush_why,sizeof(aw_brush_why),fmt,args);va_end(args);
    if(aw_brush_arena && aw_brush_catch)longjmp(*aw_brush_catch,1);
    Sys_Error("%s",aw_brush_why);
}
#define Sys_Error AW_BrushError
/* After a caught error: the loader's state as a finished load leaves it. */
static void AW_BrushCaught(model_t *mod)
{
    aw_brush_catch=NULL;aw_brush_arena=NULL;
    aw_bsp_file=NULL;aw_bsp_position=-1;aw_bsp_lumps=NULL;
    aw_bsp_slice=NULL;aw_bsp_slice_bytes=0;
    mod->needload=NL_UNREFERENCED;
    Con_Printf("CHIM: %s: bad data (%s); chunk unavailable\n",mod->name,aw_brush_why);
}
static void *AW_BrushAlloc(int size,char *name)
{
    byte *p;
    if(!aw_brush_arena)return Hunk_AllocName(size,name);
    if(size<0 || size>aw_brush_arena->size-aw_brush_arena->used ||
       ((size+15)&~15)>aw_brush_arena->size-aw_brush_arena->used)
        Sys_Error("CHIM model %s exceeds its decoded-size bound",loadmodel->name);
    p=aw_brush_arena->base+aw_brush_arena->used;aw_brush_arena->used+=(size+15)&~15;
    memset(p,0,(size+15)&~15);
    return p;
}
static int AW_BrushMark(void){return aw_brush_arena?aw_brush_arena->used:Hunk_LowMark();}
static void AW_BrushFreeToMark(int mark)
{
    if(!aw_brush_arena){Hunk_FreeToLowMark(mark);return;}
    if(mark<0 || mark>aw_brush_arena->used)Sys_Error("CHIM arena: bad mark");
    memset(aw_brush_arena->base+mark,0,aw_brush_arena->used-mark);aw_brush_arena->used=mark;
}

/* Copy bytes [offset, offset+bytes) of a lump to out. */
static void AW_LumpBytes(lump_t *l,int offset,void *out,int bytes)
{
    size_t copied=0;long position;
    if(offset<0 || bytes<0 || offset>l->filelen || bytes>l->filelen-offset)
        Sys_Error("BSP lump read outside %s",loadmodel->name);
    if(!bytes)return;
    if(!aw_bsp_file){memcpy(out,mod_base+l->fileofs+offset,bytes);return;}
    position=l->fileofs+offset;
    if(aw_load_prefetch_copy){
        copied=aw_load_prefetch_copy(loadmodel->name,position,(byte *)out,bytes);
        if(copied>(size_t)bytes)Sys_Error("Invalid BSP prefetch length");
        if(copied==(size_t)bytes)return;
        position+=copied;
    }
    if(position!=aw_bsp_position && fseek(aw_bsp_file,aw_bsp_base+position,SEEK_SET)){
        aw_bsp_position=-1;Sys_Error("Short BSP section");
    }
    aw_bsp_position=-1;
    if(AW_LoadRead((byte *)out+copied,bytes-copied,aw_bsp_file)!=(size_t)bytes-copied)
        Sys_Error("Short BSP section");
    aw_bsp_position=position+(long)(bytes-copied);
}

static int AW_RecordsBegin(aw_records_t *r,lump_t *l,int size)
{
    if(l->filelen<0 || l->filelen % size)
        Sys_Error ("MOD_LoadBmodel: funny lump size in %s",loadmodel->name);
    r->lump=l;r->size=size;r->count=l->filelen/size;r->done=r->next=0;r->tail=NULL;
    return r->count;
}

static byte *AW_SliceWindow(lump_t *l)
{
    int need=l->filelen<AW_BSP_SLICE_BYTES?l->filelen:AW_BSP_SLICE_BYTES;
    if(!aw_bsp_slice || aw_bsp_slice_bytes<aw_bsp_slice_prefix+need)Sys_Error("Missing BSP slice buffer");
    return aw_bsp_slice+aw_bsp_slice_prefix;
}

/* The next run of whole records: the rest of a file image, or one chunk. */
static void *AW_RecordsNext(aw_records_t *r,int *n)
{
    int take,left,chunk;byte *window,*start;
    if(r->done>=r->count){*n=0;return NULL;}
    take=r->count-r->done;
    if(!aw_bsp_file){
        *n=take;r->done=r->count;
        return mod_base+r->lump->fileofs+(r->done-take)*r->size;
    }
    window=AW_SliceWindow(r->lump);aw_bsp_window_start=-1;
    left=r->next-r->done*r->size;
    if(left<0 || left>=r->size || left>aw_bsp_slice_prefix)Sys_Error("Invalid BSP record slice");
    if(left)memmove(window-left,r->tail,left);
    chunk=r->lump->filelen-r->next;if(chunk>AW_BSP_SLICE_BYTES)chunk=AW_BSP_SLICE_BYTES;
    AW_LumpBytes(r->lump,r->next,window,chunk);r->next+=chunk;
    start=window-left;take=(left+chunk)/r->size;
    r->done+=take;r->tail=start+take*r->size;*n=take;
    return start;
}

/* Bytes [offset, offset+bytes) of a lump through the chunk window; sequential
 * access reads every chunk once, in order, as a staged lump was read. */
static void AW_WindowBytes(lump_t *l,int offset,void *out,int bytes)
{
    byte *window,*to=(byte *)out;int n;
    if(offset<0 || bytes<0 || offset>l->filelen || bytes>l->filelen-offset)
        Sys_Error("BSP lump read outside %s",loadmodel->name);
    if(!aw_bsp_file){memcpy(out,mod_base+l->fileofs+offset,bytes);return;}
    window=AW_SliceWindow(l);
    while(bytes>0){
        if(aw_bsp_window_start<0 || offset<aw_bsp_window_start ||
           offset>=aw_bsp_window_start+aw_bsp_window_bytes){
            aw_bsp_window_start=offset-offset%AW_BSP_SLICE_BYTES;
            aw_bsp_window_bytes=l->filelen-aw_bsp_window_start;
            if(aw_bsp_window_bytes>AW_BSP_SLICE_BYTES)aw_bsp_window_bytes=AW_BSP_SLICE_BYTES;
            AW_LumpBytes(l,aw_bsp_window_start,window,aw_bsp_window_bytes);
        }
        n=aw_bsp_window_start+aw_bsp_window_bytes-offset;if(n>bytes)n=bytes;
        memcpy(to,window+offset-aw_bsp_window_start,n);to+=n;offset+=n;bytes-=n;
    }
}


/*
=================
Mod_LoadTextures
=================
*/
/* CHIM: the texture lump of a CHIM brush image lists shared texture ids
 * (little-endian count, then one id per local index); texinfo indexes it as
 * it would a miptex lump. The textures stay in CHIM's shared pool. */
static void AW_LoadTextureRefs (lump_t *l)
{
    int i, n, id;

    if (l->filelen < 4)
        Sys_Error ("Invalid CHIM texture references in %s", loadmodel->name);
    AW_WindowBytes (l, 0, &n, 4);
    n = LittleLong (n);
    if (n < 0 || n > MAX_MAP_TEXTURES || l->filelen != 4 + 4*n)
        Sys_Error ("Invalid CHIM texture references in %s", loadmodel->name);
    loadmodel->numtextures = n;
    loadmodel->textures = AW_BrushAlloc (n * sizeof(*loadmodel->textures), loadname);
    for (i=0 ; i<n ; i++)
    {
        AW_WindowBytes (l, 4 + 4*i, &id, 4);
        loadmodel->textures[i] = aw_brush_arena->texture (aw_brush_arena->context, LittleLong (id));
        if (!loadmodel->textures[i])
            Sys_Error ("Missing CHIM texture %ld in %s", (long)LittleLong (id), loadmodel->name);
    }
}

void Mod_LoadTextures (lump_t *l)
{
    int		i, j, pixels, num, max, altmax;
    miptex_t	*mt;
    texture_t	*tx, *tx2;
    texture_t	*anims[10];
    texture_t	*altanims[10];
    int		nummiptex, dataofs, *directory;
    miptex_t	header;

    if (!l->filelen)
    {
        loadmodel->textures = NULL;
        return;
    }
    if (aw_brush_arena && aw_brush_arena->texture)
    {
        AW_LoadTextureRefs (l);
        return;
    }
    /* The directory (kept in the slice prefix) and each miptex header are read
     * into locals; the pixels are copied from the window into their texture_t. */
    mt = &header;
    AW_WindowBytes (l, 0, &nummiptex, 4);
    nummiptex = LittleLong (nummiptex);
    if (nummiptex < 0 || nummiptex > MAX_MAP_TEXTURES || 4 + nummiptex*4 > l->filelen)
        Sys_Error ("Mod_LoadTextures: bad texture count in %s", loadmodel->name);

    if (aw_bsp_file && aw_bsp_slice_prefix)
    {
        if (!aw_bsp_slice || aw_bsp_slice_prefix < 4 + nummiptex*4)
            Sys_Error ("Missing BSP slice buffer");
        AW_WindowBytes (l, 0, aw_bsp_slice, 4 + nummiptex*4);
        directory = (int *)aw_bsp_slice + 1;
    }
    else if (aw_bsp_file) /* the whole lump stays in the window */
        directory = (int *)AW_SliceWindow (l) + 1;
    else
        directory = (int *)(mod_base + l->fileofs) + 1;

    loadmodel->numtextures = nummiptex;
    loadmodel->textures = AW_BrushAlloc (nummiptex * sizeof(*loadmodel->textures) , loadname);

    for (i=0 ; i<nummiptex ; i++)
    {
        if(!(i&255))AW_LoadAudioTick();
        dataofs = LittleLong(directory[i]);
        if (dataofs == -1)
            continue;
        if (dataofs < 0 || dataofs > l->filelen - (int)sizeof(*mt))
            Sys_Error ("Mod_LoadTextures: bad miptex offset in %s", loadmodel->name);
        AW_WindowBytes (l, dataofs, mt, sizeof(*mt));
        mt->width = LittleLong (mt->width);
        mt->height = LittleLong (mt->height);
        for (j=0 ; j<MIPLEVELS ; j++)
            mt->offsets[j] = LittleLong (mt->offsets[j]);

        if ( (mt->width & 15) || (mt->height & 15) )
            Sys_Error ("Texture %s is not 16 aligned", mt->name);
        if ( (unsigned)mt->width > 4096 || (unsigned)mt->height > 4096 )
            Sys_Error ("Texture %s is too large", mt->name);
        pixels = mt->width*mt->height/64*85;
        if (pixels > l->filelen - dataofs - (int)sizeof(*mt))
            Sys_Error ("Texture %s is truncated", mt->name);
        tx = AW_BrushAlloc (sizeof(texture_t) +pixels, loadname );
        loadmodel->textures[i] = tx;

        memcpy (tx->name, mt->name, sizeof(tx->name));
        tx->width = mt->width;
        tx->height = mt->height;
        for (j=0 ; j<MIPLEVELS ; j++)
            tx->offsets[j] = mt->offsets[j] + sizeof(texture_t) - sizeof(miptex_t);
        // the pixels immediately follow the structures
        AW_WindowBytes (l, dataofs + sizeof(*mt), tx+1, pixels);

        if (!Q_strncmp(mt->name,"sky",3))
            R_InitSky (tx);
    }

//
// sequence the animations
//
    for (i=0 ; i<nummiptex ; i++)
    {
        if(!(i&255))AW_LoadAudioTick();
        tx = loadmodel->textures[i];
        if (!tx || tx->name[0] != '+')
            continue;
        if (tx->anim_next)
            continue;	// allready sequenced

    // find the number of frames in the animation
        memset (anims, 0, sizeof(anims));
        memset (altanims, 0, sizeof(altanims));

        max = tx->name[1];
        altmax = 0;
        if (max >= 'a' && max <= 'z')
            max -= 'a' - 'A';
        if (max >= '0' && max <= '9')
        {
            max -= '0';
            altmax = 0;
            anims[max] = tx;
            max++;
        }
        else if (max >= 'A' && max <= 'J')
        {
            altmax = max - 'A';
            max = 0;
            altanims[altmax] = tx;
            altmax++;
        }
        else
            Sys_Error ("Bad animating texture %s", tx->name);

        for (j=i+1 ; j<nummiptex ; j++)
        {
            tx2 = loadmodel->textures[j];
            if (!tx2 || tx2->name[0] != '+')
                continue;
            if (strcmp (tx2->name+2, tx->name+2))
                continue;

            num = tx2->name[1];
            if (num >= 'a' && num <= 'z')
                num -= 'a' - 'A';
            if (num >= '0' && num <= '9')
            {
                num -= '0';
                anims[num] = tx2;
                if (num+1 > max)
                    max = num + 1;
            }
            else if (num >= 'A' && num <= 'J')
            {
                num = num - 'A';
                altanims[num] = tx2;
                if (num+1 > altmax)
                    altmax = num+1;
            }
            else
                Sys_Error ("Bad animating texture %s", tx->name);
        }

#define	ANIM_CYCLE	2
    // link them all together
        for (j=0 ; j<max ; j++)
        {
            tx2 = anims[j];
            if (!tx2)
                Sys_Error ("Missing frame %ld of %s",j, tx->name);
            tx2->anim_total = max * ANIM_CYCLE;
            tx2->anim_min = j * ANIM_CYCLE;
            tx2->anim_max = (j+1) * ANIM_CYCLE;
            tx2->anim_next = anims[ (j+1)%max ];
            if (altmax)
                tx2->alternate_anims = altanims[0];
        }
        for (j=0 ; j<altmax ; j++)
        {
            tx2 = altanims[j];
            if (!tx2)
                Sys_Error ("Missing frame %ld of %s",j, tx->name);
            tx2->anim_total = altmax * ANIM_CYCLE;
            tx2->anim_min = j * ANIM_CYCLE;
            tx2->anim_max = (j+1) * ANIM_CYCLE;
            tx2->anim_next = altanims[ (j+1)%altmax ];
            if (max)
                tx2->alternate_anims = anims[0];
        }
    }
}

/*
=================
Mod_LoadLighting
=================
*/
void Mod_LoadLighting (lump_t *l)
{
    if (!l->filelen)
    {
        loadmodel->lightdata = NULL;
        return;
    }
    loadmodel->lightdata = AW_BrushAlloc ( l->filelen, loadname);
    memcpy (loadmodel->lightdata, mod_base + l->fileofs, l->filelen);
}


/*
=================
Mod_LoadVisibility
=================
*/
void Mod_LoadVisibility (lump_t *l)
{
    if (!l->filelen)
    {
        loadmodel->visdata = NULL;
        return;
    }
    loadmodel->visdata = AW_BrushAlloc ( l->filelen, loadname);
    memcpy (loadmodel->visdata, mod_base + l->fileofs, l->filelen);
}


/*
=================
Mod_LoadEntities
=================
*/
void Mod_LoadEntities (lump_t *l)
{
    if (!l->filelen)
    {
        loadmodel->entities = NULL;
        return;
    }
    loadmodel->entities = AW_BrushAlloc ( l->filelen, loadname);
    memcpy (loadmodel->entities, mod_base + l->fileofs, l->filelen);
}


/*
=================
Mod_LoadVertexes
=================
*/
void Mod_LoadVertexes (lump_t *l)
{
    dvertex_t	*in;
    mvertex_t	*out;
    int			i, count, n;
    aw_records_t	records;

    count = AW_RecordsBegin (&records, l, sizeof(*in));
    out = AW_BrushAlloc ( count*sizeof(*out), loadname);

    loadmodel->vertexes = out;
    loadmodel->numvertexes = count;

    for ( i=0 ; (in = AW_RecordsNext (&records, &n)) ; )
    for ( ; n-- ; i++, in++, out++)
    {
        if(!(i&255))AW_LoadAudioTick();
        out->position[0] = LittleFloat (in->point[0]);
        out->position[1] = LittleFloat (in->point[1]);
        out->position[2] = LittleFloat (in->point[2]);
    }
}

/*
=================
Mod_LoadSubmodels
=================
*/
void Mod_LoadSubmodels (lump_t *l)
{
    dmodel_t	*in;
    dmodel_t	*out;
    int			i, j, count, n;
    aw_records_t	records;

    count = AW_RecordsBegin (&records, l, sizeof(*in));
    out = AW_BrushAlloc ( count*sizeof(*out), loadname);

    loadmodel->submodels = out;
    loadmodel->numsubmodels = count;

    for ( i=0 ; (in = AW_RecordsNext (&records, &n)) ; )
    for ( ; n-- ; i++, in++, out++)
    {
        if(!(i&255))AW_LoadAudioTick();
        for (j=0 ; j<3 ; j++)
        {	// spread the mins / maxs by a pixel
            out->mins[j] = LittleFloat (in->mins[j]) - 1;
            out->maxs[j] = LittleFloat (in->maxs[j]) + 1;
            out->origin[j] = LittleFloat (in->origin[j]);
        }
        for (j=0 ; j<MAX_MAP_HULLS ; j++)
            out->headnode[j] = LittleLong (in->headnode[j]);
        out->visleafs = LittleLong (in->visleafs);
        out->firstface = LittleLong (in->firstface);
        out->numfaces = LittleLong (in->numfaces);
    }
}

/*
=================
Mod_LoadEdges
=================
*/
void Mod_LoadEdges (lump_t *l)
{
    dedge_t *in;
    medge_t *out;
    int	i, count, n;
    aw_records_t records;

    count = AW_RecordsBegin (&records, l, sizeof(*in));
    out = AW_BrushAlloc ( (count + 1) * sizeof(*out), loadname);

    loadmodel->edges = out;
    loadmodel->numedges = count;
    loadmodel->edgecache=NULL;loadmodel->edgecache_count=0;

    for ( i=0 ; (in = AW_RecordsNext (&records, &n)) ; )
    for ( ; n-- ; i++, in++, out++)
    {
        if(!(i&255))AW_LoadAudioTick();
        out->v[0] = (unsigned short)LittleShort(in->v[0]);
        out->v[1] = (unsigned short)LittleShort(in->v[1]);
    }
}

/*
=================
Mod_LoadTexinfo
=================
*/
void Mod_LoadTexinfo (lump_t *l)
{
    texinfo_t *in;
    mtexinfo_t *out;
    int	i, j, count, n;
    int		miptex;
    float	len1, len2;
    aw_records_t records;

    count = AW_RecordsBegin (&records, l, sizeof(*in));
    out = AW_BrushAlloc ( count*sizeof(*out), loadname);

    loadmodel->texinfo = out;
    loadmodel->numtexinfo = count;

    for ( i=0 ; (in = AW_RecordsNext (&records, &n)) ; )
    for ( ; n-- ; i++, in++, out++)
    {
        if(!(i&255))AW_LoadAudioTick();
        /* Respect each four-float row; indexing row zero past column 3 is UB. */
        for (j=0 ; j<4 ; j++) {
            out->vecs[0][j] = LittleFloat (in->vecs[0][j]);
            out->vecs[1][j] = LittleFloat (in->vecs[1][j]);
        }
        len1 = Length (out->vecs[0]);
        len2 = Length (out->vecs[1]);
        len1 = (len1 + len2)/2;
        if (len1 < 0.32)
            out->mipadjust = 4;
        else if (len1 < 0.49)
            out->mipadjust = 3;
        else if (len1 < 0.99)
            out->mipadjust = 2;
        else
            out->mipadjust = 1;
#if 0
        if (len1 + len2 < 0.001)
            out->mipadjust = 1;		// don't crash
        else
            out->mipadjust = 1 / floor( (len1+len2)/2 + 0.1 );
#endif

        miptex = LittleLong (in->miptex);
        out->flags = LittleLong (in->flags);

        if (!loadmodel->textures)
        {
            out->texture = r_notexture_mip;	// checkerboard texture
            out->flags = 0;
        }
        else
        {
            if (miptex < 0 || miptex >= loadmodel->numtextures)
                Sys_Error ("miptex >= loadmodel->numtextures");
            out->texture = loadmodel->textures[miptex];
            if (!out->texture)
            {
                out->texture = r_notexture_mip; // texture not found
                out->flags = 0;
            }
        }
    }
}

/*
================
CalcSurfaceExtents

Fills in s->texturemins[] and s->extents[]
================
*/
/* Surface extents decide each lightmap's size, so the engine, the light
 * compiler and the map converter must compute the same texture coordinates
 * on every FPU. The rule, as in QuakeSpasm's CalcSurfaceExtents and ericw
 * light: IEEE double precision after every product and sum, in source order
 * (float*float products are exact in double). GCC -m68040 would otherwise
 * round each step to single precision (fsmul/fsadd) while emulators compute
 * wider; the volatile store pins double rounding everywhere. The converter
 * (tools/surface_grid.py) computes the identical values. */
static double AW_DoubleRound (double x)
{
    volatile double r = x;
    return r;
}

void CalcSurfaceExtents (msurface_t *s)
{
    double	mins[2], maxs[2], val;
    int		i,j, e;
    mvertex_t	*v;
    mtexinfo_t	*tex;
    int		bmins[2], bmaxs[2];

    mins[0] = mins[1] = 999999;
    maxs[0] = maxs[1] = -99999;

    tex = s->texinfo;

    for (i=0 ; i<s->numedges ; i++)
    {
        e = loadmodel->surfedges[s->firstedge+i];
        if (e >= 0)
            v = &loadmodel->vertexes[loadmodel->edges[e].v[0]];
        else
            v = &loadmodel->vertexes[loadmodel->edges[-e].v[1]];

        for (j=0 ; j<2 ; j++)
        {
            val = AW_DoubleRound(AW_DoubleRound(AW_DoubleRound(
                      AW_DoubleRound((double)v->position[0] * tex->vecs[j][0]) +
                      AW_DoubleRound((double)v->position[1] * tex->vecs[j][1])) +
                  AW_DoubleRound((double)v->position[2] * tex->vecs[j][2])) +
                  tex->vecs[j][3]);
            if (val < mins[j])
                mins[j] = val;
            if (val > maxs[j])
                maxs[j] = val;
        }
    }

    for (i=0 ; i<2 ; i++)
    {
        bmins[i] = floor(mins[i]/16);
        bmaxs[i] = ceil(maxs[i]/16);

        s->texturemins[i] = bmins[i] * 16;
        s->extents[i] = (bmaxs[i] - bmins[i]) * 16;
        /* Imported constant-UV faces still need a nonempty cache tile. */
        if(s->extents[i]<16)s->extents[i]=16;
        if ( !(tex->flags & TEX_SPECIAL) && s->extents[i] > 256)
            Sys_Error ("Bad surface extents");
    }
}


/*
=================
Mod_LoadFaces
=================
*/
void Mod_LoadFaces (lump_t *l)
{
    dface_t		*in;
    msurface_t	*out;
    int			i, count, surfnum, n;
    int			planenum, side, firstedge, numedges, texnum;
    aw_records_t	records;

    count = AW_RecordsBegin (&records, l, sizeof(*in));
    out = AW_BrushAlloc ( count*sizeof(*out), loadname);

    loadmodel->surfaces = out;
    loadmodel->numsurfaces = count;

    for ( surfnum=0 ; (in = AW_RecordsNext (&records, &n)) ; )
    for ( ; n-- ; surfnum++, in++, out++)
    {
        if(!(surfnum&127))AW_LoadAudioTick();
        firstedge = LittleLong(in->firstedge);
        numedges = LittleShort(in->numedges);
        if(firstedge<0 || numedges<0 || firstedge>loadmodel->numsurfedges-numedges)
            Sys_Error("Invalid BSP face edge span");
        out->firstedge = firstedge;
        out->numedges = numedges;
        out->flags = 0;

        /* BSP29 face plane indices occupy all 16 bits. LittleShort returns
         * a signed short; sign extension selected memory before the plane
         * array once a converted scene passed 32767 planes. */
        planenum = (unsigned short)LittleShort(in->planenum);
        if (planenum >= loadmodel->numplanes)
            Sys_Error("Face plane index outside plane lump");
        side = LittleShort(in->side);
        if (side)
            out->flags |= SURF_PLANEBACK;

        out->plane = loadmodel->planes + planenum;

        /* The texinfo index is 16 bits as well; read it unsigned like the
         * plane index so converted maps may use up to 65535 mappings. */
        texnum = (unsigned short)LittleShort(in->texinfo);
        if (texnum >= loadmodel->numtexinfo)
            Sys_Error("Face texinfo index outside texinfo lump");
        out->texinfo = loadmodel->texinfo + texnum;

        CalcSurfaceExtents (out);

    // lighting info

        for (i=0 ; i<MAXLIGHTMAPS ; i++)
            out->styles[i] = in->styles[i];
        i = LittleLong(in->lightofs);
        if (i == -1)
            out->samples = NULL;
        else
            out->samples = loadmodel->lightdata + i;

    // set the drawing flags flag

        if (!Q_strncmp(out->texinfo->texture->name,"sky",3))	// sky
        {
            out->flags |= (SURF_DRAWSKY | SURF_DRAWTILED);
            continue;
        }

        if (!Q_strncmp(out->texinfo->texture->name,"*",1))		// turbulent
        {
            out->flags |= (SURF_DRAWTURB | SURF_DRAWTILED);
            for (i=0 ; i<2 ; i++)
            {
                out->extents[i] = 16384;
                out->texturemins[i] = -8192;
            }
            continue;
        }
    }
}


/*
=================
Mod_SetParent
=================
*/
void Mod_SetParent (mnode_t *node, mnode_t *parent)
{
    node->parent = parent;
    if (node->contents < 0)
        return;
    Mod_SetParent (node->children[0], node);
    Mod_SetParent (node->children[1], node);
}

/*
=================
Mod_LoadNodes
=================
*/
/* Converted inline models use point-collision dnodes, not render trees.
 * Keep all original-index hull0 clipnodes, but only expand a certified world
 * prefix to mnode_t. World rendering, PVS, leaf ancestry and torch face ranges
 * remain unchanged. Unsupported layouts retain the legacy full representation.
 * Classification uses ceil(node_count/8) temporary OS bytes. It never creates a
 * second disk-node or submodel table.
 *
 * The disk nodes arrive in slices, so one forward pass validates each node
 * before any pointer is made from it, certifies the prefix and decodes. A valid
 * prefix always ends just before the lowest inline point root, so that root
 * predicts it and both resident arrays are allocated before the pass. If the
 * certification fails, the attempt is released and the lump is decoded again
 * with the legacy representation (generic BSPs only). */
static qboolean aw_direct_hull0;

#define AW_SEEN(i) (seen[(i)>>3]&(1u<<((i)&7)))
#define AW_MARK(i) (seen[(i)>>3]|=1u<<((i)&7))

/* 0 when no prefix can be certified, else the predicted world node count. */
static int AW_PredictRenderPrefix(int count)
{
    int i,root,world=count;
    if(!loadmodel->submodels || loadmodel->numsubmodels<2 ||
       loadmodel->submodels[0].headnode[0]!=0)return 0;
    for(i=1;i<loadmodel->numsubmodels;i++){
        root=loadmodel->submodels[i].headnode[0];
        if(root>=0 && root<world)world=root;
    }
    return world>0 && world<count?world:0;
}

/* One pass over the disk nodes. world==count decodes the legacy full tree.
 * Returns false only when a predicted prefix fails certification. */
static qboolean AW_DecodeNodes(lump_t *l,int count,int world,byte *seen)
{
    aw_records_t records;dnode_t *in;mnode_t *out=loadmodel->nodes;
    dclipnode_t *clip=world<count?loadmodel->hulls[0].clipnodes:NULL;
    int i,j,n,p,first,nfaces,last=0,root;
    AW_RecordsBegin(&records,l,sizeof(*in));
    if(clip){memset(seen,0,(count+7)/8);AW_MARK(0);}
    for(i=0;(in=AW_RecordsNext(&records,&n));)
    for(;n--;i++,in++){
        if(!(i&255))AW_LoadAudioTick();
        p=LittleLong(in->planenum);
        first=(unsigned short)LittleShort(in->firstface);
        nfaces=(unsigned short)LittleShort(in->numfaces);
        if(p<0 || p>=loadmodel->numplanes || first>loadmodel->numsurfaces ||
           nfaces>loadmodel->numsurfaces-first)Sys_Error("Invalid BSP node data");
        for(j=0;j<2;j++){
            p=LittleShort(in->children[j]);
            if(p>=count || (p<0 && -1-p>=loadmodel->numleafs))
                Sys_Error("Invalid BSP node child");
        }
        if(clip){
            /* Generated world nodes are a forward tree in a contiguous prefix;
             * every tail node is reached from an inline root and has no faces.
             * Shared/backward/disconnected layouts use the original loader. */
            if(i<world){
                if(i>last || !AW_SEEN(i))return false;
                for(j=0;j<2;j++){
                    p=LittleShort(in->children[j]);
                    if(p<0)continue;
                    if(p<=i || p>=world || AW_SEEN(p))return false;
                    AW_MARK(p);if(p>last)last=p;
                }
            }else{
                if(i==world){
                    if(last+1!=world)return false;
                    memset(seen,0,(count+7)/8);
                    for(j=1;j<loadmodel->numsubmodels;j++){
                        root=loadmodel->submodels[j].headnode[0];
                        if(root>=0)AW_MARK(root);
                    }
                }
                if(!AW_SEEN(i) || nfaces)return false;
                for(j=0;j<2;j++){
                    p=LittleShort(in->children[j]);
                    if(p<0)continue;
                    if(p<=i)return false;
                    AW_MARK(p);
                }
            }
            clip[i].planenum=LittleLong(in->planenum);
            for(j=0;j<2;j++){
                p=LittleShort(in->children[j]);
                clip[i].children[j]=p<0?loadmodel->leafs[-1-p].contents:p;
            }
        }
        if(i>=world)continue;
        for (j=0 ; j<3 ; j++)
        {
            out[i].minmaxs[j] = LittleShort (in->mins[j]);
            out[i].minmaxs[3+j] = LittleShort (in->maxs[j]);
        }

        p = LittleLong(in->planenum);
        out[i].plane = loadmodel->planes + p;

        /* Unsigned on disk; checked above. */
        out[i].firstsurface = first;
        out[i].numsurfaces = nfaces;

        for (j=0 ; j<2 ; j++)
        {
            p = LittleShort (in->children[j]);
            if (p >= 0)
                out[i].children[j] = loadmodel->nodes + p;
            else
                out[i].children[j] = (mnode_t *)(loadmodel->leafs + (-1 - p));
        }
    }
    return true;
}

void Mod_LoadNodes (lump_t *l)
{
    int             i, count, world, mark, root;
    byte            *seen=NULL;
    hull_t          *hull=&loadmodel->hulls[0];
    aw_records_t    records;

    count = AW_RecordsBegin (&records, l, sizeof(dnode_t));
    if(count<1 || count>MAX_MAP_NODES)Sys_Error("Invalid BSP node count");
    for(i=0;i<loadmodel->numsubmodels;i++){
        root=loadmodel->submodels[i].headnode[0];
        if(root>=count || root < -loadmodel->numleafs)
            Sys_Error("Invalid BSP point hull root");
    }
    aw_direct_hull0 = false;
    if(aw_brush_arena && aw_brush_arena->point_hull_only){
        /* A brush entity never walks its own nodes to draw (its faces come
         * from firstmodelsurface); only hull 0 traces use them. The chain
         * of pieces is a graph with shared subtrees, which Mod_SetParent
         * would walk once per path, exponentially often. */
        aw_records_t r;dnode_t *in;dclipnode_t *clip;int n,j,p;
        clip=AW_BrushAlloc(count*sizeof(dclipnode_t),loadname);
        AW_RecordsBegin(&r,l,sizeof(*in));
        for(i=0;(in=AW_RecordsNext(&r,&n));)
        for(;n--;i++,in++){
            p=LittleLong(in->planenum);
            if(p<0 || p>=loadmodel->numplanes)Sys_Error("Invalid BSP node data");
            clip[i].planenum=p;
            for(j=0;j<2;j++){
                p=LittleShort(in->children[j]);
                if(p>=count || (p<0 && -1-p>=loadmodel->numleafs))Sys_Error("Invalid BSP node child");
                clip[i].children[j]=p<0?loadmodel->leafs[-1-p].contents:p;
            }
        }
        hull->clipnodes=clip;hull->planes=loadmodel->planes;
        hull->firstclipnode=0;hull->lastclipnode=count-1;
        loadmodel->nodes=NULL;loadmodel->numnodes=0;
        aw_direct_hull0=true;
        return;
    }
    world = AW_PredictRenderPrefix(count);
    /* Optional optimization: scratch allocation failure is safe. */
    if(world)seen=(byte *)calloc((count+7)/8,1);
    if(seen){
        mark=AW_BrushMark();
        hull->clipnodes=AW_BrushAlloc(count*sizeof(dclipnode_t),loadname);
        loadmodel->nodes=AW_BrushAlloc(world*sizeof(mnode_t),loadname);
        loadmodel->numnodes=world;
        if(AW_DecodeNodes(l,count,world,seen)){
            /* Original disk indices stay valid for every model point-trace root. */
            hull->planes=loadmodel->planes;
            hull->firstclipnode=0;hull->lastclipnode=count-1;
            aw_direct_hull0 = true;
        }else{
            hull->clipnodes=NULL;
            AW_BrushFreeToMark(mark);
        }
        free(seen);
    }
    if(!aw_direct_hull0){
        loadmodel->nodes=AW_BrushAlloc(count*sizeof(mnode_t),loadname);
        loadmodel->numnodes=count;
        AW_DecodeNodes(l,count,count,NULL);
    }

    Mod_SetParent (loadmodel->nodes, NULL);	// sets nodes and leafs
}

/*
=================
Mod_LoadLeafs
=================
*/
void Mod_LoadLeafs (lump_t *l)
{
    dleaf_t	*in;
    mleaf_t	*out;
    int			i, j, count, p, first, marks, n;
    aw_records_t	records;

    count = AW_RecordsBegin (&records, l, sizeof(*in));
    /* The PVS buffers (decompressed, mod_novis, fatpvs, checkpvs) hold
       MAX_MAP_LEAFS leaves (ENGINE-LEAF-LIMIT-UNCHECKED-35); the builder's map
       gate keeps every shipped map below it. */
    if (count > MAX_MAP_LEAFS)
        Sys_Error ("Mod_LoadLeafs: %s has %ld leaves, the engine holds %ld", loadmodel->name,
                   (long)count, (long)MAX_MAP_LEAFS);
    out = AW_BrushAlloc ( count*sizeof(*out), loadname);

    loadmodel->leafs = out;
    loadmodel->numleafs = count;

    for ( i=0 ; (in = AW_RecordsNext (&records, &n)) ; )
    for ( ; n-- ; i++, in++, out++)
    {
        if(!(i&255))AW_LoadAudioTick();
        for (j=0 ; j<3 ; j++)
        {
            out->minmaxs[j] = LittleShort (in->mins[j]);
            out->minmaxs[3+j] = LittleShort (in->maxs[j]);
        }

        p = LittleLong(in->contents);
        out->contents = p;

        /* Both fields are unsigned 16-bit on disk; signed reads pointed
         * before the mark list once a map passed 32767 marks. */
        first = (unsigned short)LittleShort(in->firstmarksurface);
        marks = (unsigned short)LittleShort(in->nummarksurfaces);
        if (first > loadmodel->nummarksurfaces ||
            marks > loadmodel->nummarksurfaces - first)
            Sys_Error ("Mod_LoadLeafs: bad marksurface range");
        out->firstmarksurface = loadmodel->marksurfaces + first;
        out->nummarksurfaces = marks;

        p = LittleLong(in->visofs);
        if (p == -1)
            out->compressed_vis = NULL;
        else
            out->compressed_vis = loadmodel->visdata + p;
        out->efrags = NULL;

        for (j=0 ; j<4 ; j++)
            out->ambient_sound_level[j] = in->ambient_level[j];
    }
}

/*
=================
Mod_LoadClipnodes
=================
*/
/* Disk/runtime clipnode records are both eight bytes. This decoder supports
 * in==out: streamed loading owns final storage before reading, then endian-fixes
 * it once. All indices and hull geometry retain their original values. */
static void AW_DecodeClipnodes(dclipnode_t *in,dclipnode_t *out,int count)
{
    int i,j,p,child,root;
    hull_t *hull;
    dclipnode_t *destination=out;
    if(count<0 || count>65520 || sizeof(*out)!=8)Sys_Error("Invalid BSP clipnode count");
    for(i=0;i<count;i++,in++,out++){
        if(!(i&255))AW_LoadAudioTick();
        p=LittleLong(in->planenum);
        if(p<0 || p>=loadmodel->numplanes)Sys_Error("Invalid BSP clipnode plane");
        out->planenum=p;
        for(j=0;j<2;j++){
            child=(unsigned short)LittleShort(in->children[j]);
            /* -1..-15 are contents; other unsigned values are node indices. */
            if(child<65521 && child>=count)Sys_Error("Invalid BSP clipnode child");
            out->children[j]=(short)child;
        }
    }
    for(i=0;i<loadmodel->numsubmodels;i++)for(j=1;j<MAX_MAP_HULLS;j++){
        root=loadmodel->submodels[i].headnode[j];
        if(root>=count || root < -15)Sys_Error("Invalid BSP clip hull root");
    }
    out=destination;
    loadmodel->clipnodes = out;
    loadmodel->numclipnodes = count;

    hull = &loadmodel->hulls[1];
    hull->clipnodes = out;
    hull->firstclipnode = 0;
    hull->lastclipnode = count-1;
    hull->planes = loadmodel->planes;
    hull->clip_mins[0] = -7.32f;
    hull->clip_mins[1] = -7.12f;
    hull->clip_mins[2] = -16.625f;
    hull->clip_maxs[0] = 7.32f;
    hull->clip_maxs[1] = 7.12f;
    hull->clip_maxs[2] = 16.625f;

    hull = &loadmodel->hulls[2];
    hull->clipnodes = out;
    hull->firstclipnode = 0;
    hull->lastclipnode = count-1;
    hull->planes = loadmodel->planes;
    hull->clip_mins[0] = -32;
    hull->clip_mins[1] = -32;
    hull->clip_mins[2] = -24;
    hull->clip_maxs[0] = 32;
    hull->clip_maxs[1] = 32;
    hull->clip_maxs[2] = 64;

}

void Mod_LoadClipnodes (lump_t *l)
{
    dclipnode_t *in,*out;
    int count;
    if(l->filelen<0 || l->filelen%sizeof(*in))
        Sys_Error("MOD_LoadBmodel: funny clipnode lump size");
    count=l->filelen/sizeof(*in);
    if(count>65520)Sys_Error("Invalid BSP clipnode count");
    in=(void *)(mod_base+l->fileofs);
    out=AW_BrushAlloc(count*sizeof(*out),loadname);
    AW_DecodeClipnodes(in,out,count);
}

/*
=================
Mod_MakeHull0

Deplicate the drawing hull structure as a clipping hull
=================
*/
void Mod_MakeHull0 (void)
{
    mnode_t		*in, *child;
    dclipnode_t *out;
    int			i, j, count;
    hull_t		*hull;

    hull = &loadmodel->hulls[0];
    if(aw_direct_hull0)return; /* Constructed directly while disk nodes existed. */

    in = loadmodel->nodes;
    count = loadmodel->numnodes;
    out = AW_BrushAlloc ( count*sizeof(*out), loadname);

    hull->clipnodes = out;
    hull->firstclipnode = 0;
    hull->lastclipnode = count-1;
    hull->planes = loadmodel->planes;

    for (i=0 ; i<count ; i++, out++, in++)
    {
        if(!(i&255))AW_LoadAudioTick();
        out->planenum = in->plane - loadmodel->planes;
        for (j=0 ; j<2 ; j++)
        {
            child = in->children[j];
            if (child->contents < 0)
                out->children[j] = child->contents;
            else
                out->children[j] = child - loadmodel->nodes;
        }
    }
}

/*
=================
Mod_LoadMarksurfaces
=================
*/
void Mod_LoadMarksurfaces (lump_t *l)
{
    int		i, j, count, n;
    short		*in;
    msurface_t **out;
    aw_records_t	records;

    count = AW_RecordsBegin (&records, l, sizeof(*in));
    out = AW_BrushAlloc ( count*sizeof(*out), loadname);

    loadmodel->marksurfaces = out;
    loadmodel->nummarksurfaces = count;

    for ( i=0 ; (in = AW_RecordsNext (&records, &n)) ; )
    for ( ; n-- ; i++, in++)
    {
        if(!(i&255))AW_LoadAudioTick();
        /* Face indices are unsigned 16-bit (0..65535); a signed read
         * turned faces past 32767 into negative indices. */
        j = (unsigned short)LittleShort(*in);
        if (j >= loadmodel->numsurfaces)
            Sys_Error ("Mod_ParseMarksurfaces: bad surface number");
        out[i] = loadmodel->surfaces + j;
    }
}

/*
=================
Mod_LoadSurfedges
=================
*/
void Mod_LoadSurfedges (lump_t *l)
{
    int		i, count, n;
    int		*in, *out;
    aw_records_t	records;

    count = AW_RecordsBegin (&records, l, sizeof(*in));
    out = AW_BrushAlloc ( count*sizeof(*out), loadname);

    loadmodel->surfedges = out;
    loadmodel->numsurfedges = count;

    for ( i=0 ; (in = AW_RecordsNext (&records, &n)) ; )
    for ( ; n-- ; i++, in++) {
        unsigned int index;
        if(!(i&255))AW_LoadAudioTick();
        out[i] = LittleLong (*in);
        index=out[i]<0?0U-(unsigned int)out[i]:(unsigned int)out[i];
        if(index>=(unsigned int)loadmodel->numedges)Sys_Error("Invalid signed surface edge index");
    }
}

/*
=================
Mod_LoadPlanes
=================
*/
void Mod_LoadPlanes (lump_t *l)
{
    int			i, j;
    mplane_t	*out;
    dplane_t	*in;
    int			count, n;
    int			bits;
    aw_records_t	records;

    count = AW_RecordsBegin (&records, l, sizeof(*in));
    /* Only count planes are initialized or referenced; the old double
     * allocation wasted Fast RAM on larger converted cells. */
    out = AW_BrushAlloc ( count*sizeof(*out), loadname);

    loadmodel->planes = out;
    loadmodel->numplanes = count;

    for ( i=0 ; (in = AW_RecordsNext (&records, &n)) ; )
    for ( ; n-- ; i++, in++, out++)
    {
        if(!(i&255))AW_LoadAudioTick();
        bits = 0;
        for (j=0 ; j<3 ; j++)
        {
            out->normal[j] = LittleFloat (in->normal[j]);
            if (out->normal[j] < 0)
                bits |= 1<<j;
        }

        out->dist = LittleFloat (in->dist);
        out->type = LittleLong (in->type);
        out->signbits = bits;
    }
}

/*
=================
RadiusFromBounds
=================
*/
float RadiusFromBounds (vec3_t mins, vec3_t maxs)
{
    int		i;
    vec3_t	corner;

    for (i=0 ; i<3 ; i++)
    {
        corner[i] = fabs(mins[i]) > fabs(maxs[i]) ? fabs(mins[i]) : fabs(maxs[i]);
    }

    return Length (corner);
}

/*
=================
Mod_LoadBrushModel
=================
*/
static void AW_LoadBrushSection(lump_t *l,void (*decode)(lump_t *)) {
    int mark;double started,disk;
    if(!aw_bsp_file){decode(l);return;}
    if(l->fileofs<0 || l->filelen<0 || l->fileofs>aw_bsp_bytes || l->filelen>aw_bsp_bytes-l->fileofs)
        Sys_Error("Invalid BSP section");
    /* Read fixed-size collision records into their final resident array.
     * Unlike a staged section, no temporary copy survives beside this array. */
    if(decode==Mod_LoadClipnodes){
        dclipnode_t *target;
        if(l->filelen%sizeof(*target) || l->filelen/sizeof(*target)>65520)
            Sys_Error("Invalid BSP clipnode section");
        target=AW_BrushAlloc(l->filelen,loadname);
        AW_LumpBytes(l,0,target,l->filelen);
        started=aw_load_clock?aw_load_clock():0;
        AW_DecodeClipnodes(target,target,l->filelen/sizeof(*target));
        if(aw_load_clock)aw_load_decode_seconds+=aw_load_clock()-started;
        if(l->filelen>aw_bsp_peak)aw_bsp_peak=l->filelen;
        AW_RecordSection(l,0);aw_bsp_reads++;AW_LoadAudioTick();return;
    }
    /* These byte lumps require no conversion. Reading into final storage
     * avoids holding two complete copies of a large visibility table. */
    if(decode==Mod_LoadVisibility || decode==Mod_LoadLighting || decode==Mod_LoadEntities){
        byte *target=NULL;
        if(l->filelen){
            target=AW_BrushAlloc(l->filelen,loadname);
            AW_LumpBytes(l,0,target,l->filelen);
        }
        if(decode==Mod_LoadVisibility)loadmodel->visdata=target;
        else if(decode==Mod_LoadLighting)loadmodel->lightdata=target;
        else loadmodel->entities=(char *)target;
        if(l->filelen>aw_bsp_peak)aw_bsp_peak=l->filelen;
        AW_RecordSection(l,0);aw_bsp_reads++;AW_LoadAudioTick();return;
    }
    /* Every other lump is decoded from bounded slices of this temporary
     * buffer straight into its final allocations (AW_RecordsNext). */
    mark=aw_brush_arena?0:Hunk_HighMark();aw_bsp_slice=NULL;
    aw_bsp_slice_bytes=l->filelen<AW_BSP_SLICE_BYTES?l->filelen:AW_BSP_SLICE_BYTES;
    /* Prefix: split records, or the texture directory (never > lump). A lump
     * that fits one window needs neither. */
    aw_bsp_slice_prefix=l->filelen<=AW_BSP_SLICE_BYTES?0:decode!=Mod_LoadTextures?AW_BSP_RECORD_PREFIX:
        ((l->filelen<AW_BSP_DIRECTORY_BYTES?l->filelen:AW_BSP_DIRECTORY_BYTES)+15)&~15;
    if(aw_bsp_slice_bytes)aw_bsp_slice_bytes+=aw_bsp_slice_prefix;
    aw_bsp_window_start=-1;
    if(aw_bsp_slice_bytes && aw_brush_arena){
        /* CHIM loads use their own loading buffer, never the high Hunk. */
        if(!aw_brush_arena->slice || aw_brush_arena->slice_bytes<aw_bsp_slice_bytes)
            Sys_Error("CHIM loading buffer too small for %s",loadmodel->name);
        aw_bsp_slice=aw_brush_arena->slice;
    }else if(aw_bsp_slice_bytes){
        aw_bsp_slice=Hunk_TempAlloc(aw_bsp_slice_bytes);
        if(!aw_bsp_slice)Sys_Error("BSP section allocation failed");
    }
    if(aw_bsp_slice_bytes>aw_bsp_slice_peak)aw_bsp_slice_peak=aw_bsp_slice_bytes;
    if(l->filelen>aw_bsp_peak)aw_bsp_peak=l->filelen;
    aw_bsp_reads++;
    started=aw_load_clock?aw_load_clock():0;disk=aw_load_disk_seconds;
    decode(l);
    /* Decode time excludes the disk reads now interleaved with it. */
    if(aw_load_clock)aw_load_decode_seconds+=aw_load_clock()-started-(aw_load_disk_seconds-disk);
    AW_LoadAudioTick();
    AW_RecordSection(l,aw_bsp_slice_bytes);
    if(!aw_brush_arena)Hunk_FreeToHighMark(mark);
    aw_bsp_slice=NULL;aw_bsp_slice_bytes=0;
}

/* Immutable edge vertices keep their original IDs. Only the mutable world
 * raster cache is sparse; a prefix also supports arbitrary unsorted BSPs. */
static void AW_EdgeCacheService(int *work) {
    if(++*work==256){*work=0;AW_LoadAudioTick();}
}
static void AW_EdgeCacheFace(model_t *mod,int index,int *limit,int *work) {
    msurface_t *face;int i,edge;
    AW_EdgeCacheService(work);
    if(index<0 || index>=mod->numsurfaces)Sys_Error("Invalid edge cache face");
    face=&mod->surfaces[index];
    if(face->firstedge<0 || face->numedges<0 || face->firstedge>mod->numsurfedges-face->numedges)
        Sys_Error("Invalid edge cache face range");
    for(i=0;i<face->numedges;i++){
        AW_EdgeCacheService(work);
        edge=mod->surfedges[face->firstedge+i];
        if(edge==INT_MIN)Sys_Error("Invalid edge cache index");
        if(edge<0)edge=-edge;
        if(edge>=mod->numedges)Sys_Error("Invalid edge cache index");
        if(edge>=*limit)*limit=edge+1;
    }
}
static void AW_InitEdgeCache(model_t *mod) {
    int i,j,first,count,work=0,limit=mod->numedges?1:0;dmodel_t *world;
    AW_LoadAudioTick();
    if(mod->numsubmodels<1)Sys_Error("Missing world model for edge cache");
    world=&mod->submodels[0];first=world->firstface;count=world->numfaces;
    if(first<0 || count<0 || first>mod->numsurfaces-count)Sys_Error("Invalid world edge cache range");
    for(i=first;i<first+count;i++)AW_EdgeCacheFace(mod,i,&limit,&work);
    /* Include every retained render-node and leaf mark, even on generic BSPs
     * whose ranges are not a dense prefix of the world's face list. */
    for(i=0;i<mod->numnodes;i++){
        AW_EdgeCacheService(&work);
        first=mod->nodes[i].firstsurface;count=mod->nodes[i].numsurfaces;
        if(first>mod->numsurfaces-count)Sys_Error("Invalid node edge cache range");
        for(j=first;j<first+count;j++)AW_EdgeCacheFace(mod,j,&limit,&work);
    }
    for(i=0;i<mod->nummarksurfaces;i++){
        ptrdiff_t index=mod->marksurfaces[i]-mod->surfaces;
        AW_EdgeCacheService(&work);
        if(index<0 || index>=mod->numsurfaces)Sys_Error("Invalid mark edge cache range");
        AW_EdgeCacheFace(mod,(int)index,&limit,&work);
    }
    if(limit>INT_MAX/(int)sizeof(unsigned int))Sys_Error("Edge cache size overflow");
    mod->edgecache_count=limit;
    mod->edgecache=limit?AW_BrushAlloc(limit*sizeof(unsigned int),loadname):NULL;
    AW_LoadAudioTick();
}

/* One section of a brush load, in Mod_LoadBrushModel's order (step 0-14). A
 * CHIM image stores the entities before the clipnodes (its collision lump
 * comes last), so a CHIM stream swaps the last two steps and reads its file
 * front to back. A switch, not a table: unused decoders stay out of tests
 * that link only part of this file. */
static void AW_BrushSection (dheader_t *h, int step, qboolean chim)
{
    if (chim && step >= 13)
        step = step == 13 ? 14 : 13;
    switch (step)
    {
    case 0: AW_LoadBrushSection(&h->lumps[LUMP_VERTEXES],Mod_LoadVertexes); break;
    case 1: AW_LoadBrushSection(&h->lumps[LUMP_EDGES],Mod_LoadEdges); break;
    case 2: AW_LoadBrushSection(&h->lumps[LUMP_SURFEDGES],Mod_LoadSurfedges); break;
    case 3: AW_LoadBrushSection(&h->lumps[LUMP_TEXTURES],Mod_LoadTextures); break;
    case 4: AW_LoadBrushSection(&h->lumps[LUMP_LIGHTING],Mod_LoadLighting); break;
    case 5: AW_LoadBrushSection(&h->lumps[LUMP_PLANES],Mod_LoadPlanes); break;
    case 6: AW_LoadBrushSection(&h->lumps[LUMP_TEXINFO],Mod_LoadTexinfo); break;
    case 7: AW_LoadBrushSection(&h->lumps[LUMP_FACES],Mod_LoadFaces); break;
    case 8: AW_LoadBrushSection(&h->lumps[LUMP_MARKSURFACES],Mod_LoadMarksurfaces); break;
    case 9: AW_LoadBrushSection(&h->lumps[LUMP_VISIBILITY],Mod_LoadVisibility); break;
    case 10: AW_LoadBrushSection(&h->lumps[LUMP_LEAFS],Mod_LoadLeafs); break;
    /* Validate all model point roots before selecting the renderer node prefix. */
    case 11: AW_LoadBrushSection(&h->lumps[LUMP_MODELS],Mod_LoadSubmodels); break;
    case 12: AW_LoadBrushSection(&h->lumps[LUMP_NODES],Mod_LoadNodes); break;
    case 13: AW_LoadBrushSection(&h->lumps[LUMP_CLIPNODES],Mod_LoadClipnodes); break;
    case 14: AW_LoadBrushSection(&h->lumps[LUMP_ENTITIES],Mod_LoadEntities); break;
    }
}

static void AW_BrushFinish (model_t *mod)
{
    int			i, j;
    dmodel_t	*bm;

    /* A CHIM model is always drawn as a brush entity, never as the world, so
     * the world-only edge cache is not built for it. */
    if(!aw_brush_arena)AW_InitEdgeCache(loadmodel);
    Mod_MakeHull0 ();
    if(aw_bsp_lumps && aw_load_hunk_used)aw_bsp_used[HEADER_LUMPS+1]=aw_load_hunk_used();

    mod->numframes = 2;		// regular and alternate animation
    mod->flags = 0;

//
// set up the submodels (FIXME: this is confusing)
//
    for (i=0 ; i<mod->numsubmodels ; i++)
    {
        bm = &mod->submodels[i];

        mod->hulls[0].firstclipnode = bm->headnode[0];
        for (j=1 ; j<MAX_MAP_HULLS ; j++)
        {
            mod->hulls[j].firstclipnode = bm->headnode[j];
            mod->hulls[j].lastclipnode = mod->numclipnodes-1;
        }

        mod->firstmodelsurface = bm->firstface;
        mod->nummodelsurfaces = bm->numfaces;

        VectorCopy (bm->maxs, mod->maxs);
        VectorCopy (bm->mins, mod->mins);
        mod->radius = RadiusFromBounds (mod->mins, mod->maxs);

        mod->numleafs = bm->visleafs;

        if (i < mod->numsubmodels-1)
        {	// duplicate the basic information
            char	name[16];

            sprintf (name, "*%ld", (long)(i+1));
            loadmodel = Mod_FindName (name);
            *loadmodel = *mod;
            strcpy (loadmodel->name, name);
            mod = loadmodel;
        }
    }
}

void Mod_LoadBrushModel (model_t *mod, void *buffer)
{
    int			i;
    dheader_t	*header;

    loadmodel->type = mod_brush;

    header = (dheader_t *)buffer;

    i = LittleLong (header->version);
    if (i != BSPVERSION)
        Sys_Error ("Mod_LoadBrushModel: %s has wrong version number (%ld should be %ld)", mod->name, i, BSPVERSION);

// swap all the lumps
    mod_base = (byte *)header;

    for (i=0 ; i<sizeof(dheader_t)/4 ; i++)
        ((int *)header)[i] = LittleLong ( ((int *)header)[i]);

// load into heap

    for (i=0 ; i<AW_BRUSH_SECTIONS ; i++)
        AW_BrushSection (header, i, false);

    AW_BrushFinish (mod);
}

/* CHIM: a copy of a BSP header, byte-swapped and checked against the bytes
 * that hold it. A CHIM model has exactly one submodel: AW_BrushFinish would
 * otherwise register "*N" inline models of the current map. */
int AW_BrushHeader (dheader_t *out, const void *raw, long bytes)
{
    int i;
    if (!out || !raw || bytes < (long)sizeof(dheader_t))
        return 0;
    memcpy (out, raw, sizeof(*out));
    for (i=0 ; i<sizeof(dheader_t)/4 ; i++)
        ((int *)out)[i] = LittleLong ( ((int *)out)[i]);
    if (out->version != BSPVERSION)
        return 0;
    for (i=0 ; i<HEADER_LUMPS ; i++)
        if (out->lumps[i].fileofs < 0 || out->lumps[i].filelen < 0 ||
            out->lumps[i].fileofs > bytes || out->lumps[i].filelen > bytes - out->lumps[i].fileofs)
            return 0;
    return out->lumps[LUMP_MODELS].filelen == (int)sizeof(dmodel_t);
}

/* CHIM: upper bound of the arena bytes the decoders allocate for a checked
 * header (every allocation 16-byte aligned, no edge cache). Texture pixels
 * are bounded by their lump, which holds each texture once; a malformed lump
 * that overruns its arena stops with an error instead of overwriting memory. */
#define AW_ARENA16(n) ((((long)(n))+15)&~15L)
int AW_BrushBound (const dheader_t *h, int texture_refs)
{
    const lump_t *l = h->lumps;
    long total = 0, n, k;

    total += AW_ARENA16 (l[LUMP_VERTEXES].filelen/(long)sizeof(dvertex_t)*(long)sizeof(mvertex_t));
    total += AW_ARENA16 ((l[LUMP_EDGES].filelen/(long)sizeof(dedge_t)+1)*(long)sizeof(medge_t));
    total += AW_ARENA16 (l[LUMP_SURFEDGES].filelen/(long)sizeof(int)*(long)sizeof(int));
    if (l[LUMP_TEXTURES].filelen && texture_refs)
        total += AW_ARENA16 ((l[LUMP_TEXTURES].filelen/4)*(long)sizeof(texture_t *));
    else if (l[LUMP_TEXTURES].filelen)
    {
        n = l[LUMP_TEXTURES].filelen >= 4 ? (l[LUMP_TEXTURES].filelen-4)/4 : 0;
        if (n > MAX_MAP_TEXTURES)
            n = MAX_MAP_TEXTURES;
        k = l[LUMP_TEXTURES].filelen/(long)sizeof(miptex_t);
        if (k > n)
            k = n;
        total += AW_ARENA16 (n*(long)sizeof(texture_t *)) + k*((long)sizeof(texture_t)+15) + l[LUMP_TEXTURES].filelen;
    }
    total += AW_ARENA16 (l[LUMP_LIGHTING].filelen) + AW_ARENA16 (l[LUMP_VISIBILITY].filelen) +
        AW_ARENA16 (l[LUMP_ENTITIES].filelen) + AW_ARENA16 (l[LUMP_CLIPNODES].filelen);
    total += AW_ARENA16 (l[LUMP_PLANES].filelen/(long)sizeof(dplane_t)*(long)sizeof(mplane_t));
    total += AW_ARENA16 (l[LUMP_TEXINFO].filelen/(long)sizeof(texinfo_t)*(long)sizeof(mtexinfo_t));
    total += AW_ARENA16 (l[LUMP_FACES].filelen/(long)sizeof(dface_t)*(long)sizeof(msurface_t));
    total += AW_ARENA16 (l[LUMP_MARKSURFACES].filelen/(long)sizeof(short)*(long)sizeof(msurface_t *));
    total += AW_ARENA16 (l[LUMP_LEAFS].filelen/(long)sizeof(dleaf_t)*(long)sizeof(mleaf_t));
    total += AW_ARENA16 (l[LUMP_MODELS].filelen/(long)sizeof(dmodel_t)*(long)sizeof(dmodel_t));
    /* Nodes: the direct hull-0 attempt (clipnodes + nodes), or after its
     * rollback the full node array plus Mod_MakeHull0's clipnodes. */
    n = l[LUMP_NODES].filelen/(long)sizeof(dnode_t);
    total += AW_ARENA16 (n*(long)sizeof(dclipnode_t)) + AW_ARENA16 (n*(long)sizeof(mnode_t));
    return total > INT_MAX ? -1 : (int)total;
}

/* CHIM: decode a complete BSP file image (in a loading buffer) into an arena.
 * Returns 0 for an image whose header does not check out. */
int AW_BrushImage (model_t *mod, byte *image, long bytes, aw_brush_arena_t *arena)
{
    model_t *saved_model = loadmodel;
    dheader_t header;
    jmp_buf caught;

    if (!arena || !AW_BrushHeader (&header, image, bytes))
        return 0;
    COM_FileBase (mod->name, loadname);
    loadmodel = mod;
    mod->needload = NL_PRESENT;
    aw_brush_arena = arena;
    if (setjmp (caught))
    {
        AW_BrushCaught (mod);
        loadmodel = saved_model;
        return 0;
    }
    aw_brush_catch = &caught;
    Mod_LoadBrushModel (mod, image);
    aw_brush_catch = NULL;
    aw_brush_arena = NULL;
    loadmodel = saved_model;
    return 1;
}

/* CHIM: stream a BSP from an open pack file at an offset, one section per
 * call, so a large model can be spread over several frames. The loader's
 * file state is installed for the step and cleared after it, so ordinary
 * loads between two steps are unaffected. */
int AW_BrushStreamBegin (aw_brush_stream_t *s, model_t *mod, FILE *file, long base, long bytes, aw_brush_arena_t *arena)
{
    byte raw[sizeof(dheader_t)];

    memset (s, 0, sizeof(*s));
    if (!file || !arena || base < 0 || bytes < (long)sizeof(raw) || fseek (file, base, SEEK_SET) ||
        fread (raw, 1, sizeof(raw), file) != sizeof(raw) || !AW_BrushHeader (&s->header, raw, bytes))
        return 0;
    s->mod = mod; s->file = file; s->base = base; s->bytes = bytes; s->arena = arena;
    mod->type = mod_brush;
    mod->needload = NL_PRESENT;
    return 1;
}

int AW_BrushStreamStep (aw_brush_stream_t *s)
{
    model_t *saved_model = loadmodel;
    char saved_name[sizeof(loadname)];
    jmp_buf caught;
    int i;

    if (s->next >= AW_BRUSH_SECTIONS)
        return 1;
    memcpy (saved_name, loadname, sizeof(saved_name));
    if (setjmp (caught))
    {
        AW_BrushCaught (s->mod);
        s->next = AW_BRUSH_SECTIONS;
        loadmodel = saved_model;
        memcpy (loadname, saved_name, sizeof(saved_name));
        return -1;
    }
    COM_FileBase (s->mod->name, loadname);
    loadmodel = s->mod;
    aw_bsp_file = s->file; aw_bsp_base = s->base; aw_bsp_bytes = s->bytes;
    aw_bsp_position = -1; aw_bsp_lumps = NULL; mod_base = NULL;
    aw_brush_arena = s->arena;
    aw_brush_catch = &caught;
    i = s->next++;
    AW_BrushSection (&s->header, i, true);
    if (s->next == AW_BRUSH_SECTIONS)
        AW_BrushFinish (s->mod);
    aw_brush_catch = NULL;
    aw_brush_arena = NULL;
    aw_bsp_file = NULL; aw_bsp_position = -1;
    loadmodel = saved_model;
    memcpy (loadname, saved_name, sizeof(saved_name));
    return s->next == AW_BRUSH_SECTIONS;
}

#undef Sys_Error

/*
==============================================================================

ALIAS MODELS

==============================================================================
*/

/* Decode small aliases without growing the low hunk through hot cache blocks.
 * Cache_FreeLow relocates by address, not LRU; releasing hunk staging only
 * after decoding is too late to prevent a visible actor/torch reload cycle.
 * Preserve the old 16-byte block padding and offsets, including zero tail
 * padding, so target cache budgets do not change. No resident staging slab. */
#define AW_ALIAS_STAGING_LIMIT (512*1024)
static byte *aw_alias_stage;
static int aw_alias_stage_used,aw_alias_stage_size;
static int AW_AliasSum(size_t *total,int count,size_t unit) {
    if(count<0 || unit>(size_t)INT_MAX || (size_t)count>((size_t)INT_MAX-*total)/unit)return 0;
    *total+=(size_t)count*unit;return 1;
}
static int AW_AliasBlock(size_t *total,size_t bytes) {
    size_t block;
    if(bytes>(size_t)INT_MAX-31)return 0;
    block=16+((bytes+15)&~(size_t)15);
    if(*total>(size_t)INT_MAX-block)return 0;
    *total+=block;return 1;
}
static const byte *AW_AliasTake(const byte **at,size_t *left,size_t bytes) {
    const byte *p=*at;if(bytes>*left)return NULL;
    *at+=bytes;*left-=bytes;return p;
}
/* Validate all lengths before allocation, including grouped skins/frames.
 * The decoder uses the same allocation sequence as this sizing pass. */
static int AW_AliasStageBytes(const void *buffer,int bytes) {
    const byte *at=buffer,*p;const mdl_t *m;size_t left,total=0,header=0,skinbytes;
    int skins,width,height,verts,tris,frames,i,j,count,type;float interval;
    if(bytes<(int)sizeof(mdl_t) || (r_pixbytes!=1 && r_pixbytes!=2))return 0;
    left=bytes;p=AW_AliasTake(&at,&left,sizeof(mdl_t));m=(const mdl_t *)p;
    if(LittleLong(m->ident)!=IDPOLYHEADER || LittleLong(m->version)!=ALIAS_VERSION)return 0;
    skins=LittleLong(m->numskins);width=LittleLong(m->skinwidth);height=LittleLong(m->skinheight);
    verts=LittleLong(m->numverts);tris=LittleLong(m->numtris);frames=LittleLong(m->numframes);
    if(skins<1 || width<1 || (width&3) || height<1 || height>MAX_LBM_HEIGHT ||
       verts<1 || verts>MAXALIASVERTS || tris<1 || frames<1)return 0;
    skinbytes=0;if(!AW_AliasSum(&skinbytes,height,(size_t)width) || skinbytes>(size_t)INT_MAX/r_pixbytes)return 0;
    if(!AW_AliasSum(&header,1,sizeof(aliashdr_t)) || !AW_AliasSum(&header,frames-1,sizeof(maliasframedesc_t)) ||
       !AW_AliasSum(&header,1,sizeof(mdl_t)) || !AW_AliasSum(&header,verts,sizeof(stvert_t)) ||
       !AW_AliasSum(&header,tris,sizeof(mtriangle_t)) || !AW_AliasBlock(&total,header))return 0;
    header=0;if(!AW_AliasSum(&header,skins,sizeof(maliasskindesc_t)) || !AW_AliasBlock(&total,header))return 0;
    for(i=0;i<skins;i++){
        p=AW_AliasTake(&at,&left,sizeof(daliasskintype_t));if(!p)return 0;
        type=LittleLong(((const daliasskintype_t *)p)->type);count=1;
        if(type==ALIAS_SKIN_GROUP){
            p=AW_AliasTake(&at,&left,sizeof(daliasskingroup_t));if(!p)return 0;
            count=LittleLong(((const daliasskingroup_t *)p)->numskins);if(count<1 || (size_t)count>left/sizeof(float))return 0;
            header=sizeof(maliasskingroup_t);
            if(!AW_AliasSum(&header,count-1,sizeof(maliasskindesc_t)) || !AW_AliasBlock(&total,header) ||
               !AW_AliasBlock(&total,(size_t)count*sizeof(float)))return 0;
            for(j=0;j<count;j++){p=AW_AliasTake(&at,&left,sizeof(daliasskininterval_t));
                interval=LittleFloat(((const daliasskininterval_t *)p)->interval);if(!(interval>0) || !isfinite(interval))return 0;}
        }else if(type!=ALIAS_SKIN_SINGLE)return 0;
        if((size_t)count>left/skinbytes)return 0;
        for(j=0;j<count;j++)if(!AW_AliasTake(&at,&left,skinbytes) || !AW_AliasBlock(&total,skinbytes*r_pixbytes))return 0;
    }
    header=0;if(!AW_AliasSum(&header,verts,sizeof(stvert_t)) || !AW_AliasSum(&header,tris,sizeof(dtriangle_t)) ||
       !AW_AliasTake(&at,&left,header))return 0;
    for(i=0;i<frames;i++){
        p=AW_AliasTake(&at,&left,sizeof(daliasframetype_t));if(!p)return 0;
        type=LittleLong(((const daliasframetype_t *)p)->type);count=1;
        if(type==ALIAS_GROUP){
            p=AW_AliasTake(&at,&left,sizeof(daliasgroup_t));if(!p)return 0;
            count=LittleLong(((const daliasgroup_t *)p)->numframes);if(count<1 || (size_t)count>left/sizeof(float))return 0;
            header=sizeof(maliasgroup_t);
            if(!AW_AliasSum(&header,count-1,sizeof(maliasgroupframedesc_t)) || !AW_AliasBlock(&total,header) ||
               !AW_AliasBlock(&total,(size_t)count*sizeof(float)))return 0;
            for(j=0;j<count;j++){p=AW_AliasTake(&at,&left,sizeof(daliasinterval_t));
                interval=LittleFloat(((const daliasinterval_t *)p)->interval);if(!(interval>0) || !isfinite(interval))return 0;}
        }else if(type!=ALIAS_SINGLE)return 0;
        header=sizeof(daliasframe_t)+(size_t)verts*sizeof(trivertx_t);
        if((size_t)count>left/header)return 0;
        for(j=0;j<count;j++){
            p=AW_AliasTake(&at,&left,header);
            if(!memchr(((const daliasframe_t *)p)->name,0,16) || !AW_AliasBlock(&total,(size_t)verts*sizeof(trivertx_t)))return 0;
        }
    }
    return (int)total;
}
static void *AW_AliasAlloc(int bytes,char *name) {
    byte *p;size_t block;
    if(!aw_alias_stage)return Hunk_AllocName(bytes,name);
    block=16+(((size_t)bytes+15)&~(size_t)15);
    if(bytes<0 || block>(size_t)(aw_alias_stage_size-aw_alias_stage_used))Sys_Error("Alias staging size mismatch");
    p=aw_alias_stage+aw_alias_stage_used;memset(p,0,block);aw_alias_stage_used+=(int)block;return p;
}

#include "model_alias_stream.inc"

/*
=================
Mod_LoadAliasFrame
=================
*/
void * Mod_LoadAliasFrame (void * pin, int *pframeindex, int numv,
    trivertx_t *pbboxmin, trivertx_t *pbboxmax, aliashdr_t *pheader, char *name)
{
    trivertx_t		*pframe, *pinframe;
    int				i, j;
    daliasframe_t	*pdaliasframe;

    pdaliasframe = (daliasframe_t *)pin;

    /* the file's 16-byte frame name need not end in a NUL (ENGINE-ENTITY-TEXT-UNBOUNDED-35) */
    memcpy (name, pdaliasframe->name, sizeof(pdaliasframe->name));
    name[sizeof(pdaliasframe->name) - 1] = 0;

    for (i=0 ; i<3 ; i++)
    {
    // these are byte values, so we don't have to worry about
    // endianness
        pbboxmin->v[i] = pdaliasframe->bboxmin.v[i];
        pbboxmax->v[i] = pdaliasframe->bboxmax.v[i];
    }

    pinframe = (trivertx_t *)(pdaliasframe + 1);
    pframe = AW_AliasAlloc (numv * sizeof(*pframe), loadname);

    *pframeindex = (byte *)pframe - (byte *)pheader;

    for (j=0 ; j<numv ; j++)
    {
        int		k;

    // these are all byte values, so no need to deal with endianness
        pframe[j].lightnormalindex = pinframe[j].lightnormalindex;

        for (k=0 ; k<3 ; k++)
        {
            pframe[j].v[k] = pinframe[j].v[k];
        }
    }

    pinframe += numv;

    return (void *)pinframe;
}


/*
=================
Mod_LoadAliasGroup
=================
*/
void * Mod_LoadAliasGroup (void * pin, int *pframeindex, int numv,
    trivertx_t *pbboxmin, trivertx_t *pbboxmax, aliashdr_t *pheader, char *name)
{
    daliasgroup_t		*pingroup;
    maliasgroup_t		*paliasgroup;
    int					i, numframes;
    daliasinterval_t	*pin_intervals;
    float				*poutintervals;
    void				*ptemp;

    pingroup = (daliasgroup_t *)pin;

    numframes = LittleLong (pingroup->numframes);

    paliasgroup = AW_AliasAlloc (sizeof (maliasgroup_t) +
            (numframes - 1) * sizeof (paliasgroup->frames[0]), loadname);

    paliasgroup->numframes = numframes;

    for (i=0 ; i<3 ; i++)
    {
    // these are byte values, so we don't have to worry about endianness
        pbboxmin->v[i] = pingroup->bboxmin.v[i];
        pbboxmax->v[i] = pingroup->bboxmax.v[i];
    }

    *pframeindex = (byte *)paliasgroup - (byte *)pheader;

    pin_intervals = (daliasinterval_t *)(pingroup + 1);

    poutintervals = AW_AliasAlloc (numframes * sizeof (float), loadname);

    paliasgroup->intervals = (byte *)poutintervals - (byte *)pheader;

    for (i=0 ; i<numframes ; i++)
    {
        *poutintervals = LittleFloat (pin_intervals->interval);
        if (*poutintervals <= 0.0)
            Sys_Error ("Mod_LoadAliasGroup: interval<=0");

        poutintervals++;
        pin_intervals++;
    }

    ptemp = (void *)pin_intervals;

    for (i=0 ; i<numframes ; i++)
    {
        ptemp = Mod_LoadAliasFrame (ptemp,
                                    &paliasgroup->frames[i].frame,
                                    numv,
                                    &paliasgroup->frames[i].bboxmin,
                                    &paliasgroup->frames[i].bboxmax,
                                    pheader, name);
    }

    return ptemp;
}


/*
=================
Mod_LoadAliasSkin
=================
*/
void * Mod_LoadAliasSkin (void * pin, int *pskinindex, int skinsize,
    aliashdr_t *pheader)
{
    int		i;
    byte	*pskin, *pinskin;
    unsigned short	*pusskin;

    pskin = AW_AliasAlloc (skinsize * r_pixbytes, loadname);
    pinskin = (byte *)pin;
    *pskinindex = (byte *)pskin - (byte *)pheader;

    if (r_pixbytes == 1)
    {
        Q_memcpy (pskin, pinskin, skinsize);
    }
    else if (r_pixbytes == 2)
    {
        pusskin = (unsigned short *)pskin;

        for (i=0 ; i<skinsize ; i++)
            pusskin[i] = d_8to16table[pinskin[i]];
    }
    else
    {
        Sys_Error ("Mod_LoadAliasSkin: driver set invalid r_pixbytes: %ld\n",
                 r_pixbytes);
    }

    pinskin += skinsize;

    return ((void *)pinskin);
}


/*
=================
Mod_LoadAliasSkinGroup
=================
*/
void * Mod_LoadAliasSkinGroup (void * pin, int *pskinindex, int skinsize,
    aliashdr_t *pheader)
{
    daliasskingroup_t		*pinskingroup;
    maliasskingroup_t		*paliasskingroup;
    int						i, numskins;
    daliasskininterval_t	*pinskinintervals;
    float					*poutskinintervals;
    void					*ptemp;

    pinskingroup = (daliasskingroup_t *)pin;

    numskins = LittleLong (pinskingroup->numskins);

    paliasskingroup = AW_AliasAlloc (sizeof (maliasskingroup_t) +
            (numskins - 1) * sizeof (paliasskingroup->skindescs[0]),
            loadname);

    paliasskingroup->numskins = numskins;

    *pskinindex = (byte *)paliasskingroup - (byte *)pheader;

    pinskinintervals = (daliasskininterval_t *)(pinskingroup + 1);

    poutskinintervals = AW_AliasAlloc (numskins * sizeof (float),loadname);

    paliasskingroup->intervals = (byte *)poutskinintervals - (byte *)pheader;

    for (i=0 ; i<numskins ; i++)
    {
        *poutskinintervals = LittleFloat (pinskinintervals->interval);
        if (*poutskinintervals <= 0)
            Sys_Error ("Mod_LoadAliasSkinGroup: interval<=0");

        poutskinintervals++;
        pinskinintervals++;
    }

    ptemp = (void *)pinskinintervals;

    for (i=0 ; i<numskins ; i++)
    {
        ptemp = Mod_LoadAliasSkin (ptemp,
                &paliasskingroup->skindescs[i].skin, skinsize, pheader);
    }

    return ptemp;
}


/*
=================
Mod_LoadAliasModel
=================
*/
void Mod_LoadAliasModel (model_t *mod, void *buffer, int bytes)
{
    int					i;
    mdl_t				*pmodel, *pinmodel;
    stvert_t			*pstverts, *pinstverts;
    aliashdr_t			*pheader;
    mtriangle_t			*ptri;
    dtriangle_t			*pintriangles;
    int					version, numframes, numskins;
    int					size;
    daliasframetype_t	*pframetype;
    daliasskintype_t	*pskintype;
    maliasskindesc_t	*pskindesc;
    int					skinsize;
    int					start, end, total;
    void *copy;

    total=AW_AliasStageBytes(buffer,bytes);
    if(!total)Sys_Error("Mod_LoadAliasModel: malformed or truncated alias");
    aw_alias_stage=total<=AW_ALIAS_STAGING_LIMIT?malloc(total):NULL;
    aw_alias_stage_used=0;aw_alias_stage_size=total;
    start = Hunk_LowMark ();

    pinmodel = (mdl_t *)buffer;

    version = LittleLong (pinmodel->version);
    if (version != ALIAS_VERSION)
        Sys_Error ("%s has wrong version number (%ld should be %ld)",
                 mod->name, version, ALIAS_VERSION);

//
// allocate space for a working header, plus all the data except the frames,
// skin and group info
//
    size =	sizeof (aliashdr_t) + (LittleLong (pinmodel->numframes) - 1) *
             sizeof (pheader->frames[0]) +
            sizeof (mdl_t) +
            LittleLong (pinmodel->numverts) * sizeof (stvert_t) +
            LittleLong (pinmodel->numtris) * sizeof (mtriangle_t);

    pheader = AW_AliasAlloc (size, loadname);
    pmodel = (mdl_t *) ((byte *)&pheader[1] +
            (LittleLong (pinmodel->numframes) - 1) *
             sizeof (pheader->frames[0]));

//	mod->cache.data = pheader;
    mod->flags = LittleLong (pinmodel->flags);

//
// endian-adjust and copy the data, starting with the alias model header
//
    pmodel->boundingradius = LittleFloat (pinmodel->boundingradius);
    pmodel->numskins = LittleLong (pinmodel->numskins);
    pmodel->skinwidth = LittleLong (pinmodel->skinwidth);
    pmodel->skinheight = LittleLong (pinmodel->skinheight);

    if (pmodel->skinheight > MAX_LBM_HEIGHT)
        Sys_Error ("model %s has a skin taller than %ld", mod->name,
                   MAX_LBM_HEIGHT);

    pmodel->numverts = LittleLong (pinmodel->numverts);

    if (pmodel->numverts <= 0)
        Sys_Error ("model %s has no vertices", mod->name);

    if (pmodel->numverts > MAXALIASVERTS)
        Sys_Error ("model %s has too many vertices", mod->name);

    pmodel->numtris = LittleLong (pinmodel->numtris);

    if (pmodel->numtris <= 0)
        Sys_Error ("model %s has no triangles", mod->name);

    pmodel->numframes = LittleLong (pinmodel->numframes);
    pmodel->size = LittleFloat (pinmodel->size) * ALIAS_BASE_SIZE_RATIO;
    mod->synctype = LittleLong (pinmodel->synctype);
    mod->numframes = pmodel->numframes;

    for (i=0 ; i<3 ; i++)
    {
        pmodel->scale[i] = LittleFloat (pinmodel->scale[i]);
        pmodel->scale_origin[i] = LittleFloat (pinmodel->scale_origin[i]);
        pmodel->eyeposition[i] = LittleFloat (pinmodel->eyeposition[i]);
    }

    numskins = pmodel->numskins;
    numframes = pmodel->numframes;

    if (pmodel->skinwidth & 0x03)
        Sys_Error ("Mod_LoadAliasModel: skinwidth not multiple of 4");

    pheader->model = (byte *)pmodel - (byte *)pheader;

//
// load the skins
//
    skinsize = pmodel->skinheight * pmodel->skinwidth;

    if (numskins < 1)
        Sys_Error ("Mod_LoadAliasModel: Invalid # of skins: %ld\n", numskins);

    pskintype = (daliasskintype_t *)&pinmodel[1];

    pskindesc = AW_AliasAlloc (numskins * sizeof (maliasskindesc_t),
                                loadname);

    pheader->skindesc = (byte *)pskindesc - (byte *)pheader;

    for (i=0 ; i<numskins ; i++)
    {
        aliasskintype_t	skintype;

        skintype = LittleLong (pskintype->type);
        pskindesc[i].type = skintype;

        if (skintype == ALIAS_SKIN_SINGLE)
        {
            pskintype = (daliasskintype_t *)
                    Mod_LoadAliasSkin (pskintype + 1,
                                       &pskindesc[i].skin,
                                       skinsize, pheader);
        }
        else
        {
            pskintype = (daliasskintype_t *)
                    Mod_LoadAliasSkinGroup (pskintype + 1,
                                            &pskindesc[i].skin,
                                            skinsize, pheader);
        }
    }

//
// set base s and t vertices
//
    pstverts = (stvert_t *)&pmodel[1];
    pinstverts = (stvert_t *)pskintype;

    pheader->stverts = (byte *)pstverts - (byte *)pheader;

    for (i=0 ; i<pmodel->numverts ; i++)
    {
        pstverts[i].onseam = LittleLong (pinstverts[i].onseam);
    // put s and t in 16.16 format
        pstverts[i].s = LittleLong (pinstverts[i].s) << 16;
        pstverts[i].t = LittleLong (pinstverts[i].t) << 16;
    }

//
// set up the triangles
//
    ptri = (mtriangle_t *)&pstverts[pmodel->numverts];
    pintriangles = (dtriangle_t *)&pinstverts[pmodel->numverts];

    pheader->triangles = (byte *)ptri - (byte *)pheader;

    for (i=0 ; i<pmodel->numtris ; i++)
    {
        int		j;

        ptri[i].facesfront = LittleLong (pintriangles[i].facesfront);

        for (j=0 ; j<3 ; j++)
        {
            ptri[i].vertindex[j] =
                    LittleLong (pintriangles[i].vertindex[j]);
        }
    }

//
// load the frames
//
    if (numframes < 1)
        Sys_Error ("Mod_LoadAliasModel: Invalid # of frames: %ld\n", numframes);

    pframetype = (daliasframetype_t *)&pintriangles[pmodel->numtris];

    for (i=0 ; i<numframes ; i++)
    {
        aliasframetype_t	frametype;

        frametype = LittleLong (pframetype->type);
        pheader->frames[i].type = frametype;

        if (frametype == ALIAS_SINGLE)
        {
            pframetype = (daliasframetype_t *)
                    Mod_LoadAliasFrame (pframetype + 1,
                                        &pheader->frames[i].frame,
                                        pmodel->numverts,
                                        &pheader->frames[i].bboxmin,
                                        &pheader->frames[i].bboxmax,
                                        pheader, pheader->frames[i].name);
        }
        else
        {
            pframetype = (daliasframetype_t *)
                    Mod_LoadAliasGroup (pframetype + 1,
                                        &pheader->frames[i].frame,
                                        pmodel->numverts,
                                        &pheader->frames[i].bboxmin,
                                        &pheader->frames[i].bboxmax,
                                        pheader, pheader->frames[i].name);
        }
    }

    mod->type = mod_alias;

// FIXME: do this right
    /* The quantization domain encloses every frame, including head morphs.
     * Keep this small bound resident even when the alias payload is evicted. */
    for (i=0 ; i<3 ; i++) {
        mod->mins[i] = pmodel->scale_origin[i];
        mod->maxs[i] = pmodel->scale_origin[i] + pmodel->scale[i]*255;
    }
    mod->radius = RadiusFromBounds(mod->mins, mod->maxs) + 0.125f;

//
// move the complete, relocatable alias model to the cache
//
    if(aw_alias_stage){
        if(aw_alias_stage_used!=aw_alias_stage_size)Sys_Error("Alias staging size mismatch");
        total=aw_alias_stage_used;copy=aw_alias_stage;
        aw_alias_stage=NULL;aw_alias_stage_used=aw_alias_stage_size=0;
    }else{
        end = Hunk_LowMark ();
        total = end - start;
        /* Allocation failure/large aliases retain the original hunk path. */
        copy=total<=AW_ALIAS_STAGING_LIMIT?malloc(total):NULL;
        if(copy){memcpy(copy,pheader,total);Hunk_FreeToLowMark(start);}
    }
    Cache_Alloc (&mod->cache, total, loadname);
    if(mod->cache.data)memcpy(mod->cache.data,copy?copy:(void *)pheader,total);
    if(copy)free(copy);else Hunk_FreeToLowMark(start);

}

//=============================================================================

/*
=================
Mod_LoadSpriteFrame
=================
*/
void * Mod_LoadSpriteFrame (void * pin, mspriteframe_t **ppframe)
{
    dspriteframe_t		*pinframe;
    mspriteframe_t		*pspriteframe;
    int					i, width, height, size, origin[2];
    unsigned short		*ppixout;
    byte				*ppixin;

    pinframe = (dspriteframe_t *)pin;

    width = LittleLong (pinframe->width);
    height = LittleLong (pinframe->height);
    size = width * height;

    pspriteframe = Hunk_AllocName (sizeof (mspriteframe_t) + size*r_pixbytes,
                                   loadname);

    Q_memset (pspriteframe, 0, sizeof (mspriteframe_t) + size);
    *ppframe = pspriteframe;

    pspriteframe->width = width;
    pspriteframe->height = height;
    origin[0] = LittleLong (pinframe->origin[0]);
    origin[1] = LittleLong (pinframe->origin[1]);

    pspriteframe->up = origin[1];
    pspriteframe->down = origin[1] - height;
    pspriteframe->left = origin[0];
    pspriteframe->right = width + origin[0];

    if (r_pixbytes == 1)
    {
        Q_memcpy (&pspriteframe->pixels[0], (byte *)(pinframe + 1), size);
    }
    else if (r_pixbytes == 2)
    {
        ppixin = (byte *)(pinframe + 1);
        ppixout = (unsigned short *)&pspriteframe->pixels[0];

        for (i=0 ; i<size ; i++)
            ppixout[i] = d_8to16table[ppixin[i]];
    }
    else
    {
        Sys_Error ("Mod_LoadSpriteFrame: driver set invalid r_pixbytes: %ld\n",
                 r_pixbytes);
    }

    return (void *)((byte *)pinframe + sizeof (dspriteframe_t) + size);
}


/*
=================
Mod_LoadSpriteGroup
=================
*/
void * Mod_LoadSpriteGroup (void * pin, mspriteframe_t **ppframe)
{
    dspritegroup_t		*pingroup;
    mspritegroup_t		*pspritegroup;
    int					i, numframes;
    dspriteinterval_t	*pin_intervals;
    float				*poutintervals;
    void				*ptemp;

    pingroup = (dspritegroup_t *)pin;

    numframes = LittleLong (pingroup->numframes);

    pspritegroup = Hunk_AllocName (sizeof (mspritegroup_t) +
                (numframes - 1) * sizeof (pspritegroup->frames[0]), loadname);

    pspritegroup->numframes = numframes;

    *ppframe = (mspriteframe_t *)pspritegroup;

    pin_intervals = (dspriteinterval_t *)(pingroup + 1);

    poutintervals = Hunk_AllocName (numframes * sizeof (float), loadname);

    pspritegroup->intervals = poutintervals;

    for (i=0 ; i<numframes ; i++)
    {
        *poutintervals = LittleFloat (pin_intervals->interval);
        if (*poutintervals <= 0.0)
            Sys_Error ("Mod_LoadSpriteGroup: interval<=0");

        poutintervals++;
        pin_intervals++;
    }

    ptemp = (void *)pin_intervals;

    for (i=0 ; i<numframes ; i++)
    {
        ptemp = Mod_LoadSpriteFrame (ptemp, &pspritegroup->frames[i]);
    }

    return ptemp;
}


/*
=================
Mod_LoadSpriteModel
=================
*/
static float Mod_SpriteFrameRadius(const mspriteframe_t *frame)
{
    float x = (fabs(frame->left) > fabs(frame->right) ? fabs(frame->left) : fabs(frame->right));
    float y = (fabs(frame->up) > fabs(frame->down) ? fabs(frame->up) : fabs(frame->down));
    return sqrt(x*x + y*y);
}

/* The small source readers keep the PAK member's base/end as hard bounds.
 * No decoded sprite input buffer is assembled alongside resident pixels. */
#define AW_SPRITE_PIXEL_CHUNK 2048

static int AW_SpriteRead(FILE *file,long base,long end,void *data,size_t bytes)
{
    long position=ftell(file);
    if(position<base || position>end || bytes>(size_t)(end-position))return 0;
    return AW_LoadRead((byte *)data,bytes,file)==bytes;
}

/* Where a sprite's blocks go: the Hunk (Mod_ForName), or a caller's allocator
 * (Mod_LoadSpriteInto: CHIM's streamed statics decode into its zone). */
static void *(*aw_sprite_alloc)(void *context,int size);
static void *aw_sprite_context;
static void *AW_SpriteAlloc(int size)
{
    void *data;
    if(!aw_sprite_alloc)return Hunk_AllocName(size,loadname);
    data=aw_sprite_alloc(aw_sprite_context,size);
    if(!data)Sys_Error("Mod_LoadSpriteInto: %s: allocator out of room",loadmodel?loadmodel->name:"?");
    return data;
}
static int AW_SpriteError(FILE *file,model_t *mod,const char *reason)
{
    if(file)fclose(file);
    Sys_Error("Mod_LoadSpriteModel: %s: %s",reason,mod->name);
    return 0;
}

static mspriteframe_t *AW_StreamSpriteFrame(FILE *file,long base,long end,model_t *mod)
{
    dspriteframe_t disk;
    mspriteframe_t *frame;
    unsigned short *out16;
    byte chunk[AW_SPRITE_PIXEL_CHUNK];
    size_t pixels,allocation,done,take,i;
    long position;
    int width,height,origin[2],bpp;
    if(!AW_SpriteRead(file,base,end,&disk,sizeof(disk)))
        {AW_SpriteError(file,mod,"truncated frame header");return NULL;}
    width=LittleLong(disk.width);height=LittleLong(disk.height);
    if(width<1 || height<1 || (size_t)width>(size_t)INT_MAX/(size_t)height)
        {AW_SpriteError(file,mod,"invalid frame dimensions");return NULL;}
    pixels=(size_t)width*(size_t)height;
    bpp=r_pixbytes;
    if((bpp!=1 && bpp!=2) || pixels>(size_t)INT_MAX/(size_t)bpp ||
       pixels*bpp>INT_MAX-sizeof(*frame))
        {AW_SpriteError(file,mod,"frame allocation overflow or invalid pixel depth");return NULL;}
    position=ftell(file);
    if(position<base || position>end || pixels>(size_t)(end-position))
        {AW_SpriteError(file,mod,"truncated frame pixels");return NULL;}
    allocation=sizeof(*frame)+pixels*bpp;
    frame=AW_SpriteAlloc((int)allocation);
    Q_memset(frame,0,(int)(sizeof(*frame)+pixels));
    origin[0]=LittleLong(disk.origin[0]);origin[1]=LittleLong(disk.origin[1]);
    if(origin[0]>INT_MAX-width || origin[1]<INT_MIN+height)
        {AW_SpriteError(file,mod,"frame origin bounds overflow");return NULL;}
    frame->width=width;frame->height=height;
    frame->up=origin[1];frame->down=origin[1]-height;
    frame->left=origin[0];frame->right=width+origin[0];
    if(bpp==1){
        if(!AW_SpriteRead(file,base,end,frame->pixels,pixels))
            {AW_SpriteError(file,mod,"short frame pixel read");return NULL;}
    }else{
        out16=(unsigned short *)frame->pixels;
        for(done=0;done<pixels;done+=take){
            take=pixels-done;if(take>sizeof(chunk))take=sizeof(chunk);
            if(!AW_SpriteRead(file,base,end,chunk,take))
                {AW_SpriteError(file,mod,"short frame pixel read");return NULL;}
            for(i=0;i<take;i++)out16[done+i]=d_8to16table[chunk[i]];
        }
    }
    return frame;
}

/* Return zero only for a non-IDSP member so the established generic loader can
 * retain its existing fallback/search behavior. A recognized but malformed
 * sprite is a load error, after closing the exact loose-file or PAK handle. */
int Mod_TryStreamSprite(model_t *mod)
{
    FILE *file=NULL;
    dsprite_t header;
    msprite_t *sprite;
    dspriteframetype_t type_disk;
    dspritegroup_t group_disk;
    dspriteinterval_t interval_disk;
    int filebytes,ident,numframes,i,j,frametype,group_frames,size;
    long base,end,position;
    size_t group_size,interval_bytes;
    filebytes=COM_FOpenFile(mod->name,&file);
    if(!file)return 0;
    if(filebytes<4){fclose(file);return 0;}
    base=ftell(file);
    if(base<0 || (long)filebytes>LONG_MAX-base){fclose(file);return 0;}
    end=base+(long)filebytes;
    if(!AW_SpriteRead(file,base,end,&ident,sizeof(ident))){fclose(file);return 0;}
    if(LittleLong(ident)!=IDSPRITEHEADER){fclose(file);return 0;}
    header.ident=ident;
    if(filebytes<(int)sizeof(header) ||
       !AW_SpriteRead(file,base,end,(byte *)&header+sizeof(ident),sizeof(header)-sizeof(ident)))
        return AW_SpriteError(file,mod,"truncated sprite header");
    if(LittleLong(header.version)!=SPRITE_VERSION){
        int version=LittleLong(header.version);fclose(file);file=NULL;
        Sys_Error("%s has wrong version number (%ld should be %ld)",mod->name,version,SPRITE_VERSION);
        return 0;
    }
    numframes=LittleLong(header.numframes);
    if(numframes<1 || numframes>(INT_MAX-(int)sizeof(*sprite))/(int)sizeof(mspriteframedesc_t)+1)
        return AW_SpriteError(file,mod,"invalid frame count");
    if(LittleLong(header.width)<1 || LittleLong(header.height)<1)
        return AW_SpriteError(file,mod,"invalid sprite dimensions");
    if(LittleLong(header.type)<SPR_VP_PARALLEL_UPRIGHT ||
       LittleLong(header.type)>SPR_VP_PARALLEL_ORIENTED ||
       LittleLong(header.synctype)<ST_SYNC || LittleLong(header.synctype)>ST_RAND)
        return AW_SpriteError(file,mod,"invalid sprite header fields");
    position=ftell(file);
    if(position<base || position>end ||
       (size_t)numframes>(size_t)(end-position)/(sizeof(type_disk)+sizeof(dspriteframe_t)+1))
        return AW_SpriteError(file,mod,"frame count exceeds member bounds");

    if(!isfinite(LittleFloat(header.boundingradius)))
        return AW_SpriteError(file,mod,"invalid sprite bounding radius");
    if(!isfinite(LittleFloat(header.beamlength)))
        return AW_SpriteError(file,mod,"invalid sprite beam length");
    COM_FileBase(mod->name,loadname);loadmodel=mod;mod->needload=NL_PRESENT;
    size=sizeof(*sprite)+(numframes-1)*sizeof(mspriteframedesc_t);
    sprite=AW_SpriteAlloc(size);mod->cache.data=sprite;
    sprite->type=LittleLong(header.type);sprite->maxwidth=LittleLong(header.width);
    sprite->maxheight=LittleLong(header.height);sprite->beamlength=LittleFloat(header.beamlength);
    sprite->numframes=numframes;mod->synctype=LittleLong(header.synctype);
    mod->mins[0]=mod->mins[1]=-sprite->maxwidth/2;
    mod->maxs[0]=mod->maxs[1]=sprite->maxwidth/2;
    mod->mins[2]=-sprite->maxheight/2;mod->maxs[2]=sprite->maxheight/2;
    mod->numframes=numframes;mod->flags=0;
    for(i=0;i<numframes;i++){
        int raw_type;
        if(!AW_SpriteRead(file,base,end,&type_disk,sizeof(type_disk)))
            return AW_SpriteError(file,mod,"truncated frame type");
        raw_type=LittleLong(type_disk.type);frametype=raw_type;
        if(frametype!=SPR_SINGLE && frametype!=SPR_GROUP)
            return AW_SpriteError(file,mod,"invalid frame type");
        sprite->frames[i].type=frametype;
        if(frametype==SPR_SINGLE){
            sprite->frames[i].frameptr=AW_StreamSpriteFrame(file,base,end,mod);
            if(!sprite->frames[i].frameptr)return 0;
            continue;
        }
        if(!AW_SpriteRead(file,base,end,&group_disk,sizeof(group_disk)))
            return AW_SpriteError(file,mod,"truncated group header");
        group_frames=LittleLong(group_disk.numframes);position=ftell(file);
        if(group_frames<1 || position<base || position>end ||
           (size_t)group_frames>(size_t)(end-position)/
             (sizeof(interval_disk)+sizeof(dspriteframe_t)+1) ||
           (size_t)(group_frames-1)>(INT_MAX-sizeof(mspritegroup_t))/sizeof(mspriteframe_t * ) ||
           (size_t)group_frames>INT_MAX/sizeof(float))
            return AW_SpriteError(file,mod,"invalid or truncated group frame count");
        group_size=sizeof(mspritegroup_t)+(size_t)(group_frames-1)*sizeof(mspriteframe_t *);
        interval_bytes=(size_t)group_frames*sizeof(float);
        {
            mspritegroup_t *group=AW_SpriteAlloc((int)group_size);
            float *intervals=AW_SpriteAlloc((int)interval_bytes);
            group->numframes=group_frames;group->intervals=intervals;
            sprite->frames[i].frameptr=(mspriteframe_t *)group;
            for(j=0;j<group_frames;j++){
                float value;
                if(!AW_SpriteRead(file,base,end,&interval_disk,sizeof(interval_disk)))
                    return AW_SpriteError(file,mod,"truncated group intervals");
                value=LittleFloat(interval_disk.interval);
                if(!isfinite(value) || value<=0.0f)
                    return AW_SpriteError(file,mod,"invalid group interval");
                intervals[j]=value;
            }
            for(j=0;j<group_frames;j++){
                group->frames[j]=AW_StreamSpriteFrame(file,base,end,mod);
                if(!group->frames[j])return 0;
            }
        }
    }
    position=ftell(file);
    if(position!=end)return AW_SpriteError(file,mod,"trailing or unread sprite bytes");
    fclose(file);file=NULL;
    mod->radius=0;
    for(i=0;i<numframes;i++){
        if(sprite->frames[i].type==SPR_SINGLE){
            float radius=Mod_SpriteFrameRadius(sprite->frames[i].frameptr);
            if(radius>mod->radius)mod->radius=radius;
        }else{
            mspritegroup_t *group=(mspritegroup_t *)sprite->frames[i].frameptr;
            for(j=0;j<group->numframes;j++){
                float radius=Mod_SpriteFrameRadius(group->frames[j]);
                if(radius>mod->radius)mod->radius=radius;
            }
        }
    }
    if(!isfinite(mod->radius) || mod->radius<=0)
        return AW_SpriteError(file,mod,"invalid sprite frame radius");
    for(i=0;i<3;i++){mod->mins[i]=-mod->radius;mod->maxs[i]=mod->radius;}
    mod->type=mod_sprite;
    return 1;
}
void Mod_LoadSpriteModel (model_t *mod, void *buffer)
{
    int					i;
    int					version;
    dsprite_t			*pin;
    msprite_t			*psprite;
    int					numframes;
    int					size;
    dspriteframetype_t	*pframetype;

    pin = (dsprite_t *)buffer;

    version = LittleLong (pin->version);
    if (version != SPRITE_VERSION)
        Sys_Error ("%s has wrong version number "
                 "(%ld should be %ld)", mod->name, version, SPRITE_VERSION);

    numframes = LittleLong (pin->numframes);

    size = sizeof (msprite_t) +	(numframes - 1) * sizeof (psprite->frames);

    psprite = Hunk_AllocName (size, loadname);

    mod->cache.data = psprite;

    psprite->type = LittleLong (pin->type);
    psprite->maxwidth = LittleLong (pin->width);
    psprite->maxheight = LittleLong (pin->height);
    psprite->beamlength = LittleFloat (pin->beamlength);
    mod->synctype = LittleLong (pin->synctype);
    psprite->numframes = numframes;

    mod->mins[0] = mod->mins[1] = -psprite->maxwidth/2;
    mod->maxs[0] = mod->maxs[1] = psprite->maxwidth/2;
    mod->mins[2] = -psprite->maxheight/2;
    mod->maxs[2] = psprite->maxheight/2;

//
// load the frames
//
    if (numframes < 1)
        Sys_Error ("Mod_LoadSpriteModel: Invalid # of frames: %ld\n", numframes);

    mod->numframes = numframes;
    mod->flags = 0;

    pframetype = (dspriteframetype_t *)(pin + 1);

    for (i=0 ; i<numframes ; i++)
    {
        spriteframetype_t	frametype;

        frametype = LittleLong (pframetype->type);
        psprite->frames[i].type = frametype;

        if (frametype == SPR_SINGLE)
        {
            pframetype = (dspriteframetype_t *)
                    Mod_LoadSpriteFrame (pframetype + 1,
                                         &psprite->frames[i].frameptr);
        }
        else
        {
            pframetype = (dspriteframetype_t *)
                    Mod_LoadSpriteGroup (pframetype + 1,
                                         &psprite->frames[i].frameptr);
        }
    }

    mod->radius = 0;
    for (i = 0; i < numframes; i++) {
        if (psprite->frames[i].type == SPR_SINGLE) {
            float radius = Mod_SpriteFrameRadius(psprite->frames[i].frameptr);
            if (radius > mod->radius) mod->radius = radius;
        } else {
            mspritegroup_t *group = (mspritegroup_t *)psprite->frames[i].frameptr;
            int j;
            for (j = 0; j < group->numframes; j++) {
                float radius = Mod_SpriteFrameRadius(group->frames[j]);
                if (radius > mod->radius) mod->radius = radius;
            }
        }
    }
    if (!isfinite(mod->radius) || mod->radius <= 0)
        Sys_Error("Invalid sprite frame radius: %s", mod->name);
    for (i = 0; i < 3; i++) {
        mod->mins[i] = -mod->radius;
        mod->maxs[i] = mod->radius;
    }
    mod->type = mod_sprite;
}

//=============================================================================

/*
================
Mod_Print
================
*/
void Mod_Print (void)
{
    int		i;
    model_t	*mod;

    Con_Printf ("Cached models:\n");
    for (i=0, mod=mod_known ; i < mod_numknown ; i++, mod++)
    {
        Con_Printf ("%8p : %s",mod->cache.data, mod->name);
        if (mod->needload & NL_UNREFERENCED)
            Con_Printf (" (!R)");
        if (mod->needload & NL_NEEDS_LOADED)
            Con_Printf (" (!P)");
        Con_Printf ("\n");
    }
}

/* A sprite decoded through a caller's allocator instead of the Hunk (CHIM's
 * streamed statics, chim/chim_statics.c). The allocator must not fail for
 * the sizes it was sized for (Sys_Error otherwise, like a bad sprite). The
 * model is not in mod_known. Returns 1 when loaded, 0 when the file is
 * missing or not a sprite. */
int Mod_LoadSpriteInto(model_t *mod,void *(*alloc)(void *context,int size),void *context)
{
    int ok;
    aw_sprite_alloc=alloc;aw_sprite_context=context;
    ok=Mod_TryStreamSprite(mod);
    aw_sprite_alloc=NULL;aw_sprite_context=NULL;
    if(ok)mod->type=mod_sprite;
    return ok;
}
