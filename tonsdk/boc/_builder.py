

from ._bit_string import BitString
from ._cell import Cell

class Builder:
    def __init__(self):
        self.bits = BitString(1023)
        self.refs = []
        self.is_exotic = False

    def __repr__(self):
        return "<Builder refs_num: %d, %s>" % (len(self.refs), repr(self.bits))

    def store_cell(self, src: Cell):
        self.bits.write_bit_string(src.bits)
        self.refs += src.refs
        return self

    def store_ref(self, src: Cell):
        self.refs.append(src)
        return self

    def store_maybe_ref(self, src):
        if src:
            self.bits.write_bit(1)
            self.store_ref(src)
        else:
            self.bits.write_bit(0)

        return self

    def store_bit(self, value):
        self.bits.write_bit(value)
        return self

    def store_bit_array(self, value):
        self.bits.write_bit_array(value)
        return self

    def store_uint(self, value, bit_length):
        self.bits.write_uint(value, bit_length)
        return self

    def store_uint8(self, value):
        self.bits.write_uint8(value)
        return self

    def store_int(self, value, bit_length):
        self.bits.write_int(value, bit_length)
        return self

    def store_string(self, value):
        self.bits.write_string(value)
        return self

    def store_bytes(self, value):
        self.bits.write_bytes(value)
        return self

    def store_bit_string(self, value):
        self.bits.write_bit_string(value)
        return self

    def store_address(self, value):
        self.bits.write_address(value)
        return self

    def store_grams(self, value):
        self.bits.write_grams(value)
        return self

    def store_coins(self, value):
        self.bits.write_coins(value)
        return self

    def end_cell(self):
        cell = Cell()
        cell.write_cell(self)
        return cell


def begin_cell():
    return Builder()
