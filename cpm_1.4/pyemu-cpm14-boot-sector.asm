;
;	CP/M 1.4 boot sector for Python emulator
;
msize	equ	64	;cp/m version memory size in kilobytes
;
;	"bias" is address offset from 3400H for memory systems
;	than 16K (referred to as "b" throughout the text).
;
bias	equ	(msize-16)*1024
ccp	equ	bias+2900h	;base of ccp
bdos	equ	bias+3106h	;base of bdos
bios	equ	msize*1024-2*256;base of bios
biossz	equ	110h
;
nsects	equ	2dh	;cp/m sector count
;
disk	equ 0f9h	;base address of disk ports
dstat	equ disk	;status port
dcom	equ disk	;command port: 0 = read, 1 = write
ddisk	equ disk+1	;disk port
dtrack	equ disk+2	;track port
dsect	equ disk+3	;sector port
ddmahi	equ disk+4	;DMA address (high) port
ddmalo	equ disk+5	;DMA address (low) port
;
;
		org 0
;
	mvi e,10	;try to load up to 10 times
tryld:	lxi sp,0100h	;reset the stack
	lxi h,ccp	;hl = load destination
	mvi d,nsects
	mvi b,0		;start with track 0
	mvi c,2		;start with sector 2 of first track
traclp:	mov a,b
	out dtrack
sectlp:	call ldsect
	dcr d
	jz bios		;if loaded everything, jump to bios
	push b
	lxi b,128
	dad b		;hl=hl+128
	pop b
	inr c		;next sector
	mov a,c
	cpi 27
	jc sectlp	;if next < 27 load another sector
	inr b		;otherwise, next track
	mvi c,1		;now start with sector 1
	jmp traclp
;
; load sector c into address hl
;
ldsect:	mov a,c
	out dsect
	mov a,h
	out ddmahi
	mov a,l
	out ddmalo
	mvi a,0		;"read sector" command
	out dcom	;send command
	in dstat	;get read sector status
	ora a
	rz		;return if no errors
; on read error, start over completely
	dcr e
	jnz tryld	;if e>0, try again
; halt after too many retries
halt:	jmp halt	;halt
;