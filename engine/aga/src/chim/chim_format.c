/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM world format 0.4 to 0.8 decoders (chim_format.h). Byte access only, so the
 * same code reads the big-endian structures on the 68k and on a host test.
 * Every decoder checks what it can see on its own; the caller checks offsets
 * against the file it read them from.
 */
#include <string.h>
#include "chim_format.h"

unsigned ChimFormat_U32 (const unsigned char *p)
{
	return ((unsigned)p[0]<<24) | ((unsigned)p[1]<<16) | ((unsigned)p[2]<<8) | (unsigned)p[3];
}

int ChimFormat_U16 (const unsigned char *p)
{
	return (p[0]<<8) | p[1];
}

int ChimFormat_S16 (const unsigned char *p)
{
	int v = (p[0]<<8) | p[1];
	return v >= 32768 ? v - 65536 : v;
}

float ChimFormat_F32 (const unsigned char *p)
{
	union { unsigned u; float f; } v;
	v.u = ChimFormat_U32 (p);
	return v.f;
}

/* No libm: inf - inf and NaN - NaN are NaN, which never equals 0. */
static int Finite (float f)
{
	float zero = f - f;
	return zero == 0.0f;
}

static int Kind (const unsigned char *p, char *out)
{
	static const char *const kinds[] = {"INDX", "FRAM", "SECT", "ROOM"};
	int i;
	memcpy (out, p, 4);
	out[4] = 0;
	for (i=0 ; i<4 ; i++)
		if (!memcmp (out, kinds[i], 4))
			return 1;
	return 0;
}

int ChimFormat_Header (const unsigned char *p, long bytes, const char *kind, chim_header_t *h)
{
	memset (h, 0, sizeof(*h));
	if (bytes < CHIM_HEADER_BYTES || memcmp (p, "CHIM", 4) || !Kind (p+4, h->kind))
		return 0;
	if (kind && strcmp (h->kind, kind))
		return 0;
	h->major = ChimFormat_U16 (p+8);
	h->minor = ChimFormat_U16 (p+10);
	h->count = ChimFormat_U32 (p+16);
	h->directory = ChimFormat_U32 (p+20);
	h->data = ChimFormat_U32 (p+24);
	h->bytes = ChimFormat_U32 (p+28);
	if (h->major != CHIM_FORMAT_MAJOR || h->minor < CHIM_FORMAT_MINOR_OLDEST || h->minor > CHIM_FORMAT_MINOR ||
		ChimFormat_U32 (p+12) != CHIM_HEADER_BYTES)
		return 0;
	return h->directory >= CHIM_HEADER_BYTES && h->directory <= h->data &&
		h->data <= h->bytes && (long)h->bytes == bytes;
}

int ChimFormat_Settings (const unsigned char *p, chim_settings_t *s)
{
	s->draw_distance = ChimFormat_F32 (p);
	s->hysteresis = ChimFormat_F32 (p+4);
	s->collision_margin = ChimFormat_F32 (p+8);
	s->prefetch_margin = ChimFormat_F32 (p+12);
	s->grain = ChimFormat_U16 (p+16);
	s->terrain_light = p[18];
	s->placements = ChimFormat_U32 (p+20);
	s->models = ChimFormat_U32 (p+24);
	s->textures = ChimFormat_U32 (p+28);
	s->frames = ChimFormat_U32 (p+32);
	s->sector_chunks = ChimFormat_U16 (p+36);
	return s->sector_chunks >= 1 && s->sector_chunks <= 16 && Finite (s->draw_distance) && s->draw_distance > 0 && s->draw_distance < 8192 &&
		Finite (s->hysteresis) && s->hysteresis >= 0 && s->hysteresis < 4096 &&
		Finite (s->collision_margin) && s->collision_margin >= 0 && s->collision_margin < 4096 &&
		Finite (s->prefetch_margin) && s->prefetch_margin >= 0 && s->prefetch_margin < 4096 &&
		s->grain >= 32 && s->grain <= 4096 && !(s->grain & (s->grain-1));
}

void ChimFormat_Toc (const unsigned char *p, chim_toc_t *t)
{
	t->files_at = ChimFormat_U32 (p);
	t->files = ChimFormat_U32 (p+4);
	t->models_at = ChimFormat_U32 (p+8);
	t->models = ChimFormat_U32 (p+12);
	t->order_at = ChimFormat_U32 (p+16);
	t->textures_at = ChimFormat_U32 (p+20);
	t->textures = ChimFormat_U32 (p+24);
	t->names_at = ChimFormat_U32 (p+28);
}

/* Paths are relative to chim/: printable, no drive or parent parts. */
int ChimFormat_File (const unsigned char *p, chim_file_t *f)
{
	int i, n;
	if (!Kind (p, f->kind) || !strcmp (f->kind, "INDX"))
		return 0;
	f->sector = ChimFormat_U16 (p+4);
	f->cx = ChimFormat_S16 (p+6);
	f->cy = ChimFormat_S16 (p+8);
	f->bytes = ChimFormat_U32 (p+12);
	f->crc = ChimFormat_U32 (p+16);
	f->entries = ChimFormat_U32 (p+20);
	memcpy (f->path, p+28, CHIM_PATH_CHARS);
	f->path[CHIM_PATH_CHARS] = 0;
	n = (int)strlen (f->path);
	if (!n || n >= CHIM_PATH_CHARS || f->path[0] == '/' || strstr (f->path, ".."))
		return 0;
	for (i=n ; i<CHIM_PATH_CHARS ; i++)
		if (p[28+i])
			return 0;
	for (i=0 ; i<n ; i++)
		if ((unsigned char)f->path[i] <= 32 || (unsigned char)f->path[i] >= 127 || f->path[i] == ':')
			return 0;
	return 1;
}

void ChimFormat_ModelDir (const unsigned char *p, chim_asset_t *m)
{
	m->file = (unsigned short)ChimFormat_U16 (p);
	m->offset = ChimFormat_U32 (p+4);
	m->bytes = ChimFormat_U32 (p+8);
	m->render = ChimFormat_U32 (p+12);
	m->width = m->height = m->pad = 0;
}

void ChimFormat_TextureDir (const unsigned char *p, chim_asset_t *t)
{
	t->file = (unsigned short)ChimFormat_U16 (p);
	t->offset = ChimFormat_U32 (p+4);
	t->bytes = ChimFormat_U32 (p+8);
	t->render = t->bytes;
	t->width = (unsigned short)ChimFormat_U16 (p+20);
	t->height = (unsigned short)ChimFormat_U16 (p+22);
	t->pad = 0;
}

int ChimFormat_Frame (const unsigned char *p, chim_frame_t *f)
{
	f->cx = ChimFormat_S16 (p);
	f->cy = ChimFormat_S16 (p+2);
	f->centre[0] = ChimFormat_F32 (p+4);
	f->centre[1] = ChimFormat_F32 (p+8);
	f->low[0] = ChimFormat_F32 (p+12);
	f->low[1] = ChimFormat_F32 (p+16);
	f->grain = ChimFormat_U16 (p+20);
	f->nx = ChimFormat_U16 (p+22);
	f->ny = ChimFormat_U16 (p+24);
	f->sector_chunks = ChimFormat_U16 (p+26);
	f->owned_total = ChimFormat_U32 (p+28);
	return Finite (f->centre[0]) && Finite (f->centre[1]) && Finite (f->low[0]) && Finite (f->low[1]) &&
		f->low[0] > -8192 && f->low[0] < 8192 && f->low[1] > -8192 && f->low[1] < 8192 &&
		f->grain >= 32 && f->grain <= 4096 && f->nx >= 1 && f->nx <= 256 && f->ny >= 1 && f->ny <= 256 &&
		f->sector_chunks >= 1 && !(f->nx % f->sector_chunks) && !(f->ny % f->sector_chunks);
}

void ChimFormat_ChunkEntry (const unsigned char *p, chim_chunk_entry_t *c)
{
	c->cx = ChimFormat_U16 (p);
	c->cy = ChimFormat_U16 (p+2);
	c->sector = ChimFormat_U16 (p+4);
	c->offset = ChimFormat_U32 (p+8);
	c->render = ChimFormat_U32 (p+12);
	c->collision = ChimFormat_U32 (p+16);
	c->owned = ChimFormat_U16 (p+20);
	c->reach = ChimFormat_U16 (p+22);
	c->zmin = ChimFormat_S16 (p+24);
	c->zmax = ChimFormat_S16 (p+26);
}

int ChimFormat_ChunkHead (const unsigned char *p, chim_chunk_head_t *h)
{
	/* CHK0 inline terrain, CHK1 terrain reference (0.7); CHK2 and CHK3 the
	 * same with reach references (0.9) */
	if (memcmp (p, "CHK", 3) || p[3] < '0' || p[3] > '3')
		return 0;
	h->ref = p[3] == '1' || p[3] == '3';
	h->reach_refs = p[3] >= '2';
	h->owned = ChimFormat_U16 (p+4);
	h->reach = ChimFormat_U16 (p+6);
	h->image_at = ChimFormat_U32 (p+8);
	h->image_render = ChimFormat_U32 (p+12);
	h->pvs_bytes = ChimFormat_U16 (p+16);
	h->terrain_leaves = ChimFormat_U16 (p+18);
	h->pvl_bytes = ChimFormat_U16 (p+20);
	h->record_bytes = ChimFormat_U16 (p+22);
	return 1;
}

/* 0.7: a CHK1 chunk's reference block. The shift is whole units, finite and
 * inside the frame range (a bad block fails the load, never the game). */
int ChimFormat_TerrainRef (const unsigned char *p, chim_terrain_ref_t *t)
{
	int k;
	t->id = ChimFormat_U32 (p);
	t->file = (unsigned)ChimFormat_U16 (p+4);
	t->offset = ChimFormat_U32 (p+8);
	t->bytes = ChimFormat_U32 (p+12);
	t->render = ChimFormat_U32 (p+16);
	for (k=0 ; k<3 ; k++)
	{
		t->shift[k] = ChimFormat_F32 (p+20+4*k);
		if (!Finite (t->shift[k]) || t->shift[k] <= -8192 || t->shift[k] >= 8192 ||
			t->shift[k] != (float)(int)t->shift[k])
			return 0;
	}
	return ChimFormat_U16 (p+6) == 0 && t->render <= t->bytes && (t->offset & 3) == 0;
}

int ChimFormat_Record (const unsigned char *p, chim_record_t *r)
{
	int k;
	r->pid = ChimFormat_U32 (p);
	r->ref = ChimFormat_U32 (p+4);
	r->model = ChimFormat_U32 (p+8);
	r->origin[0] = ChimFormat_F32 (p+12);
	r->origin[1] = ChimFormat_F32 (p+16);
	r->origin[2] = ChimFormat_F32 (p+20);
	r->yaw = ChimFormat_F32 (p+24);
	r->owner = ChimFormat_U16 (p+28);
	r->cell_dx = (signed char)p[30];
	r->cell_dy = (signed char)p[31];
	for (k=0 ; k<3 ; k++)
	{
		r->mins[k] = (short)ChimFormat_S16 (p+32+2*k);
		r->maxs[k] = (short)ChimFormat_S16 (p+38+2*k);
		if (r->mins[k] > r->maxs[k])
			return 0;
	}
	r->leaves = ChimFormat_U16 (p+44);
	r->flags = ChimFormat_U16 (p+46);
	r->pitch = r->roll = 0;
	return Finite (r->origin[0]) && Finite (r->origin[1]) && Finite (r->origin[2]) && Finite (r->yaw) &&
		r->origin[0] > -8192 && r->origin[0] < 8192 && r->origin[1] > -8192 && r->origin[1] < 8192 &&
		r->origin[2] > -8192 && r->origin[2] < 8192 && r->yaw >= -720 && r->yaw <= 720;
}

int ChimFormat_RecordPlaced (const unsigned char *p, chim_record_t *r)
{
	if (!ChimFormat_Record (p, r))
		return 0;
	r->pitch = ChimFormat_F32 (p+48);
	r->roll = ChimFormat_F32 (p+52);
	return Finite (r->pitch) && Finite (r->roll) && r->pitch >= -720 && r->pitch <= 720 &&
		r->roll >= -720 && r->roll <= 720;
}

void ChimFormat_ReachRef (const unsigned char *p, int *owner, int *record)
{
	*owner = ChimFormat_U16 (p);
	*record = ChimFormat_U16 (p+2);
}

int ChimFormat_RecordBytes (int minor)
{
	return minor >= CHIM_PLACED_MINOR ? CHIM_RECORD_BYTES_PLACED : CHIM_RECORD_BYTES;
}

int ChimFormat_RecordLight (int minor, int flags)
{
	return minor >= CHIM_LIGHT_MINOR ? (flags >> CHIM_RECORD_LIGHT_SHIFT) & 255 : 0;
}

int ChimFormat_RecordTint (int minor, int flags)
{
	return minor >= CHIM_TINT_MINOR ? (flags >> CHIM_RECORD_TINT_SHIFT) & 7 : 0;
}

int ChimFormat_StoreNameValid (const char *name)
{
	int n;
	if (!name)
		return 0;
	for (n=0 ; name[n] ; n++)
		if (n >= CHIM_STORE_CHARS || !((name[n] >= 'a' && name[n] <= 'z') || (name[n] >= '0' && name[n] <= '9') ||
			name[n] == '_'))
			return 0;
	return n > 0;
}

int ChimFormat_RoomNameValid (const char *name)
{
	int n;
	if (!name)
		return 0;
	for (n=0 ; name[n] ; n++)
		if (n >= CHIM_ROOM_NAME_CHARS || !((name[n] >= 'a' && name[n] <= 'z') || (name[n] >= '0' && name[n] <= '9') ||
			name[n] == '_' || name[n] == '-'))
			return 0;
	return n > 0;
}

int ChimFormat_Room (const unsigned char *p, long bytes, chim_header_t *h, chim_room_t *room)
{
	const unsigned char *b;
	int k;
	unsigned long list;
	memset (room, 0, sizeof(*room));
	if (!ChimFormat_Header (p, bytes, "ROOM", h) || h->minor < CHIM_PLACED_MINOR ||
		bytes < CHIM_HEADER_BYTES + CHIM_ROOM_BLOCK_BYTES || h->count > 65535)
		return 0;
	b = p + CHIM_HEADER_BYTES;
	for (k=0 ; k<3 ; k++)
	{
		room->mins[k] = ChimFormat_F32 (b + 4*k);
		room->maxs[k] = ChimFormat_F32 (b + 12 + 4*k);
		if (!Finite (room->mins[k]) || !Finite (room->maxs[k]) || room->mins[k] > room->maxs[k] ||
			room->mins[k] <= -32768 || room->maxs[k] >= 32768)
			return 0;
	}
	room->models = ChimFormat_U32 (b + 24);
	if (ChimFormat_U32 (b + 28) != 0 || room->models > 65535 || (h->count && !room->models))
		return 0;
	list = (unsigned long)CHIM_HEADER_BYTES + CHIM_ROOM_BLOCK_BYTES;
	return h->directory == list && h->data == list + 4UL*room->models &&
		(unsigned long)h->bytes == h->data + (unsigned long)CHIM_RECORD_BYTES_PLACED*h->count;
}

int ChimFormat_StorePath (char *out, int size, const char *store, const char *relative)
{
	int n, r;
	if (!out || size <= 0 || !relative || !ChimFormat_StoreNameValid (store))
		return 0;
	n = (int)strlen (store);
	r = (int)strlen (relative);
	if (n + 1 + r + 1 > size)
		return 0;
	memcpy (out, store, n);
	out[n] = '/';
	memcpy (out + n + 1, relative, r + 1);
	return 1;
}

/* 1 when a texture of this name and size is drawn turbulent and must be tiled to 64 x 64 first. */
int ChimFormat_TurbulentTile (const char *name, int width, int height)
{
	if (!name || name[0] != '*' || width <= 0 || height <= 0)
		return 0;
	if (width > CHIM_TURB_SIZE || height > CHIM_TURB_SIZE || (width == CHIM_TURB_SIZE && height == CHIM_TURB_SIZE))
		return 0;
	return width >= 8 && height >= 8 && CHIM_TURB_SIZE % width == 0 && CHIM_TURB_SIZE % height == 0;
}

/* src: the four mip levels of a width x height miptex, one after the other; dst: the four levels of the
 * 64 x 64 texture (CHIM_TURB_PIXELS bytes), each level the source level repeated. */
void ChimFormat_TileTurbulent (const unsigned char *src, int width, int height, unsigned char *dst)
{
	int j, x, y, sw, sh, dw;
	for (j = 0; j < 4; j++)
	{
		sw = width >> j; sh = height >> j; dw = CHIM_TURB_SIZE >> j;
		for (y = 0; y < dw; y++)
			for (x = 0; x < dw; x++)
				dst[y*dw + x] = src[(y % sh)*sw + x % sw];
		src += sw*sh;
		dst += dw*dw;
	}
}
