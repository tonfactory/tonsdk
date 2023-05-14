import decimal
from enum import Enum
from typing import Union

from .. import Contract
from ...boc import Cell
from ...utils import Address, sign_message


class SendModeEnum(int, Enum):
    carry_all_remaining_balance = 128
    carry_all_remaining_incoming_value = 64
    destroy_account_if_zero = 32
    ignore_errors = 2
    pay_gas_separately = 1

    def __str__(self) -> str:
        return super().__str__()


class WalletContract(Contract):
    def __init__(self, **kwargs):
        if (("public_key" not in kwargs or "private_key" not in kwargs) and "address" not in kwargs) and 'public_keys' not in kwargs:
            raise Exception(
                "WalletContract required publicKey or address in options")
        super().__init__(**kwargs)

    def create_data_cell(self):
        cell = Cell()
        cell.bits.write_uint(0, 32)
        cell.bits.write_bytes(self.options["public_key"])
        return cell

    def create_signing_message(self, seqno=None):
        seqno = seqno or 0
        cell = Cell()
        cell.bits.write_uint(seqno, 32)
        return cell

    def create_transfer_message(self,
                                to_addr: str,
                                amount: int,
                                seqno: int,
                                payload: Union[Cell, str, bytes, None] = None,
                                send_mode=SendModeEnum.ignore_errors | SendModeEnum.pay_gas_separately,
                                dummy_signature=False, state_init=None):
        payload_cell = Cell()
        if payload:
            if isinstance(payload, str):
                payload_cell.bits.write_uint(0, 32)
                payload_cell.bits.write_string(payload)
            elif isinstance(payload, Cell):
                payload_cell = payload
            else:
                payload_cell.bits.write_bytes(payload)

        order_header = Contract.create_internal_message_header(
            Address(to_addr), decimal.Decimal(amount))
        order = Contract.create_common_msg_info(
            order_header, state_init, payload_cell)
        signing_message = self.create_signing_message(seqno)
        signing_message.bits.write_uint8(send_mode)
        signing_message.refs.append(order)

        return self.create_external_message(signing_message, seqno, dummy_signature)

    def create_external_message(self, signing_message, seqno, dummy_signature=False):
        signature = bytes(64) if dummy_signature else sign_message(
            bytes(signing_message.bytes_hash()), self.options['private_key']).signature

        body = Cell()
        body.bits.write_bytes(signature)
        body.write_cell(signing_message)

        state_init = code = data = None

        if seqno == 0:
            deploy = self.create_state_init()
            state_init = deploy["state_init"]
            code = deploy["code"]
            data = deploy["data"]

        self_address = self.address
        header = Contract.create_external_message_header(self_address)
        result_message = Contract.create_common_msg_info(
            header, state_init, body)

        return {
            "address": self_address,
            "message": result_message,
            "body": body,
            "signature": signature,
            "signing_message": signing_message,
            "state_init": state_init,
            "code": code,
            "data": data,
        }

    def create_init_external_message(self):
        create_state_init = self.create_state_init()
        state_init = create_state_init["state_init"]
        address = create_state_init["address"]
        code = create_state_init["code"]
        data = create_state_init["data"]

        signing_message = self.create_signing_message()
        signature = sign_message(
            bytes(signing_message.bytes_hash()), self.options['private_key']).signature

        body = Cell()
        body.bits.write_bytes(signature)
        body.write_cell(signing_message)

        header = Contract.create_external_message_header(address)
        external_message = Contract.create_common_msg_info(
            header, state_init, body)

        return {
            "address": address,
            "message": external_message,

            "body": body,
            "signing_message": signing_message,
            "state_init": state_init,
            "code": code,
            "data": data,
        }
