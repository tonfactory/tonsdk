import codecs
import ctypes
import math
import struct

import nacl
from nacl.bindings import crypto_sign, crypto_sign_BYTES
from nacl.signing import SignedMessage

from tonsdk.boc import Builder, Slice, Cell


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


def concat_bytes(a, b):
    return a + b  # ?


def move_to_end(index_hashmap, topological_order_arr, target):
    target_index = index_hashmap[target]
    for _hash in index_hashmap:
        if index_hashmap[_hash] > target_index:
            index_hashmap[_hash] -= 1
    index_hashmap[target] = len(topological_order_arr) - 1
    data = topological_order_arr.pop(target_index)
    topological_order_arr.append(data)
    for sub_cell in data[1].refs:
        topological_order_arr, index_hashmap = move_to_end(index_hashmap, topological_order_arr, sub_cell.bytes_hash())
    return [topological_order_arr, index_hashmap]


def tree_walk(cell, topological_order_arr, index_hashmap, parent_hash=None):
    cell_hash = cell.bytes_hash()
    if cell_hash in index_hashmap:
        if parent_hash:
            if index_hashmap[parent_hash] > index_hashmap[cell_hash]:
                topological_order_arr, index_hashmap = move_to_end(index_hashmap, topological_order_arr, cell_hash)
        return [topological_order_arr, index_hashmap]

    index_hashmap[cell_hash] = len(topological_order_arr)
    topological_order_arr.append([cell_hash, cell])
    for sub_cell in cell.refs:
        topological_order_arr, index_hashmap = tree_walk(sub_cell, topological_order_arr, index_hashmap, cell_hash)
    return [topological_order_arr, index_hashmap]


def _crc32c(crc, bytes_arr):
    POLY = 0x82f63b78

    crc ^= 0xffffffff

    for n in range(len(bytes_arr)):
        crc ^= bytes_arr[n]
        crc = (crc >> 1) ^ POLY if crc & 1 else crc >> 1
        crc = (crc >> 1) ^ POLY if crc & 1 else crc >> 1
        crc = (crc >> 1) ^ POLY if crc & 1 else crc >> 1
        crc = (crc >> 1) ^ POLY if crc & 1 else crc >> 1
        crc = (crc >> 1) ^ POLY if crc & 1 else crc >> 1
        crc = (crc >> 1) ^ POLY if crc & 1 else crc >> 1
        crc = (crc >> 1) ^ POLY if crc & 1 else crc >> 1
        crc = (crc >> 1) ^ POLY if crc & 1 else crc >> 1

    return crc ^ 0xffffffff


def crc32c(bytes_array):
    int_crc = _crc32c(0, bytes_array)

    # TODO: check mistakes
    arr = bytearray(4)
    struct.pack_into('>I', arr, 0, int_crc)

    return bytes(arr)[::-1]


def crc16(data):
    POLY = 0x1021
    reg = 0
    message = bytes(data) + bytes(2)

    for byte in message:
        mask = 0x80
        while mask > 0:
            reg <<= 1
            if byte & mask:
                reg += 1
            mask >>= 1
            if reg > 0xffff:
                reg &= 0xffff
                reg ^= POLY

    return bytearray([math.floor(reg / 256), reg % 256])


def read_n_bytes_uint_from_array(size_bytes, uint8_array):
    res = 0
    for c in range(size_bytes):
        res *= 256
        res += uint8_array[c]  # must be uint8

    return res


def compare_bytes(bytes_1, bytes_2):
    return str(bytes_1) == str(bytes_2)  # why str?


def string_to_bytes(string, size=1):  # ?
    if size == 1:
        buf = (ctypes.c_uint8 * len(string))()
    elif size == 2:
        buf = (ctypes.c_uint16 * len(string) * 2)()
    elif size == 4:
        buf = (ctypes.c_uint32 * len(string) * 4)()

    for i, c in enumerate(string):
        # buf[i] = ord(c)
        buf[i] = c  # ?

    return bytes(buf)


def sign_message(message: bytes,
                 signing_key,
                 encoder: nacl.encoding.Encoder = nacl.encoding.RawEncoder, ) -> SignedMessage:
    raw_signed = crypto_sign(message, signing_key)

    signature = encoder.encode(raw_signed[:crypto_sign_BYTES])
    message = encoder.encode(raw_signed[crypto_sign_BYTES:])
    signed = encoder.encode(raw_signed)

    return SignedMessage._from_parts(signature, message, signed)


def b64str_to_bytes(b64str):
    b64bytes = codecs.encode(b64str, "utf-8")
    return codecs.decode(b64bytes, "base64")


def b64str_to_hex(b64str):
    _bytes = b64str_to_bytes(b64str)
    _hex = codecs.encode(_bytes, "hex")
    return codecs.decode(_hex, "utf-8")


def bytes_to_b64str(bytes_arr):
    return codecs.decode(codecs.encode(
        bytes_arr, "base64"), 'utf-8').replace("\n", '')
