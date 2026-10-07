/*
Copyright (C) 2000 Peter McGavin.

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
// vid_amiga.h -- amiga video driver

#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#ifdef __SASC
#include <dos.h>
#endif

#include <exec/exec.h>
#include <dos/dos.h>
#include <clib/alib_protos.h>
#include <graphics/gfx.h>
#include <graphics/gfxbase.h>
#include <graphics/displayinfo.h>
#include <intuition/intuition.h>
#include <utility/tagitem.h>
#include <libraries/asl.h>
#include <cybergraphics/cybergraphics.h>
#include <devices/timer.h>

#if defined(__VBCC__) || (defined(__STORM__) && defined(__PPC__))
#include <clib/exec_protos.h>
#include <clib/dos_protos.h>
#include <clib/graphics_protos.h>
#include <clib/intuition_protos.h>
#include <clib/asl_protos.h>
#include <clib/cybergraphics_protos.h>
#else
#include <proto/exec.h>
#include <proto/dos.h>
#include <proto/graphics.h>
#include <proto/intuition.h>
#include <proto/asl.h>
#ifndef __PPC__
#include <proto/timer.h>
#endif
#include <proto/cybergraphics.h>
#endif

#include "quakedef.h"
#include <graphics/videocontrol.h>
#include "d_local.h"

#if defined(__PPC__) && defined(__SASC)
#include "amiga_ppc_stubs.h"
#endif

#ifdef __PPC__
extern void ppc_c2p_line (int line, int src, struct BitMap *dst, int cnt);
#else
#ifdef __GNUC__
// GCC-compatible C2P stub - will link to assembly implementation
extern void *aw_c2p_reloc(struct BitMap *bitmap );
extern void aw_c2p_deinit(void *c2p );
extern void aw_c2p(void *c2p , struct BitMap *bmp , UBYTE *chunky , ULONG size );
#else
#include "c2p8_040_amlaukka.h"
#endif
#endif

// Mouse globals for NovaCoder's simplified input handling
// Mouse globals now defined in sys_amiga.c
extern int mouseX;
extern int mouseY;
extern qboolean mouse_has_moved;

#define	BASEWIDTH	320
#define	BASEHEIGHT	200

#if 0
 static byte	vid_buffer[BASEWIDTH*BASEHEIGHT];
 static short	zbuffer[BASEWIDTH*BASEHEIGHT];
 /* static byte	surfcache[256*1024]; */
 static byte	surfcache[(BASEWIDTH*BASEHEIGHT/(320*200))*256*1024*2];
#else
 static pixel_t *vid_buffer = NULL;
 static short *zbuffer = NULL;
 static byte *surfcache = NULL;
#endif

unsigned short	d_8to16table[256];
/* unsigned	d_8to24table[256]; */

/**********************************************************************/

#if defined(__STORM__) || defined(__VBCC__)
extern struct GfxBase *GfxBase;
#endif
struct Library *CyberGfxBase = NULL;
struct Library *AslBase = NULL;

static struct Screen *video_screen = NULL;
struct Window *video_window = NULL;  // Non-static so sys_amiga.c can access it
static struct RastPort tmp_rp, rp;
static struct ScreenModeRequester *smr = NULL;
static struct ScreenBuffer *sbuffer[3] = {NULL, NULL, NULL};
static struct ScreenBuffer *nextsbuffer = NULL;
static APTR bitmap_handle = NULL;
static BOOL is_cyber_mode = FALSE;
static BOOL is_native_mode = FALSE;
static BOOL is_directcgx = FALSE;
static BOOL do_fps = FALSE;
static UWORD *emptypointer;
static struct RastPort temprp;
static struct BitMap tmp_bm = {
  0, 0, 0, 0, 0, {NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL}
};

#ifndef __PPC__
struct Device *TimerBase = NULL;  // Changed from Library to Device for GCC NDK compatibility
static struct MsgPort *timermp = NULL;
static struct timerequest *timerio = NULL;
static ULONG timerclosed = TRUE;
ULONG eclocks_per_second; /* EClock frequency in Hz - extern for timer() */

void *c2p[3] = {NULL, NULL, NULL};
void *nextc2p = NULL;
#endif

/**********************************************************************/
void	VID_SetPalette (unsigned char *palette)
{
  int i;
  ULONG v;
  static ULONG colourtable[1+3*256+1];

  colourtable[0] = (256 << 16) + 0;
  for (i = 0; i < 3*256; i++) {
    v = *palette++;
    v += (v << 8);
    v += (v << 16);
    colourtable[i+1] = v;
  }
  colourtable[1 + 3*256] = 0;
  LoadRGB32 (&video_screen->ViewPort, colourtable);
}

/**********************************************************************/
void	VID_ShiftPalette (unsigned char *palette)
{
  VID_SetPalette (palette);
}

/****************************************************************************/
#ifndef __PPC__
#ifdef __GNUC__
// GCC version - regular C function (hook will work without register optimizations)
static ULONG smr_filter (struct Hook *smr_filter_hook,
                         struct ScreenModeRequester *smr,
                         ULONG mode)
#else
static ULONG __saveds __asm smr_filter (register __a0 struct Hook *smr_filter_hook,
                                        register __a2 struct ScreenModeRequester *smr,
                                        register __a1 ULONG mode)
#endif
/* reject modes deeper than depth 8 */
/* (because setting ASLSM_MaxDepth = 8 seems to be insufficient) */
{
  UWORD count;
  struct DimensionInfo dimsinfo;
  void *handle;

  if ((handle = FindDisplayInfo (mode)) != NULL &&
      (count = GetDisplayInfoData (handle, (UBYTE *)&dimsinfo,
                                   sizeof(struct DimensionInfo), DTAG_DIMS,
                                   NULL)) < 66
                                             /* sizeof(struct DimensionInfo) */)
    Sys_Error ("GetDisplayInfoData(Dims) failed");
  return (ULONG)(dimsinfo.MaxDepth == 8);
}
#endif

/**********************************************************************/
void	VID_Init (unsigned char *palette)
{
  int mode, width, height, nbytes, d;
#ifndef __PPC__
  struct EClockVal start_time;
  static struct Hook smr_filter_hook = {
    {NULL},
    (ULONG (*)())smr_filter,
    NULL,
    NULL
  };
#endif
  ULONG propertymask, idcmp, flags;
  DisplayInfoHandle handle;
  struct DisplayInfo dispinfo;
  static struct TextAttr topaz8 = {
    (STRPTR)"topaz.font", 8, FS_NORMAL, FPF_ROMFONT
  };

//  printf ("VID_Init %08x\n", palette);

#ifndef __PPC__
  if ((timermp = CreatePort (NULL, 0)) == NULL)
    Sys_Error ("Can't create messageport!");
  if ((timerio = (struct timerequest *)CreateExtIO (timermp,
                  sizeof(struct timerequest))) == NULL)
    Sys_Error ("Can't create External IO!");
  if ((timerclosed = OpenDevice (TIMERNAME, UNIT_ECLOCK,
                                (struct IORequest *)timerio, 0)))
    Sys_Error ("Can't open timer.device!");
  TimerBase = timerio->tr_node.io_Device;
  eclocks_per_second = ReadEClock (&start_time);
#endif

  SetChipRev (SETCHIPREV_BEST);
  CyberGfxBase = OpenLibrary ("cybergraphics.library", 0);

  propertymask = DIPF_IS_EXTRAHALFBRITE | DIPF_IS_DUALPF | DIPF_IS_PF2PRI |
                 DIPF_IS_HAM;
  if (CyberGfxBase != NULL)
    mode = BestCModeIDTags (CYBRBIDTG_NominalWidth,  BASEWIDTH,
                            CYBRBIDTG_NominalHeight, BASEHEIGHT,
                            CYBRBIDTG_Depth,         8,
                            TAG_DONE);
  else if (GfxBase->LibNode.lib_Version >= 39)
    mode = BestModeID (BIDTAG_NominalWidth,     BASEWIDTH,
                       BIDTAG_NominalHeight,    BASEHEIGHT,
                       BIDTAG_Depth,            8,
                       BIDTAG_DIPFMustNotHave,  propertymask,
                       BIDTAG_MonitorID,        PAL_MONITOR_ID,
                       TAG_DONE);
  else
    mode = PAL_MONITOR_ID;  // Default to PAL for older systems

  // Try to show screen mode requester, but if it fails (e.g., headless/emulator),
  // just use the default mode that was calculated above
  // Skip requester on RTG systems - auto-detected mode works fine
  if (0 && AslRequestTags (smr,
                       ASLSM_TitleText,            (ULONG)"Quake",
                       ASLSM_InitialDisplayID,     mode,
                       ASLSM_InitialDisplayWidth,  BASEWIDTH,
                       ASLSM_InitialDisplayHeight, BASEHEIGHT,
                       ASLSM_MinWidth,             BASEWIDTH,
                       ASLSM_MinHeight,            BASEHEIGHT,
/*
                       ASLSM_MaxWidth,             BASEWIDTH,
                       ASLSM_MaxHeight,            BASEHEIGHT,
*/
                       ASLSM_MinDepth,             8,
                       ASLSM_MaxDepth,             8,
                       ASLSM_PropertyMask,         propertymask,
                       ASLSM_PropertyFlags,        0,
                       ASLSM_DoWidth,              TRUE,
                       ASLSM_DoHeight,             TRUE,
#ifndef __PPC__
                       ASLSM_FilterFunc,           &smr_filter_hook,
#endif
                       TAG_END))
  {
    // User selected a mode via requester
    mode = smr->sm_DisplayID;
    width = smr->sm_DisplayWidth;
    height = smr->sm_DisplayHeight;
  }
  else
  {
    // Requester failed (headless/emulator) - use default mode
    Con_Printf ("Screen mode requester failed, using default mode\n");
    width = BASEWIDTH;
    height = BASEHEIGHT;
    // mode already set from BestCModeIDTags/BestModeID above
  }

  if ((handle = FindDisplayInfo (mode)) == NULL) {
    Sys_Error ("Can't FindDisplayInfo() for mode %08x", mode);
  }
  nbytes = GetDisplayInfoData (handle, (UBYTE *)&dispinfo,
                               sizeof(struct DisplayInfo), DTAG_DISP,
                               0);
  if (nbytes < 40 /*sizeof(struct DisplayInfo)*/)
    Sys_Error ("Can't GetDisplayInfoData() for mode %08x, got %d bytes",
               mode, nbytes);

  is_cyber_mode = 0;
  if (CyberGfxBase != NULL)
    is_cyber_mode = IsCyberModeID (mode);

  /* this test needs improving */
  is_native_mode = ((GfxBase->LibNode.lib_Version < 39 ||
                     (dispinfo.PropertyFlags & DIPF_IS_EXTRAHALFBRITE) != 0 ||
                     (dispinfo.PropertyFlags & DIPF_IS_AA) != 0 ||
                     (dispinfo.PropertyFlags & DIPF_IS_ECS) != 0 ||
                     (dispinfo.PropertyFlags & DIPF_IS_DBUFFER) != 0) &&
                    !is_cyber_mode &&
                    (dispinfo.PropertyFlags & DIPF_IS_FOREIGN) == 0);

  Con_Printf ("Screen Mode $%08x is", mode);
  if (is_native_mode)
    Con_Printf (" NATIVE-PLANAR");
  else
    Con_Printf (" FOREIGN");
  Con_Printf (" 8-BIT");
  if (is_cyber_mode)
    Con_Printf (" CYBERGRAPHX");
  Con_Printf (", using size %d x %d\n", width, height);

  Con_Printf ("Opening screen with mode $%08x, size %dx%d...\n", mode, width, height);

  if ((video_screen = OpenScreenTags (NULL,
        SA_Type,        CUSTOMSCREEN,
        SA_DisplayID,   mode,
        /* SA_DClip,       (ULONG)&rect, */
        SA_Width,       width,
        SA_Height,      height,
        SA_Depth,       8,
        SA_Font,        &topaz8,
        /* SA_Draggable,FALSE, */
        /* SA_AutoScroll,FALSE, */
        /* SA_Exclusive,TRUE, */
        SA_Quiet,       TRUE,
        TAG_DONE,       0)) == NULL) {
    Sys_Error ("OpenScreen() failed");
  }

  {
    struct TagItem border_tags[] = {{VTAG_BORDERBLANK_SET,0},{TAG_DONE,0}};
    VideoControl(video_screen->ViewPort.ColorMap,border_tags);
    MakeScreen(video_screen);
    RethinkDisplay();
  }
  Con_Printf ("Screen opened successfully\n");

  idcmp = IDCMP_RAWKEY | IDCMP_ACTIVEWINDOW | IDCMP_INACTIVEWINDOW;
  flags = WFLG_ACTIVATE | WFLG_BORDERLESS | WFLG_NOCAREREFRESH |
          WFLG_SIMPLE_REFRESH;
  // NovaCoder's input code always uses mouse
  idcmp |= IDCMP_MOUSEBUTTONS | IDCMP_DELTAMOVE | IDCMP_MOUSEMOVE;
  flags |= WFLG_RMBTRAP | WFLG_REPORTMOUSE;
  if ((video_window = OpenWindowTags (NULL,
        WA_Left,         0,
        WA_Top,          0,
        WA_Width,        width,
        WA_Height,       height,
        WA_IDCMP,        idcmp,
        WA_Flags,        flags,
        WA_CustomScreen, video_screen,
        TAG_DONE,        0)) == NULL) {
    Sys_Error ("OpenWindow() failed");
  }

  Con_Printf ("Window opened successfully\n");
  AW_InputGuardInit();

  // Bring screen and window to front so they're visible
  ScreenToFront (video_screen);
  WindowToFront (video_window);
  ActivateWindow (video_window);
  Con_Printf ("Screen brought to front\n");

  if (!COM_CheckParm ("-mousepointer")) {
    if ((emptypointer = AllocVec (16, MEMF_CHIP | MEMF_CLEAR)) == NULL)
      Sys_Error ("Couldn't allocate chip memory for pointer");
    SetPointer (video_window, emptypointer, 1, 16, 0, 0);
  }

  InitRastPort (&tmp_rp);
  tmp_rp.BitMap = NULL;
  InitRastPort (&rp);
  rp.BitMap = video_screen->ViewPort.RasInfo->BitMap;

  /* tmp rastport and bitmap for WritePixelArray8() */
  InitBitMap (&tmp_bm, 8, width, 1);
  for (d = 0; d < 8; d++)
    if ((tmp_bm.Planes[d] = (PLANEPTR)AllocRaster (width, 1)) == NULL)
      Sys_Error ("AllocRaster() failed");
  temprp = *video_window->RPort;
  temprp.Layer = NULL;
  temprp.BitMap = &tmp_bm;

  if (is_native_mode) {
    if ((sbuffer[0] = AllocScreenBuffer (video_screen, NULL, SB_SCREEN_BITMAP)) == NULL ||
        (sbuffer[1] = AllocScreenBuffer (video_screen, NULL, 0)) == NULL ||
        (sbuffer[2] = AllocScreenBuffer (video_screen, NULL, 0)) == NULL)
      Sys_Error ("AllocScreenBuffer() failed");
    nextsbuffer = sbuffer[1];
    rp.BitMap = nextsbuffer->sb_BitMap;
#ifndef __PPC__
    c2p[0] = aw_c2p_reloc (sbuffer[0]->sb_BitMap);
    c2p[1] = aw_c2p_reloc (sbuffer[1]->sb_BitMap);
    c2p[2] = aw_c2p_reloc (sbuffer[2]->sb_BitMap);
    nextc2p = c2p[1];
#endif
  }

  is_directcgx = (is_cyber_mode && COM_CheckParm ("-directcgx"));

  if (!is_directcgx)
    if ((vid_buffer = (pixel_t *)malloc(sizeof(pixel_t) *
                                        width * height)) == NULL)
      Sys_Error ("Out of memory");
  if ((zbuffer = (short *)malloc(sizeof(short) * width * height)) == NULL ||
      (surfcache = (byte *)malloc(sizeof(byte) *
                                  (width*height/(320*200))*256*1024*2)) == NULL)
    Sys_Error ("Out of memory");

  vid.width = vid.conwidth = width;
  vid.height = vid.conheight = height;
  vid.maxwarpwidth = WARP_WIDTH;
  vid.maxwarpheight = WARP_HEIGHT;
  vid.aspect = 1.0;
  if (is_native_mode) {
    if ((mode & (LACE | HIRES)) != (LACE | HIRES)) {
      if (mode & LACE)
        vid.aspect *= 2.0;
      if (mode & HIRES)
        vid.aspect /= 2.0;
    }
    if (mode & SUPERHIRES)
      vid.aspect /= 2.0;
  }
  if (is_native_mode)
    vid.numpages = 3;
  else
    vid.numpages = 1;
  vid.colormap = host_colormap;
  vid.fullbright = 256; /* Generated AmiWind palette has no fullbright range. */
  vid.buffer = vid.conbuffer = vid_buffer;
  vid.rowbytes = vid.conrowbytes = width;
  vid.direct = NULL;

  d_pzbuffer = zbuffer;

  D_InitCaches (surfcache, sizeof(byte) *
                           (width*height/(320*200))*256*1024*2);

  VID_SetPalette (palette);

  do_fps = COM_CheckParm("-fps");

  Con_Printf ("VID_Init completed successfully\n");
}

/**********************************************************************/
void	VID_Shutdown (void)
{
  int d;

  VID_UnlockBuffer ();
  if (surfcache != NULL) {
    free (surfcache);
    surfcache = NULL;
  }
  if (zbuffer != NULL) {
    free (zbuffer);
    zbuffer = NULL;
  }
  if (vid_buffer != NULL) {
    free (vid_buffer);
    vid_buffer = NULL;
  }
  if (sbuffer[0] != NULL) {
    ChangeScreenBuffer (video_screen, sbuffer[0]);
    WaitTOF ();
    WaitTOF ();
    FreeScreenBuffer (video_screen, sbuffer[0]);
    sbuffer[0] = NULL;
  }
  if (sbuffer[1] != NULL) {
    FreeScreenBuffer (video_screen, sbuffer[1]);
    sbuffer[1] = NULL;
  }
  if (sbuffer[2] != NULL) {
    FreeScreenBuffer (video_screen, sbuffer[2]);
    sbuffer[2] = NULL;
  }
  if (video_window != NULL) {
    ClearPointer (video_window);
    AW_InputGuardShutdown();
    CloseWindow (video_window);
    video_window = NULL;
  }
  if (emptypointer != NULL) {
    FreeVec (emptypointer);
    emptypointer = NULL;
  }
  if (video_screen != NULL) {
    CloseScreen (video_screen);
    video_screen = NULL;
  }
  for (d = 0; d < 8; d++) {
    if (tmp_bm.Planes[d] != NULL) {
      FreeRaster (tmp_bm.Planes[d], vid.width, 1);
      tmp_bm.Planes[d] = NULL;
    }
  }
  if (smr != NULL) {
    FreeAslRequest (smr);
    smr = NULL;
  }
  if (AslBase != NULL) {
    CloseLibrary (AslBase);
    AslBase = NULL;
  }
  if (CyberGfxBase != NULL) {
    CloseLibrary (CyberGfxBase);
    CyberGfxBase = NULL;
  }
#ifndef __PPC__
  if (!timerclosed) {
    // GCC build uses stub timer implementation, so don't try to abort/wait for IO
    // Just close the device directly
    CloseDevice ((struct IORequest *)timerio);
    timerclosed = TRUE;
    TimerBase = NULL;
  }
  if (timerio != NULL) {
    DeleteExtIO ((struct IORequest *)timerio);
    timerio = NULL;
  }
  if (timermp != NULL) {
    DeletePort (timermp);
    timermp = NULL;
  }
  if (c2p[0]) {
    aw_c2p_deinit (c2p[0]);
    c2p[0] = NULL;
  }
  if (c2p[1]) {
    aw_c2p_deinit (c2p[1]);
    c2p[1] = NULL;
  }
  if (c2p[2]) {
    aw_c2p_deinit (c2p[2]);
    c2p[2] = NULL;
  }
#endif
}

/**********************************************************************/
#ifdef __SASC
void _STD_VID_Shutdown (void)
{
//  printf ("_STD_VID_Shutdown\n");
  S_Shutdown ();
  VID_Shutdown ();
}
#endif

/**********************************************************************/
#ifdef __STORM__
void EXIT_9_VID_Shutdown (void)
{
//  printf ("EXIT_9_VID_Shutdown\n");
  S_Shutdown ();
  VID_Shutdown ();
}
#endif

/**********************************************************************/
#ifdef __VBCC__
void _EXIT_9_VID_Shutdown (void)
{
//  printf ("_EXIT_9_VID_Shutdown\n");
  S_Shutdown ();
  VID_Shutdown ();
}
#endif

/**********************************************************************/
static void video_do_fps (struct RastPort *rp, int yoffset)
{
  ULONG x;
  char msg[4];

#ifdef __PPC__

  static double start_time = 0.0;
  double end_time;

  end_time = Sys_FloatTime ();
  x = (ULONG)(1.0 / (end_time - start_time) + 0.5);
  if (TRUE) {

#else

  static struct EClockVal start_time = {0, 0};
  struct EClockVal end_time;

  ReadEClock (&end_time);
  x = end_time.ev_lo - start_time.ev_lo;
  if (x != 0) {
    x = (eclocks_per_second + (x >> 1)) / x;   /* round to nearest */

#endif

    msg[0] = (x % 1000) / 100 + '0';
    msg[1] = (x % 100) / 10 + '0';
    msg[2] = (x % 10) + '0';
    msg[3] = '\0';
    Move (rp, vid.width - 24, yoffset + 6);
    Text (rp, msg, 3);
  }
  start_time = end_time;
}

/**********************************************************************/
#if 0
static void PPCWriteChunkyPixels (struct RastPort *dst_rp,
                                  int dst_x, int dst_y, int stop_x, int stop_y,
                                  UBYTE *src, int src_bytesperrow)
{
  APTR bitmap_handle;
  LONG pixfmt, dst_bytesperrow;
  UBYTE *dst;
  static ULONG bitmap_width = 0, bitmap_height = 0;
  int width, height, i;
  static BOOL first = TRUE;

  if (!is_cyber_mode) {
    WriteChunkyPixels (dst_rp, dst_x, dst_y, stop_x, stop_y, src,
                       src_bytesperrow);
    return;
  }
  if (first) {
    first = FALSE;
    if (dst_rp == video_window->RPort) {
      bitmap_width = video_window->Width;
      bitmap_height = video_window->Height;
    } else {
      bitmap_width = GetBitMapAttr (dst_rp->BitMap, BMA_WIDTH);
      bitmap_height = GetBitMapAttr (dst_rp->BitMap, BMA_HEIGHT);
    }
  }
  width = stop_x - dst_x + 1;
  height = stop_y - dst_y + 1;
  if (dst_x < 0) {
    src -= dst_x;
    width += dst_x;
    if (width <= 0)
      return;
    dst_x = 0;
  } else if (width > bitmap_width - dst_x) {
    width = bitmap_width - dst_x;
    if (width <= 0)
      return;
  }
  if (dst_y < 0) {
    src -= (dst_y * width);
    height += dst_y;
    if (height <= 0)
      return;
    dst_y = 0;
  } else if (height > bitmap_height - dst_y) {
    height = bitmap_height - dst_y;
    if (height < 0)
      return;
  }
  if ((bitmap_handle = LockBitMapTags (dst_rp->BitMap,
                                       LBMI_BASEADDRESS, &dst,
                                       LBMI_PIXFMT,      &pixfmt,
                                       LBMI_BYTESPERROW, &dst_bytesperrow,
                                       TAG_DONE)) == NULL)
    Sys_Error ("Error locking BitMap");
  dst += dst_y * dst_bytesperrow + dst_x;
  for ( ; height > 0; height--) {
    /* memcpy (dst, src, width); */
    for (i = width >> 2; i > 0; --i) {
      *(ULONG *)dst = *(ULONG *)src;
      dst += 4;
      src += 4;
    }
    dst += dst_bytesperrow - width;
    src += src_bytesperrow - width;
  }
  UnLockBitMap (bitmap_handle);
}
#endif

/**********************************************************************/
void VID_LockBuffer (void)
{
//  printf ("Lock\n");
  if (is_directcgx && bitmap_handle == NULL) {
    if ((bitmap_handle = LockBitMapTags (rp.BitMap,
                                         LBMI_BASEADDRESS, &vid.direct,
                                         LBMI_BYTESPERROW, &vid.rowbytes,
                                         TAG_DONE)) == NULL)
      Sys_Error ("Error locking BitMap");
    vid.buffer = vid.conbuffer = vid.direct;
    vid.conrowbytes = vid.rowbytes;
  }
}

/**********************************************************************/
void VID_UnlockBuffer (void)
{
//  printf ("Unlock\n");
  if (is_directcgx && bitmap_handle != NULL) {
    UnLockBitMap (bitmap_handle);
    bitmap_handle = NULL;
    vid.buffer = vid.conbuffer = vid.direct = NULL;
  }
}

/**********************************************************************/
void	VID_Update (vrect_t *rects)
{
#ifdef __PPC__
  int i, j;
#endif

  if (is_directcgx)
    return;

  if (is_native_mode) {
#ifdef __PPC__
    while (rects != NULL) {
      for (i = rects->y, j = ((int)(vid.buffer)) + rects->y * vid.width;
           i < rects->y + rects->height; i++, j += vid.width)
        ppc_c2p_line (i, j, rp.BitMap, (vid.width + 31) >> 5);
      rects = rects->pnext;
    }
#else
    AW_Mark(2);
    if (rects != NULL)
      aw_c2p (nextc2p, nextsbuffer->sb_BitMap, vid.buffer,
            vid.width * (rects->y + rects->height));
    AW_EndMark(2);
#endif
  } else {
    while (rects != NULL) {
#if 0
      if (GfxBase->LibNode.lib_Version >= 40)
        WriteChunkyPixels (&rp, rects->x, rects->y,
                           rects->x + rects->width - 1,
                           rects->y + rects->height - 1,
                           vid.buffer, rects->width);
      else if (CyberGfxBase != NULL)
        WritePixelArray (vid.buffer, rects->x, rects->y, rects->width, &rp,
                         rects->x, rects->y, rects->width, rects->height,
                         RECTFMT_LUT8);
      else
#endif
        WritePixelArray8 (&rp, rects->x, rects->y,
                          rects->x + rects->width - 1,
                          rects->y + rects->height - 1,
                          vid.buffer, &temprp);
      rects = rects->pnext;
    }
  }
  if (do_fps)
    video_do_fps (&rp, 0);
  if (is_native_mode) {
    if (ChangeScreenBuffer (video_screen, nextsbuffer)) {
      if (nextsbuffer == sbuffer[0]) {
        nextsbuffer = sbuffer[1];
#ifndef __PPC__
        nextc2p = c2p[1];
#endif
      } else if (nextsbuffer == sbuffer[1]) {
        nextsbuffer = sbuffer[2];
#ifndef __PPC__
        nextc2p = c2p[2];
#endif
      } else {
        nextsbuffer = sbuffer[0];
#ifndef __PPC__
        nextc2p = c2p[0];
#endif
      }
      rp.BitMap = nextsbuffer->sb_BitMap;
    }
  }
}

/**********************************************************************/
/*
================
D_BeginDirectRect
================
*/
static struct BitMap *saved_bm = NULL;

void D_BeginDirectRect (int x, int y, byte *pbitmap, int width, int height)
{
//  printf ("D_BeginDirectRect %d %d %08x %d %d\n", x, y, pbitmap, width, height);
  if (video_window != NULL) {
    saved_bm = rp.BitMap;
    rp.BitMap = video_screen->ViewPort.RasInfo->BitMap;
    if ((tmp_rp.BitMap = AllocBitMap (width, height, 8, 0,
                                      rp.BitMap)) == NULL)
      Sys_Error ("AllocBitMap failed");
    ClipBlit (&rp, x, y, &tmp_rp, 0, 0, width, height, 0xc0);
    if (GfxBase->LibNode.lib_Version >= 40)
      WriteChunkyPixels (&rp, x, y, x+width-1, y+height-1,
                         pbitmap, width);
    else if (CyberGfxBase != NULL)
      WritePixelArray (pbitmap, 0, 0, width, &rp, x, y, width, height,
                       RECTFMT_LUT8);
    //else
    //  Sys_Error ("KS3.1 or cybergraphics.library required\n");
  }
}

/**********************************************************************/
/*
================
D_EndDirectRect
================
*/
void D_EndDirectRect (int x, int y, int width, int height)
{
//  printf ("D_EndDirectRect %d %d %d %d\n", x, y, width, height);
  if (video_window != NULL && tmp_rp.BitMap != NULL) {
    ClipBlit (&tmp_rp, 0, 0, &rp, x, y, width, height, 0xc0);
    FreeBitMap (tmp_rp.BitMap);
    tmp_rp.BitMap = NULL;
    rp.BitMap = saved_bm;
    saved_bm = NULL;
  }
}

/**********************************************************************/
extern void (*vid_menudrawfn)(void);
extern void (*vid_menukeyfn)(int key);

/**********************************************************************/
// NOTE: Sys_SendKeyEvents() moved to sys_amiga.c in NovaCoder's version
#if 0
void Sys_SendKeyEvents(void)
{
  ULONG class;
  UWORD code;
  WORD mousex, mousey;
  struct IntuiMessage *msg;


  if (video_window != NULL) {
    while ((msg = (struct IntuiMessage *)GetMsg (video_window->UserPort)) != NULL) {
      class = msg->Class;
      code = msg->Code;
      mousex = msg->MouseX;
      mousey = msg->MouseY;
      ReplyMsg ((struct Message *)msg);
      switch (class) {
        case IDCMP_RAWKEY:
          if(Key_AmigaRaw(code))Key_Event(Key_AmigaRaw(code),(code & 0x80)==0);
          break;
        case IDCMP_MOUSEBUTTONS:
          switch (code) {
            case IECODE_LBUTTON:
              Key_Event (K_MOUSE1, true);
              break;
            case IECODE_LBUTTON + IECODE_UP_PREFIX:
              Key_Event (K_MOUSE1, false);
              break;
            case IECODE_MBUTTON:
              Key_Event (K_MOUSE2, true);
              break;
            case IECODE_MBUTTON + IECODE_UP_PREFIX:
              Key_Event (K_MOUSE2, false);
              break;
            case IECODE_RBUTTON:
              Key_Event (K_MOUSE3, true);
              break;
            case IECODE_RBUTTON + IECODE_UP_PREFIX:
              Key_Event (K_MOUSE3, false);
              break;
            default:
              break;
          }
          break;
        case IDCMP_MOUSEMOVE:
        case IDCMP_DELTAMOVE:
          mouseX = mousex;
          mouseY = mousey;
          mouse_has_moved = true;
          break;
        default:
          break;
      }
    }
  }
}
#endif  // Sys_SendKeyEvents moved to sys_amiga.c

/**********************************************************************/
#if 0
char *Sys_ConsoleInput (void)
{
  printf ("Sys_ConsoleInput\n");
  return 0;
}
#endif

/**********************************************************************/
