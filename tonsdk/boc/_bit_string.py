import copy
import math
from typing import Union, Optional

from ..utils._address import Address


class BitString:
    def __init__(self, length: int):
        self.array = bytearray(math.ceil(length / 8))
        self.cursor = 0
        self.length = length

    def __repr__(self):
        return str(self.get_top_upped_array())

    def __iter__(self):
        for i in range(self.cursor):
            yield self.get(i)

    def __getitem__(self, key):
        if isinstance(key, slice):
            start = key.start if key.start else 0
            stop = key.stop if key.stop else len(self)
            step = key.step if key.step else 1

            return [self[ii] for ii in range(start, stop, step)]
        elif isinstance(key, int):
            if key < 0:
                key += len(self)
            if key < 0 or key >= len(self):
                raise IndexError("The index (%d) is out of range." % key)
            return self.get(key)
        else:
            raise TypeError("Invalid argument type.")

    def __len__(self):
        return self.length

    def get(self, n: int):
        """Just returns n bits from cursor. Does not move the cursor."""
        return int((self.array[(n // 8) | 0] & (1 << (7 - (n % 8)))) > 0)

    def off(self, n):
        """Sets next from cursor n bits to 0. Does not move cursor."""
        self.check_range(n)
        self.array[(n // 8) | 0] &= ~(1 << (7 - (n % 8)))

    def on(self, n):
        """Sets next from cursor n bits to 1. Does not move cursor."""
        self.check_range(n)
        self.array[(n // 8) | 0] |= 1 << (7 - (n % 8))

    def check_range(self, n: int) -> None:
        """Throws an exception if the cursor + n is out of range."""
        if n > self.length:
            raise Exception("BitString overflow")

    def set_top_upped_array(self, array: bytearray, fullfilled_bytes=True):
        self.length = len(array) * 8
        self.array = array
        self.cursor = self.length

        if fullfilled_bytes or not self.length:
            return

        else:
            found_end_bit = False
            for c in range(7):
                self.cursor -= 1

                if self.get(self.cursor):
                    found_end_bit = True
                    self.off(self.cursor)
                    break

            if not found_end_bit:
                raise Exception(
                    f"Incorrect TopUppedArray {array}, {fullfilled_bytes}")

    def get_top_upped_array(self) -> bytearray:
        ret = copy.deepcopy(self)
        tu = math.ceil(ret.cursor / 8) * 8 - ret.cursor
        if tu > 0:
            tu -= 1
            ret.write_bit(1)
            while tu > 0:
                tu -= 1
                ret.write_bit(0)
        ret.array = ret.array[:math.ceil(ret.cursor / 8)]
        return ret.array

    def get_free_bits(self) -> int:
        """Returns the number of not used bits in the BitString."""
        return self.length - self.cursor

    def get_used_bits(self):
        return self.cursor

    def write_bit_array(self, ba: bytearray):
        """Writes a bytearray as a bit array one bit by one."""
        for b in ba.decode('utf-8'):
            self.write_bit(b)

    def write_bit(self, b: Union[str, int]):
        b = int(b)
        if b == 1:
            self.on(self.cursor)
        elif b == 0:
            self.off(self.cursor)
        else:
            raise Exception("BitString can only write 1 or 0")

        self.cursor += 1

    def write_uint(self, number: int, bit_length: int):
        if bit_length == 0 or len("{0:b}".format(number)) > bit_length:
            if number == 0:
                return

            raise Exception(
                f"bitLength is too small for number, got number={number},bitLength={bit_length}")

        for i in range(bit_length, 0, -1):
            k = (2 ** (i - 1))
            if number // k == 1:
                self.write_bit(1)
                number -= k
            else:
                self.write_bit(0)

    def write_uint8(self, ui8: int):
        """Just as write_uint(n, 8), but only write_uint8(n) (?)."""
        self.write_uint(ui8, 8)

    def write_int(self, number: int, bit_length: int):
        if bit_length == 1:
            if number == -1:
                self.write_bit(1)
                return

            if number == 0:
                self.write_bit(0)
                return

            raise Exception("Bitlength is too small for number")
        else:
            if number < 0:
                self.write_bit(1)
                s = 2 ** (bit_length - 1)
                self.write_uint(s + number, bit_length - 1)
            else:
                self.write_bit(0)
                self.write_uint(number, bit_length - 1)

    def write_string(self, value: str):
        self.write_bytes(bytes(value, encoding="utf-8"))

    def write_bytes(self, ui8_array: bytes):
        for ui8 in ui8_array:
            self.write_uint8(ui8)

    def write_bit_string(self, another_bit_string: "BitString"):
        for bit in another_bit_string:
            self.write_bit(bit)

    def write_address(self, address: Optional[Address]):
        """Writes an address, maybe zero-address (None) to the BitString."""
        if address is None:
            self.write_uint(0, 2)
        else:
            self.write_uint(2, 2)
            self.write_uint(0, 1)  # anycast
            self.write_int(address.wc, 8)
            self.write_bytes(address.hash_part)

    def write_grams(self, amount: int):
        if amount == 0:
            self.write_uint(0, 4)
        else:
            amount = int(amount)
            l = math.ceil(len(hex(amount)[2:]) / 2)  # ? [2:] removes 0x
            self.write_uint(l, 4)
            self.write_uint(amount, l * 8)

    def write_coins(self, amount):
        self.write_grams(amount)
