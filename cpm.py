# This is free and unencumbered software released into the public domain.
#
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
#
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# For more information, please refer to <https://unlicense.org>

"""Rough emulation of a generic CP/M machine.

Emulated machine has 16 8" 250 KB floppy disk drives and an ADM-3A terminal."""


import argparse
import datetime
import os
import time
from typing import Dict, List, Optional, Tuple

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
from pygame.constants import KEYDOWN, KMOD_CTRL, KMOD_SHIFT, QUIT
from pygame.freetype import Font
from pygame.rect import Rect
from pygame.surface import Surface

from virtual8080 import Virtual8080
from virtual_device import VirtualDevice
from cpm_disk import CPM_Disk


TIME_TRAVEL_YEARS = -28


class CPM_Machine(VirtualDevice):

    def __init__(self, vm: Virtual8080, disk_images: List[str] = []):
        self.vm: Virtual8080 = vm

        self.input_buffer: bytes = b''
        self.output_char: int = -1

        self.bank_size: int = 0xF0 << 8
        self.current_bank: int = 0
        self.memory_banks: Dict[int, List[int]] = {self.current_bank: [0 for _ in range(self.bank_size)]}

        self.dma_bank: int = self.current_bank
        self.dma_addr: int = 0
        self.disk_controller_error: int = 0

        self.current_drive: int = 0
        self.drive_status: List[Dict[str, int]] = [{'track': 0, 'sector': 0} for _ in range(16)]
        self.disk_image: List[Optional[CPM_Disk]] = [None for _ in range(16)]
        for i, fn in enumerate(disk_images):
            if fn is not None:
                self.drive_status[i] = {'track': 0, 'sector': 0}
                self.disk_image[i] = CPM_Disk(fn, 128, 26, 77, 1, write_protect=False)

        boot_sector = self.read_disk(0, 0, 1)
        self.vm.load(boot_sector)


    def select_bank(self, bank_num: int) -> None:
            if bank_num == self.current_bank:
                return
            if bank_num not in self.memory_banks:
                self.memory_banks[bank_num] = [0 for _ in range(self.bank_size)]
            self.memory_banks[self.current_bank] = self.vm.memory[:self.bank_size]
            self.vm.memory[:self.bank_size] = self.memory_banks[bank_num]
            self.current_bank = bank_num


    def read_disk(self, drive_num: int, track: int, sector: int) -> bytes:
        drive = self.disk_image[drive_num]
        if drive is not None:
            return drive.get_sector(track, sector)
        else:
            raise ValueError


    def write_disk(self, drive_num: int, track: int, sector: int, sector_data: bytes) -> None:
        drive = self.disk_image[drive_num]
        if drive is not None:
            drive.set_sector(track, sector, sector_data)
            drive.save_image()


    def get_input(self, port_addr: int) -> Optional[int]:
        if port_addr == 0:
            # Console status
            if len(self.input_buffer) > 0:
                return 0xff
            else:
                return 0x00
        elif port_addr == 1:
            # Console input
            if len(self.input_buffer) > 0:
                c = self.input_buffer[0]
                self.input_buffer = self.input_buffer[1:]
                return c
            else:
                self.vm.registers['pc'] -= 2  # Loop again with same PC
                return None
        elif port_addr == 2:
            # List device status
            return 1  # Ready
        elif port_addr in (0x10, 0x11, 0x12, 0x13, 0x14):
            # System clock
            now = datetime.datetime.now()
            virtually_now = datetime.datetime(now.year + TIME_TRAVEL_YEARS,
                                              now.month,
                                              now.day,
                                              now.hour,
                                              now.minute,
                                              now.second)
            cpm_time = virtually_now.date() - datetime.date(1977, 12, 31)
            days = cpm_time.days
            hour = virtually_now.hour
            minute = virtually_now.minute
            second = virtually_now.second
            if port_addr == 0x10:
                # Day, high byte
                return (days & 0xFF00) >> 8
            elif port_addr == 0x11:
                # Day, low byte
                return days & 0x00FF
            elif port_addr == 0x12:
                # Hour
                tens = hour // 10
                ones = hour % 10
                return (tens << 4) | ones
            elif port_addr == 0x13:
                # Minute
                tens = minute // 10
                ones = minute % 10
                return (tens << 4) | ones
            elif port_addr == 0x14:
                # Second
                tens = second // 10
                ones = second % 10
                return (tens << 4) | ones
        elif port_addr == 0x20:
            # Get currently selected bank
            return self.current_bank
        elif port_addr == 0xf9:
            # Disk error status
            return self.disk_controller_error
        elif port_addr == 0xff:
            # Get DMA bank
            return self.dma_bank
        raise Exception


    def send_output(self, port_addr: int, value: int) -> None:
        if port_addr == 1:
            # Console output
            self.output_char = value
            return
        elif port_addr == 3:
            # List device output
            print(chr(value), end='', flush=True)
            return
        elif port_addr == 0x20:
            # Bank select
            self.select_bank(value)
            return
        elif port_addr == 0xf9:
            # Disk read/write commands
            if value == 0:
                # Read current drive/track/sector into [dma]
                orig_bank = self.current_bank
                self.select_bank(self.dma_bank)
                if self.disk_image[self.current_drive] is not None:
                    data = self.read_disk(self.current_drive,
                                          self.drive_status[self.current_drive]['track'],
                                          self.drive_status[self.current_drive]['sector'])
                    data_len = min(65536 - self.dma_addr, len(data))
                    for i in range(data_len):
                        self.vm.memory[self.dma_addr + i] = data[i]
                    self.disk_controller_error = 0x00  # OK
                else:
                    self.disk_controller_error = 0xff  # Error
                self.select_bank(orig_bank)
                return
            elif value == 1:
                # Write [dma] to current drive/track/sector
                orig_bank = self.current_bank
                self.select_bank(self.dma_bank)
                drive = self.disk_image[self.current_drive]
                if drive is not None:
                    sector_size = drive.sector_size
                    sector_data = bytes(self.vm.memory[self.dma_addr:self.dma_addr+sector_size])
                    self.write_disk(self.current_drive,
                                    self.drive_status[self.current_drive]['track'],
                                    self.drive_status[self.current_drive]['sector'],
                                    sector_data)
                    self.disk_controller_error = 0x00  # OK
                else:
                    self.disk_controller_error = 0xff  # Error
                self.select_bank(orig_bank)
                return
        elif port_addr == 0xfa:
            # Disk drive select
            self.current_drive = value
            return
        elif port_addr == 0xfb:
            # Track select
            self.drive_status[self.current_drive]['track'] = value
            return
        elif port_addr == 0xfc:
            # Sector select
            self.drive_status[self.current_drive]['sector'] = value
            return
        elif port_addr == 0xfd:
            # Set DMA address high byte
            self.dma_addr = (self.dma_addr & 0x00ff) | (value << 8)
            return
        elif port_addr == 0xfe:
            # Set DMA address low byte
            self.dma_addr = (self.dma_addr & 0xff00) | (value & 0x00ff)
            return
        elif port_addr == 0xff:
            # Set DMA bank
            self.dma_bank = value
            return
        raise Exception


class CPM_TTY:

    background = (0, 0, 0)
    foreground = (200, 200, 200)
    margin = 5

    shift_keymap = {
        ord('`'): ord('~'),
        ord('1'): ord('!'),
        ord('2'): ord('@'),
        ord('3'): ord('#'),
        ord('4'): ord('$'),
        ord('5'): ord('%'),
        ord('6'): ord('^'),
        ord('7'): ord('&'),
        ord('8'): ord('*'),
        ord('9'): ord('('),
        ord('0'): ord(')'),
        ord('-'): ord('_'),
        ord('='): ord('+'),
        ord('['): ord('{'),
        ord(']'): ord('}'),
        ord(';'): ord(':'),
        ord("'"): ord('"'),
        ord(','): ord('<'),
        ord('.'): ord('>'),
        ord('/'): ord('?'),
    }

    def __init__(self, disk_images: List[str] = []):
        self.disk_images: List[str] = disk_images

        self.buffer: bytearray = bytearray([32 for _ in range(80 * 24)])
        self.cursor: int = 0
        self.esc_sequence: bytes = b''

        pygame.init()
        pygame.display.set_caption('CP/M')
        pygame.key.set_repeat(1000, 100)

        self.screen: Surface = pygame.display.set_mode(
            (80 * 10 + 2 * self.margin, 24 * 20 + 2 * self.margin))
        self.font: Font = Font('BmPlus_Rainbow100_re_80.otb', 24)
        self.blink_rate: int = 750


    def putch(self, ch: int) -> None:
        ## ADM-3A cursor control
        ch = ch & 0b01111111
        if ch == 27:      # Esc
            self.esc_sequence = b'\x1b'
        elif len(self.esc_sequence) > 0:
            self.esc_sequence += bytes([ch])
            if self.esc_sequence.startswith(b'\x1b=') and len(self.esc_sequence) >= 4:
                y = self.esc_sequence[2] - 0x20
                x = self.esc_sequence[3] - 0x20
                self.cursor = 80 * y + x
                self.esc_sequence = b''

        elif ch == 8:         # ^H
            self.cursor = max(0, self.cursor - 1)
        elif ch == 10:         # ^J, \n
            self.cursor = self.cursor + 80
            if self.cursor >= 80 * 24 - 1:
                self.buffer = self.buffer[80:] + bytearray([32 for _ in range(80)])
                self.cursor = 80 * 23
        elif ch == 11:         # ^K
            self.cursor = max(0, self.cursor - 80)
        elif ch == 12:         # ^L
            self.cursor = min(80 * 24 - 1, self.cursor + 1)
        elif ch == 13:      # \r
            self.cursor = self.cursor // 80 * 80
        elif ch == 26:      # ^Z
            self.buffer = bytearray([32 for _ in range(80 * 24)])
            self.cursor = 0
        elif ch == 30:      # Home
            self.cursor = 0

        elif 32 <= ch < 127: # Printable
            if self.cursor >= 80 * 24 - 1:
                self.buffer = self.buffer[80:] + bytearray([32 for _ in range(80)])
                self.cursor = 80 * 23
            self.buffer[self.cursor] = ch
            self.cursor += 1
        else:
            # print(f'{ch} {ch & 0x7f}')
            print(chr(ch & 0x7f), end='', flush=True)


    def render_buffer(self) -> List[Tuple[Surface, Rect]]:
        cursor_on = (time.time_ns() // 1000000 // self.blink_rate) % 2 == 0
        curs_col = self.cursor % 80
        curs_row = self.cursor // 80

        # Render the cursor
        if cursor_on:
            surface, rect = self.font.render(bytes([self.buffer[80*curs_row+curs_col]]),
                                             fgcolor=self.background,
                                             bgcolor=self.foreground)
        else:
            surface, rect = self.font.render(bytes([self.buffer[80*curs_row+curs_col]]),
                                             fgcolor=self.foreground,
                                             bgcolor=self.background)
        rect.topleft = (curs_col * 10 + self.margin, curs_row * 20 + self.margin)
        rect.size = surface.get_size()
        blits = [(surface, rect)]

        # Render rows up to the cursor row
        for row in range(0, curs_row):
            surface, rect = self.font.render(bytes(self.buffer[80*row:80*row+80]),
                                             fgcolor=self.foreground)
            rect.topleft = (self.margin, row * 20 + self.margin)
            rect.size = surface.get_size()
            blits += [(surface, rect)]

        # Render the cursor row, but not the cursor
        surface, rect = self.font.render(bytes(self.buffer[80*curs_row:80*curs_row+curs_col]),
                                         fgcolor=self.foreground)
        rect.topleft = (self.margin, curs_row * 20 + self.margin)
        rect.size = surface.get_size()
        blits += [(surface, rect)]
        surface, rect = self.font.render(bytes(self.buffer[80*curs_row+curs_col+1:80*curs_row+80]),
                                         fgcolor=self.foreground)
        rect.topleft = ((curs_col + 1) * 10 + self.margin, curs_row * 20 + self.margin)
        rect.size = surface.get_size()
        blits += [(surface, rect)]

        # Render rows after the cursor row
        for row in range(curs_row+1, 24):
            surface, rect = self.font.render(bytes(self.buffer[80*row:80*row+80]),
                                             fgcolor=self.foreground)
            rect.topleft = (self.margin, row * 20 + self.margin)
            rect.size = surface.get_size()
            blits += [(surface, rect)]
        return blits


    def run(self) -> None:
        vm = Virtual8080()
        vm.io = CPM_Machine(vm, self.disk_images)

        work_ms = 1000 // 60    # Allow ~17ms of emulation time to maintain ~60fps.
        vm.halted = False
        while not vm.halted:
            work_until = pygame.time.get_ticks() + work_ms
            while pygame.time.get_ticks() < work_until:
                if not vm.halted:
                    vm.step()
                ch = vm.io.output_char
                if ch != -1:
                    self.putch(ch)
                    vm.io.output_char = -1

            for event in pygame.event.get():
                if event.type == QUIT:
                    vm.halted = True
                
                if event.type == KEYDOWN:
                    if 0 <= event.key <= 255: 
                        key = event.key
                        if 97 <= key <= 122 and event.mod & KMOD_SHIFT: # A-Z
                            key -= 32
                        elif event.mod & KMOD_SHIFT:                    # Other
                            if key in self.shift_keymap.keys():
                                key = self.shift_keymap[key]
                        elif 97 <= key <= 122 and event.mod & KMOD_CTRL: # ^A - ^Z
                            key -= 96
                        vm.io.input_buffer += bytes([key])

            self.screen.fill(self.background)
            self.screen.blits(self.render_buffer())
            pygame.display.update()

        pygame.quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for d in range(ord('a'), ord('a') + 16):
        parser.add_argument(f'-d{chr(d)}', f'--drive_{chr(d)}', type=str, default=None,
                            help=f'disk image for drive {chr(d)}')
    args = parser.parse_args()

    tty = CPM_TTY(disk_images=[getattr(args, f'drive_{chr(d)}')
                               for d in range(ord('a'), ord('a') + 16)])
    tty.run()
