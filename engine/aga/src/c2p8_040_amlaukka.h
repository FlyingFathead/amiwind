#ifndef _C2P8_040_AMLAUKKA_H
#define _C2P8_040_AMLAUKKA_H

/*
 *  c2p8_040_amlaukka.h - optimized c2p
 *  by Aki Laukkanen <amlaukka@cc.helsinki.fi>
 *
 *  This file is public domain.
 */

#include <graphics/gfx.h>

void __asm *c2p8_reloc(register __a0 struct BitMap *bitmap);
void __asm c2p8_deinit(register __a0 void *c2p);
void __asm c2p8(register __a0 void *c2p,
		register __a1 struct BitMap *bmp,
		register __a2 UBYTE *chunky,
		register __d0 ULONG size);
#endif
