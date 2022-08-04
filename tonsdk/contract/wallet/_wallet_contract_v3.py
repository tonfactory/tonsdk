import time

from ...boc import Cell
from ._wallet_contract import WalletContract


class WalletV3ContractBase(WalletContract):
    def create_data_cell(self):
        cell = Cell()
        cell.bits.write_uint(0, 32)
        cell.bits.write_uint(self.options["wallet_id"], 32)
        cell.bits.write_bytes(self.options["public_key"])
        return cell

    def create_signing_message(self, seqno=None):
        seqno = seqno or 0
        message = Cell()
        message.bits.write_uint(self.options["wallet_id"], 32)
        if seqno == 0:
            for _ in range(32):
                message.bits.write_bit(1)
        else:
            timestamp = int(time.time())  # get timestamp in seconds
            message.bits.write_uint(timestamp + 60, 32)

        message.bits.write_uint(seqno, 32)
        return message


class WalletV3ContractR1(WalletV3ContractBase):
    def __init__(self, **kwargs) -> None:
        self.code = "B5EE9C724101010100620000C0FF0020DD2082014C97BA9730ED44D0D70B1FE0A4F2608308D71820D31FD31FD31FF82313BBF263ED44D0D31FD31FD3FFD15132BAF2A15144BAF2A204F901541055F910F2A3F8009320D74A96D307D402FB00E8D101A4C8CB1FCB1FCBFFC9ED543FBE6EE0"
        kwargs["code"] = Cell.one_from_boc(self.code)
        super().__init__(**kwargs)
        if "wallet_id" not in kwargs:
            self.options["wallet_id"] = 698983191 + self.options["wc"]


class WalletV3ContractR2(WalletV3ContractBase):
    def __init__(self, **kwargs) -> None:
        self.code = "B5EE9C724101010100710000DEFF0020DD2082014C97BA218201339CBAB19F71B0ED44D0D31FD31F31D70BFFE304E0A4F2608308D71820D31FD31FD31FF82313BBF263ED44D0D31FD31FD3FFD15132BAF2A15144BAF2A204F901541055F910F2A3F8009320D74A96D307D402FB00E8D101A4C8CB1FCB1FCBFFC9ED5410BD6DAD"
        kwargs["code"] = Cell.one_from_boc(self.code)
        super().__init__(**kwargs)
        if "wallet_id" not in kwargs:
            self.options["wallet_id"] = 698983191 + self.options["wc"]
