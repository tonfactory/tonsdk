import time
import decimal

from .. import Contract
from ._wallet_contract import WalletContract
from ...boc import Cell, begin_cell, begin_dict
from ...utils import Address, sign_message


class HighloadWalletContractBase(WalletContract):
    def create_data_cell(self):
        return begin_cell() \
            .store_uint(self.options["wallet_id"], 32) \
            .store_uint(0, 64) \
            .store_bytes(self.options["public_key"]) \
            .store_maybe_ref(None) \
            .end_cell()

    def create_signing_message(self, query_id: int=0):
        message = begin_cell().store_uint(self.options["wallet_id"], 32)
        return message.store_uint(query_id, 64)


class HighloadWalletV2Contract(HighloadWalletContractBase):
    def __init__(self, **kwargs) -> None:
        # https://github.com/akifoq/highload-wallet/blob/master/highload-wallet-v2-code.fc
        self.code = "B5EE9C720101090100E5000114FF00F4A413F4BCF2C80B010201200203020148040501EAF28308D71820D31FD33FF823AA1F5320B9F263ED44D0D31FD33FD3FFF404D153608040F40E6FA131F2605173BAF2A207F901541087F910F2A302F404D1F8007F8E16218010F4786FA5209802D307D43001FB009132E201B3E65B8325A1C840348040F4438AE63101C8CB1F13CB3FCBFFF400C9ED54080004D03002012006070017BD9CE76A26869AF98EB85FFC0041BE5F976A268698F98E99FE9FF98FA0268A91040207A0737D098C92DBFC95DD1F140034208040F4966FA56C122094305303B9DE2093333601926C21E2B3"
        kwargs["code"] = Cell.one_from_boc(self.code)
        super().__init__(**kwargs)
        if "wallet_id" not in kwargs:
            self.options["wallet_id"] = 698983191 + self.options["wc"]

    def create_transfer_message(self, recipients_list: list, query_id: int, timeout=60, dummy_signature=False):
        if query_id < int(time.time() + timeout) << 32:
            query_id = int(time.time() + timeout) << 32 + query_id

        signing_message = self.create_signing_message(query_id)
        recipients = begin_dict(16)
        for i, recipient in enumerate(recipients_list):
            payload_cell = Cell()
            if recipient.get('payload'):
                if type(recipient['payload']) == str:
                    if len(recipient['payload']) > 0:
                        payload_cell.bits.write_uint(0, 32)
                        payload_cell.bits.write_string(recipient['payload'])
                elif hasattr(recipient['payload'], 'refs'):
                    payload_cell = recipient['payload']
                else:
                    payload_cell.bits.write_bytes(recipient['payload'])

            order_header = Contract.create_internal_message_header(
                Address(recipient['address']), decimal.Decimal(recipient['amount'])
            )
            order = Contract.create_common_msg_info(
                order_header, recipient.get('state_init'), payload_cell
            )
            recipients.store_cell(
                i, begin_cell() \
                    .store_uint8(recipient.get('send_mode', 0)) \
                    .store_ref(order).end_cell()
            )

        signing_message.store_maybe_ref(recipients.end_cell())
        return self.create_external_message(
            signing_message.end_cell(), dummy_signature
        )

    def create_external_message(self, signing_message, dummy_signature=False):
        signature = bytes(64) if dummy_signature else sign_message(
            bytes(signing_message.bytes_hash()), self.options['private_key']).signature

        body = Cell()
        body.bits.write_bytes(signature)
        body.write_cell(signing_message)

        state_init = code = data = None
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
            "query_id": int.from_bytes(signing_message.bits.array[4:12], 'big')
        }

    def create_init_external_message(self, timeout=60):
        create_state_init = self.create_state_init()
        state_init = create_state_init["state_init"]
        address = create_state_init["address"]
        code = create_state_init["code"]
        data = create_state_init["data"]

        signing_message = self.create_signing_message(int(time.time() + timeout) << 32) \
            .store_maybe_ref(None).end_cell()
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
