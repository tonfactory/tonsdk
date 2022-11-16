from .find_common_prefix import find_common_prefix
from .._cell import Cell

from math import ceil, log2


def pad(src: str, size: int) -> str:
    while len(src) < size:
        src = '0' + src

    return src


def remove_prefix_map(src, length):
    if length == 0:
        return src
    else:
        res = {}
        for k in src:
            res[k[length:]] = src[k]

        return res


def fork_map(src):
    assert len(src) > 0, 'Internal inconsistency'
    left = {}
    right = {}
    for k in src:
        if k.find('0') == 0:
            left[k[1:]] = src[k]
        else:
            right[k[1:]] = src[k]

    assert len(left) > 0, 'Internal inconsistency. Left empty.'
    assert len(right) > 0, 'Internal inconsistency. Left empty.'
    return left, right


def build_node(src):
    assert len(src) > 0, 'Internal inconsistency'
    if len(src) == 1:
        return {
            'type': 'leaf',
            'value': list(src.values())[0]
        }

    left, right = fork_map(src)
    return {
        'type': 'fork',
        'left': build_edge(left),
        'right': build_edge(right)
    }


def build_edge(src):
    assert len(src) > 0, 'Internal inconsistency'
    label = find_common_prefix(list(src.keys()))
    return {
        'label': label,
        'node': build_node(
            remove_prefix_map(src, len(label))
        )
    }


def build_tree(src, key_size):
    # Convert map keys
    tree = {}
    for key in src:
        padded = pad(bin(key)[2:], key_size)
        tree[padded] = src[key]

    # Calculate root label
    return build_edge(tree)


# Serialization
def write_label_short(src, to):
    # Header
    to.write_bit(0)

    # Unary length
    for e in src: to.write_bit(1)
    to.write_bit(0)

    # Value
    for e in src:
        to.write_bit(e == '1')

    return to


def label_short_length(src):
    return 1 + len(src) + 1 + len(src)


def write_label_long(src, key_length, to):
    # Header
    to.write_bit(1)
    to.write_bit(0)

    # Length
    length = ceil(log2(key_length + 1))
    to.write_uint(len(src), length)

    # Value
    for e in src:
        to.write_bit(e == '1')

    return to


def label_long_length(src, key_length):
    return 1 + 1 + ceil(log2(key_length + 1)) + len(src)


def write_label_same(value: bool, length, key_length, to):
    to.write_bit(1)
    to.write_bit(1)

    to.write_bit(value)

    len_len = ceil(log2(key_length + 1))
    to.write_uint(length, len_len)


def label_same_length(key_size):
    return 1 + 1 + 1 + ceil(log2(key_size + 1))


def is_same(src):
    if len(src) == 0 or len(src) == 1:
        return True

    for e in src[1:]:
        if e != src[0]:
            return False

    return True


def detect_label_type(src, key_size):
    kind = 'short'
    kind_length = label_short_length(src)

    long_length = label_long_length(src, key_size)
    if long_length < kind_length:
        kind_length = long_length
        kind = 'long'

    if is_same(src):
        same_length = label_same_length(key_size)
        if same_length < kind_length:
            kind_length = same_length
            kind = 'same'

    return kind


def write_label(src, key_size, to):
    type = detect_label_type(src, key_size)
    if type == 'short':
        write_label_short(src, to)
    elif type == 'long':
        write_label_long(src, key_size, to)
    elif type == 'same':
        write_label_same(src[0] == '1', len(src), key_size, to)


def write_node(src, key_size, serializer, to):
    if src['type'] == 'leaf':
        serializer(src['value'], to)

    if src['type'] == 'fork':
        left_cell = Cell()
        right_cell = Cell()
        write_edge(src['left'], key_size - 1, serializer, left_cell)
        write_edge(src['right'], key_size - 1, serializer, right_cell)
        to.refs.append(left_cell)
        to.refs.append(right_cell)


def write_edge(src, key_size, serializer, to):
    write_label(src['label'], key_size, to.bits)
    write_node(src['node'], key_size - len(src['label']), serializer, to)


def serialize_dict(src, key_size, serializer):
    tree = build_tree(src, key_size)
    dest = Cell()
    write_edge(tree, key_size, serializer, dest)
    return dest
