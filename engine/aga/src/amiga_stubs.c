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

// REST-CUT-TOO-OFTEN-67: the machine's clocks for the boot seed (host.c boot_seed, once at the end of Host_Init):
// DateStamp (a battery clock's date and time; an emulated A1200 has none, so it counts from boot) and the E-clock's
// count since boot (its low word moves 709379 times a second, so two boots differ in it), mixed by the caller.
unsigned long AW_ClockSeed(void) {
    struct DateStamp stamp;
    unsigned long h;
    DateStamp(&stamp);
    h = ((unsigned long)stamp.ds_Days * 1440UL + (unsigned long)stamp.ds_Minute) * 3000UL + (unsigned long)stamp.ds_Tick;
#ifndef __PPC__
    if (TimerBase != NULL) {
        struct EClockVal eclock;
        ReadEClock(&eclock);
        h ^= (unsigned long)eclock.ev_lo * 2654435761UL ^ (unsigned long)eclock.ev_hi * 2246822519UL;
    }
#endif
    return h & 0xffffffffUL;
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
