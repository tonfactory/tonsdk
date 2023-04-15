from tonsdk.boc import begin_cell, Cell
from tonsdk.utils import Address

cell = begin_cell()\
    .store_uint(4, 32)\
    .store_address(Address('EQBvW8Z5huBkMJYdnfAEM5JqTNkuWX3diqYENkWsIL0XggGG'))\
    .end_cell()
