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

        ; MEMF_TOTAL and later graphics fields are read only on OS 3.1+.
        move.l  4.w,a6
        cmp.w   #40,LIB_VERSION(a6)
        bhs.s   .os_ok
        lea     need_os(pc),a0
        bsr     puts
        bra     failed
.os_ok:
        moveq   #0,d7
        move.w  AttnFlags(a6),d0
        btst    #AFB_68040,d0
        beq.s   .cpu_fail
        btst    #AFB_FPU40,d0
        bne.s   .cpu_ok
.cpu_fail:
        lea     need_cpu(pc),a0
        bsr     puts
        moveq   #20,d7
.cpu_ok:
        move.l  4.w,a6
        lea     graphics_name(pc),a1
        moveq   #40,d0
        jsr     _LVOOpenLibrary(a6)
        tst.l   d0
        beq.s   .aga_fail
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
        beq.s   .aga_ok
.aga_fail:
        lea     need_aga(pc),a0
        bsr     puts
        moveq   #20,d7
.aga_ok:
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

        lea     memory_format(pc),a0
        lea     memory_kib,a1
        lea     put_char(pc),a2
        lea     report_buffer,a3
        jsr     _LVORawDoFmt(a6)
        lea     report_buffer,a0
        bsr     puts

        ; These are conservative startup budgets, not measured minima.
        ; Exec excludes some reserved bytes from MEMF_TOTAL, so use 1984 KiB
        ; to recognize a physical 2 MiB Chip pool (never require exact equality).
        lea     memory_bytes,a0
        cmp.l   #1984*1024,(a0)
        blo.s   .chip_fail
        cmp.l   #512*1024,4(a0)
        blo.s   .chip_fail
        cmp.l   #256*1024,8(a0)
        bhs.s   .chip_ok
.chip_fail:
        lea     need_chip(pc),a0
        bsr     puts
        moveq   #20,d7
.chip_ok:
        lea     memory_bytes,a0
        cmp.l   #12*1024*1024,16(a0)
        blo.s   .fast_fail
        cmp.l   #9*1024*1024+16,20(a0)
        bhs.s   .fast_ok
.fast_fail:
        lea     need_fast(pc),a0
        bsr     puts
        moveq   #20,d7
.fast_ok:
        tst.l   d7
        bne.s   failed
        lea     passed(pc),a0
        bsr     puts
        bra.s   close_dos
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
        beq.s   .write
        addq.l  #1,d3
        bra.s   .length
.write:
        move.l  output_handle,d1
        move.l  dos_base,a6
        jsr     _LVOWrite(a6)
        movem.l (sp)+,d0-d3/a0-a1/a6
        rts

dos_name:       dc.b "dos.library",0
graphics_name:  dc.b "graphics.library",0
               include "amiwind_version.i"
               dc.b "By FlyingFathead +- ChaosWhisperer",10
               dc.b "https://github.com/FlyingFathead/amiwind/",10
               dc.b "Hardware preflight",10,0
need_os:       dc.b "FAIL: this AGA build needs Kickstart 3.1 or newer.",10,0
need_cpu:      dc.b "FAIL: this build needs a 68040/68060 with internal FPU.",10,0
need_aga:      dc.b "FAIL: this build needs the AGA chipset.",10,0
need_chip:     dc.b "FAIL: select 2 MB Chip; keep 512 KiB free (256 KiB contiguous).",10,0
need_fast:     dc.b "FAIL: select 16 MB Fast RAM or more.",10
               dc.b "      Need 12 MiB free; 9 MiB + 16 bytes must be contiguous.",10,0
memory_format: dc.b "Chip KiB: installed %ld, free %ld, largest %ld",10
               dc.b "Fast KiB: installed %ld, free %ld, largest %ld",10,0
passed:        dc.b "Preflight OK. Starting the engine...",10,0
stopped:       dc.b "AmiWind was not loaded. Change settings and reboot.",10,0
        even
memory_flags:
        dc.l    MEMF_CHIP!MEMF_TOTAL,MEMF_CHIP,MEMF_CHIP!MEMF_LARGEST
        dc.l    MEMF_FAST!MEMF_TOTAL,MEMF_FAST,MEMF_FAST!MEMF_LARGEST
        section storage,bss
dos_base:      ds.l 1
output_handle: ds.l 1
memory_bytes:  ds.l 6
memory_kib:    ds.l 6
report_buffer: ds.b 192
