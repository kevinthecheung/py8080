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

"""8080 machine code interpreter."""

import re
from typing import Callable, Dict, List, Optional

from virtual_device import VirtualDevice


class Virtual8080:

    def __init__(self, max_memory: int = 2**16, io: Optional[VirtualDevice] = None):
        self.max_memory: int = max_memory
        self.memory: List[int] = [0 for _ in range(self.max_memory)]
        self.io = io
        self.halted: bool = True

        self.registers: Dict[str, int] = {}
        self.registers['a'] = 0
        self.registers['f'] = 0b00000010
        self.registers['b'] = 0
        self.registers['c'] = 0
        self.registers['d'] = 0
        self.registers['e'] = 0
        self.registers['h'] = 0
        self.registers['l'] = 0
        self.registers['sp'] = self.max_memory - 1
        self.registers['pc'] = 0

        self.op: Dict[int, Callable[[], None]] = {}
        self.op[0x00] = self.instr_nop()
        self.op[0x10] = self.instr_nop()
        self.op[0x20] = self.instr_nop()
        self.op[0x30] = self.instr_nop()
        self.op[0x40] = self.instr_mov_reg_reg('b', 'b')
        self.op[0x50] = self.instr_mov_reg_reg('d', 'b')
        self.op[0x60] = self.instr_mov_reg_reg('h', 'b')
        self.op[0x70] = self.instr_mov_mem_reg('b')
        self.op[0x80] = self.instr_add_reg('b')
        self.op[0x90] = self.instr_sub_reg('b')
        self.op[0xa0] = self.instr_ana_reg('b')
        self.op[0xb0] = self.instr_ora_reg('b')
        self.op[0xc0] = self.instr_ret_zero(0)
        self.op[0xd0] = self.instr_ret_carry(0)
        self.op[0xe0] = self.instr_ret_parity(0)
        self.op[0xf0] = self.instr_ret_sign(0)

        self.op[0x01] = self.instr_lxi('b', 'c')
        self.op[0x11] = self.instr_lxi('d', 'e')
        self.op[0x21] = self.instr_lxi('h', 'l')
        self.op[0x31] = self.instr_lxi_sp()
        self.op[0x41] = self.instr_mov_reg_reg('b', 'c')
        self.op[0x51] = self.instr_mov_reg_reg('d', 'c')
        self.op[0x61] = self.instr_mov_reg_reg('h', 'c')
        self.op[0x71] = self.instr_mov_mem_reg('c')
        self.op[0x81] = self.instr_add_reg('c')
        self.op[0x91] = self.instr_sub_reg('c')
        self.op[0xa1] = self.instr_ana_reg('c')
        self.op[0xb1] = self.instr_ora_reg('c')
        self.op[0xc1] = self.instr_pop('b', 'c')
        self.op[0xd1] = self.instr_pop('d', 'e')
        self.op[0xe1] = self.instr_pop('h', 'l')
        self.op[0xf1] = self.instr_pop('a', 'f')

        self.op[0x02] = self.instr_stax('b', 'c')
        self.op[0x12] = self.instr_stax('d', 'e')
        self.op[0x22] = self.instr_shld()
        self.op[0x32] = self.instr_sta()
        self.op[0x42] = self.instr_mov_reg_reg('b', 'd')
        self.op[0x52] = self.instr_mov_reg_reg('d', 'd')
        self.op[0x62] = self.instr_mov_reg_reg('h', 'd')
        self.op[0x72] = self.instr_mov_mem_reg('d')
        self.op[0x82] = self.instr_add_reg('d')
        self.op[0x92] = self.instr_sub_reg('d')
        self.op[0xa2] = self.instr_ana_reg('d')
        self.op[0xb2] = self.instr_ora_reg('d')
        self.op[0xc2] = self.instr_jmp_zero(0)
        self.op[0xd2] = self.instr_jmp_carry(0)
        self.op[0xe2] = self.instr_jmp_parity(0)
        self.op[0xf2] = self.instr_jmp_sign(0)

        self.op[0x03] = self.instr_inx('b', 'c')
        self.op[0x13] = self.instr_inx('d', 'e')
        self.op[0x23] = self.instr_inx('h', 'l')
        self.op[0x33] = self.instr_inx_sp()
        self.op[0x43] = self.instr_mov_reg_reg('b', 'e')
        self.op[0x53] = self.instr_mov_reg_reg('d', 'e')
        self.op[0x63] = self.instr_mov_reg_reg('h', 'e')
        self.op[0x73] = self.instr_mov_mem_reg('e')
        self.op[0x83] = self.instr_add_reg('e')
        self.op[0x93] = self.instr_sub_reg('e')
        self.op[0xa3] = self.instr_ana_reg('e')
        self.op[0xb3] = self.instr_ora_reg('e')
        self.op[0xc3] = self.instr_jmp()
        self.op[0xd3] = self.instr_out()
        self.op[0xe3] = self.instr_xthl()
        self.op[0xf3] = self.instr_di()

        self.op[0x04] = self.instr_inc_reg('b')
        self.op[0x14] = self.instr_inc_reg('d')
        self.op[0x24] = self.instr_inc_reg('h')
        self.op[0x34] = self.instr_inc_mem()
        self.op[0x44] = self.instr_mov_reg_reg('b', 'h')
        self.op[0x54] = self.instr_mov_reg_reg('d', 'h')
        self.op[0x64] = self.instr_mov_reg_reg('h', 'h')
        self.op[0x74] = self.instr_mov_mem_reg('h')
        self.op[0x84] = self.instr_add_reg('h')
        self.op[0x94] = self.instr_sub_reg('h')
        self.op[0xa4] = self.instr_ana_reg('h')
        self.op[0xb4] = self.instr_ora_reg('h')
        self.op[0xc4] = self.instr_call_zero(0)
        self.op[0xd4] = self.instr_call_carry(0)
        self.op[0xe4] = self.instr_call_parity(0)
        self.op[0xf4] = self.instr_call_sign(0)

        self.op[0x05] = self.instr_dcr_reg('b')
        self.op[0x15] = self.instr_dcr_reg('d')
        self.op[0x25] = self.instr_dcr_reg('h')
        self.op[0x35] = self.instr_dcr_mem()
        self.op[0x45] = self.instr_mov_reg_reg('b', 'l')
        self.op[0x55] = self.instr_mov_reg_reg('d', 'l')
        self.op[0x65] = self.instr_mov_reg_reg('h', 'l')
        self.op[0x75] = self.instr_mov_mem_reg('l')
        self.op[0x85] = self.instr_add_reg('l')
        self.op[0x95] = self.instr_sub_reg('l')
        self.op[0xa5] = self.instr_ana_reg('l')
        self.op[0xb5] = self.instr_ora_reg('l')
        self.op[0xc5] = self.instr_push('b', 'c')
        self.op[0xd5] = self.instr_push('d', 'e')
        self.op[0xe5] = self.instr_push('h', 'l')
        self.op[0xf5] = self.instr_push('a', 'f')

        self.op[0x06] = self.instr_mov_reg_immed('b')
        self.op[0x16] = self.instr_mov_reg_immed('d')
        self.op[0x26] = self.instr_mov_reg_immed('h')
        self.op[0x36] = self.instr_mov_mem_immed()
        self.op[0x46] = self.instr_mov_reg_mem('b')
        self.op[0x56] = self.instr_mov_reg_mem('d')
        self.op[0x66] = self.instr_mov_reg_mem('h')
        self.op[0x76] = self.instr_halt()
        self.op[0x86] = self.instr_add_mem()
        self.op[0x96] = self.instr_sub_mem()
        self.op[0xa6] = self.instr_ana_mem()
        self.op[0xb6] = self.instr_ora_mem()
        self.op[0xc6] = self.instr_add_immed()
        self.op[0xd6] = self.instr_sub_immed()
        self.op[0xe6] = self.instr_ana_immed()
        self.op[0xf6] = self.instr_ora_immed()

        self.op[0x07] = self.instr_rlc()
        self.op[0x17] = self.instr_ral()
        self.op[0x27] = self.instr_daa()
        self.op[0x37] = self.instr_stc()
        self.op[0x47] = self.instr_mov_reg_reg('b', 'a')
        self.op[0x57] = self.instr_mov_reg_reg('d', 'a')
        self.op[0x67] = self.instr_mov_reg_reg('h', 'a')
        self.op[0x77] = self.instr_mov_mem_reg('a')
        self.op[0x87] = self.instr_add_reg('a')
        self.op[0x97] = self.instr_sub_reg('a')
        self.op[0xa7] = self.instr_ana_reg('a')
        self.op[0xb7] = self.instr_ora_reg('a')
        self.op[0xc7] = self.instr_reset(0)
        self.op[0xd7] = self.instr_reset(2)
        self.op[0xe7] = self.instr_reset(4)
        self.op[0xf7] = self.instr_reset(6)

        self.op[0x08] = self.instr_nop()
        self.op[0x18] = self.instr_nop()
        self.op[0x28] = self.instr_nop()
        self.op[0x38] = self.instr_nop()
        self.op[0x48] = self.instr_mov_reg_reg('c', 'b')
        self.op[0x58] = self.instr_mov_reg_reg('e', 'b')
        self.op[0x68] = self.instr_mov_reg_reg('l', 'b')
        self.op[0x78] = self.instr_mov_reg_reg('a', 'b')
        self.op[0x88] = self.instr_adc_reg('b')
        self.op[0x98] = self.instr_sbb_reg('b')
        self.op[0xa8] = self.instr_xra_reg('b')
        self.op[0xb8] = self.instr_cmp_reg('b')
        self.op[0xc8] = self.instr_ret_zero(1)
        self.op[0xd8] = self.instr_ret_carry(1)
        self.op[0xe8] = self.instr_ret_parity(1)
        self.op[0xf8] = self.instr_ret_sign(1)

        self.op[0x09] = self.instr_dad('b', 'c')
        self.op[0x19] = self.instr_dad('d', 'e')
        self.op[0x29] = self.instr_dad('h', 'l')
        self.op[0x39] = self.instr_dad_sp()
        self.op[0x49] = self.instr_mov_reg_reg('c', 'c')
        self.op[0x59] = self.instr_mov_reg_reg('e', 'c')
        self.op[0x69] = self.instr_mov_reg_reg('l', 'c')
        self.op[0x79] = self.instr_mov_reg_reg('a', 'c')
        self.op[0x89] = self.instr_adc_reg('c')
        self.op[0x99] = self.instr_sbb_reg('c')
        self.op[0xa9] = self.instr_xra_reg('c')
        self.op[0xb9] = self.instr_cmp_reg('c')
        self.op[0xc9] = self.instr_ret()
        self.op[0xd9] = self.instr_ret()
        self.op[0xe9] = self.instr_pchl()
        self.op[0xf9] = self.instr_sphl()

        self.op[0x0a] = self.instr_ldax('b', 'c')
        self.op[0x1a] = self.instr_ldax('d', 'e')
        self.op[0x2a] = self.instr_lhld()
        self.op[0x3a] = self.instr_lda()
        self.op[0x4a] = self.instr_mov_reg_reg('c', 'd')
        self.op[0x5a] = self.instr_mov_reg_reg('e', 'd')
        self.op[0x6a] = self.instr_mov_reg_reg('l', 'd')
        self.op[0x7a] = self.instr_mov_reg_reg('a', 'd')
        self.op[0x8a] = self.instr_adc_reg('d')
        self.op[0x9a] = self.instr_sbb_reg('d')
        self.op[0xaa] = self.instr_xra_reg('d')
        self.op[0xba] = self.instr_cmp_reg('d')
        self.op[0xca] = self.instr_jmp_zero(1)
        self.op[0xda] = self.instr_jmp_carry(1)
        self.op[0xea] = self.instr_jmp_parity(1)
        self.op[0xfa] = self.instr_jmp_sign(1)

        self.op[0x0b] = self.instr_dcx('b', 'c')
        self.op[0x1b] = self.instr_dcx('d', 'e')
        self.op[0x2b] = self.instr_dcx('h', 'l')
        self.op[0x3b] = self.instr_dcx_sp()
        self.op[0x4b] = self.instr_mov_reg_reg('c', 'e')
        self.op[0x5b] = self.instr_mov_reg_reg('e', 'e')
        self.op[0x6b] = self.instr_mov_reg_reg('l', 'e')
        self.op[0x7b] = self.instr_mov_reg_reg('a', 'e')
        self.op[0x8b] = self.instr_adc_reg('e')
        self.op[0x9b] = self.instr_sbb_reg('e')
        self.op[0xab] = self.instr_xra_reg('e')
        self.op[0xbb] = self.instr_cmp_reg('e')
        self.op[0xcb] = self.instr_jmp()
        self.op[0xdb] = self.instr_in()
        self.op[0xeb] = self.instr_xchg()
        self.op[0xfb] = self.instr_ei()

        self.op[0x0c] = self.instr_inc_reg('c')
        self.op[0x1c] = self.instr_inc_reg('e')
        self.op[0x2c] = self.instr_inc_reg('l')
        self.op[0x3c] = self.instr_inc_reg('a')
        self.op[0x4c] = self.instr_mov_reg_reg('c', 'h')
        self.op[0x5c] = self.instr_mov_reg_reg('e', 'h')
        self.op[0x6c] = self.instr_mov_reg_reg('l', 'h')
        self.op[0x7c] = self.instr_mov_reg_reg('a', 'h')
        self.op[0x8c] = self.instr_adc_reg('h')
        self.op[0x9c] = self.instr_sbb_reg('h')
        self.op[0xac] = self.instr_xra_reg('h')
        self.op[0xbc] = self.instr_cmp_reg('h')
        self.op[0xcc] = self.instr_call_zero(1)
        self.op[0xdc] = self.instr_call_carry(1)
        self.op[0xec] = self.instr_call_parity(1)
        self.op[0xfc] = self.instr_call_sign(1)

        self.op[0x0d] = self.instr_dcr_reg('c')
        self.op[0x1d] = self.instr_dcr_reg('e')
        self.op[0x2d] = self.instr_dcr_reg('l')
        self.op[0x3d] = self.instr_dcr_reg('a')
        self.op[0x4d] = self.instr_mov_reg_reg('c', 'l')
        self.op[0x5d] = self.instr_mov_reg_reg('e', 'l')
        self.op[0x6d] = self.instr_mov_reg_reg('l', 'l')
        self.op[0x7d] = self.instr_mov_reg_reg('a', 'l')
        self.op[0x8d] = self.instr_adc_reg('l')
        self.op[0x9d] = self.instr_sbb_reg('l')
        self.op[0xad] = self.instr_xra_reg('l')
        self.op[0xbd] = self.instr_cmp_reg('l')
        self.op[0xcd] = self.instr_call()
        self.op[0xdd] = self.instr_call()
        self.op[0xed] = self.instr_call()
        self.op[0xfd] = self.instr_call()

        self.op[0x0e] = self.instr_mov_reg_immed('c')
        self.op[0x1e] = self.instr_mov_reg_immed('e')
        self.op[0x2e] = self.instr_mov_reg_immed('l')
        self.op[0x3e] = self.instr_mov_reg_immed('a')
        self.op[0x4e] = self.instr_mov_reg_mem('c')
        self.op[0x5e] = self.instr_mov_reg_mem('e')
        self.op[0x6e] = self.instr_mov_reg_mem('l')
        self.op[0x7e] = self.instr_mov_reg_mem('a')
        self.op[0x8e] = self.instr_adc_mem()
        self.op[0x9e] = self.instr_sbb_mem()
        self.op[0xae] = self.instr_xra_mem()
        self.op[0xbe] = self.instr_cmp_mem()
        self.op[0xce] = self.instr_adc_immed()
        self.op[0xde] = self.instr_sbb_immed()
        self.op[0xee] = self.instr_xra_immed()
        self.op[0xfe] = self.instr_cmp_immed()

        self.op[0x0f] = self.instr_rrc()
        self.op[0x1f] = self.instr_rar()
        self.op[0x2f] = self.instr_cma()
        self.op[0x3f] = self.instr_cmc()
        self.op[0x4f] = self.instr_mov_reg_reg('c', 'a')
        self.op[0x5f] = self.instr_mov_reg_reg('e', 'a')
        self.op[0x6f] = self.instr_mov_reg_reg('l', 'a')
        self.op[0x7f] = self.instr_mov_reg_reg('a', 'a')
        self.op[0x8f] = self.instr_adc_reg('a')
        self.op[0x9f] = self.instr_sbb_reg('a')
        self.op[0xaf] = self.instr_xra_reg('a')
        self.op[0xbf] = self.instr_cmp_reg('a')
        self.op[0xcf] = self.instr_reset(1)
        self.op[0xdf] = self.instr_reset(3)
        self.op[0xef] = self.instr_reset(5)
        self.op[0xff] = self.instr_reset(7)

    def run(self) -> None:
        self.halted = False
        while not self.halted:
            self.step()

    def step(self) -> None:
        _pc = self.registers['pc']  # for easier breakpoints
        opcode = self.get_program_byte()
        self.op[opcode]()
    
    def load(self, data: bytes, offset: int = 0) -> None:
        i = offset
        for c in data:
            self.memory[i] = c
            i += 1
    
    def load_hex(self, hex_str: str) -> None:
        hex_re = re.compile(
            r'^:(?P<length>[0-9a-f]{2})(?P<address>[0-9a-f]{4})(?P<type>[0-9a-f]{2})(?P<data>[0-9a-f]*?)(?P<checksum>[0-9a-f]{2})$',
            flags=re.IGNORECASE
        )
        for hex_line in hex_str.splitlines():
            match = hex_re.fullmatch(hex_line)
            if match is None:
                continue

            length = int(match.group('length'), 16)
            address = int(match.group('address'), 16)
            rec_type = int(match.group('type'), 16)
            data = match.group('data')
            data_bytes = [int(data[i:i+2], 16) for i in range(0, length * 2, 2)]
            if len(data_bytes) != length:
                raise ValueError

            if rec_type == 0:
                self.memory[address:address+length] = data_bytes
            elif rec_type == 1:
                return

    
    def get_mem(self, addr: int) -> int:
        return self.memory[addr] if addr < self.max_memory else 0
    
    def set_mem(self, addr: int, val: int):
        if addr < self.max_memory:
            self.memory[addr] = val

    def set_flag_sign(self, val: int) -> None:
        self.registers['f'] = (self.registers['f'] & 0b01111111) ^ (val << 7)

    def set_flag_zero(self, val: int) -> None:
        self.registers['f'] = (self.registers['f'] & 0b10111111) ^ (val << 6)

    def set_flag_auxcarry(self, val: int) -> None:
        self.registers['f'] = (self.registers['f'] & 0b11101111) ^ (val << 4)

    def set_flag_parity(self, val: int) -> None:
        self.registers['f'] = (self.registers['f'] & 0b11111011) ^ (val << 2)

    def set_flag_carry(self, val: int) -> None:
        self.registers['f'] = (self.registers['f'] & 0b11111110) ^ val

    def get_flag_sign(self) -> int:
        return (self.registers['f'] & 0b10000000) >> 7

    def get_flag_zero(self) -> int:
        return (self.registers['f'] & 0b01000000) >> 6

    def get_flag_auxcarry(self) -> int:
        return (self.registers['f'] & 0b00010000) >> 4

    def get_flag_parity(self) -> int:
        return (self.registers['f'] & 0b00000100) >> 2

    def get_flag_carry(self) -> int:
        return (self.registers['f'] & 0b00000001)

    def get_program_byte(self) -> int:
        val = self.get_mem(self.registers['pc'])
        self.registers['pc'] += 1
        return val

    ##
    ## 8-bit load/store/move instructions
    ##

    def instr_mov_reg_reg(self, dest: str, src: str) -> Callable[[], None]:
        def fn() -> None:
            self.registers[dest] = self.registers[src]
        return fn

    def instr_mov_reg_immed(self, dest: str) -> Callable[[], None]:
        def fn() -> None:
            val = self.get_program_byte()
            self.registers[dest] = val
        return fn

    def instr_mov_reg_mem(self, dest: str) -> Callable[[], None]:
        def fn() -> None:
            addr = (self.registers['h'] << 8) | self.registers['l']
            self.registers[dest] = self.get_mem(addr)
        return fn

    def instr_mov_mem_reg(self, src: str) -> Callable[[], None]:
        def fn() -> None:
            addr = (self.registers['h'] << 8) | self.registers['l']
            self.set_mem(addr, self.registers[src])
        return fn

    def instr_mov_mem_immed(self) -> Callable[[], None]:
        def fn() -> None:
            val = self.get_program_byte()
            addr = (self.registers['h'] << 8) | self.registers['l']
            self.set_mem(addr, val)
        return fn

    def instr_sta(self) -> Callable[[], None]:
        def fn() -> None:
            lo_addr = self.get_program_byte()
            hi_addr = self.get_program_byte()
            addr = (hi_addr << 8) | lo_addr
            self.set_mem(addr, self.registers['a'])
        return fn

    def instr_stax(self, addr_hi: str, addr_lo: str) -> Callable[[], None]:
        def fn() -> None:
            addr = (self.registers[addr_hi] << 8) | self.registers[addr_lo]
            self.set_mem(addr, self.registers['a'])
        return fn

    def instr_lda(self) -> Callable[[], None]:
        def fn() -> None:
            lo_addr = self.get_program_byte()
            hi_addr = self.get_program_byte()
            addr = (hi_addr << 8) | lo_addr
            self.registers['a'] = self.get_mem(addr)
        return fn

    def instr_ldax(self, addr_hi: str, addr_lo: str):
        def fn() -> None:
            addr = (self.registers[addr_hi] << 8) | self.registers[addr_lo]
            self.registers['a'] = self.get_mem(addr)
        return fn

    ##
    ## 16-bit load/store/move instructions
    ##

    def instr_lxi(self, dest_hi: str, dest_lo: str) -> Callable[[], None]:
        def fn() -> None:
            self.registers[dest_lo] = self.get_program_byte()
            self.registers[dest_hi] = self.get_program_byte()
        return fn

    def instr_lxi_sp(self) -> Callable[[], None]:
        def fn() -> None:
            lo = self.get_program_byte()
            hi = self.get_program_byte()
            self.registers['sp'] = (hi << 8) | lo
        return fn

    def instr_sphl(self) -> Callable[[], None]:
        def fn() -> None:
            lo_addr = self.registers['l']
            hi_addr = self.registers['h']
            addr = (hi_addr << 8) | lo_addr
            self.registers['sp'] = addr
        return fn

    def instr_pop(self, dest_hi: str, dest_lo: str) -> Callable[[], None]:
        def fn() -> None:
            sp = self.registers['sp']
            self.registers[dest_lo] = self.get_mem(sp)
            if dest_lo == 'f':
                self.registers[dest_lo] = self.registers[dest_lo] & 0b11010111
                self.registers[dest_lo] = self.registers[dest_lo] | 0b00000010
            self.registers[dest_hi] = self.get_mem(sp + 1)
            self.registers['sp'] += 2
        return fn

    def instr_push(self, src_hi: str, src_lo: str) -> Callable[[], None]:
        def fn() -> None:
            sp = self.registers['sp']
            self.set_mem(sp - 1, self.registers[src_hi])
            self.set_mem(sp - 2, self.registers[src_lo])
            self.registers['sp'] -= 2
        return fn

    def instr_shld(self) -> Callable[[], None]:
        def fn() -> None:
            lo_addr = self.get_program_byte()
            hi_addr = self.get_program_byte()
            addr = (hi_addr << 8) | lo_addr
            self.set_mem(addr, self.registers['l'])
            self.set_mem(addr + 1, self.registers['h'])
        return fn

    def instr_lhld(self) -> Callable[[], None]:
        def fn() -> None:
            lo_addr = self.get_program_byte()
            hi_addr = self.get_program_byte()
            addr = (hi_addr << 8) | lo_addr
            self.registers['l'] = self.get_mem(addr)
            self.registers['h'] = self.get_mem(addr + 1)
        return fn

    def instr_xchg(self) -> Callable[[], None]:
        def fn() -> None:
            self.registers['h'], self.registers['d'] = self.registers['d'], self.registers['h']
            self.registers['l'], self.registers['e'] = self.registers['e'], self.registers['l']
        return fn

    def instr_xthl(self) -> Callable[[], None]:
        def fn() -> None:
            sp = self.registers['sp']
            val_lo = self.get_mem(sp)
            val_hi = self.get_mem(sp + 1)
            self.set_mem(sp, self.registers['l'])
            self.set_mem(sp + 1, self.registers['h'])
            self.registers['l'] = val_lo
            self.registers['h'] = val_hi
        return fn

    ##
    ## 8-bit logic/arithmetic instructions
    ##

    def instr_add_reg(self, src: str) -> Callable[[], None]:
        def fn() -> None:
            sum = self.registers['a'] + self.registers[src]
            lsn_sum = (self.registers['a'] & 0x0f) + (self.registers[src] & 0x0f)
            result = sum % 256
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(1 if lsn_sum > 15 else 0)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(1 if sum > 255 else 0)
            self.registers['a'] = result
        return fn

    def instr_adc_reg(self, src: str) -> Callable[[], None]:
        def fn() -> None:
            sum = self.registers['a'] + self.registers[src] + self.get_flag_carry()
            lsn_sum = (self.registers['a'] & 0x0f) + (self.registers[src] & 0x0f) + self.get_flag_carry()
            result = sum % 256
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(1 if lsn_sum > 15 else 0)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(1 if sum > 255 else 0)
            self.registers['a'] = result
        return fn

    def instr_sub_reg(self, src: str) -> Callable[[], None]:
        def fn() -> None:
            diff = self.registers['a'] - self.registers[src]
            lsn_diff = (self.registers['a'] & 0x0f) - (self.registers[src] & 0x0f)
            result = diff % 256
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(0 if lsn_diff < 0 else 1)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(1 if diff < 0 else 0)
            self.registers['a'] = result
        return fn

    def instr_sbb_reg(self, src: str) -> Callable[[], None]:
        def fn() -> None:
            diff = self.registers['a'] - self.registers[src] - self.get_flag_carry()
            lsn_diff = (self.registers['a'] & 0x0f) - (self.registers[src] & 0x0f) - self.get_flag_carry()
            result = diff % 256
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(0 if lsn_diff < 0 else 1)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(1 if diff < 0 else 0)
            self.registers['a'] = result
        return fn

    def instr_ana_reg(self, src: str) -> Callable[[], None]:
        def fn() -> None:
            result = self.registers['a'] & self.registers[src]
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(((self.registers['a'] | self.registers[src]) & 0x08) >> 3)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(0)
            self.registers['a'] = result
        return fn

    def instr_ora_reg(self, src: str) -> Callable[[], None]:
        def fn() -> None:
            result = self.registers['a'] | self.registers[src]
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(0)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(0)
            self.registers['a'] = result
        return fn

    def instr_xra_reg(self, src: str) -> Callable[[], None]:
        def fn() -> None:
            result = self.registers['a'] ^ self.registers[src]
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(0)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(0)
            self.registers['a'] = result
        return fn

    def instr_cmp_reg(self, src: str) -> Callable[[], None]:
        def fn() -> None:
            diff = self.registers['a'] - self.registers[src]
            lsn_diff = (self.registers['a'] & 0x0f) - (self.registers[src] & 0x0f)
            result = diff % 256
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(0 if lsn_diff < 0 else 1)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(1 if diff < 0 else 0)
        return fn

    def instr_add_mem(self) -> Callable[[], None]:
        def fn() -> None:
            addr = (self.registers['h'] << 8) | self.registers['l']
            sum = self.registers['a'] + self.get_mem(addr)
            lsn_sum = (self.registers['a'] &0x0f) + (self.get_mem(addr) & 0x0f)
            result = sum % 256
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(1 if lsn_sum > 15 else 0)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(1 if sum > 255 else 0)
            self.registers['a'] = result
        return fn

    def instr_adc_mem(self) -> Callable[[], None]:
        def fn() -> None:
            addr = (self.registers['h'] << 8) | self.registers['l']
            sum = self.registers['a'] + self.get_mem(addr) + self.get_flag_carry()
            lsn_sum = (self.registers['a'] &0x0f) + (self.get_mem(addr) & 0x0f) + self.get_flag_carry()
            result = sum % 256
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(1 if lsn_sum > 15 else 0)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(1 if sum > 255 else 0)
            self.registers['a'] = result
        return fn

    def instr_cmp_mem(self) -> Callable[[], None]:
        def fn() -> None:
            addr = (self.registers['h'] << 8) | self.registers['l']
            diff = self.registers['a'] - self.get_mem(addr)
            lsn_diff = (self.registers['a'] & 0x0f) - (self.get_mem(addr) &0x0f)
            result = diff % 256
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(0 if lsn_diff < 0 else 1)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(1 if diff < 0 else 0)
        return fn

    def instr_sub_mem(self) -> Callable[[], None]:
        def fn() -> None:
            addr = (self.registers['h'] << 8) | self.registers['l']
            diff = self.registers['a'] - self.get_mem(addr)
            lsn_diff = (self.registers['a'] & 0x0f) - (self.get_mem(addr) &0x0f)
            result = diff % 256
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(0 if lsn_diff < 0 else 1)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(1 if diff < 0 else 0)
            self.registers['a'] = result
        return fn

    def instr_sbb_mem(self) -> Callable[[], None]:
        def fn() -> None:
            addr = (self.registers['h'] << 8) | self.registers['l']
            diff = self.registers['a'] - self.get_mem(addr) - self.get_flag_carry()
            lsn_diff = (self.registers['a'] & 0x0f) - (self.get_mem(addr) &0x0f) - self.get_flag_carry()
            result = diff % 256
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(0 if lsn_diff < 0 else 1)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(1 if diff < 0 else 0)
            self.registers['a'] = result
        return fn

    def instr_ana_mem(self) -> Callable[[], None]:
        def fn() -> None:
            addr = (self.registers['h'] << 8) | self.registers['l']
            result = self.registers['a'] & self.get_mem(addr)
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(((self.registers['a'] | self.get_mem(addr)) & 0x08) >> 3)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(0)
            self.registers['a'] = result
        return fn

    def instr_ora_mem(self) -> Callable[[], None]:
        def fn() -> None:
            addr = (self.registers['h'] << 8) | self.registers['l']
            result = self.registers['a'] | self.get_mem(addr)
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(0)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(0)
            self.registers['a'] = result
        return fn

    def instr_xra_mem(self) -> Callable[[], None]:
        def fn() -> None:
            addr = (self.registers['h'] << 8) | self.registers['l']
            result = self.registers['a'] ^ self.get_mem(addr)
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(0)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(0)
            self.registers['a'] = result
        return fn

    def instr_add_immed(self) -> Callable[[], None]:
        def fn() -> None:
            immed = self.get_program_byte()
            sum = self.registers['a'] + immed
            lsn_sum = (self.registers['a'] & 0x0f) + (immed & 0x0f)
            result = sum % 256
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(1 if lsn_sum > 15 else 0)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(1 if sum > 255 else 0)
            self.registers['a'] = result
        return fn

    def instr_adc_immed(self) -> Callable[[], None]:
        def fn() -> None:
            immed = self.get_program_byte()
            sum_ = self.registers['a'] + immed + self.get_flag_carry()
            lsn_sum = (self.registers['a'] & 0x0f) + (immed & 0x0f) + self.get_flag_carry()
            result = sum_ % 256
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(1 if lsn_sum > 15 else 0)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(1 if sum_ > 255 else 0)
            self.registers['a'] = result
        return fn

    def instr_cmp_immed(self) -> Callable[[], None]:
        def fn() -> None:
            immed = self.get_program_byte()
            diff = self.registers['a'] - immed
            lsn_diff = (self.registers['a'] & 0x0f) - (immed & 0x0f)
            result = diff % 256
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(0 if lsn_diff < 0 else 1)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(1 if diff < 0 else 0)
        return fn

    def instr_sub_immed(self) -> Callable[[], None]:
        def fn() -> None:
            immed = self.get_program_byte()
            diff = self.registers['a'] - immed
            lsn_diff = (self.registers['a'] & 0x0f) - (immed & 0x0f)
            result = diff % 256
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(0 if lsn_diff < 0 else 1)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(1 if diff < 0 else 0)
            self.registers['a'] = result
        return fn

    def instr_sbb_immed(self) -> Callable[[], None]:
        def fn() -> None:
            immed = self.get_program_byte()
            diff = self.registers['a'] - immed - self.get_flag_carry()
            lsn_diff = (self.registers['a'] & 0x0f) - (immed & 0x0f) - self.get_flag_carry()
            result = diff % 256
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(0 if lsn_diff < 0 else 1)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(1 if diff < 0 else 0)
            self.registers['a'] = result
        return fn

    def instr_ana_immed(self) -> Callable[[], None]:
        def fn() -> None:
            immed = self.get_program_byte()
            result = self.registers['a'] & immed
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(((self.registers['a'] | immed) & 0x08) >> 3)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(0)
            self.registers['a'] = result
        return fn

    def instr_ora_immed(self) -> Callable[[], None]:
        def fn() -> None:
            immed = self.get_program_byte()
            result = self.registers['a'] | immed
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(0)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(0)
            self.registers['a'] = result
        return fn

    def instr_xra_immed(self) -> Callable[[], None]:
        def fn() -> None:
            immed = self.get_program_byte()
            result = self.registers['a'] ^ immed
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(0)
            self.set_flag_parity(parity(result))
            self.set_flag_carry(0)
            self.registers['a'] = result
        return fn

    def instr_inc_reg(self, reg: str) -> Callable[[], None]:
        def fn() -> None:
            result = (self.registers[reg] + 1) % 256
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(1 if (result & 0x0f) == 0 else 0)
            self.set_flag_parity(parity(result))
            self.registers[reg] = result
        return fn

    def instr_inc_mem(self) -> Callable[[], None]:
        def fn() -> None:
            addr = (self.registers['h'] << 8) | self.registers['l']
            result = (self.get_mem(addr) + 1) % 256
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(1 if (result & 0x0f) == 0 else 0)
            self.set_flag_parity(parity(result))
            self.set_mem(addr, result)
        return fn

    def instr_dcr_reg(self, reg: str) -> Callable[[], None]:
        def fn() -> None:
            result = (self.registers[reg] - 1) % 256
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(1 if self.registers[reg] & 0x0f > 0 else 0)
            self.set_flag_parity(parity(result))
            self.registers[reg] = result
        return fn

    def instr_dcr_mem(self) -> Callable[[], None]:
        def fn() -> None:
            addr = (self.registers['h'] << 8) | self.registers['l']
            result = (self.get_mem(addr) - 1) % 256
            self.set_flag_sign(result >> 7)
            self.set_flag_zero(1 if result == 0 else 0)
            self.set_flag_auxcarry(1 if self.get_mem(addr) & 0x0f > 0 else 0)
            self.set_flag_parity(parity(result))
            self.set_mem(addr, result)
        return fn
    
    def instr_rlc(self) -> Callable[[], None]:
        def fn() -> None:
            self.set_flag_carry((self.registers['a'] & 0b10000000) >> 7)
            self.registers['a'] = (((self.registers['a'] << 1) & 0xff)
                                   | self.get_flag_carry())
        return fn
    
    def instr_ral(self) -> Callable[[], None]:
        def fn() -> None:
            c = self.get_flag_carry()
            self.set_flag_carry((self.registers['a'] & 0b10000000) >> 7)
            self.registers['a'] = ((self.registers['a'] << 1) & 0xff) | c
        return fn
    
    def instr_rrc(self) -> Callable[[], None]:
        def fn() -> None:
            self.set_flag_carry(self.registers['a'] & 0b00000001)
            self.registers['a'] = ((self.registers['a'] >> 1)
                                   | (self.get_flag_carry() << 7))
        return fn
    
    def instr_rar(self) -> Callable[[], None]:
        def fn() -> None:
            c = self.get_flag_carry()
            self.set_flag_carry(self.registers['a'] & 0b00000001)
            self.registers['a'] = ((self.registers['a'] >> 1) | (c << 7))
        return fn

    def instr_cma(self) -> Callable[[], None]:
        def fn() -> None:
            self.registers['a'] = self.registers['a'] ^ 0xff
        return fn

    def instr_stc(self) -> Callable[[], None]:
        def fn() -> None:
            self.set_flag_carry(1)
        return fn

    def instr_cmc(self) -> Callable[[], None]:
        def fn() -> None:
            self.set_flag_carry(0 if self.get_flag_carry() else 1)
        return fn

    def instr_daa(self) -> Callable[[], None]:
        def fn() -> None:
            acc = self.registers['a']
            carry = self.get_flag_carry()
            aux_carry = self.get_flag_auxcarry()

            low_nibble = acc & 0x0f
            if aux_carry == 1 or low_nibble > 9:
                acc += 6
                aux_carry = 1 if low_nibble > 9 else 0
            
            high_nibble = acc >> 4
            if carry == 1 or high_nibble > 9:
                acc += 0x60
                if carry != 1:
                    carry = 1 if high_nibble > 9 else 0

            acc = acc & 0xff

            self.registers['a'] = acc
            self.set_flag_sign(acc >> 7)
            self.set_flag_zero(1 if acc == 0 else 0)
            self.set_flag_auxcarry(aux_carry)
            self.set_flag_parity(parity(acc))
            self.set_flag_carry(carry)
        return fn

    ##
    ## 16-bit logic/arithmetic instructions
    ##

    def instr_dad(self, hi: str, lo: str) -> Callable[[], None]:
        def fn() -> None:
            acc = (self.registers['h'] << 8) | self.registers['l']
            operand = (self.registers[hi] << 8) | self.registers[lo]
            sum_ = acc + operand
            val = sum_ % 65536
            val_hi = (val & 0xff00) >> 8
            val_lo = val & 0x00ff
            self.registers['h'] = val_hi
            self.registers['l'] = val_lo
            self.set_flag_carry(1 if sum_ > 0xffff else 0)
        return fn

    def instr_dad_sp(self) -> Callable[[], None]:
        def fn() -> None:
            acc = (self.registers['h'] << 8) | self.registers['l']
            operand = self.registers['sp']
            sum_ = acc + operand
            val = sum_ % 65536
            val_hi = (val & 0xff00) >> 8
            val_lo = val & 0x00ff
            self.registers['h'] = val_hi
            self.registers['l'] = val_lo
            self.set_flag_carry(1 if sum_ > 0xffff else 0)
        return fn

    def instr_inx(self, hi: str, lo: str) -> Callable[[], None]:
        def fn() -> None:
            val = (self.registers[hi] << 8) | self.registers[lo]
            val = (val + 1) % 65536
            val_hi = (val & 0xff00) >> 8
            val_lo = val & 0x00ff
            self.registers[hi] = val_hi
            self.registers[lo] = val_lo
        return fn

    def instr_inx_sp(self) -> Callable[[], None]:
        def fn() -> None:
            self.registers['sp'] = (self.registers['sp'] + 1) % 65536
        return fn

    def instr_dcx(self, hi: str, lo: str) -> Callable[[], None]:
        def fn() -> None:
            val = (self.registers[hi] << 8) | self.registers[lo]
            val = (val - 1) % 65536
            val_hi = (val & 0xff00) >> 8
            val_lo = val & 0x00ff
            self.registers[hi] = val_hi
            self.registers[lo] = val_lo
        return fn

    def instr_dcx_sp(self) -> Callable[[], None]:
        def fn() -> None:
            self.registers['sp'] = (self.registers['sp'] - 1) % 65536
        return fn

    ##
    ## Jump/call instructions
    ##

    def instr_ret(self) -> Callable[[], None]:
        def fn() -> None:
            self.return_from_sub()
        return fn

    def instr_ret_zero(self, cmp: int) -> Callable[[], None]:
        def fn() -> None:
            if self.get_flag_zero() == cmp:
                self.return_from_sub()
        return fn

    def instr_ret_carry(self, cmp: int) -> Callable[[], None]:
        def fn() -> None:
            if self.get_flag_carry() == cmp:
                self.return_from_sub()
        return fn

    def instr_ret_parity(self, cmp: int) -> Callable[[], None]:
        def fn() -> None:
            if self.get_flag_parity() == cmp:
                self.return_from_sub()
        return fn

    def instr_ret_sign(self, cmp: int) -> Callable[[], None]:
        def fn() -> None:
            if self.get_flag_sign() == cmp:
                self.return_from_sub()
        return fn

    def instr_pchl(self) -> Callable[[], None]:
        def fn() -> None:
            lo_addr = self.registers['l']
            hi_addr = self.registers['h']
            addr = (hi_addr << 8) | lo_addr
            self.registers['pc'] = addr
        return fn

    def instr_jmp(self) -> Callable[[], None]:
        def fn() -> None:
            lo_addr = self.get_program_byte()
            hi_addr = self.get_program_byte()
            addr = (hi_addr << 8) | lo_addr
            self.registers['pc'] = addr
        return fn

    def instr_jmp_zero(self, cmp: int) -> Callable[[], None]:
        def fn() -> None:
            lo_addr = self.get_program_byte()
            hi_addr = self.get_program_byte()
            addr = (hi_addr << 8) | lo_addr
            if self.get_flag_zero() == cmp:
                self.registers['pc'] = addr
        return fn

    def instr_jmp_carry(self, cmp: int) -> Callable[[], None]:
        def fn() -> None:
            lo_addr = self.get_program_byte()
            hi_addr = self.get_program_byte()
            addr = (hi_addr << 8) | lo_addr
            if self.get_flag_carry() == cmp:
                self.registers['pc'] = addr
        return fn

    def instr_jmp_parity(self, cmp: int) -> Callable[[], None]:
        def fn() -> None:
            lo_addr = self.get_program_byte()
            hi_addr = self.get_program_byte()
            addr = (hi_addr << 8) | lo_addr
            if self.get_flag_parity() == cmp:
                self.registers['pc'] = addr
        return fn

    def instr_jmp_sign(self, cmp: int) -> Callable[[], None]:
        def fn() -> None:
            lo_addr = self.get_program_byte()
            hi_addr = self.get_program_byte()
            addr = (hi_addr << 8) | lo_addr
            if self.get_flag_sign() == cmp:
                self.registers['pc'] = addr
        return fn

    def instr_call(self) -> Callable[[], None]:
        def fn() -> None:
            lo_addr = self.get_program_byte()
            hi_addr = self.get_program_byte()
            addr = (hi_addr << 8) | lo_addr
            self.call_sub(addr)
        return fn

    def instr_call_zero(self, cmp: int) -> Callable[[], None]:
        def fn() -> None:
            lo_addr = self.get_program_byte()
            hi_addr = self.get_program_byte()
            addr = (hi_addr << 8) | lo_addr
            if self.get_flag_zero() == cmp:
                self.call_sub(addr)
        return fn

    def instr_call_carry(self, cmp: int) -> Callable[[], None]:
        def fn() -> None:
            lo_addr = self.get_program_byte()
            hi_addr = self.get_program_byte()
            addr = (hi_addr << 8) | lo_addr
            if self.get_flag_carry() == cmp:
                self.call_sub(addr)
        return fn

    def instr_call_parity(self, cmp: int) -> Callable[[], None]:
        def fn() -> None:
            lo_addr = self.get_program_byte()
            hi_addr = self.get_program_byte()
            addr = (hi_addr << 8) | lo_addr
            if self.get_flag_parity() == cmp:
                self.call_sub(addr)
        return fn

    def instr_call_sign(self, cmp: int) -> Callable[[], None]:
        def fn() -> None:
            lo_addr = self.get_program_byte()
            hi_addr = self.get_program_byte()
            addr = (hi_addr << 8) | lo_addr
            if self.get_flag_sign() == cmp:
                self.call_sub(addr)
        return fn

    def instr_reset(self, exp: int) -> Callable[[], None]:
        def fn() -> None:
            addr = exp << 3
            self.call_sub(addr)
        return fn

    def return_from_sub(self) -> None:
        sp = self.registers['sp']
        addr_lo = self.get_mem(sp)
        addr_hi = self.get_mem(sp + 1)
        self.registers['pc'] = (addr_hi << 8) | addr_lo
        self.registers['sp'] += 2

    def call_sub(self, addr: int) -> None:
        pc = self.registers['pc']
        sp = self.registers['sp']
        self.set_mem(sp - 1, (pc & 0xff00) >> 8)
        self.set_mem(sp - 2, pc & 0x00ff)
        self.registers['sp'] -= 2
        self.registers['pc'] = addr

    ##
    ## Misc. instructions
    ##

    def instr_nop(self) -> Callable[[], None]:
        def fn() -> None:
            pass
        return fn

    def instr_halt(self) -> Callable[[], None]:
        def fn() -> None:
            self.halted = True
            self.registers['pc'] -= 1
        return fn

    def instr_ei(self) -> Callable[[], None]:
        def fn() -> None:
            pass
        return fn

    def instr_di(self) -> Callable[[], None]:
        def fn() -> None:
            pass
        return fn

    def instr_in(self) -> Callable[[], None]:
        def fn() -> None:
            port_addr = self.get_program_byte()
            ch = self.io.get_input(port_addr) if self.io is not None else None
            if ch is not None:
                self.registers['a'] = ch
        return fn

    def instr_out(self) -> Callable[[], None]:
        def fn() -> None:
            port_addr = self.get_program_byte()
            val = self.registers['a']
            if self.io is not None:
                self.io.send_output(port_addr, val)
        return fn


def parity(n: int) -> int:
    num = n
    ones = 0
    for _ in range(8):
        ones += num & 0b00000001
        num = num >> 1
    return 1 if ones % 2 == 0 else 0


if __name__ == '__main__':
    vm = Virtual8080()
    vm.set_flag_carry(0)
    vm.set_flag_auxcarry(0)
    vm.memory[0] = 0x3e     # mvi a, 
    vm.memory[1] = 0x9b
    vm.memory[2] = 0x27     # daa
    vm.step()
    vm.step()
    assert(vm.registers['a'] == 1)
    assert(vm.get_flag_carry() == 1)
    assert(vm.get_flag_auxcarry() == 1)

    vm = Virtual8080()
    vm.memory[0] = 0x3e     # mvi a, 
    vm.memory[1] = 0x6c
    vm.memory[2] = 0x06     # mvi b,
    vm.memory[3] = 0x2e
    vm.memory[4] = 0x80     # add b
    vm.step()
    vm.step()
    vm.step()
    assert(vm.registers['a'] == 0x9a)
    assert(vm.get_flag_sign() == 1)
    assert(vm.get_flag_zero() == 0)
    assert(vm.get_flag_auxcarry() == 1)
    assert(vm.get_flag_parity() == 1)
    assert(vm.get_flag_carry() == 0)

    vm = Virtual8080()
    vm.memory[0] = 0x3e     # mvi a, 
    vm.memory[1] = 0x42
    vm.memory[2] = 0x06     # mvi b,
    vm.memory[3] = 0x3d
    vm.memory[4] = 0x88     # adc b
    vm.step()
    vm.step()
    vm.step()
    assert(vm.registers['a'] == 0x7f)
    assert(vm.get_flag_sign() == 0)
    assert(vm.get_flag_zero() == 0)
    assert(vm.get_flag_auxcarry() == 0)
    assert(vm.get_flag_parity() == 0)
    assert(vm.get_flag_carry() == 0)

    vm = Virtual8080()
    vm.set_flag_carry(1)
    vm.memory[0] = 0x3e     # mvi a, 
    vm.memory[1] = 0x42
    vm.memory[2] = 0x06     # mvi b,
    vm.memory[3] = 0x3d
    vm.memory[4] = 0x88     # adc b
    vm.step()
    vm.step()
    vm.step()
    assert(vm.registers['a'] == 0x80)
    assert(vm.get_flag_sign() == 1)
    assert(vm.get_flag_zero() == 0)
    assert(vm.get_flag_auxcarry() == 1)
    assert(vm.get_flag_parity() == 0)
    assert(vm.get_flag_carry() == 0)

    vm = Virtual8080()
    vm.memory[0] = 0x3e     # mvi a, 
    vm.memory[1] = 0x3e
    vm.memory[2] = 0x97     # sub a
    vm.step()
    vm.step()
    assert(vm.registers['a'] == 0)
    assert(vm.get_flag_sign() == 0)
    assert(vm.get_flag_zero() == 1)
    assert(vm.get_flag_auxcarry() == 1)
    assert(vm.get_flag_parity() == 1)
    assert(vm.get_flag_carry() == 0)

    vm = Virtual8080()
    vm.set_flag_carry(1)
    vm.memory[0] = 0x3e     # mvi a, 
    vm.memory[1] = 4
    vm.memory[2] = 0x06     # mvi b,
    vm.memory[3] = 2
    vm.memory[4] = 0x98     # sbb b
    vm.step()
    vm.step()
    vm.step()
    assert(vm.registers['a'] == 1)
    assert(vm.get_flag_sign() == 0)
    assert(vm.get_flag_zero() == 0)
    assert(vm.get_flag_auxcarry() == 1)
    assert(vm.get_flag_parity() == 0)
    assert(vm.get_flag_carry() == 0)

    vm = Virtual8080()
    vm.memory[0] = 0x3e     # mvi a, 
    vm.memory[1] = 0x14
    vm.memory[2] = 0xc6     # adi
    vm.memory[3] = 0x42
    vm.step()
    vm.step()
    assert(vm.registers['a'] == 0x56)
    assert(vm.get_flag_sign() == 0)
    assert(vm.get_flag_zero() == 0)
    assert(vm.get_flag_auxcarry() == 0)
    assert(vm.get_flag_parity() == 1)
    assert(vm.get_flag_carry() == 0)

    vm = Virtual8080()
    vm.memory[0] = 0x3e     # mvi a, 
    vm.memory[1] = 0x56
    vm.memory[2] = 0xc6     # adi
    vm.memory[3] = 0xbe
    vm.step()
    vm.step()
    assert(vm.registers['a'] == 0x14)
    assert(vm.get_flag_sign() == 0)
    assert(vm.get_flag_zero() == 0)
    assert(vm.get_flag_auxcarry() == 1)
    assert(vm.get_flag_parity() == 1)
    assert(vm.get_flag_carry() == 1)

    vm = Virtual8080()
    vm.memory[0] = 0x3e     # mvi a, 
    vm.memory[1] = 0x00
    vm.memory[2] = 0xd6     # sui
    vm.memory[3] = 0x01
    vm.step()
    vm.step()
    assert(vm.registers['a'] == 0xff)
    assert(vm.get_flag_sign() == 1)
    assert(vm.get_flag_zero() == 0)
    assert(vm.get_flag_auxcarry() == 0)   # wtf
    assert(vm.get_flag_parity() == 1)
    assert(vm.get_flag_carry() == 1)

    vm = Virtual8080()
    vm.set_flag_carry(0)
    vm.memory[0] = 0x3e     # mvi a, 
    vm.memory[1] = 0x00
    vm.memory[2] = 0xde     # sbi
    vm.memory[3] = 0x01
    vm.step()
    vm.step()
    assert(vm.registers['a'] == 0xff)
    assert(vm.get_flag_sign() == 1)
    assert(vm.get_flag_zero() == 0)
    assert(vm.get_flag_auxcarry() == 0)   # wtf
    assert(vm.get_flag_parity() == 1)
    assert(vm.get_flag_carry() == 1)

    vm = Virtual8080()
    vm.set_flag_carry(1)
    vm.memory[0] = 0x3e     # mvi a, 
    vm.memory[1] = 0x00
    vm.memory[2] = 0xde     # sbi
    vm.memory[3] = 0x01
    vm.step()
    vm.step()
    assert(vm.registers['a'] == 0xfe)
    assert(vm.get_flag_sign() == 1)
    assert(vm.get_flag_zero() == 0)
    assert(vm.get_flag_auxcarry() == 0)   # wtf
    assert(vm.get_flag_parity() == 0)
    assert(vm.get_flag_carry() == 1)
