from .. import Contract
from ._wallet_contract import WalletContract
from ...boc import Cell
from ...utils import sign_message, HighloadQueryId, check_timeout
from ...crypto import private_key_to_public_key


class HighloadWalletV3Contract(WalletContract):
    def __init__(self, **kwargs):
        # https://github.com/ton-blockchain/highload-wallet-contract-v3
        self.code = "b5ee9c7241021001000228000114ff00f4a413f4bcf2c80b01020120020d02014803040078d020d74bc00101c060b0915be101d0d3030171b0915be0fa4030f828c705b39130e0d31f018210ae42e5a4ba9d8040d721d74cf82a01ed55fb04e030020120050a02027306070011adce76a2686b85ffc00201200809001aabb6ed44d0810122d721d70b3f0018aa3bed44d08307d721d70b1f0201200b0c001bb9a6eed44d0810162d721d70b15800e5b8bf2eda2edfb21ab09028409b0ed44d0810120d721f404f404d33fd315d1058e1bf82325a15210b99f326df82305aa0015a112b992306dde923033e2923033e25230800df40f6fa19ed021d721d70a00955f037fdb31e09130e259800df40f6fa19cd001d721d70a00937fdb31e0915be270801f6f2d48308d718d121f900ed44d0d3ffd31ff404f404d33fd315d1f82321a15220b98e12336df82324aa00a112b9926d32de58f82301de541675f910f2a106d0d31fd4d307d30cd309d33fd315d15168baf2a2515abaf2a6f8232aa15250bcf2a304f823bbf2a35304800df40f6fa199d024d721d70a00f2649130e20e01fe5309800df40f6fa18e13d05004d718d20001f264c858cf16cf8301cf168e1030c824cf40cf8384095005a1a514cf40e2f800c94039800df41704c8cbff13cb1ff40012f40012cb3f12cb15c9ed54f80f21d0d30001f265d3020171b0925f03e0fa4001d70b01c000f2a5fa4031fa0031f401fa0031fa00318060d721d300010f0020f265d2000193d431d19130e272b1fb00b585bf03"  # noqa:E501
        kwargs["code"] = Cell.one_from_boc(self.code)

        super().__init__(**kwargs)
        if kwargs.get("wc"):
            raise ValueError("only basechain (wc = 0) supported")
        kwargs["wc"] = 0
        check_timeout(kwargs.get("timeout"))
        super().__init__(**kwargs)
        if not self.options["wallet_id"]:
            self.options["wallet_id"] = 0x10AD

    def create_data_cell(self):
        check_timeout(self.options["timeout"])

        cell = Cell()
        cell.bits.write_bytes(self.options["public_key"])
        cell.bits.write_uint(self.options["wallet_id"], 32)
        cell.bits.write_uint(0, 1)  # empty old_queries
        cell.bits.write_uint(0, 1)  # empty queries
        cell.bits.write_uint(0, 64)  # last_clean_time
        cell.bits.write_uint(self.options["timeout"], 22)
        return cell

    def create_signing_message(
        self,
        query_id: HighloadQueryId,
        created_at: int,
        send_mode: int,
        message_to_send,
    ):
        check_timeout(self.options["timeout"])

        cell = Cell()
        cell.bits.write_uint(self.options["wallet_id"], 32)
        cell.refs.append(message_to_send)
        cell.bits.write_uint(send_mode, 8)
        cell.bits.write_uint(query_id.shift, 13)
        cell.bits.write_uint(query_id.bit_number, 10)
        cell.bits.write_uint(created_at, 64)
        cell.bits.write_uint(self.options["timeout"], 22)
        return cell

    def create_transfer_message(
        self,
        address: str,
        amount: int,
        query_id: HighloadQueryId,
        create_at: int,
        payload: str = "",
        send_mode: int = 3,
        need_deploy: bool = False,
    ):
        if create_at is None or create_at < 0:
            raise ValueError("create_at must be number >= 0")
        message_to_send = self.create_out_msg(address, amount, payload)
        signing_message = self.create_signing_message(
            query_id, create_at, send_mode, message_to_send
        )

        return self.create_external_message(
            signing_message, need_deploy
        )

    def create_external_message(
        self,
        signing_message: Cell,
        need_deploy: bool,
    ):
        signature = sign_message(bytes(signing_message.bytes_hash()), self.options['private_key']).signature

        body = Cell()
        body.bits.write_bytes(signature)
        body.refs.append(signing_message)

        state_init = None
        code = None
        data = None

        if need_deploy:
            if not self.options.get("public_key"):
                public_key = private_key_to_public_key(secret_key)
                self.options["public_key"] = public_key
            deploy = self.create_state_init()
            state_init = deploy.state_init
            code = deploy.code
            data = deploy.data

        header = self.create_external_message_header(self.address)
        result_message = Contract.create_common_msg_info(
            header, state_init, body
        )

        return {
            "address": self.address,
            "message": result_message,
            "body": body,
            "signature": signature,
            "signing_message": signing_message,
            "state_init": state_init,
            "code": code,
            "data": data,
        }