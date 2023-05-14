from tonsdk.boc import Slice, begin_cell
from tonsdk.utils import Address

cell = begin_cell()\
    .store_uint(4, 32)\
    .store_address(Address('EQBvW8Z5huBkMJYdnfAEM5JqTNkuWX3diqYENkWsIL0XggGG'))\
    .end_cell()

slice = cell.begin_parse()  # or Slice(cell)

stored_value_uint = slice.read_uint(32)

stored_value_addr = slice.read_msg_addr()

assert stored_value_uint == 4
assert stored_value_addr.to_string(True, True, True) == 'EQBvW8Z5huBkMJYdnfAEM5JqTNkuWX3diqYENkWsIL0XggGG'
