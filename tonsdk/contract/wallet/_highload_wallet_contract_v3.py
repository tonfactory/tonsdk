from functools import reduce
from typing import Any, Dict, List, Union
from .. import Contract
from ._wallet_contract import WalletContract, SendModeEnum
from ...boc import Cell, begin_cell
from ...utils import sign_message, HighloadQueryId, check_timeout


class OPEnum:
    InternalTransfer = 0xae42e5a4
    OutActionSendMsg = 0x0ec3c86d


class HighloadWalletV3ContractBase(WalletContract):

    def create_data_cell(self) -> Cell:
        """
        Creates a Cell object with specific configuration.
        """
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
            message_to_send: Cell,
    ) -> Cell:
        """
        Creates and initializes a Cell object for a signing message.
        """
        cell = Cell()
        cell.bits.write_uint(self.options["wallet_id"], 32)
        cell.refs.append(message_to_send)
        cell.bits.write_uint(send_mode, 8)
        cell.bits.write_uint(query_id.query_id, 23)
        cell.bits.write_uint(created_at, 64)
        cell.bits.write_uint(self.options["timeout"], 22)
        return cell


class HighloadWalletV3Contract(HighloadWalletV3ContractBase):
    def __init__(self, **kwargs):
        # https://github.com/ton-blockchain/highload-wallet-contract-v3
        self.code = "b5ee9c7241021001000228000114ff00f4a413f4bcf2c80b01020120020d02014803040078d020d74bc00101c060b0915be101d0d3030171b0915be0fa4030f828c705b39130e0d31f018210ae42e5a4ba9d8040d721d74cf82a01ed55fb04e030020120050a02027306070011adce76a2686b85ffc00201200809001aabb6ed44d0810122d721d70b3f0018aa3bed44d08307d721d70b1f0201200b0c001bb9a6eed44d0810162d721d70b15800e5b8bf2eda2edfb21ab09028409b0ed44d0810120d721f404f404d33fd315d1058e1bf82325a15210b99f326df82305aa0015a112b992306dde923033e2923033e25230800df40f6fa19ed021d721d70a00955f037fdb31e09130e259800df40f6fa19cd001d721d70a00937fdb31e0915be270801f6f2d48308d718d121f900ed44d0d3ffd31ff404f404d33fd315d1f82321a15220b98e12336df82324aa00a112b9926d32de58f82301de541675f910f2a106d0d31fd4d307d30cd309d33fd315d15168baf2a2515abaf2a6f8232aa15250bcf2a304f823bbf2a35304800df40f6fa199d024d721d70a00f2649130e20e01fe5309800df40f6fa18e13d05004d718d20001f264c858cf16cf8301cf168e1030c824cf40cf8384095005a1a514cf40e2f800c94039800df41704c8cbff13cb1ff40012f40012cb3f12cb15c9ed54f80f21d0d30001f265d3020171b0925f03e0fa4001d70b01c000f2a5fa4031fa0031f401fa0031fa00318060d721d300010f0020f265d2000193d431d19130e272b1fb00b585bf03"  # noqa:E501
        kwargs["code"] = Cell.one_from_boc(self.code)
        super().__init__(**kwargs)
        if kwargs.get("wc"):
            raise ValueError("only basechain (wc = 0) supported")
        kwargs["wc"] = 0
        super().__init__(**kwargs)
        if not self.options.get("wallet_id", None):
            self.options["wallet_id"] = 0x10AD

    def create_external_message(
            self,
            signing_message: Cell,
            need_deploy: bool,
            dummy_signature=False
    ) -> Dict[str, Any]:
        """
        Creates an external message with the specified signing message.

        If `dummy_signature` is True, a zeroed 64-byte signature is used.
        Otherwise, the signature is generated using the provided signing message and private key.

        If `need_deploy` is True, the state initialization is included in the message.
        """
        signature = bytes(64) if dummy_signature else sign_message(
            bytes(signing_message.bytes_hash()), self.options['private_key']).signature

        body = Cell()
        body.bits.write_bytes(signature)
        body.refs.append(signing_message)

        state_init = None
        code = None
        data = None

        if need_deploy:
            deploy = self.create_state_init()
            state_init = deploy["state_init"]
            code = deploy["code"]
            data = deploy["data"]

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

    @classmethod
    def store_out_msgs(cls, out_msgs: List[Cell], send_mode: int) -> Cell:
        """
        Uses a reducer function to iterate through the list of out_msgs,
        storing each out_msg in a cell and chaining them together.
        """
        def store_out_msg(out_msg: Cell) -> Cell:
            message_cell = begin_cell().store_cell(out_msg).end_cell()
            return begin_cell().store_uint(OPEnum.OutActionSendMsg, 32).store_uint8(send_mode).store_ref(
                message_cell).end_cell()

        def reducer(cell: Cell, out_msg: Cell) -> Cell:
            return begin_cell().store_ref(cell).store_cell(store_out_msg(out_msg)).end_cell()

        initial_cell = begin_cell().end_cell()
        cell = reduce(reducer, out_msgs, initial_cell)
        return cell

    def create_internal_transfer_body(self,  out_msgs: List[Cell], query_id: HighloadQueryId, send_mode: int) -> Cell:
        """
        Creates the body(payload) of out_msgs for an internal transfer message.
        """
        actions = self.store_out_msgs(out_msgs, send_mode)
        return begin_cell().store_uint(OPEnum.InternalTransfer, 32).store_uint(query_id.query_id, 64).store_ref(
            actions).end_cell()

    @classmethod
    def create_out_msg(
            cls,
            address: str,
            amount: int,
            payload: Union[str, bytes, Cell, None] = None,
            state_init: Union[Cell, None] = None,
    ) -> Cell:
        payload_cell = Cell()
        if payload:
            if isinstance(payload, Cell):
                payload_cell = payload
            elif isinstance(payload, str):
                if len(payload) > 0:
                    payload_cell.bits.write_uint(0, 32)
                    payload_cell.bits.write_string(payload)
            else:
                payload_cell.bits.write_bytes(payload)

        order_header = cls.create_internal_message_header(address, amount)
        order = cls.create_common_msg_info(
            order_header, state_init, payload_cell
        )
        return order

    def create_transfer_message(
            self,
            address: str,
            amount: int,
            query_id: HighloadQueryId,
            create_at: int,
            payload: str = "",
            send_mode: int = SendModeEnum.ignore_errors | SendModeEnum.pay_gas_separately,
            need_deploy: bool = False,
            dummy_signature: bool = False
    ) -> Dict[str, Any]:
        """
        Creates a single transfer message.
        Args:
            address (str): The recipient address of the transfer.
            amount (int): The amount to be transferred.
            query_id (HighloadQueryId): The query ID for the transfer.
            create_at (int): The creation time of the message.
            payload (str, optional): Optional payload to include in the message. Defaults to "".
            send_mode (int, optional): The mode in which the message should be sent. Defaults to SendModeEnum.ignore_errors | SendModeEnum.pay_gas_separately.
            need_deploy (bool, optional): Flag indicating whether deployment state initialization is needed. Defaults to False.
            dummy_signature (bool, optional): Flag to use a dummy signature. Defaults to False.
        """
        check_timeout(self.options["timeout"])

        if create_at is None or create_at < 0:
            raise ValueError("create_at must be number >= 0")
        message_to_send = self.create_out_msg(address, amount, payload)
        signing_message = self.create_signing_message(query_id, create_at, send_mode, message_to_send)
        return self.create_external_message(signing_message, need_deploy, dummy_signature)

    def create_batch_transfer_message(
            self,
            recipients_list: List[Dict],
            query_id: HighloadQueryId,
            create_at: int,
            send_mode: int = SendModeEnum.ignore_errors | SendModeEnum.pay_gas_separately,
            need_deploy: bool = False,
            dummy_signature: bool = False
    ) -> Dict[str, Any]:
        """
        Constructs a batch-transfer message that includes multiple recipients, each with their respective
        addresses, amounts, and optional payloads.
        Args:
            recipients_list (List[Dict]): The list of recipients with their details.
                Each recipient should have the following keys:
                - "address" (str): The recipient address.
                - "amount" (int): The amount to be transferred.
                - "payload" (Union[str, bytes, Cell], optional): Optional payload to include in the message.
            query_id (HighloadQueryId): The query ID for the transfer.
            create_at (int): The creation time of the message.
            send_mode (int, optional): The mode in which the message should be sent.
            need_deploy (bool, optional): Flag indicating whether deployment state initialization is needed.
            dummy_signature (bool, optional): Flag to use a dummy signature. Defaults to False.
        """

        check_timeout(self.options["timeout"])

        if create_at is None or create_at < 0:
            raise ValueError("create_at must be number >= 0")

        grams = 0
        out_msgs = []
        for i, recipient in enumerate(recipients_list):
            out_msg = self.create_out_msg(
                address=recipient['address'],
                amount=recipient['amount'],
                payload=recipient.get('payload'))
            out_msgs.append(out_msg)
            grams += recipient['amount']

        body = self.create_internal_transfer_body(out_msgs, query_id, send_mode)
        msg_to_send = self.create_out_msg(address=self.address, amount=grams, payload=body)
        signing_message = self.create_signing_message(query_id, create_at, send_mode, msg_to_send)
        return self.create_external_message(signing_message, need_deploy, dummy_signature)

