from _cell import Cell
from _slice import Slice


def main():
    cell = Cell()
    cell.bits.write_uint(10, 32)
    myslice = Slice(cell)
    print(myslice.read_uint(32))
