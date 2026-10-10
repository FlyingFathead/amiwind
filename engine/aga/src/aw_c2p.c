/* SPDX-License-Identifier: GPL-2.0-or-later
 * AmiWind independent 8x8 bit transpose for packed non-interleaved planes.
 * Three mask/exchange stages transpose eight chunky pixels into eight bytes.
 */
#include <exec/types.h>
#include <graphics/gfx.h>
void *aw_c2p_reloc(struct BitMap *bm) { return bm; }
void aw_c2p_deinit(void *unused) { (void)unused; }
/* width chunky pixels per row (a multiple of 8), rows rows from the top.
 * Each plane row starts BytesPerRow apart: screens whose rows are padded for
 * the fetch mode no longer render skewed (ENGINE-C2P-ROWSTRIDE-35). */
void aw_c2p(void *unused, struct BitMap *bm, UBYTE *src, ULONG width, ULONG rows)
{
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
