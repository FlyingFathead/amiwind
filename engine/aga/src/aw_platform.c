/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#ifdef AMIWIND_CLIB2
#include <proto/exec.h>
#include <graphics/gfxbase.h>
#include <intuition/intuitionbase.h>
struct GfxBase *GfxBase;
struct IntuitionBase *IntuitionBase;
void AW_PlatformClose(void) {
    if(IntuitionBase){CloseLibrary((struct Library *)IntuitionBase);IntuitionBase=NULL;}
    if(GfxBase){CloseLibrary((struct Library *)GfxBase);GfxBase=NULL;}
}
void AW_PlatformInit(void) {
    GfxBase=(struct GfxBase *)OpenLibrary("graphics.library",39);
    IntuitionBase=(struct IntuitionBase *)OpenLibrary("intuition.library",39);
    if(!GfxBase || !IntuitionBase){AW_PlatformClose();exit(20);}
}
#else
void AW_PlatformClose(void) {}
void AW_PlatformInit(void) {}
#endif
