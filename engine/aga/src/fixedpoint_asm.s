; AmiWind: upstream AmiQuake (TerribleFire's GCC port, Stephen Leary), src/fixedpoint_asm.s at revision
; 9c62d905151614af3e788ae3145a0d4ecc8a7bb8, GPL v2 (docs/LICENSING_AND_CREDITS.md). Linked only by the
; upstream engine profile (docs/ENGINE_PROFILES.md); unchanged below this header.
;
; Fixed-Point Math Library for AmiQuake Non-FPU Build
; Provides integer-only arithmetic for 68020/68040 without FPU
;
; Formats:
;   16.16: Standard Quake fixed-point (16-bit integer, 16-bit fraction)
;   22.10: Extended range for perspective division (22-bit integer, 10-bit fraction)
;

	XDEF	_FixedMul_Internal
	XDEF	_FixedMul_22_10_Internal
	XDEF	_FixedDiv_Internal
	XDEF	_TestAdd_Internal
	XDEF	_TestIdentity_Internal
	XDEF	_TestDivPassthrough_Internal
	XDEF	_DebugDiv_ReturnD1
	XDEF	_DebugDiv_ReturnD3
	XDEF	_DebugDiv_OneIteration

	section	text,code

;
; TestAdd_Internal - Simple test function: returns a + b
; Used to verify calling conventions
;
; Entry: D0 = a, D1 = b
; Exit: D0 = a + b
;
_TestAdd_Internal:
	add.l	d1,d0
	rts

;
; TestIdentity_Internal - Simple test function: returns input unchanged
; Used to verify calling conventions
;
; Entry: D0 = value
; Exit: D0 = value (unchanged)
;
_TestIdentity_Internal:
	rts

;
; TestDivPassthrough_Internal - Test division wrapper
; Just returns input unchanged to verify division calling convention
;
; Entry: D0 = value
; Exit: D0 = value (unchanged)
;
_TestDivPassthrough_Internal:
	rts

;
; Debug functions to trace division behavior
;
_DebugDiv_ReturnD1:
	; Run full division, return D1 (quotient before final move)
	moveq	#0,d1
	moveq	#31,d2
	move.l	#$10,d3		; Correct numerator
	moveq	#0,d4
.loop:
	add.l	d1,d1
	add.l	d4,d4
	addx.l	d3,d3
	cmp.l	d0,d3
	bcs.s	.no_sub
	sub.l	d0,d3
	addq.l	#1,d1
.no_sub:
	dbf	d2,.loop
	move.l	d1,d0		; Return D1
	rts

_DebugDiv_ReturnD3:
	; Return D3 after first shift to see intermediate remainder
	moveq	#0,d1
	move.l	#$10,d3
	moveq	#0,d4
	; Do first iteration
	add.l	d1,d1
	add.l	d4,d4
	addx.l	d3,d3
	move.l	d3,d0		; Return shifted D3
	rts

_DebugDiv_OneIteration:
	; Run one iteration and return quotient
	moveq	#0,d1
	move.l	#$10,d3
	moveq	#0,d4
	; Iteration
	add.l	d1,d1
	add.l	d4,d4
	addx.l	d3,d3
	cmp.l	d0,d3
	bcs.s	.skip
	sub.l	d0,d3
	addq.l	#1,d1
.skip:
	move.l	d1,d0		; Return quotient after one iteration
	rts

;
; FixedMul - Multiply two 16.16 fixed-point numbers
;
; Entry:
;   D0 = multiplicand (16.16 fixed-point)
;   D1 = multiplier (16.16 fixed-point)
;
; Exit:
;   D0 = result (16.16 fixed-point)
;   D2 = clobbered
;
; Formula: result = (a * b) >> 16
;
_FixedMul_Internal:
	move.l	d2,-(sp)	; Save D2 (preserved register)

	muls.l	d1,d2:d0	; 32×32→64-bit signed multiply
				; D2:D0 = full 64-bit product

	; Extract middle 32 bits (shift right by 16)
	; We want bits 16-47 of the 64-bit result

	lsl.l	#8,d2		; Shift high word left 8
	lsl.l	#8,d2		; (total 16 bits)
	lsr.l	#8,d0		; Shift low word right 8
	lsr.l	#8,d0		; (total 16 bits)
	or.l	d2,d0		; Combine: D0 = (D2 << 16) | (D0 >> 16)

	move.l	(sp)+,d2	; Restore D2
	rts

;
; FixedMul_22_10 - Multiply two 22.10 fixed-point numbers
;
; Entry:
;   D0 = multiplicand (22.10 fixed-point)
;   D1 = multiplier (22.10 fixed-point)
;
; Exit:
;   D0 = result (22.10 fixed-point)
;   D2 = clobbered
;
; Formula: result = (a * b) >> 10
;
_FixedMul_22_10_Internal:
	move.l	d2,-(sp)	; Save D2 (preserved register)

	muls.l	d1,d2:d0	; 32×32→64-bit signed multiply
				; D2:D0 = full 64-bit product

	; Extract middle 32 bits (shift right by 10)
	; We want bits 10-41 of the 64-bit result

	lsl.l	#8,d2		; Shift high left 8
	lsl.l	#2,d2		; Shift high left 2 more (total 10)
	lsl.l	#8,d2		; Shift high left 8 more (total 18)
	lsl.l	#4,d2		; Shift high left 4 more (total 22)

	lsr.l	#2,d0		; Shift low right 2
	lsr.l	#8,d0		; Shift low right 8 more (total 10)

	or.l	d2,d0		; Combine: D0 = (D2 << 22) | (D0 >> 10)

	move.l	(sp)+,d2	; Restore D2
	rts

;
; FixedDiv_65536_by_zi - Perspective division using 22.10 fixed-point
;
; Entry:
;   D0 = zi (22.10 fixed-point inverse depth)
;
; Exit:
;   D0 = z (22.10 fixed-point depth)
;   D1-D4 = clobbered
;
; Formula: z = (65536 * 1024) / zi = 0x04000000 / zi
;
; Algorithm: 64-bit shift-and-subtract division
;   - Numerator: 0x04000000_00000000 (65536 in 22.10 format, shifted left 32)
;   - Denominator: zi (22.10)
;   - Result: 32-bit quotient in 22.10 format
;
_FixedDiv_Internal:
	; Handle special cases
	tst.l	d0
	beq.s	.div_zero	; zi = 0, return max value
	bpl.s	.div_positive	; zi > 0, proceed

	; zi < 0: negate, divide, then negate result
	neg.l	d0
	bsr.s	.do_division
	neg.l	d0
	rts

.div_positive:
	bsr.s	.do_division
	rts

.div_zero:
	; Return max positive value
	move.l	#$7FFFFFFF,d0
	rts

;
; Internal division routine (assumes D0 > 0)
;
.do_division:
	moveq	#0,d1		; D1 = quotient accumulator
	moveq	#31,d2		; D2 = loop counter (32 iterations)

	; 64-bit remainder for 22.10 division
	; (65536 in 22.10) << 10 = 0x4000000 << 10 = 0x100000000
	move.l	#$10,d3		; High 32 bits
	moveq	#0,d4		; Low 32 bits

.div_loop:
	; Shift quotient left (make room for new bit)
	add.l	d1,d1

	; Shift 64-bit remainder left
	add.l	d4,d4		; Shift low 32 bits
	addx.l	d3,d3		; Shift high 32 bits with carry

	; Can we subtract divisor from remainder?
	cmp.l	d0,d3
	bcs.s	.no_subtract	; Unsigned comparison (remainder < divisor)

	; Yes - subtract divisor and set quotient bit
	sub.l	d0,d3
	addq.l	#1,d1		; Set LSB of quotient

.no_subtract:
	dbf	d2,.div_loop

	move.l	d1,d0		; Return quotient in D0
	rts

	end
