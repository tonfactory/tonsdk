from ._wallet_contract import WalletContract
from ...boc import Cell
import time


class WalletV5ContractR1(WalletContract):
    def __init__(self, **kwargs):
        self.code = "b5ee9c7241021401000281000114ff00f4a413f4bcf2c80b01020120020d020148030402dcd020d749c120915b8f6320d70b1f2082106578746ebd21821073696e74bdb0925f03e082106578746eba8eb48020d72101d074d721fa4030fa44f828fa443058bd915be0ed44d0810141d721f4058307f40e6fa1319130e18040d721707fdb3ce03120d749810280b99130e070e2100f020120050c020120060902016e07080019adce76a2684020eb90eb85ffc00019af1df6a2684010eb90eb858fc00201480a0b0017b325fb51341c75c875c2c7e00011b262fb513435c280200019be5f0f6a2684080a0eb90fa02c0102f20e011e20d70b1f82107369676ebaf2e08a7f0f01e68ef0eda2edfb218308d722028308d723208020d721d31fd31fd31fed44d0d200d31f20d31fd3ffd70a000af90140ccf9109a28945f0adb31e1f2c087df02b35007b0f2d0845125baf2e0855036baf2e086f823bbf2d0882292f800de01a47fc8ca00cb1f01cf16c9ed542092f80fde70db3cd81003f6eda2edfb02f404216e926c218e4c0221d73930709421c700b38e2d01d72820761e436c20d749c008f2e09320d74ac002f2e09320d71d06c712c2005230b0f2d089d74cd7393001a4e86c128407bbf2e093d74ac000f2e093ed55e2d20001c000915be0ebd72c08142091709601d72c081c12e25210b1e30f20d74a111213009601fa4001fa44f828fa443058baf2e091ed44d0810141d718f405049d7fc8ca0040048307f453f2e08b8e14038307f45bf2e08c22d70a00216e01b3b0f2d090e2c85003cf1612f400c9ed54007230d72c08248e2d21f2e092d200ed44d0d2005113baf2d08f54503091319c01810140d721d70a00f2e08ee2c8ca0058cf16c9ed5493f2c08de20010935bdb31e1d74cd0b4d6c35e"
        kwargs["code"] = Cell.one_from_boc(self.code)
        super().__init__(**kwargs)
        self.workchain = kwargs.get("wc", 0)
        self.network_global_id = kwargs.get("network_global_id", -239)  # MainnetGlobalID
        self.wallet_id = self._gen_wallet_id()
        self.is_signature_allowed = True

    def _gen_context_id(self):
        context_cell = Cell()
        context_cell.bits.write_uint(1, 1)
        context_cell.bits.write_int(self.workchain, 8)
        context_cell.bits.write_uint(0, 8)
        context_cell.bits.write_uint(0, 15)
        return context_cell.bits.get_top_upped_array()

    def _gen_wallet_id(self):
        context_id = int.from_bytes(self._gen_context_id(), byteorder='big')
        wallet_id = context_id ^ (self.network_global_id & 0xFFFFFFFF)
        return wallet_id & 0xFFFFFFFF  # Ensure it's a 32-bit unsigned integer

    def create_data_cell(self):
        cell = Cell()
        cell.bits.write_uint(1 if self.is_signature_allowed else 0, 1)
        cell.bits.write_uint(0, 32)  # seqno
        cell.bits.write_uint(self.wallet_id, 32)
        cell.bits.write_bytes(self.options["public_key"])
        cell.bits.write_uint(0, 1)  # Empty dict for extensions
        return cell

    def create_signing_message(self, seqno=None, messages=None):
        seqno = seqno or 0
        wallet_id = self.wallet_id
        valid_until = int(time.time()) + self.options.get("timeout", 60)

        message = Cell()
        message.bits.write_uint(0x7369676e, 32)  # 'sign' magic prefix
        message.bits.write_uint(wallet_id, 32)
        message.bits.write_uint(valid_until, 32)
        message.bits.write_uint(seqno, 32)

        if messages:
            actions = self._pack_actions(messages)
            message.refs.append(actions)

        return message

    def _pack_actions(self, messages):
        actions = Cell()
        actions.bits.write_uint(1, 1)  # Store 1 at the beginning

        prev_cell = None
        for msg in reversed(messages):
            cell = Cell()
            if prev_cell:
                cell.refs.append(prev_cell)

            out_msg = self._create_outbound_message(msg)

            cell.bits.write_uint(0x0ec3c86d, 32)  # action_send_msg prefix
            cell.bits.write_uint(msg.get("mode", 3), 8)  # mode
            cell.refs.append(out_msg)

            prev_cell = cell

        if prev_cell:
            actions.refs.append(prev_cell)
        actions.bits.write_uint(0, 1)  # Store 0 at the end

        return actions

    def _create_outbound_message(self, msg):
        # This method needs to be implemented based on your specific message structure
        # It should create a Cell object representing the outbound message
        pass

    def get_address(self):
        state_init = self.create_state_init()
        return state_init["address"]
