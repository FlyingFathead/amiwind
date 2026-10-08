; AmiWind boot helpers shared by AmiWindCheck and AmiWindFPU. GPL-2.0-or-later.
; Created by FlyingFathead a.k.a. Horstator. Thanks to ChaosWhisperer.
; Include inside a code section after exec/execbase.i, exec/libraries.i and
; lvo/exec_lib.i. Plain 68000 code except the two MOVEC words below, which
; run only after AttnFlags has reported a 68040-class CPU.

; probe_68060: d0 = 1 on a 68060, 0 on other 68040-class CPUs.
; Kickstart 3.1 does not know the 68060: it reports one as a 68040 until a
; 68060.library sets AFF_68060. So read the 68060-only Processor
; Configuration Register (PCR, control register $808) in supervisor mode. A
; 68040 takes an illegal-instruction exception there (unknown MOVEC control
; register); a temporary vector skips the instruction. Interrupts are off
; while the vector is replaced.
probe_68060:
        movem.l d1/a0-a1/a5-a6,-(sp)
        move.l  4.w,a6
        jsr     _LVODisable(a6)
        lea     .supervisor(pc),a5
        jsr     _LVOSupervisor(a6)
        move.l  d0,-(sp)
        jsr     _LVOEnable(a6)
        move.l  (sp)+,d0
        movem.l (sp)+,d1/a0-a1/a5-a6
        rts
.supervisor:
        dc.l    $4e7a8801               ; movec vbr,a0
        move.l  $10(a0),a1              ; vector 4: illegal instruction
        lea     .no_pcr(pc),a5
        move.l  a5,$10(a0)
        moveq   #1,d0
        dc.l    $4e7a1808               ; movec pcr,d1 (68060 only)
        move.l  a1,$10(a0)
        rte
.no_pcr:
        moveq   #0,d0
        addq.l  #4,2(sp)                ; resume after the 4-byte MOVEC
        rte

; find_fpu_library: the FPU support library that is resident now, looked up
; by name in SysBase->LibList under Forbid: 68060.library first, then
; 68040.library. d0 = library base or 0; a1 = its name; d1 = version in the
; high word, revision in the low word (valid only when d0 is not 0).
; Nothing is opened or loaded from disk.
find_fpu_library:
        movem.l a0/a2/a6,-(sp)
        move.l  4.w,a6
        jsr     _LVOForbid(a6)
        lea     fpu_name_060(pc),a2
        lea     LibList(a6),a0
        move.l  a2,a1
        jsr     _LVOFindName(a6)
        tst.l   d0
        bne.s   .found
        lea     fpu_name_040(pc),a2
        lea     LibList(a6),a0
        move.l  a2,a1
        jsr     _LVOFindName(a6)
        tst.l   d0
        beq.s   .done
.found:
        move.l  d0,a0
        move.l  LIB_VERSION(a0),d1      ; LIB_VERSION.w, LIB_REVISION.w
.done:
        movem.l d0-d1,-(sp)
        jsr     _LVOPermit(a6)
        movem.l (sp)+,d0-d1
        move.l  a2,a1
        movem.l (sp)+,a0/a2/a6
        rts

fpu_name_040:   dc.b "68040.library",0
fpu_name_060:   dc.b "68060.library",0
        even
