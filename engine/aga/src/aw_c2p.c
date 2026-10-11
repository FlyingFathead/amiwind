/* SPDX-License-Identifier: GPL-2.0-or-later
 * AmiWind independent 8x8 bit transpose for packed non-interleaved planes.
 * Three mask/exchange stages transpose eight chunky pixels into eight bytes.
 */
#include <exec/types.h>
#include <graphics/gfx.h>
#if AW_ASM_C2P
/* Engine profile (docs/ENGINE_PROFILES.md): upstream AmiQuake's c2p8.s, NovaCoder's chunky-to-planar
 * routine. c2p8_reloc copies the routine to Fast RAM with this bitmap's plane offsets patched in;
 * c2p8 converts `size` chunky bytes, 32 at a time, into consecutive plane bytes. It is used when the
 * plane rows are unpadded (BytesPerRow == width / 8) and the size is a multiple of 32; otherwise,
 * or when the copy could not be made, the C conversion below runs. */
extern void *c2p8_reloc(struct BitMap *bm __asm("a0"));
extern void c2p8_deinit(void *c2p __asm("a0"));
extern void c2p8(void *c2p __asm("a0"), struct BitMap *bmp __asm("a1"), UBYTE *chunky __asm("a2"), ULONG size __asm("d0"));
static void aw_c2p_c(void *unused, struct BitMap *bm, UBYTE *src, ULONG width, ULONG rows);
void *aw_c2p_reloc(struct BitMap *bm) { return c2p8_reloc(bm); }
void aw_c2p_deinit(void *c2p) { if (c2p) c2p8_deinit(c2p); }
void aw_c2p(void *c2p, struct BitMap *bm, UBYTE *src, ULONG width, ULONG rows)
{
    if (c2p && bm->BytesPerRow == width / 8 && !((width * rows) & 31))
        c2p8(c2p, bm, src, width * rows);
    else
        aw_c2p_c(c2p, bm, src, width, rows);
}
static void aw_c2p_c(void *unused, struct BitMap *bm, UBYTE *src, ULONG width, ULONG rows)
{
#else
void *aw_c2p_reloc(struct BitMap *bm) { return bm; }
void aw_c2p_deinit(void *unused) { (void)unused; }
/* width chunky pixels per row (a multiple of 8), rows rows from the top.
 * Each plane row starts BytesPerRow apart: screens whose rows are padded for
 * the fetch mode no longer render skewed (ENGINE-C2P-ROWSTRIDE-35). */
void aw_c2p(void *unused, struct BitMap *bm, UBYTE *src, ULONG width, ULONG rows)
{
#endif
    ULONG n,a,b,t,u,r,end,stride=bm->BytesPerRow,groups=width/8;
    (void)unused;
    for (r=0;r<rows;r++)
    for (n=r*stride,end=n+groups;n<end;n++) {
        a=((ULONG)src[0]<<24)|((ULONG)src[1]<<16)|((ULONG)src[2]<<8)|src[3];
        b=((ULONG)src[4]<<24)|((ULONG)src[5]<<16)|((ULONG)src[6]<<8)|src[7];src+=8;
        t=(a^(a>>7))&0x00aa00aaUL;
        u=(b^((b>>7)|(a<<25)))&0x00aa00aaUL;
        a^=t|(t<<7)|(u>>25);b^=u|(u<<7);
        t=(a^(a>>14))&0x0000ccccUL;
        u=(b^((b>>14)|(a<<18)))&0x0000ccccUL;
        a^=t|(t<<14)|(u>>18);b^=u|(u<<14);
        u=(b^((b>>28)|(a<<4)))&0xf0f0f0f0UL;
        a^=u>>4;b^=u|(u<<28);
        bm->Planes[7][n]=a>>24;bm->Planes[6][n]=a>>16;
        bm->Planes[5][n]=a>>8;bm->Planes[4][n]=a;
        bm->Planes[3][n]=b>>24;bm->Planes[2][n]=b>>16;
        bm->Planes[1][n]=b>>8;bm->Planes[0][n]=b;
    }
}
