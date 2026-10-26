/* aw_skel_load.c: the shared animation tables skeletal models name (aw_skel.h), each loaded once by its path and
 * kept for the session: one table serves every humanoid (docs/MODULAR_NPCS.md, "Runtime method C"). A table that
 * cannot be read or is invalid says so once on the console; its models then draw their rest frame. */
#include "quakedef.h"
#include "aw_skel.h"
#include "aw_tryalloc.h"
#ifdef AMIGA
#include <proto/exec.h>
#include <exec/memory.h>
/* The toolchain's malloc never returns NULL: when exec has no block for it, its allocator (libc malloc.o,
 * MemMap::alloc) stores through the NULL AllocMem gave it and stops on TRAP #7, a Software Failure #80000027
 * (SKEL-16MB-TRAP-52: the female table at 16 MB of Fast RAM). A table is only asked for when the largest free block
 * holds it with room to spare; otherwise it is refused as unreadable and its models draw their rest frame. */
#define AW_SKEL_ALLOC_SPARE	65536L
static void *table_alloc (long size)
{
	long largest = (long)AvailMem (MEMF_LARGEST);
	if (largest < size + 4 + AW_SKEL_ALLOC_SPARE)
	{
		Con_Printf ("Animation table: no memory for %ld bytes (largest free block %ld)\n", size, largest);
		return NULL;
	}
	return AW_TryMalloc (size);
}
#else
#define table_alloc(size)	AW_TryMalloc (size)
#endif

#define AW_SKEL_TABLES	8

static struct {
	char			name[AW_SKEL_TABLE_NAME];
	unsigned char	*data;
	long			size;
	aw_skel_table_t	table;
	int				failed;
} tables[AW_SKEL_TABLES];

/* Every table given back (aw_skel_release.c, before a room takes Fast RAM): the next lookup loads it again from its
 * file. The caller has flushed every model that points into them. Returns the bytes given back. */
unsigned long AW_SkelTablesRelease (void)
{
	unsigned long given = 0;
	int i;
	for (i=0 ; i<AW_SKEL_TABLES ; i++)
		if (tables[i].data)
		{
			free (tables[i].data);
			given += (unsigned long)tables[i].size;
		}
	memset (tables, 0, sizeof(tables));
	return given;
}

const aw_skel_table_t *AW_SkelTableFor (const char *name)
{
	int i, size;
	FILE *f;
	for (i=0 ; i<AW_SKEL_TABLES && tables[i].name[0] ; i++)
		if (!strcmp (tables[i].name, name))
			return tables[i].failed ? NULL : &tables[i].table;
	if (i == AW_SKEL_TABLES)
		return NULL;		/* more tables than any game has: refuse quietly, the rest frame draws */
	strncpy (tables[i].name, name, AW_SKEL_TABLE_NAME - 1);
	{
		/* "progs/humanoid.awsk|f": a view of a table, its file loaded once with the table's (SKEL-TABLE-SHARED-
		 * FEMALE-52: the female groups live in the common table as "f:..."); its lookups try "f:" + name first */
		const char *bar = strchr (name, '|');
		if (bar)
		{
			char file[AW_SKEL_TABLE_NAME];
			const aw_skel_table_t *of;
			int n = (int)(bar - name);
			if (n <= 0 || n >= AW_SKEL_TABLE_NAME || !bar[1] || strlen (bar + 1) + 2 > AW_SKEL_PREFIX)
			{
				tables[i].failed = 1;
				Con_Printf ("Animation table %s: not a table view\n", name);
				return NULL;
			}
			memcpy (file, name, n);
			file[n] = 0;
			if (!(of = AW_SkelTableFor (file)))
			{
				tables[i].failed = 1;
				return NULL;
			}
			tables[i].table = *of;
			strcpy (tables[i].table.prefix, bar + 1);
			strcat (tables[i].table.prefix, ":");
			return &tables[i].table;
		}
	}
	size = COM_FOpenFile ((char *)name, &f);
	if (!f || size <= 0)
	{
		tables[i].failed = 1;
		Con_Printf ("Animation table %s: not found\n", name);
		return NULL;
	}
	tables[i].data = table_alloc (size);
	tables[i].size = size;
	if (!tables[i].data || fread (tables[i].data, 1, size, f) != (size_t)size ||
		!AW_SkelParse (tables[i].data, size, &tables[i].table))
	{
		fclose (f);
		tables[i].failed = 1;
		Con_Printf ("Animation table %s: unreadable or invalid\n", name);
		return NULL;
	}
	fclose (f);
	return &tables[i].table;
}
