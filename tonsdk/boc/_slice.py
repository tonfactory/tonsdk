import bitarray
from typing import Optional

from ._cell import Cell
from ..utils._address import Address


class Slice:
    """Slice like an analog of slice in FunC. Used only for reading."""
    def __init__(self, cell: Cell):
        self.bits = bitarray.bitarray()
        self.bits.frombytes(cell.bits.array)
        self.bits = self.bits[:cell.bits.cursor]
        self.refs = cell.refs
        self.ref_offset = 0

    def __len__(self):
        return len(self.bits)

    def __repr__(self):
        return hex(int(self.bits.to01(), 2))[2:].upper()

    def is_empty(self) -> bool:
        return len(self.bits) == 0

    def end_parse(self):
        """Throws an exception if the slice is not empty."""
        if not self.is_empty() or self.ref_offset != len(self.refs):
            raise Exception("Slice is not empty.")

    def read_bit(self) -> int:
        """Reads single bit from the slice."""
        bit = self.bits[0]
        del self.bits[0]
        return bit

    def preload_bit(self) -> int:
        return self.bits[0]

    def read_bits(self, bit_count: int) -> bitarray.bitarray:
        bits = self.bits[:bit_count]
        del self.bits[:bit_count]
        return bits

    def preload_bits(self, bit_count: int) -> bitarray.bitarray:
        return self.bits[:bit_count]

    def skip_bits(self, bit_count: int):
        del self.bits[:bit_count]

    def read_uint(self, bit_length: int) -> int:
        value = self.bits[:bit_length]
        del self.bits[:bit_length]
        return int(value.to01(), 2)

    def preload_uint(self, bit_length: int) -> int:
        value = self.bits[:bit_length]
        return int(value.to01(), 2)

    def read_bytes(self, bytes_count: int) -> bytes:
        length = bytes_count * 8
        value = self.bits[:length]
        del self.bits[:length]
        return value.tobytes()

    def read_int(self, bit_length: int) -> int:
        if bit_length == 1:
            # if num is -1 then bit is 1. if 0 then 1. see _bit_string.py
            return - self.read_bit()
        else:
            is_negative = self.read_bit()
            value = self.read_uint(bit_length - 1)
            if is_negative == 1:
                # ones complement
                return - (2 ** (bit_length - 1) - value)
            else:
                return value

    def preload_int(self, bit_length: int) -> int:
        tmp = self.bits
        value = self.read_int(bit_length)
        self.bits = tmp
        return value

    def read_msg_addr(self) -> Optional[Address]:
        """Reads contract address from the slice.
        May return None if there is a zero-address."""
        if self.read_uint(2) == 0:
            return None
        self.read_bit()  # anycast
        workchain_id = hex(self.read_int(8)).replace('0x', '')
        hashpart = self.read_bytes(32).hex()
        return Address(workchain_id + ":" + hashpart)

    def read_coins(self) -> int:
        """Reads an amount of coins from the slice. Returns nanocoins."""
        length = self.read_uint(4)
        if length == 0:  # 0 in length means 0 coins
            return 0
        else:
            return self.read_uint(length * 8)

    def read_grams(self) -> int:
        """Reads an amount of coins from the slice. Returns nanocoins."""
        return self.read_coins()

    def read_string(self, length: int = 0) -> str:
        """Reads string from the slice.
        If length is 0, then reads string until the end of the slice."""
        if length == 0:
            length = len(self.bits) // 8
        return self.read_bytes(length).decode("utf-8")

    def read_ref(self) -> Cell:
        """Reads next reference cell from the slice."""
        ref = self.refs[self.ref_offset]
        self.ref_offset += 1
        return ref

    def preload_ref(self) -> Cell:
        return self.refs[self.ref_offset]

    def load_dict(self) -> Optional[Cell]:
        """Loads dictionary like a Cell from the slice.
        Returns None if the dictionary was null()."""
        not_null = self.read_bit()
        if not_null:
            return self.read_ref()
        else:
            return None

    def preload_dict(self) -> Optional[Cell]:
        not_null = self.preload_bit()
        if not_null:
            return self.preload_ref()
        else:
            return None

    def skip_dict(self):
        self.load_dict()
