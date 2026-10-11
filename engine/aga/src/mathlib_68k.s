; AmiWind: upstream AmiQuake (TerribleFire's GCC port, Stephen Leary), src/mathlib_68k.s at revision
; 9c62d905151614af3e788ae3145a0d4ecc8a7bb8, GPL v2 (docs/LICENSING_AND_CREDITS.md). Linked only by the
; upstream engine profile (docs/ENGINE_PROFILES.md); unchanged below this header.
; mathlib_68k.s - FPU-optimized math functions from NovaCoder's AmiQuake v1.36
; Extracted and adapted for GCC m68k-amigaos
; Uses Amiga mathieeedoubtrans.library (like NovaCoder's original)

	MC68040
	MC68882

	XDEF _AngleVectors
	XDEF _InitMathLib

	section	bss,bss
MathLibBase:
	ds.l	1			; Storage for library base pointer

	section	data,data

Deg2RadConst:
	dc.l	$3f91df46,$a2529d39	; M_PI*2/360 = 0.017453292519943295

	section	text,code

MathLibName:
	dc.b	"mathieeedoubtrans.library",0
	EVEN

;==============================================================================
; _InitMathLib - Initialize math library (call once at startup)
;==============================================================================
	XREF _SysBase
_InitMathLib:
	movem.l	d0/d1/a0/a1/a6,-(sp)

	; Check if already open
	lea	MathLibBase(pc),a0
	tst.l	(a0)
	bne.s	.already_open

	; Open mathieeedoubtrans.library
	move.l	_SysBase,a6
	lea	MathLibName(pc),a1
	moveq	#0,d0			; any version
	jsr	-552(a6)		; OpenLibrary

	; Save library base
	lea	MathLibBase(pc),a0
	move.l	d0,(a0)

.already_open:
	movem.l	(sp)+,d0/d1/a0/a1/a6
	rts

;==============================================================================
; _NCSin - Call Amiga mathieeedoubtrans.library IEEEDPSin
;==============================================================================
; Input: D0:D1 = double parameter (passed on stack)
; Output: D0:D1 = double result
;==============================================================================
_NCSin:
	movem.l	a6,-(sp)

	; Load parameter from stack into D0:D1
	move.l	(8,sp),d0		; High word
	move.l	(12,sp),d1		; Low word

	; Call IEEEDPSin
	lea	MathLibBase(pc),a6
	move.l	(a6),a6
	jsr	-36(a6)			; IEEEDPSin

	movem.l	(sp)+,a6
	rts

;==============================================================================
; _NCCos - Call Amiga mathieeedoubtrans.library IEEEDPCos
;==============================================================================
; Input: D0:D1 = double parameter (passed on stack)
; Output: D0:D1 = double result
;==============================================================================
_NCCos:
	movem.l	a6,-(sp)

	; Load parameter from stack into D0:D1
	move.l	(8,sp),d0		; High word
	move.l	(12,sp),d1		; Low word

	; Call IEEEDPCos
	lea	MathLibBase(pc),a6
	move.l	(a6),a6
	jsr	-42(a6)			; IEEEDPCos

	movem.l	(sp)+,a6
	rts

;==============================================================================
; AngleVectors - Convert Euler angles to directional vectors
;==============================================================================
; NovaCoder's optimized implementation from AmiQuake v1.36 @ 0x00235dca
; Calls Amiga mathieeedoubtrans.library functions (IEEEDPSin/IEEEDPCos)
;
; void AngleVectors(vec3_t angles, vec3_t forward, vec3_t right, vec3_t up)
;==============================================================================
_AngleVectors:
	link.w	a5,#0
	fmovem.x fp2/fp3/fp4/fp5/fp6/fp7,-(sp)
	movem.l	d2/d3/d4/d5/d6/d7/a2/a3/a4/a6,-(sp)

	; No library opening needed - using GCC libm

	; Load parameters from stack
	movea.l	(8,a5),a4		; a4 = angles
	movea.l	(12,a5),a6		; a6 = forward
	move.l	(16,a5),d6		; d6 = right
	move.l	(20,a5),d7		; d7 = up

	; Load deg2rad constant from memory
	lea	Deg2RadConst,a0
	fmove.d	(a0),fp2

	;----------------------------------------------------------------------
	; Calculate YAW (angles[1])
	;----------------------------------------------------------------------
	fdmove.s (4,a4),fp0		; fp0 = angles[YAW]
	fdmul	fp2,fp0			; fp0 *= deg2rad
	fsmove	fp0,fp0			; convert to single
	fmove.d	fp0,-(sp)		; convert back to double
	move.l	(sp)+,d2		; d2:d3 = parameter
	move.l	(sp)+,d3

	; Call sin(yaw) via wrapper - parameter in D2:D3, result in D0:D1
	move.l	d3,-(sp)
	move.l	d2,-(sp)
	bsr	_NCSin
	move.l	d1,-(sp)		; Convert D0:D1 to FP0
	move.l	d0,-(sp)
	fdmove.d (sp)+,fp0
	fsmove	fp0,fp0
	fmove.s	fp0,d5			; d5 = sy (sin yaw)

	; Call cos(yaw) via wrapper
	move.l	d2,(sp)
	move.l	d3,(4,sp)
	bsr	_NCCos
	addq.l	#8,sp
	move.l	d1,-(sp)		; Convert D0:D1 to FP0
	move.l	d0,-(sp)
	fdmove.d (sp)+,fp0
	fsmove	fp0,fp7			; fp7 = cy (cos yaw)

	;----------------------------------------------------------------------
	; Calculate PITCH (angles[0])
	;----------------------------------------------------------------------
	fdmove.s (a4),fp0		; fp0 = angles[PITCH]
	fdmul	fp2,fp0
	fsmove	fp0,fp0
	fmove.d	fp0,-(sp)
	move.l	(sp)+,d2
	move.l	(sp)+,d3

	move.l	d2,(sp)
	move.l	d3,(4,sp)
	bsr	_NCSin
	move.l	d1,-(sp)
	move.l	d0,-(sp)
	fdmove.d (sp)+,fp0
	fsmove	fp0,fp0
	fmove.s	fp0,d4			; d4 = sp (sin pitch)

	move.l	d2,(sp)
	move.l	d3,(4,sp)
	bsr	_NCCos
	move.l	d1,-(sp)
	move.l	d0,-(sp)
	fdmove.d (sp)+,fp0
	fsmove	fp0,fp6			; fp6 = cp (cos pitch)

	;----------------------------------------------------------------------
	; Calculate ROLL (angles[2])
	;----------------------------------------------------------------------
	fdmove.s (8,a4),fp0		; fp0 = angles[ROLL]
	fdmul	fp2,fp0
	fsmove	fp0,fp0
	fmove.d	fp0,-(sp)
	move.l	(sp)+,d2
	move.l	(sp)+,d3

	move.l	d2,(sp)
	move.l	d3,(4,sp)
	bsr	_NCSin
	move.l	d1,-(sp)
	move.l	d0,-(sp)
	fdmove.d (sp)+,fp0
	fsmove	fp0,fp4			; fp4 = sr (sin roll)

	move.l	d2,(sp)
	move.l	d3,(4,sp)
	bsr	_NCCos
	addq.l	#8,sp
	move.l	d1,-(sp)
	move.l	d0,-(sp)
	fdmove.d (sp)+,fp0
	fsmove	fp0,fp5			; fp5 = cr (cos roll)

	;----------------------------------------------------------------------
	; Calculate forward vector
	;----------------------------------------------------------------------
	; forward[0] = cp*cy
	fsmove	fp6,fp0
	fsmul	fp7,fp0
	fmove.s	fp0,(a6)

	; forward[1] = cp*sy
	fsmove	fp6,fp0
	fsmul.s	d5,fp0
	fmove.s	fp0,(4,a6)

	; forward[2] = -sp
	fsneg.s	d4,fp0
	fmove.s	fp0,(8,a6)

	;----------------------------------------------------------------------
	; Calculate right vector
	;----------------------------------------------------------------------
	fsneg	fp4,fp3			; fp3 = -sr

	; right[0] = -sr*sp*cy + cr*sy
	fsmove	fp3,fp1
	fsmul.s	d4,fp1
	fsmove	fp1,fp2
	fsmul	fp7,fp2
	fsmove	fp5,fp0
	fsmul.s	d5,fp0
	fsadd	fp0,fp2
	movea.l	d6,a0
	fmove.s	fp2,(a0)

	; right[1] = -sr*sp*sy - cr*cy
	fsmul.s	d5,fp1
	fsmove	fp5,fp0
	fsmul	fp7,fp0
	fssub.x	fp0,fp1
	fmove.s	fp1,(4,a0)

	; right[2] = -sr*cp
	fsmove	fp3,fp0
	fsmul	fp6,fp0
	fmove.s	fp0,(8,a0)

	;----------------------------------------------------------------------
	; Calculate up vector
	;----------------------------------------------------------------------
	; up[0] = cr*sp*cy + sr*sy
	fsmove	fp5,fp0
	fsmul.s	d4,fp0
	fsmove	fp0,fp1
	fsmul	fp7,fp1
	fsmul.s	d5,fp4
	fsadd	fp4,fp1
	movea.l	d7,a0
	fmove.s	fp1,(a0)

	; up[1] = cr*sp*sy - sr*cy
	fsmul.s	d5,fp0
	fsmul	fp7,fp3
	fsadd	fp3,fp0
	fmove.s	fp0,(4,a0)

	; up[2] = cr*cp
	fsmul	fp6,fp5
	fmove.s	fp5,(8,a0)

	; Don't close library - keep it open for next call

.exit:
	; Restore registers (NovaCoder's original register list)
	movem.l	(-112,a5),d2/d3/d4/d5/d6/d7/a2/a3/a4/a6
	fmovem.x (-72,a5),fp2/fp3/fp4/fp5/fp6/fp7
	unlk	a5
	rts

	end
