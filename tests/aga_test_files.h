/* SPDX-License-Identifier: GPL-2.0-or-later */
/* C fixtures run inside Python's TemporaryDirectory, which honors TMPDIR.
 * libc tmpfile() may ignore TMPDIR and use a different, exhausted filesystem.
 * Keep the same seekable, automatically removed stream behavior locally. */
#ifndef AGA_TEST_FILES_H
#define AGA_TEST_FILES_H
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static FILE *AW_TestTmpfile(void)
{
    char name[] = "aw-fixture-XXXXXX";
    int fd = mkstemp(name);
    FILE *file;
    if (fd < 0)
        return NULL;
    if (unlink(name)) {
        close(fd);
        return NULL;
    }
    file = fdopen(fd, "w+b");
    if (!file)
        close(fd);
    return file;
}

#define tmpfile AW_TestTmpfile
#endif
