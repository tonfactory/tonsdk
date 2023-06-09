from ._builder import Builder
from ._cell import Cell
from ._slice import Slice


def read_string_tail(string_slice: Slice):
    if len(string_slice) % 8 != 0:
        raise Exception(f"Invalid string length: {len(string_slice) // 8}")

    if len(string_slice.refs) > 1:
        raise Exception("Too many refs in string tail")

    if len(string_slice.refs) == 1 and 1023 - len(string_slice) > 7:
        raise Exception(f"Invalid string length: {len(string_slice) // 8}")

    text_bytes = bytes()

    if len(string_slice) != 0:
        text_bytes = string_slice.read_bytes(len(string_slice) // 8)

    if len(string_slice.refs) - string_slice.ref_offset == 1:
        text_bytes += read_string_tail(string_slice.read_ref().begin_parse())

    return text_bytes


def write_string_tail(text: bytes, builder: Builder):
    if len(text) <= 0:
        return

    free_bytes = builder.bits.get_free_bits() // 8

    if len(text) <= free_bytes:
        builder.store_bytes(text)
        return

    available = text[:free_bytes]
    tail = text[free_bytes:]
    builder.store_bytes(available)
    new_builder = Builder()
    write_string_tail(tail, new_builder)
    builder.store_ref(new_builder.end_cell())


def string_to_cell(text: str):
    builder = Builder()
    write_string_tail(bytes(text, encoding="utf8"), builder)
    return builder.end_cell()


def cell_to_string(string_cell: Cell):
    return read_string_tail(string_cell.begin_parse()).decode("utf8")
