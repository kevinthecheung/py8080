;
;	CP/M 1.4 BIOS for Python emulator
;
vers	equ	14	;version 1.4
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
cdisk	equ	0004h	;current disk number 0=A,...,15=P
iobyte	equ	0003h	;intel i/o byte
;
	org	bios	;origin of this program
;
nsects	equ	($-ccp)/128	;warm start sector count
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
;	jump vector for individual subroutines
	jmp	boot		;cold start
wboote:	jmp	wboot		;warm start
	jmp	const		;console status
	jmp	conin		;console character in
	jmp	conout		;console character out
	jmp	list		;list character out
	jmp	punch		;punch character out
	jmp	reader		;reader character in
	jmp	home		;move head to home position
	jmp	seldsk		;select disk
	jmp	settrk		;set track number
	jmp	setsec		;set sector number
	jmp	setdma		;set dma address
	jmp	rddsk		;read disk
	jmp	wridsk		;write disk
;
;	individual subroutines to perform each function
boot:
	lxi	sp,80h		;use space below buffer for stack
	lxi	h,signon
	call	prmsg		;print message
	xra	a		;zero in the accum
	sta	iobyte		;clear the iobyte
	sta	cdisk		;select disk zero
	jmp	gocpm		;initialize and go to cp/m
;
cr	equ	0dh	;carriage return
lf	equ	0ah	;line feed
;
signon:
	db	cr,lf,lf
	db	msize/10+'0',msize mod 10+'0'
	db	'K CP/M VERS '
	db	vers/10+'0','.',vers mod 10+'0'
	db	cr,lf,0
;
prmsg:	;print message at h,l to 0
	mov	a,m
	ora	a	;zero?
	rz
;	more to print
	push	h
	mov	c,a
	call	conout
	pop	h
	inx	h
	jmp	prmsg
;
wboot:	;simplest case is to read the disk until all sectors loaded
	lxi	sp,80h		;use space below buffer for stack
	mvi	c,0		;select disk 0
	call	seldsk
	call	home		;go to track 00
;
	mvi	b,nsects	;b counts # of sectors to load
	mvi	c,0		;c has the current track number
	mvi	d,2		;d has the next sector to read
;	note that we begin by reading track 0, sector 2 since sector 1
;	contains the cold start loader, which is skipped in a warm start
	lxi	h,ccp		;base of cp/m (initial load point)
load1:	;load one more sector
	push	b	;save sector count, current track
	push	d	;save next sector to read
	push	h	;save dma address
	mov	c,d	;get sector address to register c
	call	setsec	;set sector address from register c
	pop	b	;recall dma address to b,c
	push	b	;replace on stack for later recall
	call	setdma	;set dma address from b,c
;
;	drive set to 0, track set, sector set, dma address set
	call	rddsk
	cpi	00h	;any errors?
	jnz	wboot	;retry the entire boot if an error occurs
;
;	no error, move to next sector
	pop	h	;recall dma address
	lxi	d,128	;dma=dma+128
	dad	d	;new dma address is in h,l
	pop	d	;recall sector address
	pop	b	;recall number of sectors remaining, and current trk
	dcr	b	;sectors=sectors-1
	jz	gocpm	;transfer to cp/m if all have been loaded
;
;	more sectors remain to load, check for track change
	inr	d
	mov	a,d	;sector=27?, if so, change tracks
	cpi	27
	jc	load1	;carry generated if sector<27
;
;	end of current track, go to next track
	mvi	d,1	;begin with first sector of next track
	inr	c	;track=track+1
;
;	save register state, and change tracks
	push	b
	push	d
	push	h
	call	settrk	;track address set from register c
	pop	h
	pop	d
	pop	b
	jmp	load1	;for another sector
;
;	end of load operation, set parameters and go to cp/m
gocpm:
	mvi	a,0c3h	;c3 is a jmp instruction
	sta	0	;for jmp to wboot
	lxi	h,wboote	;wboot entry point
	shld	1	;set address field for jmp at 0
;
	sta	5	;for jmp to bdos
	lxi	h,bdos	;bdos entry point
	shld	6	;address field of jump at 5 to bdos
;
	lxi	b,80h	;default dma address is 80h
	call	setdma
;
;	ei		;enable the interrupt system
	lda	cdisk	;get current disk number
	mov	c,a	;send to the ccp
	jmp	ccp	;go to cp/m for further processing
;
;
;	i/o handlers
;
const:	;console status, return 0ffh if character ready, 00h if not
	in	constp
	ret
;
conin:	;console character into register a
	in	coniop
	ani	7fh	;strip parity bit
	ret
;
conout: ;console character output from register c
	mov	a,c	;get to accumulator
	out	coniop
	ret
;
list:	;list character from register c
	mov	a,c	;character to register a
	out	lstiop
	ret
;
punch:	;punch character from register c
	mov	a,c	;character to register a
	ret		;null subroutine
;
;
reader: ;read character into register a from reader device
	mvi	a,1ah	;enter end of file for now (replace later)
	ani	7fh	;remember to strip parity bit
	ret
;
;
;	i/o drivers for the disk follow
;
home:	;move to the track 00 position of current drive
;	translate this call into a settrk call with parameter 00
	mvi	c,0	;select track 0
	call	settrk
	ret		;we will move to 00 on first read/write
;
seldsk:	;select disk given by register C
	lxi	h,0000h	;error return code
	mov	a,c
	cpi	16	;must be between 0 and 15
	rnc		;no carry if 16, 17...
;	disk number is in the proper range
	out	ddisk
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
wridsk:	;perform a write operation
	mvi	a,1
	out	dcom
	in	dstat
	ret
;
	end
;