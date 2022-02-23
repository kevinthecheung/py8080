;
;	CP/M 3.0 loader BIOS for Python emulator
;
	maclib cpm3
	public @mxtpa
;
;
constp	equ 0		;console status port
coniop	equ 1		;console i/o port
;
lststp	equ 2		;list status port
lstiop	equ 3		;list i/o port
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
bdos	equ 5
;
;	jump vector for individual subroutines
	jmp	boot		;cold start
	jmp	0		;warm start
	jmp	0		;console status
	jmp	0		;console character in
	jmp	conout		;console character out
	jmp	0		;list character out
	jmp	0		;punch character out
	jmp	0		;reader character in
	jmp	home		;move head to home position
	jmp	seldsk		;select disk
	jmp	settrk		;set track number
	jmp	setsec		;set sector number
	jmp	setdma		;set dma address
	jmp	rddsk		;read disk
	jmp	0		;write disk
	jmp	0		;return list status
	jmp	sectrn		;sector translate
;
	jmp	conost
	jmp	0
	jmp	0
	jmp	0
	jmp	0
	jmp	drvtbl
	jmp	0
	jmp	0
	jmp	0
	jmp	0
	jmp	0
	jmp	0
	jmp	0
;
	jmp	0
	jmp	0
	jmp	0
;
;
tbldrv	dw	dph0,0,0,0
	dw	0,0,0,0
	dw	0,0,0,0
	dw	0,0,0,0
;
dph0	dph	tbltrn,dpbstd,16,31
;
dpbstd	dpb	128,26,77,1024,64,2,16
;
tbltrn	skew	26,6,1
;
;	individual subroutines to perform each function
boot:
	mvi	a,0C3h		;8080 "jump" opcode
	sta	bdos		;store in 1st byte of BDOS entry vector
	lhld	@mxtpa		;BDOS entry address
	shld	bdos+1		;put it after the jump opcode

	ret
;
;
;	i/o handlers
;
conout: ;console character output from register c
	mov	a,c	;get to accumulator
	out	coniop
	ret
;
;
;	i/o drivers for the disk follow
;
home:	;move to the track 00 position of current drive
;	translate this call into a settrk call with parameter 00
	mvi	c,0	;select track 0
	call	settrk
	ret
;
seldsk:	;select disk given by register C
	mov	a,c
	out	ddisk
	cpi	0
	jz	sel0
	lxi	h,0
	ret
sel0:
	lxi	h,dph0
	ret
;
settrk:	;set track given by register c
	mov	a,c
	out	dtrack
	ret
;
setsec:	;set sector given by register c
	mov	a,c
	out	dsect
	ret
;
sectrn:	;translate the sector given by BC using the
	;translate table given by DE
	xchg		;HL=.trans
	dad	b	;HL=.trans(sector)
	mov	l,m	;L = trans(sector)
	mvi	h,0	;HL= trans(sector)
	ret		;with value in HL
;
setdma:	;set dma address given by registers b and c
	mov	a,c	;low order address
	out	ddmalo
	mov	a,b	;high order address
	out	ddmahi
	ret
;
rddsk:	;perform read operation
	mvi	a,0
	out	dcom
	in	dstat
	ret
;
conost:
	mvi	a,0ffh
	ret
;
drvtbl:
	lxi	h,tbldrv
	ret
;
;	uninitialized data
@mxtpa  ds	2    		; Top of User TPA 
;
;
	end
;