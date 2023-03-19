import base64
import time
import decimal
from typing import Optional

from .. import Contract
from ._wallet_contract import WalletContract
from ...boc import Cell, begin_cell, begin_dict, Builder
from ...utils import Address, sign_message
from ...crypto import private_key_to_public_key, verify_sign


class MultiSigWalletContractBase(WalletContract):
    def create_data_cell(self):
        owners = begin_dict(8)
        for i in range(len(self.options["public_keys"])):
            owners.store_cell(
                i, begin_cell() \
                    .store_bytes(self.options["public_keys"][i]) \
                    .store_bytes(b'\x00') \
                    .end_cell()
            )

        return begin_cell() \
            .store_uint(self.options["wallet_id"], 32) \
            .store_uint(len(self.options["public_keys"]), 8) \
            .store_uint(self.options["k"], 8) \
            .store_uint(0, 64) \
            .store_maybe_ref(owners.end_cell()) \
            .store_bit(0) \
            .end_cell()


class MultiSigOrder:
    def __init__(self, payload: Cell):
        self.payload = payload
        self.signatures = {}

    def sign(self, owner_id: int, secret_key: bytes):
        signing_hash = self.payload.bytes_hash()
        self.signatures[owner_id] = sign_message(bytes(signing_hash), secret_key).signature
        return signing_hash

    def add_signature(self, owner_id: int, signature: bytes, multisig_wallet):
        signing_hash = self.payload.bytes_hash()
        if not verify_sign(public_key=multisig_wallet.options['public_keys'][owner_id],
                           signed_message=bytes(signing_hash),
                           signature=signature):
            raise Exception('Invalid signature')
        self.signatures[owner_id] = signature

    def union_signatures(self, other):
        self.signatures = dict(list(self.signatures.items()) + list(other.signatures.items()))

    def clear_signatures(self):
        self.signatures = {}

    def to_cell(self, owner_id: int):
        b = begin_cell().store_bit(0)
        for owner in self.signatures:
            signature = self.signatures[owner]
            b = begin_cell() \
                .store_bit(1) \
                .store_ref(
                    begin_cell() \
                    .store_bytes(signature) \
                    .store_uint(owner, 8) \
                    .store_cell(b.end_cell()) \
                    .end_cell()
                )
        return begin_cell() \
               .store_uint(owner_id, 8) \
               .store_cell(b.end_cell()) \
               .store_cell(self.payload) \
               .end_cell()


class MultiSigOrderBuilder:
    def __init__(self, wallet_id, offset=7200, query_id: Optional[int] = None):
        self.wallet_id = wallet_id
        self.messages = begin_cell()
        self.query_id = query_id if query_id is not None else self.generate_query_id(offset)

    def add_message(self, to_addr, amount, payload="", send_mode=3, state_init=None):
        payload_cell = Cell()
        if payload:
            if type(payload) == str:
                if len(payload) > 0:
                    payload_cell.bits.write_uint(0, 32)
                    payload_cell.bits.write_string(payload)
            elif hasattr(payload, 'refs'):
                payload_cell = payload
            else:
                payload_cell.bits.write_bytes(payload)

        order_header = Contract.create_internal_message_header(
            Address(to_addr), decimal.Decimal(amount))
        order = Contract.create_common_msg_info(
            order_header, state_init, payload_cell)

        return self.add_message_from_cell(order, send_mode)

    def add_message_from_cell(self, message: Cell, mode: int = 3):
        if len(self.messages.refs) >= 4:
            raise Exception('only 4 refs are allowed')
        self.messages.store_uint(mode, 8)
        self.messages.store_ref(begin_cell().store_cell(message).end_cell())
        return message

    def clear_messages(self):
        self.messages = begin_cell()

    def build(self):
        return MultiSigOrder(begin_cell() \
                             .store_uint(self.wallet_id, 32) \
                             .store_uint(self.query_id, 64) \
                             .store_cell(self.messages.end_cell()) \
                             .end_cell())

    @staticmethod
    def generate_query_id(offset):
        return int(time.time() + offset) << 32


class MultiSigWallet(MultiSigWalletContractBase):
    def __init__(self, **kwargs) -> None:
        # https://github.com/ton-blockchain/multisig-contract/
        # https://github.com/ton-core/ton/blob/master/src/multisig/MultisigWallet.ts
        self.code = 'B5EE9C7201022B01000418000114FF00F4A413F4BCF2C80B010201200203020148040504DAF220C7008E8330DB3CE08308D71820F90101D307DB3C22C00013A1537178F40E6FA1F29FDB3C541ABAF910F2A006F40420F90101D31F5118BAF2AAD33F705301F00A01C20801830ABCB1F26853158040F40E6FA120980EA420C20AF2670EDFF823AA1F5340B9F2615423A3534E202321220202CC06070201200C0D02012008090201660A0B0003D1840223F2980BC7A0737D0986D9E52ED9E013C7A21C2125002D00A908B5D244A824C8B5D2A5C0B5007404FC02BA1B04A0004F085BA44C78081BA44C3800740835D2B0C026B500BC02F21633C5B332781C75C8F20073C5BD0032600201200E0F02012014150115BBED96D5034705520DB3C82A020148101102012012130173B11D7420C235C6083E404074C1E08075313B50F614C81E3D039BE87CA7F5C2FFD78C7E443CA82B807D01085BA4D6DC4CB83E405636CF0069006027003DAEDA80E800E800FA02017A0211FC8080FC80DD794FF805E47A0000E78B64C00017AE19573FC100D56676A1EC40020120161702012018190151B7255B678626466A4610081E81CDF431C24D845A4000331A61E62E005AE0261C0B6FEE1C0B77746E10230189B5599B6786ABE06FEDB1C6CA2270081E8F8DF4A411C4A05A400031C38410021AE424BAE064F6451613990039E2CA840090081E886052261C52261C52265C4036625CCD8A30230201201A1B0017B506B5CE104035599DA87B100201201C1D020399381E1F0111AC1A6D9E2F81B60940230015ADF94100CC9576A1EC1840010DA936CF0557C160230015ADDFDC20806AB33B50F6200220DB3C02F265F8005043714313DB3CED54232A000AD3FFD3073004A0DB3C2FAE5320B0F26212B102A425B3531CB9B0258100E1AA23A028BCB0F269820186A0F8010597021110023E3E308E8D11101FDB3C40D778F44310BD05E254165B5473E7561053DCDB3C54710A547ABC242528260020ED44D0D31FD307D307D33FF404F404D1005E018E1A30D20001F2A3D307D3075003D70120F90105F90115BAF2A45003E06C2121D74AAA0222D749BAF2AB70542013000C01C8CBFFCB0704D6DB3CED54F80F70256E5389BEB198106E102D50C75F078F1B30542403504DDB3C5055A046501049103A4B0953B9DB3C5054167FE2F800078325A18E2C268040F4966FA52094305303B9DE208E1638393908D2000197D3073016F007059130E27F080705926C31E2B3E630062A2728290060708E2903D08308D718D307F40430531678F40E6FA1F2A5D70BFF544544F910F2A6AE5220B15203BD14A1236EE66C2232007E5230BE8E205F03F8009322D74A9802D307D402FB0002E83270C8CA0040148040F44302F0078E1771C8CB0014CB0712CB0758CF0158CF1640138040F44301E201208E8A104510344300DB3CED54925F06E22A001CC8CB1FCB07CB07CB3FF400F400C9'
        kwargs["code"] = Cell.one_from_boc(self.code)
        super().__init__(**kwargs)
        if "wallet_id" not in kwargs:
            self.options["wallet_id"] = 698983191 + self.options["wc"]

    def get_owner_id_by_public_key(self, public_key: bytes):
        if public_key not in self.options["public_keys"]:
            raise Exception('public key is not an owner')
        return list(self.options["public_keys"]).index(public_key)

    def create_transfer_message(self, order: MultiSigOrder, private_key: bytes, dummy_signature=False):
        public_key = private_key_to_public_key(private_key)
        owner_id = self.get_owner_id_by_public_key(public_key)
        signing_message = order.to_cell(owner_id)

        return self.create_external_message(
            signing_message, private_key, dummy_signature
        )

    def create_external_message(self, signing_message, private_key, dummy_signature=False):
        signature = bytes(64) if dummy_signature else sign_message(
            bytes(signing_message.bytes_hash()), private_key).signature

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

    def create_init_external_message(self):
        create_state_init = self.create_state_init()
        state_init = create_state_init["state_init"]
        address = create_state_init["address"]
        code = create_state_init["code"]
        data = create_state_init["data"]

        body = Cell()

        header = Contract.create_external_message_header(address)
        external_message = Contract.create_common_msg_info(header, state_init, body)

        return {
            "address": address,
            "message": external_message,
            "body": body,
            "state_init": state_init,
            "code": code,
            "data": data,
        }
