from ... import Contract
from ....boc import Cell
from ....utils import Address


class NFTItem(Contract):
    code = 'B5EE9C7241020D010001D0000114FF00F4A413F4BCF2C80B0102016202030202CE04050009A11F9FE00502012006070201200B0C02D70C8871C02497C0F83434C0C05C6C2497C0F83E903E900C7E800C5C75C87E800C7E800C3C00812CE3850C1B088D148CB1C17CB865407E90350C0408FC00F801B4C7F4CFE08417F30F45148C2EA3A1CC840DD78C9004F80C0D0D0D4D60840BF2C9A884AEB8C097C12103FCBC20080900113E910C1C2EBCB8536001F65135C705F2E191FA4021F001FA40D20031FA00820AFAF0801BA121945315A0A1DE22D70B01C300209206A19136E220C2FFF2E192218E3E821005138D91C85009CF16500BCF16712449145446A0708010C8CB055007CF165005FA0215CB6A12CB1FCB3F226EB39458CF17019132E201C901FB00104794102A375BE20A00727082108B77173505C8CBFF5004CF1610248040708010C8CB055007CF165005FA0215CB6A12CB1FCB3F226EB39458CF17019132E201C901FB000082028E3526F0018210D53276DB103744006D71708010C8CB055007CF165005FA0215CB6A12CB1FCB3F226EB39458CF17019132E201C901FB0093303234E25502F003003B3B513434CFFE900835D27080269FC07E90350C04090408F80C1C165B5B60001D00F232CFD633C58073C5B3327B5520BF75041B'

    def __init__(self, **kwargs):
        self.code = kwargs.get('code') or self.code
        kwargs["code"] = Cell.one_from_boc(self.code)
        super().__init__(**kwargs)

    def create_data_cell(self) -> Cell:
        cell = Cell()
        cell.bits.write_uint(self.options.get('index', 0), 64)
        cell.bits.write_address(self.options.get('collection_address', None))
        if 'owner_address' in self.options:
            cell.bits.write_address(self.options['owner_address'])
        if 'content' in self.options:
            cell.refs.append(self.options['content'])
        return cell

    def create_transfer_body(
            self, new_owner_address: Address, response_address: Address = None,
            forward_amount: int = 0, forward_payload: bytes = None, query_id: int = 0
    ) -> Cell:
        cell = Cell()
        cell.bits.write_uint(0x5fcc3d14, 32)  # transfer OP
        cell.bits.write_uint(query_id, 64)
        cell.bits.write_address(new_owner_address)
        cell.bits.write_address(response_address or new_owner_address)
        cell.bits.write_bit(False)  # null custom_payload
        cell.bits.write_grams(forward_amount)
        cell.bits.write_bit(False)  # forward_payload in this slice, not separate cell
        if forward_payload:
            cell.bits.write_bytes(forward_payload)

        return cell

    def create_get_static_data_body(self, query_id: int = 0) -> Cell:
        cell = Cell()
        cell.bits.write_uint(0x2fcb26a2, 32)
        cell.bits.write_uint(query_id, 64)
        return cell



