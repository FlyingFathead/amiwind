; AmiWind FPU support library loader (AmiWindFPU). GPL-2.0-or-later.
; Created by FlyingFathead a.k.a. Horstator. Thanks to ChaosWhisperer.
;
; The startup sequence runs this before AmiWindCheck only when the builder
; copied the user's own 68040.library or 68060.library into LIBS: (build
; option --amiga-libs). A Workbench boot gets this from SetPatch, which opens
; the 68040.library and never closes it; the AmiWind boot disk runs no
; SetPatch, so this program does that one part and nothing else:
; - pick the library for the CPU: 68060.library on a 68060 (AFF_68060, or the
;   PCR probe on Kickstart 3.1, which reports a 68060 as a 68040), otherwise
;   68040.library;
; - OpenLibrary it by name: exec's ramlib loads it from LIBS: and runs its
;   initialisation, which is where these libraries install their FPU
;   exception handlers (F-line for unimplemented instructions, unimplemented
;   data type for denormalized/unnormalized operands) and set the
;   AFF_68881/AFF_68882 emulation flags in AttnFlags;
; - keep it open (never CloseLibrary), so it can never be expunged.
; See docs/FPU_SUPPORT_LIBRARY.md. Prints one line: library, version, CPU and
; AttnFlags ("attn") before and after the open. Returns 0, or 5 (WARN, below
; the startup sequence's FailAt 10) when the library did not open.
        include "exec/execbase.i"
        include "exec/libraries.i"
        include "lvo/exec_lib.i"
        include "lvo/dos_lib.i"

        section code,code
fpulib_start:
        movem.l d2-d7/a2-a6,-(sp)
        moveq   #20,d7
        move.l  4.w,a6
        lea     dos_name(pc),a1
        moveq   #0,d0
        jsr     _LVOOpenLibrary(a6)
        move.l  d0,dos_base
        beq     .finish
        move.l  d0,a6
        jsr     _LVOOutput(a6)
        move.l  d0,output_handle
        moveq   #0,d7
        move.l  4.w,a6
        moveq   #0,d0
        move.w  AttnFlags(a6),d0
        move.l  d0,attn_before
        btst    #AFB_68040,d0
        bne.s   .cpu040
        lea     below_line(pc),a0
        bsr     puts
        bra     .close_dos
.cpu040:
        lea     cpu_040(pc),a2
        lea     fpu_name_040(pc),a3
        btst    #AFB_68060,d0
        bne.s   .cpu060
        bsr     probe_68060
        tst.l   d0
        beq.s   .open
.cpu060:
        lea     cpu_060(pc),a2
        lea     fpu_name_060(pc),a3
.open:
        move.l  4.w,a6
        move.l  a3,a1
        moveq   #0,d0
        jsr     _LVOOpenLibrary(a6)
        lea     report_args,a1
        move.l  a3,(a1)
        tst.l   d0
        beq.s   .missing
        ; Kept open on purpose: the base is never passed to CloseLibrary.
        move.l  d0,a0
        moveq   #0,d1
        move.w  LIB_VERSION(a0),d1
        move.l  d1,4(a1)
        move.w  LIB_REVISION(a0),d1
        move.l  d1,8(a1)
        move.l  a2,12(a1)
        move.l  attn_before,16(a1)
        moveq   #0,d1
        move.w  AttnFlags(a6),d1
        move.l  d1,20(a1)
        lea     opened_format(pc),a0
        bsr     report
        bra.s   .close_dos
.missing:
        move.l  a2,4(a1)
        lea     missing_format(pc),a0
        bsr     report
        moveq   #5,d7
.close_dos:
        move.l  4.w,a6
        move.l  dos_base,a1
        jsr     _LVOCloseLibrary(a6)
.finish:
        move.l  d7,d0
        movem.l (sp)+,d2-d7/a2-a6
        rts

; Format a0 with the longwords at a1 and print the result.
report:
        movem.l d0-d1/a0-a3/a6,-(sp)
        move.l  4.w,a6
        lea     put_char(pc),a2
        lea     report_buffer,a3
        jsr     _LVORawDoFmt(a6)
        lea     report_buffer,a0
        bsr     puts
        movem.l (sp)+,d0-d1/a0-a3/a6
        rts

; RawDoFmt callback includes the terminating zero byte.
put_char:
        move.b  d0,(a3)+
        rts

; Write a NUL-terminated message to the inherited CLI output, if any.
puts:
        movem.l d0-d3/a0-a1/a6,-(sp)
        move.l  output_handle,d1
        beq.s   .done
        move.l  a0,d2
        moveq   #0,d3
.length:
        tst.b   (a0)+
        beq.s   .write
        addq.l  #1,d3
        bra.s   .length
.write:
        move.l  dos_base,a6
        jsr     _LVOWrite(a6)
.done:
        movem.l (sp)+,d0-d3/a0-a1/a6
        rts

        include "fpu_support_inc.asm"

dos_name:       dc.b "dos.library",0
cpu_040:        dc.b "68040",0
cpu_060:        dc.b "68060",0
; Each line fits the 64-column boot console, even with a version like 46.16.
opened_format:  dc.b "FPU support: %s %ld.%ld open (%s) attn $%04lx>$%04lx",10,0
missing_format: dc.b "FPU support: %s not opened (%s): absent/refused",10,0
below_line:     dc.b "FPU support: not loaded (CPU below 68040)",10,0
        even
        section storage,bss
dos_base:       ds.l 1
output_handle:  ds.l 1
attn_before:    ds.l 1
report_args:    ds.l 6
report_buffer:  ds.b 160
