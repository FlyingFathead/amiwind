/* SAS/C PPC inline stubs for WritePixelArray8(), GetMsg() and
   ReplyMsg() with optimised cache modes. */

#if defined(__PPC__) && defined(__SASC)

#define	LoadRGB4(vp, colors, count) \
  _MyLoadRGB4(GRAPHICS_BASE_NAME, vp, colors, count)
static __inline void _MyLoadRGB4 (void *GfxBase, struct ViewPort *vp,
                                UWORD *colors, long count)
{
  struct Caos MyCaos;
  MyCaos.M68kCacheMode	= IF_CACHEFLUSHNO;
  MyCaos.PPCCacheMode	= IF_CACHEFLUSHAREA;
  MyCaos.PPCStart	= (APTR)colors;
  MyCaos.PPCLength	= (ULONG)((count + 2) << 2);
  MyCaos.a0		= (ULONG)vp;
  MyCaos.a1		= (ULONG)colors;
  MyCaos.d0		= (ULONG)count;
  MyCaos.caos_Un.Offset	= (-192);
  MyCaos.a6		= (ULONG)GfxBase;	
  PPCCallOS (&MyCaos);
}

#define	WritePixelArray8(rp, xstart, ystart, xstop, ystop, array, temprp) \
  _MyWritePixelArray8(GRAPHICS_BASE_NAME, rp, xstart, ystart, xstop, ystop, array, temprp)
static __inline LONG _MyWritePixelArray8 (void *GfxBase, struct RastPort *rp,
                                          unsigned long xstart,
                                          unsigned long ystart,
                                          unsigned long xstop,
                                          unsigned long ystop, UBYTE *array,
                                          struct RastPort *temprp)
{
  struct Caos MyCaos;
  MyCaos.M68kCacheMode	= IF_CACHEFLUSHNO;
  MyCaos.PPCCacheMode	= IF_CACHEFLUSHAREA;
  MyCaos.PPCStart	= &array[vid.width * ystart];
  MyCaos.PPCLength	= vid.width * (ystop - ystart + 1);
  MyCaos.a0		= (ULONG)rp;
  MyCaos.d0		= (ULONG)xstart;
  MyCaos.d1		= (ULONG)ystart;
  MyCaos.d2		= (ULONG)xstop;
  MyCaos.d3		= (ULONG)ystop;
  MyCaos.a2		= (ULONG)array;
  MyCaos.a1		= (ULONG)temprp;
  MyCaos.caos_Un.Offset	= (-786);
  MyCaos.a6		= (ULONG)GfxBase;	
  return ((LONG)PPCCallOS (&MyCaos));
}

//#define	GetMsg(port) _MyGetMsg(EXEC_BASE_NAME, port)
//static __inline struct Message *_MyGetMsg (void *SysBase, struct MsgPort *port)
//{
//  struct Caos MyCaos;
//  MyCaos.M68kCacheMode	= IF_CACHEFLUSHALL;
//  MyCaos.PPCCacheMode	= IF_CACHEFLUSHNO;
//  MyCaos.a0		= (ULONG)port;
//  MyCaos.caos_Un.Offset	= (-372);
//  MyCaos.a6		= (ULONG)SysBase;
//  return ((struct Message *)PPCCallOS (&MyCaos));
//}

#define	ReplyMsg(message) _MyReplyMsg(EXEC_BASE_NAME, message)
static __inline void _MyReplyMsg (void *SysBase, struct Message *message)
{
  struct Caos MyCaos;
  MyCaos.M68kCacheMode	= IF_CACHEFLUSHNO;
  MyCaos.PPCCacheMode	= IF_CACHEFLUSHNO;
  MyCaos.a1		= (ULONG)message;
  MyCaos.caos_Un.Offset	= (-378);
  MyCaos.a6		= (ULONG)SysBase;
  PPCCallOS(&MyCaos);
}

#define UnLockBitMap(handle) _MyUnLockBitMap(CYBERGFX_BASE_NAME, handle)
static __inline void _MyUnLockBitMap (void *CyberGfxBase, APTR handle)
{
  struct Caos MyCaos;
  MyCaos.M68kCacheMode	= IF_CACHEFLUSHNO;
  MyCaos.PPCCacheMode	= IF_CACHEFLUSHNO;
  MyCaos.a0		= (ULONG)handle;
  MyCaos.caos_Un.Offset	= (-0xae);
  MyCaos.a6		= (ULONG)CyberGfxBase;
  PPCCallOS(&MyCaos);
}

#endif  /* __PPC__ && __SASC */
