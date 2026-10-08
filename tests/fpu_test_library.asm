; AmiWind synthetic test library. GPL-2.0-or-later.
; Created by FlyingFathead a.k.a. Horstator. Thanks to ChaosWhisperer.
;
; A minimal, valid Amiga shared library of our own that does nothing but
; open: no FPU code, no exception handlers, no patches. It is assembled under
; the name of an FPU support library only to test AmiWindFPU and the boot
; check in an emulator without any vendor file:
;   vasmm68k_mot -m68000 -Fhunkexe -nosym -I <NDK> [-DCPU060=1] -o 68040.library
; Version 1.0 and the id string tell it apart from a real support library.
; Expunge is refused, like a support library that must stay resident.
        include "exec/types.i"
        include "exec/nodes.i"
        include "exec/resident.i"
        include "exec/libraries.i"

        ifnd    CPU060
CPU060  equ     0
        endc
TEST_VERSION  equ 1
TEST_REVISION equ 0

        section code,code
not_executable:
        moveq   #-1,d0
        rts

romtag:
        dc.w    RTC_MATCHWORD
        dc.l    romtag
        dc.l    end_skip
        dc.b    RTF_AUTOINIT
        dc.b    TEST_VERSION
        dc.b    NT_LIBRARY
        dc.b    0
        dc.l    library_name
        dc.l    library_id
        dc.l    init_table

init_table:
        dc.l    LIB_SIZE+4              ; base plus the segment list
        dc.l    function_table
        dc.l    0
        dc.l    init_routine

function_table:
        dc.l    library_open
        dc.l    library_close
        dc.l    library_expunge
        dc.l    library_reserved
        dc.l    -1

; d0 = library base, a0 = segment list, a6 = SysBase. Returns the base.
init_routine:
        move.l  a1,-(sp)
        move.l  d0,a1
        move.b  #NT_LIBRARY,LN_TYPE(a1)
        move.l  #library_name,LN_NAME(a1)
        move.b  #LIBF_SUMUSED!LIBF_CHANGED,LIB_FLAGS(a1)
        move.w  #TEST_VERSION,LIB_VERSION(a1)
        move.w  #TEST_REVISION,LIB_REVISION(a1)
        move.l  #library_id,LIB_IDSTRING(a1)
        move.l  a0,LIB_SIZE(a1)
        move.l  (sp)+,a1
        rts

; a6 = library base.
library_open:
        addq.w  #1,LIB_OPENCNT(a6)
        bclr    #LIBB_DELEXP,LIB_FLAGS(a6)
        move.l  a6,d0
        rts

library_close:
        subq.w  #1,LIB_OPENCNT(a6)
        moveq   #0,d0
        rts

library_expunge:
        bset    #LIBB_DELEXP,LIB_FLAGS(a6)
        moveq   #0,d0
        rts

library_reserved:
        moveq   #0,d0
        rts

        ifne    CPU060
library_name:   dc.b "68060.library",0
        else
library_name:   dc.b "68040.library",0
        endc
library_id:     dc.b "amiwind test library 1.0 (does nothing)",13,10,0
        even
end_skip:
