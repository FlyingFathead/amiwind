// Stub implementations for Amiga-specific assembly functions
// These would normally be implemented in assembly for performance

#include <exec/types.h>
#include <graphics/gfx.h>
#include <devices/timer.h>
#include <proto/timer.h>

// Timer implementation using EClock
#ifndef __PPC__
extern struct Device *TimerBase;
extern ULONG eclocks_per_second;
#endif

void timer(ULONG *clock) {
#ifndef __PPC__
    struct EClockVal eclock;

    if (TimerBase != NULL && eclocks_per_second > 0) {
        ReadEClock(&eclock);

        // Convert 64-bit EClock ticks to seconds + microseconds
        // ev_hi:ev_lo is the tick count, divide by frequency to get time
        unsigned long long ticks = ((unsigned long long)eclock.ev_hi << 32) | eclock.ev_lo;
        unsigned long long seconds = ticks / eclocks_per_second;
        unsigned long long remainder = ticks % eclocks_per_second;
        unsigned long long microseconds = (remainder * 1000000ULL) / eclocks_per_second;

        clock[0] = (ULONG)seconds;
        clock[1] = (ULONG)microseconds;
    } else {
        // Fallback if timer not initialized yet
        static ULONG counter = 0;
        clock[0] = counter++;
        clock[1] = 0;
    }
#else
    // PPC version - fallback
    static ULONG counter = 0;
    clock[0] = counter++;
    clock[1] = 0;
#endif
}

// C2P (Chunky to Planar) conversion functions are now provided by c2p8_040_amlaukka.s
// (removed stubs - using real assembly implementation)

// unlink through dos.library (ENGINE-UNLINK-STUB-35: the old stub deleted
// nothing, so -condebug appended to the previous qconsole.log).
#include <proto/dos.h>
int unlink(const char *path) {
    return DeleteFile((STRPTR)path) ? 0 : -1;
}

// strnicmp - case-insensitive string compare (DOS/Windows name)
// GCC libc has strncasecmp instead
#include <string.h>
#include <ctype.h>

#ifdef strnicmp
#undef strnicmp
#endif
int strnicmp(const char *s1, const char *s2, size_t n) {
    // Use strncasecmp if available, otherwise implement it
    #ifdef __GNUC__
    return strncasecmp(s1, s2, n);
    #else
    // Fallback implementation
    while (n > 0) {
        int c1 = tolower((unsigned char)*s1);
        int c2 = tolower((unsigned char)*s2);
        if (c1 != c2) return c1 - c2;
        if (c1 == 0) return 0;
        s1++; s2++; n--;
    }
    return 0;
    #endif
}
