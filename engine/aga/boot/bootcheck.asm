; AmiWind startup preflight. GPL-2.0-or-later.
; Created by FlyingFathead a.k.a. Horstator. Thanks to ChaosWhisperer.
; Runs on a 68000, before loading the 68040 engine or its C runtime.
; NDK includes supply public structure offsets, flags and library vectors.
        include "exec/execbase.i"
        include "exec/memory.i"
        include "graphics/gfxbase.i"
        include "lvo/exec_lib.i"
        include "lvo/dos_lib.i"
        include "lvo/graphics_lib.i"

        section code,code
bootcheck_start:
        movem.l d2-d7/a2-a6,-(sp)
        moveq   #20,d7
        move.l  4.w,a6
        lea     dos_name(pc),a1
        moveq   #0,d0
        jsr     _LVOOpenLibrary(a6)
        move.l  d0,dos_base
        beq     finish
        move.l  d0,a6
        jsr     _LVOOutput(a6)
        move.l  d0,output_handle
        beq     close_dos
        lea     banner(pc),a0
        bsr     puts
        lea     credits(pc),a0
        bsr     puts

        ; MEMF_TOTAL and later graphics fields are read only on OS 3.1+.
        ; The Exec library version is observable from the guest. The exact ROM
        ; build (for example the reference A1200 40.68 image) is checked by the
        ; host launcher using SHA-256 because exec.library's revision is not the
        ; same thing as the Kickstart ROM build revision.
        move.l  4.w,a6
        moveq   #0,d0
        move.w  LIB_VERSION(a6),d0
        move.l  d0,version_values
        moveq   #0,d0
        move.w  LIB_REVISION(a6),d0
        move.l  d0,version_values+4
        cmp.w   #40,LIB_VERSION(a6)
        bhs     .os_ok
        lea     exec_fail_format(pc),a0
        bsr     format_version
        lea     need_os(pc),a0
        bsr     puts
        bra     failed
.os_ok:
        moveq   #0,d7
        lea     exec_ok_format(pc),a0
        bsr     format_version

        move.w  AttnFlags(a6),d3
        btst    #AFB_68040,d3
        bne     .cpu_ok
        lea     cpu_fail_line(pc),a0
        bsr     puts
        moveq   #20,d7
        bra     .fpu_check
.cpu_ok:
        lea     cpu_ok_line(pc),a0
        bsr     puts
.fpu_check:
        btst    #AFB_FPU40,d3
        bne     .fpu_ok
        lea     fpu_fail_line(pc),a0
        bsr     puts
        moveq   #20,d7
        bra     .video_check
.fpu_ok:
        lea     fpu_ok_line(pc),a0
        bsr     puts

.video_check:
        ; AmiWind's accelerated reference profile is PAL. Do not hard-fail an
        ; otherwise capable machine here; report a visible warning instead.
        move.l  4.w,a6
        cmp.b   #50,VBlankFrequency(a6)
        beq     .pal_ok
        lea     video_warn_line(pc),a0
        bsr     puts
        bra     .aga_check
.pal_ok:
        lea     video_ok_line(pc),a0
        bsr     puts

.aga_check:
        move.l  4.w,a6
        lea     graphics_name(pc),a1
        moveq   #40,d0
        jsr     _LVOOpenLibrary(a6)
        tst.l   d0
        beq     .aga_fail
        ; Bare-ROM boot has not run graphics initialization from SetPatch.
        ; Ask graphics.library to enable/report the best available chipset.
        move.l  d0,a2
        move.l  d0,a6
        moveq   #-1,d0
        jsr     _LVOSetChipRev(a6)
        move.l  d0,d2
        move.l  4.w,a6
        move.l  a2,a1
        jsr     _LVOCloseLibrary(a6)
        and.w   #GFXF_AA_ALICE!GFXF_AA_LISA,d2
        cmp.w   #GFXF_AA_ALICE!GFXF_AA_LISA,d2
        bne     .aga_fail
        lea     aga_ok_line(pc),a0
        bsr     puts
        bra     .memory_check
.aga_fail:
        lea     aga_fail_line(pc),a0
        bsr     puts
        lea     need_aga(pc),a0
        bsr     puts
        moveq   #20,d7

.memory_check:
        ; Query six values: installed/free/largest for each memory pool.
        lea     memory_flags(pc),a2
        lea     memory_bytes,a3
        lea     memory_kib,a4
        moveq   #5,d2
.memory:
        move.l  (a2)+,d1
        move.l  4.w,a6
        jsr     _LVOAvailMem(a6)
        move.l  d0,(a3)+
        lsr.l   #8,d0
        lsr.l   #2,d0
        move.l  d0,(a4)+
        dbra    d2,.memory

        ; These are conservative startup budgets, not measured minima.
        ; Exec excludes some reserved bytes from MEMF_TOTAL, so use 1984 KiB
        ; to recognize a physical 2 MiB Chip pool (never require exact equality).
        lea     memory_bytes,a0
        cmp.l   #1984*1024,(a0)
        blo     .chip_fail
        cmp.l   #512*1024,4(a0)
        blo     .chip_fail
        cmp.l   #256*1024,8(a0)
        blo     .chip_fail
        lea     chip_ok_format(pc),a0
        lea     memory_kib,a1
        bsr     format_memory
        bra     .fast_check
.chip_fail:
        lea     chip_fail_format(pc),a0
        lea     memory_kib,a1
        bsr     format_memory
        lea     need_chip(pc),a0
        bsr     puts
        moveq   #20,d7

.fast_check:
        lea     memory_bytes,a0
        cmp.l   #14*1024*1024,16(a0)
        blo     .fast_fail
        cmp.l   #11*1024*1024+16,20(a0)
        blo     .fast_fail
        lea     fast_ok_format(pc),a0
        lea     memory_kib+12,a1
        bsr     format_memory
        lea     address_ok_line(pc),a0
        bsr     puts
        bra     .host_notes
.fast_fail:
        lea     fast_fail_format(pc),a0
        lea     memory_kib+12,a1
        bsr     format_memory
        lea     address_fail_line(pc),a0
        bsr     puts
        lea     need_fast(pc),a0
        bsr     puts
        moveq   #20,d7

.host_notes:
        ; UAE host policy is intentionally not guessed from guest state. The
        ; portable launcher validates the requested FS-UAE profile before launch.
        lea     host_speed_line(pc),a0
        bsr     puts
        lea     host_cycle_line(pc),a0
        bsr     puts
        lea     host_rom_line(pc),a0
        bsr     puts
        lea     separator(pc),a0
        bsr     puts

        tst.l   d7
        bne     failed
        lea     passed(pc),a0
        bsr     puts
        bsr     countdown
        bra     close_dos
failed:
        lea     stopped(pc),a0
        bsr     puts
        moveq   #20,d7
close_dos:
        move.l  4.w,a6
        move.l  dos_base,a1
        jsr     _LVOCloseLibrary(a6)
finish:
        move.l  d7,d0
        movem.l (sp)+,d2-d7/a2-a6
        rts

; Keep the successful preflight visible briefly without relying on console
; scrollback. WaitForChar uses DOS/timer time, so accelerated CPU/JIT execution
; does not collapse the delay into a tight busy loop. SPACE or Enter skips it.
countdown:
        movem.l d0-d4/a0-a3/a6,-(sp)
        move.l  dos_base,a6
        jsr     _LVOInput(a6)
        move.l  d0,input_handle
        moveq   #5,d4
.loop:
        move.l  d4,countdown_value
        move.l  4.w,a6
        lea     countdown_format(pc),a0
        lea     countdown_value,a1
        lea     put_char(pc),a2
        lea     report_buffer,a3
        jsr     _LVORawDoFmt(a6)
        lea     report_buffer,a0
        bsr     puts

        move.l  input_handle,d1
        beq.s   .no_input
        move.l  #1000000,d2
        move.l  dos_base,a6
        jsr     _LVOWaitForChar(a6)
        tst.l   d0
        beq.s   .next

        move.l  input_handle,d1
        lea     input_byte,a0
        move.l  a0,d2
        moveq   #1,d3
        jsr     _LVORead(a6)
        cmp.l   #1,d0
        bne.s   .next
        moveq   #0,d0
        move.b  input_byte,d0
        cmp.b   #' ',d0
        beq.s   .done
        cmp.b   #13,d0
        beq.s   .done
        cmp.b   #10,d0
        beq.s   .done
        bra.s   .next

.no_input:
        ; An inherited console normally supplies an input handle. If it does not,
        ; use dos.library Delay() as a non-busy one-second fallback.
        moveq   #50,d1
        move.l  dos_base,a6
        jsr     _LVODelay(a6)
.next:
        subq.l  #1,d4
        bne.w   .loop
.done:
        lea     countdown_done(pc),a0
        bsr     puts
        movem.l (sp)+,d0-d4/a0-a3/a6
        rts

; Format the two longword Exec version fields and print the result.
format_version:
        move.l  4.w,a6
        lea     version_values,a1
        lea     put_char(pc),a2
        lea     report_buffer,a3
        jsr     _LVORawDoFmt(a6)
        lea     report_buffer,a0
        bsr     puts
        rts

; Format installed/free/largest KiB. a0=format, a1=three longwords.
format_memory:
        move.l  4.w,a6
        lea     put_char(pc),a2
        lea     report_buffer,a3
        jsr     _LVORawDoFmt(a6)
        lea     report_buffer,a0
        bsr     puts
        rts

; RawDoFmt callback includes the terminating zero byte.
put_char:
        move.b  d0,(a3)+
        rts

; Write a NUL-terminated message to the inherited CLI output.
puts:
        movem.l d0-d3/a0-a1/a6,-(sp)
        move.l  a0,d2
        moveq   #0,d3
.length:
        tst.b   (a0)+
        beq     .write
        addq.l  #1,d3
        bra     .length
.write:
        move.l  output_handle,d1
        move.l  dos_base,a6
        jsr     _LVOWrite(a6)
        movem.l (sp)+,d0-d3/a0-a1/a6
        rts

dos_name:       dc.b "dos.library",0
graphics_name:  dc.b "graphics.library",0
                include "amiwind_version.i"
credits:        dc.b "By FlyingFathead",10
                dc.b "https://github.com/FlyingFathead/amiwind/",10
                dc.b "Special thanks to: ChaosWhisperer",10,0
separator:      dc.b "----------------------------------------------",10,0
exec_ok_format: dc.b "Exec API:             %ld.%ld (Kickstart 3.1+) [x] OK",10,0
exec_fail_format: dc.b "Exec API:             %ld.%ld                    [!] FAIL",10,0
cpu_ok_line:    dc.b "CPU:                  68040/68060 class          [x] OK",10,0
cpu_fail_line:  dc.b "CPU:                  below 68040 class          [!] FAIL",10,0
fpu_ok_line:    dc.b "FPU:                  internal 040/060 compatible [x] OK",10,0
fpu_fail_line:  dc.b "FPU:                  required internal FPU absent [!] FAIL",10,0
video_ok_line:  dc.b "Video timing:         PAL / 50 Hz                [x] OK",10,0
video_warn_line:dc.b "Video timing:         not PAL / 50 Hz            [!] WARN",10,0
aga_ok_line:    dc.b "Machine class:        AGA / A1200-compatible     [x] OK",10,0
aga_fail_line:  dc.b "Machine class:        AGA not detected           [!] FAIL",10,0
chip_ok_format: dc.b "Chip RAM KiB:         %ld total, %ld free, %ld largest [x] OK",10,0
chip_fail_format: dc.b "Chip RAM KiB:         %ld total, %ld free, %ld largest [!] FAIL",10,0
fast_ok_format: dc.b "Fast RAM KiB:         %ld total, %ld free, %ld largest [x] OK",10,0
fast_fail_format: dc.b "Fast RAM KiB:         %ld total, %ld free, %ld largest [!] FAIL",10,0
address_ok_line: dc.b "32-bit / Z3 memory:   usable                     [x] OK",10,0
address_fail_line: dc.b "32-bit / Z3 memory:   required Fast RAM unavailable [!] FAIL",10,0
host_speed_line: dc.b "JIT / CPU speed:      host-side; see launcher    [?] HOST",10,0
host_cycle_line: dc.b "Cycle-exact mode:     host-side; see launcher    [?] HOST",10,0
host_rom_line:   dc.b "Exact ROM revision:   host SHA-256 check         [?] HOST",10,0
countdown_format: dc.b 13,"Continuing in %ld seconds. Press SPACE or ENTER to continue now.   ",0
countdown_done:   dc.b 13,"Continuing now.                                                ",10,0
need_os:        dc.b "FAIL: this AGA build needs Kickstart 3.1 or newer.",10,0
need_aga:       dc.b "FAIL: this build needs the AGA chipset.",10,0
need_chip:      dc.b "FAIL: select 2 MB Chip; keep 512 KiB free (256 KiB contiguous).",10,0
need_fast:      dc.b "FAIL: select 16 MB Fast RAM or more.",10
                dc.b "      Need 14 MiB free; 11 MiB + 16 bytes must be contiguous.",10,0
        even
memory_flags:
        dc.l    MEMF_CHIP!MEMF_TOTAL,MEMF_CHIP,MEMF_CHIP!MEMF_LARGEST
        dc.l    MEMF_FAST!MEMF_TOTAL,MEMF_FAST,MEMF_FAST!MEMF_LARGEST
        section storage,bss
dos_base:       ds.l 1
output_handle:  ds.l 1
input_handle:   ds.l 1
input_byte:     ds.b 1
                even
countdown_value: ds.l 1
version_values: ds.l 2
memory_bytes:   ds.l 6
memory_kib:     ds.l 6
report_buffer:  ds.b 256
