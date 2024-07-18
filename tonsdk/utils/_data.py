# https://github.com/ton-blockchain/TEPs/blob/master/text/0064-token-data-standard.md#data-serialization
from ctypes import Union

from tonsdk.boc import begin_cell, Builder, Slice


class SnakeData:
    prefix = 0x00
    prefix_len = 8

    @classmethod
    def write(cls, builder: Builder, data: Union[bytes, bytearray], prefixed=False):
        if prefixed:
            builder.store_uint(cls.prefix, cls.prefix_len)

        # todo: implement data serialization logic to a given builder (now data is a bytes sequence)
        # implementation example
        builders = []

        while len(data) > 0:
            max_bytes = builder.builder_rembits >> 3
            bits, data = data[:max_bytes], data[max_bytes:]

            builder.store_bytes(bits)
            builders.append(builder)

            builder = begin_cell()

        if len(builders) > 1:
            last_builder = builders[-1]

            for builder in reversed(builders[:-1]):
                builder.store_ref(last_builder.end_cell())
                last_builder = builder

        return builders[0]

    @classmethod
    def read(cls, cs: Slice, prefixed=False):
        data = bytearray()

        if prefixed:
            assert cs.preload_uint(cls.prefix_len) == cls.prefix

        while True:
            data.extend(cs.load_bytes(cs.slice_bits >> 3))

            if cs.slice_refs > 0:
                cs = cs.load_ref().begin_parse()
                continue

            break

        return data
