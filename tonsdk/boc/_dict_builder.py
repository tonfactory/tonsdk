from .dict import serialize_dict
from ._cell import Cell

class DictBuilder:
    def __init__(self, key_size: int):
        self.key_size = key_size
        self.items = {}
        self.ended = False

    def store_cell(self, index, value: Cell):
        assert self.ended is False, 'Already ended'
        if type(index) == bytes:
            index = int(index.hex(), 16)

        assert type(index) == int, 'Invalid index type'
        assert not (index in self.items), f'Item {index} already exist'
        self.items[index] = value
        return self

    def store_ref(self, index, value: Cell):
        assert self.ended is False, 'Already ended'

        cell = Cell()
        cell.refs.append(value)
        self.store_cell(index, cell)
        return self

    def end_dict(self) -> Cell:
        assert self.ended is False, 'Already ended'
        self.ended = True
        if not self.items:
            return Cell()  # ?

        def default_serializer(src, dest):
            dest.write_cell(src)

        return serialize_dict(self.items, self.key_size, default_serializer)

    def end_cell(self) -> Cell:
        assert self.ended is False, 'Already ended'
        assert self.items, 'Dict is empty'
        return self.end_dict()

def begin_dict(key_size):
    return DictBuilder(key_size)
