import time

from ...boc import Cell
from ._wallet_contract import WalletContract


class WalletV2ContractBase(WalletContract):
    def create_signing_message(self, seqno=None):
        seqno = seqno or 0
        message = Cell()
        message.bits.write_uint(seqno, 32)
        if seqno == 0:
            for _ in range(32):
                message.bits.write_bit(1)
        else:
            timestamp = int(time.time())  # get timestamp in seconds
            message.bits.write_uint(timestamp + 60, 32)

        return message


class WalletV2ContractR1(WalletV2ContractBase):
    def __init__(self, **kwargs) -> None:
        self.code = "B5EE9C724101010100570000AAFF0020DD2082014C97BA9730ED44D0D70B1FE0A4F2608308D71820D31FD31F01F823BBF263ED44D0D31FD3FFD15131BAF2A103F901541042F910F2A2F800029320D74A96D307D402FB00E8D1A4C8CB1FCBFFC9ED54A1370BB6"
        kwargs["code"] = Cell.one_from_boc(self.code)
        super().__init__(**kwargs)


class WalletV2ContractR2(WalletV2ContractBase):
    def __init__(self, **kwargs) -> None:
        self.code = "B5EE9C724101010100630000C2FF0020DD2082014C97BA218201339CBAB19C71B0ED44D0D31FD70BFFE304E0A4F2608308D71820D31FD31F01F823BBF263ED44D0D31FD3FFD15131BAF2A103F901541042F910F2A2F800029320D74A96D307D402FB00E8D1A4C8CB1FCBFFC9ED54044CD7A1"
        kwargs["code"] = Cell.one_from_boc(self.code)
        super().__init__(**kwargs)
