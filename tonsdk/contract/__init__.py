from abc import ABC

from ..boc import Cell
from ..utils import Address


class Contract(ABC):
    def __init__(self, **kwargs):
        self.options = kwargs
        self._address = Address(
            kwargs["address"]) if "address" in kwargs else None
        if "wc" not in kwargs:
            kwargs["wc"] = self._address.wc if self._address is not None else 0

    @property
    def address(self):
        if self._address is None:
            self._address = self.create_state_init()["address"]

        return self._address

    def create_state_init(self):
        code_cell = self.create_code_cell()
        data_cell = self.create_data_cell()
        state_init = self.__create_state_init(code_cell, data_cell)
        state_init_hash = state_init.bytes_hash()

        address = Address(
            str(self.options["wc"]) + ":" + state_init_hash.hex())

        return {
            "code": code_cell,
            "data": data_cell,
            "address": address,
            "state_init": state_init,
        }

    def create_code_cell(self):
        if "code" not in self.options or self.options["code"] is None:
            raise Exception("Contract: options.code is not defined")
        return self.options["code"]

    def create_data_cell(self):
        return Cell()

    def create_init_external_message(self):
        create_state_init = self.create_state_init()
        state_init = create_state_init["state_init"]
        address = create_state_init["address"]
        code = create_state_init["code"]
        data = create_state_init["data"]
        header = Contract.create_external_message_header(address)
        external_message = Contract.create_common_msg_info(header, state_init)
        return {
            "address": address,
            "message": external_message,

            "state_init": state_init,
            "code": code,
            "data": data,
        }

    @classmethod
    def create_external_message_header(cls, dest, src=None, import_fee=0):
        message = Cell()
        message.bits.write_uint(2, 2)
        message.bits.write_address(Address(src) if src else None)
        message.bits.write_address(Address(dest))
        message.bits.write_grams(import_fee)
        return message

    @classmethod
    def create_internal_message_header(cls, dest, grams=0, ihr_disabled=True,
                                       bounce=None, bounced=False, src=None,
                                       currency_collection=None, ihr_fees=0,
                                       fwd_fees=0, created_lt=0, created_at=0):
        message = Cell()
        message.bits.write_bit(0)
        message.bits.write_bit(ihr_disabled)

        if bounce is not None:
            message.bits.write_bit(bounce)
        else:
            message.bits.write_bit(Address(dest).is_bounceable)
        message.bits.write_bit(bounced)
        message.bits.write_address(Address(src) if src else None)
        message.bits.write_address(Address(dest))
        message.bits.write_grams(grams)
        if currency_collection:
            raise Exception("Currency collections are not implemented yet")

        message.bits.write_bit(bool(currency_collection))
        message.bits.write_grams(ihr_fees)
        message.bits.write_grams(fwd_fees)
        message.bits.write_uint(created_lt, 64)
        message.bits.write_uint(created_at, 32)
        return message

    @classmethod
    def create_common_msg_info(cls, header, state_init=None, body=None):
        common_msg_info = Cell()
        common_msg_info.write_cell(header)
        if state_init:
            common_msg_info.bits.write_bit(1)
            if common_msg_info.bits.get_free_bits() - 1 >= state_init.bits.get_used_bits():
                common_msg_info.bits.write_bit(0)
                common_msg_info.write_cell(state_init)
            else:
                common_msg_info.bits.write_bit(1)
                common_msg_info.refs.append(state_init)
        else:
            common_msg_info.bits.write_bit(0)

        if body:
            if common_msg_info.bits.get_free_bits() >= body.bits.get_used_bits():
                common_msg_info.bits.write_bit(0)
                common_msg_info.write_cell(body)
            else:
                common_msg_info.bits.write_bit(1)
                common_msg_info.refs.append(body)
        else:
            common_msg_info.bits.write_bit(0)

        return common_msg_info

    def __create_state_init(self, code, data, library=None, split_depth=None, ticktock=None):
        if library or split_depth or ticktock:
            raise Exception(
                "Library/SplitDepth/Ticktock in state init is not implemented")

        state_init = Cell()
        settings = bytes(''.join(['1' if i else '0' for i in [bool(split_depth), bool(
            ticktock), bool(code), bool(data), bool(library)]]), 'utf-8')
        state_init.bits.write_bit_array(settings)

        if code:
            state_init.refs.append(code)
        if data:
            state_init.refs.append(data)
        if library:
            state_init.refs.append(library)
        return state_init
