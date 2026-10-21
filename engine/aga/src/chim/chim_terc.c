/* SPDX-License-Identifier: GPL-2.0-or-later
 * Compact terrain records: the expansion (chim_terc.h). The image is built as
 * the builder's chim.format.brush_image builds it: the BSP29 header (version
 * 29, fifteen lump offsets and lengths), then the lumps in file order, each
 * on a 4-byte boundary, the image padded to 4 bytes. Byte shuffling only: the
 * payloads keep the image's little-endian bytes. */
#include <string.h>
#include "chim_format.h"
#include "chim_terc.h"

#define BSP_HEADER	(4 + 15*8)
enum { RAW, PLANES, UNIFORM, CLIPNODES, NODES };

/* chim.format.FILE_ORDER: the loader's order, the clipnodes (collision) last */
static const int file_order[15] = {3, 12, 13, 2, 8, 1, 6, 7, 11, 4, 10, 14, 5, 0, 9};

static void PutLE (unsigned char *p, unsigned long v)
{
	p[0] = (unsigned char)v;
	p[1] = (unsigned char)(v >> 8);
	p[2] = (unsigned char)(v >> 16);
	p[3] = (unsigned char)(v >> 24);
}

static unsigned long GetLE (const unsigned char *p)
{
	return (unsigned long)p[0] | ((unsigned long)p[1] << 8) | ((unsigned long)p[2] << 16) | ((unsigned long)p[3] << 24);
}

static long Align4 (long n)
{
	return (n + 3) & ~3L;
}

int ChimTerc_Is (const unsigned char *data, long bytes)
{
	return bytes >= CHIM_TERC_HEAD_BYTES && !memcmp (data, "TRC1", 4);
}

/* One lump: METHOD's payload P (N bytes) written at DST + AT; its length in *LEN. With DST NULL only the
 * length (chim_thgt.c sizes its image first). */
int ChimTerc_Lump (int method, const unsigned char *p, long n, unsigned char *dst, long at, long room, long *len)
{
	unsigned long count, k, c;
	const unsigned char *in;
	unsigned char *o = dst ? dst + at : NULL;
	static const unsigned char one[4] = {0x00, 0x00, 0x80, 0x3f}, minus_one[4] = {0x00, 0x00, 0x80, 0xbf},
		zero[4] = {0, 0, 0, 0}, minus_zero[4] = {0x00, 0x00, 0x00, 0x80};
	switch (method)
	{
	case RAW:
		if (at + n > room)
			return 0;
		if (dst)
			memcpy (o, p, (size_t)n);
		*len = n;
		return 1;
	case PLANES:
		if (n < 4)
			return 0;
		count = GetLE (p);
		if (count > 1000000ul || 4 + (long)Align4 ((long)count) > n || at + (long)count*20 > room)
			return 0;
		in = p + 4 + Align4 ((long)count);
		for (k=0 ; dst && k<count ; k++)
		{
			c = p[4+k];
			if (!c)
			{
				if (in + 20 > p + n)
					return 0;
				memcpy (o + k*20, in, 20);
				in += 20;
				continue;
			}
			if (in + 4 > p + n || c > 1 + 24*5 + 8*2 + 4 + 3)
				return 0;
			c--;
			{
				int kind = (int)(c / 24), axis = (int)((c % 24) / 8), negative = (int)((c % 8) / 4), signs = (int)(c % 4);
				int a0 = axis == 0 ? 1 : 0, a1 = axis == 2 ? 1 : 2, j;
				unsigned char *q = o + k*20;
				for (j=0 ; j<3 ; j++)
					memcpy (q + 4*j, zero, 4);
				memcpy (q + 4*axis, negative ? minus_one : one, 4);
				if (signs & 1)
					memcpy (q + 4*a0, minus_zero, 4);
				if (signs & 2)
					memcpy (q + 4*a1, minus_zero, 4);
				memcpy (q + 12, in, 4);
				PutLE (q + 16, (unsigned long)kind);
				in += 4;
			}
		}
		*len = (long)count*20;
		return 1;
	case UNIFORM:
		if (n < 8)
			return 0;
		count = GetLE (p);
		if (at + (long)count > room)
			return 0;
		if (dst)
			memset (o, p[4], (size_t)count);
		*len = (long)count;
		return 1;
	case CLIPNODES:
		if (n < 4)
			return 0;
		count = GetLE (p);
		if (4 + (long)count*6 > n || at + (long)count*8 > room)
			return 0;
		for (k=0 ; dst && k<count ; k++)
		{
			in = p + 4 + k*6;
			PutLE (o + k*8, (unsigned long)in[0] | ((unsigned long)in[1] << 8));
			memcpy (o + k*8 + 4, in + 2, 4);
		}
		*len = (long)count*8;
		return 1;
	case NODES:
		if (n < 4)
			return 0;
		count = GetLE (p);
		if (4 + (long)count*22 > n || at + (long)count*24 > room)
			return 0;
		for (k=0 ; dst && k<count ; k++)
		{
			in = p + 4 + k*22;
			PutLE (o + k*24, (unsigned long)in[0] | ((unsigned long)in[1] << 8));
			memcpy (o + k*24 + 4, in + 2, 20);
		}
		*len = (long)count*24;
		return 1;
	}
	return 0;
}

int ChimTerc_Expand (const unsigned char *src, long bytes, unsigned char *dst, long room, long *out)
{
	long image, render, at, body, len, n;
	int slot, k, method;
	if (!ChimTerc_Is (src, bytes) || ChimFormat_U16 (src+12) != 15 || bytes < CHIM_TERC_HEAD_BYTES + 15*CHIM_TERC_ENTRY_BYTES)
		return 0;
	image = (long)ChimFormat_U32 (src+4);
	render = (long)ChimFormat_U32 (src+8);
	if (image < BSP_HEADER || image > room || render > image)
		return 0;
	memset (dst, 0, BSP_HEADER);
	PutLE (dst, 29);
	at = CHIM_TERC_HEAD_BYTES + 15*CHIM_TERC_ENTRY_BYTES;
	body = BSP_HEADER;
	for (slot=0 ; slot<15 ; slot++)
	{
		const unsigned char *e = src + CHIM_TERC_HEAD_BYTES + slot*CHIM_TERC_ENTRY_BYTES;
		k = file_order[slot];
		method = e[0];
		n = (long)ChimFormat_U32 (e+4);
		at = Align4 (at);
		if (n < 0 || at + n > bytes)
			return 0;
		if (k == 9 && body != render)
			return 0;			/* the render part ends where the head says (before the gap) */
		/* the builder starts every lump on a 4-byte boundary, the gap zero */
		while (body & 3)
		{
			if (body >= room)
				return 0;
			dst[body++] = 0;
		}
		if (!ChimTerc_Lump (method, src + at, n, dst, body, room, &len))
			return 0;
		PutLE (dst + 4 + 8*k, (unsigned long)body);
		PutLE (dst + 8 + 8*k, (unsigned long)len);
		body += len;
		at += n;
	}
	while (body & 3)
	{
		if (body >= room)
			return 0;
		dst[body++] = 0;
	}
	if (body != image)
		return 0;
	*out = body;
	return 1;
}
