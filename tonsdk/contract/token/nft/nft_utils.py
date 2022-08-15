import urllib.parse

from ....boc import Cell

SNAKE_DATA_PREFIX = 0x00
CHUNK_DATA_PREFIX = 0x01
ONCHAIN_CONTENT_PREFIX = 0x00
OFFCHAIN_CONTENT_PREFIX = 0x01


def serialize_uri(uri):
    return urllib.parse.quote(uri, safe='~@#$&()*!+=:;,?/\'').encode()


def parse_uri(uri):
    return uri.decode()


def create_offchain_uri_cell(uri):
    cell = Cell()
    cell.bits.write_uint8(OFFCHAIN_CONTENT_PREFIX)
    cell.bits.write_bytes(serialize_uri(uri))
    return cell


def parse_offchain_uri_cell(cell):
    assert cell.bits[0] == OFFCHAIN_CONTENT_PREFIX, 'Invalid offchain uri cell'
    length = 0
    c = cell
    while c:
        length += len(c.bits)
        c = c.refs[0] if c.refs else None

    _bytes = b""
    length = 0
    c = cell
    while c:
        _bytes += c.bits
        length += len(c.bits)
        c = c.refs[0] if c.refs else None

    return parse_uri(_bytes[1:])
