/* Pragmas for Amiga PPC interface to cdplayer.library */

#ifndef _PPCPRAGMA_CDPLAYER_H
#define _PPCPRAGMA_CDPLAYER_H
#ifdef __GNUC__
#ifndef _PPCINLINE__ASL_H
#include <ppcinline/asl.h>
#endif
#else

#ifndef POWERUP_PPCLIB_INTERFACE_H
#include <powerup/ppclib/interface.h>
#endif

#ifndef POWERUP_GCCLIB_PROTOS_H
#include <powerup/gcclib/powerup_protos.h>
#endif

#ifndef NO_PPCINLINE_STDARG
#define NO_PPCINLINE_STDARG
#endif/* SAS C PPC inlines */

#ifndef CDPLAYER_BASE_NAME
#define CDPLAYER_BASE_NAME CDPlayerBase
#endif /* !CDPLAYER_BASE_NAME */

#define CDEject(io_ptr) _CDEject(CDPLAYER_BASE_NAME,io_ptr)

static __inline BYTE _CDEject (void *CD_PLAYER_BASE, struct IOStdReq *io_ptr)
{
struct Caos	MyCaos;
	MyCaos.M68kCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.M68kStart	=	NULL;
//	MyCaos.M68kSize		=	0;
	MyCaos.PPCCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.PPCStart		=	NULL;
//	MyCaos.PPCSize		=	0;
	MyCaos.a5		=(ULONG) io_ptr;
	MyCaos.caos_Un.Offset	=	(-30);
	MyCaos.a6		=(ULONG) CD_PLAYER_BASE;
	return((BYTE)PPCCallOS(&MyCaos));
}

#define CDPlay(starttrack,endtrack,io_ptr) _CDPlay(CDPLAYER_BASE_NAME,starttrack,endtrack,io_ptr)

static __inline BYTE _CDPlay (void *CD_PLAYER_BASE, UBYTE starttrack, UBYTE endtrack, struct IOStdReq *io_ptr)
{
struct Caos	MyCaos;
	MyCaos.M68kCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.M68kStart	=	NULL;
//	MyCaos.M68kSize		=	0;
	MyCaos.PPCCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.PPCStart		=	NULL;
//	MyCaos.PPCSize		=	0;
	MyCaos.a0		=(ULONG) starttrack;
	MyCaos.a1		=(ULONG) endtrack;
	MyCaos.a5		=(ULONG) io_ptr;
	MyCaos.caos_Un.Offset	=	(-36);
	MyCaos.a6		=(ULONG) CD_PLAYER_BASE;	
	return((BYTE)PPCCallOS(&MyCaos));
}

#define CDResume(mode,io_ptr) _CDResume(CDPLAYER_BASE_NAME,mode,io_ptr)

static __inline BYTE _CDResume (void *CD_PLAYER_BASE, BOOL mode, struct IOStdReq *io_ptr)
{
struct Caos	MyCaos;
	MyCaos.M68kCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.M68kStart	=	NULL;
//	MyCaos.M68kSize		=	0;
	MyCaos.PPCCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.PPCStart		=	NULL;
//	MyCaos.PPCSize		=	0;
	MyCaos.a0		=(ULONG) mode;
	MyCaos.a5		=(ULONG) io_ptr;
	MyCaos.caos_Un.Offset	=	(-42);
	MyCaos.a6		=(ULONG) CD_PLAYER_BASE;	
	return((BYTE)PPCCallOS(&MyCaos));
}

#define CDStop(io_ptr) _CDStop(CDPLAYER_BASE_NAME,io_ptr)

static __inline BYTE _CDStop (void *CD_PLAYER_BASE, struct IOStdReq *io_ptr)
{
struct Caos	MyCaos;
	MyCaos.M68kCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.M68kStart	=	NULL;
//	MyCaos.M68kSize		=	0;
	MyCaos.PPCCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.PPCStart		=	NULL;
//	MyCaos.PPCSize		=	0;
	MyCaos.a5		=(ULONG) io_ptr;
	MyCaos.caos_Un.Offset	=	(-48);
	MyCaos.a6		=(ULONG) CD_PLAYER_BASE;	
	return((BYTE)PPCCallOS(&MyCaos));
}

#define CDJump(blocks,io_ptr) _CDJump(CDPLAYER_BASE_NAME,blocks,io_ptr)

static __inline BYTE _CDJump (void *CD_PLAYER_BASE, ULONG blocks, struct IOStdReq *io_ptr)
{
struct Caos	MyCaos;
	MyCaos.M68kCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.M68kStart	=	NULL;
//	MyCaos.M68kSize		=	0;
	MyCaos.PPCCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.PPCStart		=	NULL;
//	MyCaos.PPCSize		=	0;
	MyCaos.a0		=(ULONG) blocks;
	MyCaos.a5		=(ULONG) io_ptr;
	MyCaos.caos_Un.Offset	=	(-54);
	MyCaos.a6		=(ULONG) CD_PLAYER_BASE;	
	return((BYTE)PPCCallOS(&MyCaos));
}

#define CDActive(io_ptr) _CDActive(CDPLAYER_BASE_NAME,io_ptr)

static __inline BOOL _CDActive (void *CD_PLAYER_BASE, struct IOStdReq *io_ptr)
{
struct Caos	MyCaos;
	MyCaos.M68kCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.M68kStart	=	NULL;
//	MyCaos.M68kSize		=	0;
	MyCaos.PPCCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.PPCStart		=	NULL;
//	MyCaos.PPCSize		=	0;
	MyCaos.a5		=(ULONG) io_ptr;
	MyCaos.caos_Un.Offset	=	(-60);
	MyCaos.a6		=(ULONG) CD_PLAYER_BASE;	
	return((BYTE)PPCCallOS(&MyCaos));
}

#define CDCurrentTitle(io_ptr) _CDCurrentTitle(CDPLAYER_BASE_NAME,io_ptr)

static __inline ULONG _CDCurrentTitle (void *CD_PLAYER_BASE, struct IOStdReq *io_ptr)
{
struct Caos	MyCaos;
	MyCaos.M68kCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.M68kStart	=	NULL;
//	MyCaos.M68kSize		=	0;
	MyCaos.PPCCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.PPCStart		=	NULL;
//	MyCaos.PPCSize		=	0;
	MyCaos.a5		=(ULONG) io_ptr;
	MyCaos.caos_Un.Offset	=	(-66);
	MyCaos.a6		=(ULONG) CD_PLAYER_BASE;	
	return((ULONG)PPCCallOS(&MyCaos));
}

#define CDTitleTime(cd_time,io_ptr) _CDTitleTime(CDPLAYER_BASE_NAME,cd_time,io_ptr)

static __inline BYTE _CDTitleTime (void *CD_PLAYER_BASE, struct CD_Time *cd_time, struct IOStdReq *io_ptr)
{
struct Caos	MyCaos;
	MyCaos.M68kCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.M68kStart	=	NULL;
//	MyCaos.M68kSize		=	0;
	MyCaos.PPCCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.PPCStart		=	NULL;
//	MyCaos.PPCSize		=	0;
	MyCaos.a0		=(ULONG) cd_time;
	MyCaos.a5		=(ULONG) io_ptr;
	MyCaos.caos_Un.Offset	=	(-72);
	MyCaos.a6		=(ULONG) CD_PLAYER_BASE;	
	return((BYTE)PPCCallOS(&MyCaos));
}

#define CDGetVolume(cd_volume,io_ptr) _CDGetVolume(CDPLAYER_BASE_NAME,cd_volume,io_ptr)

static __inline BYTE _CDGetVolume (void *CD_PLAYER_BASE, struct CD_Volume *cd_volume, struct IOStdReq *io_ptr)
{
struct Caos	MyCaos;
	MyCaos.M68kCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.M68kStart	=	NULL;
//	MyCaos.M68kSize		=	0;
	MyCaos.PPCCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.PPCStart		=	NULL;
//	MyCaos.PPCSize		=	0;
	MyCaos.a0		=(ULONG) cd_volume;
	MyCaos.a5		=(ULONG) io_ptr;
	MyCaos.caos_Un.Offset	=	(-78);
	MyCaos.a6		=(ULONG) CD_PLAYER_BASE;	
	return((BYTE)PPCCallOS(&MyCaos));
}

#define CDSetVolume(cd_volume,io_ptr) _CDSetVolume(CDPLAYER_BASE_NAME,cd_volume,io_ptr)

static __inline BYTE _CDSetVolume (void *CD_PLAYER_BASE, struct CD_Volume *cd_volume, struct IOStdReq *io_ptr)
{
struct Caos	MyCaos;
	MyCaos.M68kCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.M68kStart	=	NULL;
//	MyCaos.M68kSize		=	0;
	MyCaos.PPCCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.PPCStart		=	NULL;
//	MyCaos.PPCSize		=	0;
	MyCaos.a0		=(ULONG) cd_volume;
	MyCaos.a5		=(ULONG) io_ptr;
	MyCaos.caos_Un.Offset	=	(-84);
	MyCaos.a6		=(ULONG) CD_PLAYER_BASE;	
	return((BYTE)PPCCallOS(&MyCaos));
}

#define CDReadTOC(toc,io_ptr) _CDReadTOC(CDPLAYER_BASE_NAME,toc,io_ptr)

static __inline BYTE _CDReadTOC (void *CD_PLAYER_BASE, struct CD_TOC *toc, struct IOStdReq *io_ptr)
{
struct Caos	MyCaos;
	MyCaos.M68kCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.M68kStart	=	NULL;
//	MyCaos.M68kSize		=	0;
	MyCaos.PPCCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.PPCStart		=	NULL;
//	MyCaos.PPCSize		=	0;
	MyCaos.a0		=(ULONG) toc;
	MyCaos.a5		=(ULONG) io_ptr;
	MyCaos.caos_Un.Offset	=	(-90);
	MyCaos.a6		=(ULONG) CD_PLAYER_BASE;	
	return((BYTE)PPCCallOS(&MyCaos));
}

#define CDInfo (cd_info,io_ptr) _CDInfo (CDPLAYER_BASE,cd_info,io_ptr)

static __inline BYTE _CDInfo(void *CD_PLAYER_BASE, struct CD_Info *cd_info, struct IOStdReq *io_ptr)
{
struct Caos	MyCaos;
	MyCaos.M68kCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.M68kStart	=	NULL;
//	MyCaos.M68kSize		=	0;
	MyCaos.PPCCacheMode	=	IF_CACHEFLUSHALL;
//	MyCaos.PPCStart		=	NULL;
//	MyCaos.PPCSize		=	0;
	MyCaos.a0		=(ULONG) cd_info;
	MyCaos.a5		=(ULONG) io_ptr;
	MyCaos.caos_Un.Offset	=	(-96);
	MyCaos.a6		=(ULONG) CD_PLAYER_BASE;	
	return((BYTE)PPCCallOS(&MyCaos));
}

#endif /* SASC Pragmas */
#endif /* !_PPCPRAGMA_CDPLAYER_H */
