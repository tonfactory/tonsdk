

from ..nft.nft_utils import create_offchain_uri_cell
from ... import Contract
from ....boc import Cell
from ....utils import Address


class JettonMinter(Contract):
    code = 'B5EE9C7241020B010001ED000114FF00F4A413F4BCF2C80B0102016202030202CC040502037A60090A03EFD9910E38048ADF068698180B8D848ADF07D201800E98FE99FF6A2687D007D206A6A18400AA9385D47181A9AA8AAE382F9702480FD207D006A18106840306B90FD001812881A28217804502A906428027D012C678B666664F6AA7041083DEECBEF29385D71811A92E001F1811802600271812F82C207F97840607080093DFC142201B82A1009AA0A01E428027D012C678B00E78B666491646580897A007A00658064907C80383A6465816503E5FFE4E83BC00C646582AC678B28027D0109E5B589666664B8FD80400FE3603FA00FA40F82854120870542013541403C85004FA0258CF1601CF16CCC922C8CB0112F400F400CB00C9F9007074C8CB02CA07CBFFC9D05008C705F2E04A12A1035024C85004FA0258CF16CCCCC9ED5401FA403020D70B01C3008E1F8210D53276DB708010C8CB055003CF1622FA0212CB6ACB1FCB3FC98042FB00915BE200303515C705F2E049FA403059C85004FA0258CF16CCCCC9ED54002E5143C705F2E049D43001C85004FA0258CF16CCCCC9ED54007DADBCF6A2687D007D206A6A183618FC1400B82A1009AA0A01E428027D012C678B00E78B666491646580897A007A00658064FC80383A6465816503E5FFE4E840001FAF16F6A2687D007D206A6A183FAA904051007F09'

    def __init__(self, **kwargs):
        self.code = kwargs.get('code') or self.code
        kwargs['code'] = Cell.one_from_boc(self.code)
        super().__init__(**kwargs)

    def create_data_cell(self) -> Cell:
        cell = Cell()
        cell.bits.write_grams(0)  # total supply
        cell.bits.write_address(self.options['admin_address'])
        cell.refs.append(create_offchain_uri_cell(self.options['jetton_content_uri']))
        cell.refs.append(Cell.one_from_boc(self.options['jetton_wallet_code_hex']))
        return cell

    def create_mint_body(self, destination: Address, jetton_amount: int, amount: int = 50000000, query_id: int = 0) -> Cell:
        body = Cell()
        body.bits.write_uint(21, 32)  # OP mint
        body.bits.write_uint(query_id, 64)
        body.bits.write_address(destination)
        body.bits.write_grams(amount)

        transfer_body = Cell()  # internal transfer
        transfer_body.bits.write_uint(0x178d4519, 32)  # OP transfer
        transfer_body.bits.write_uint(query_id, 64)
        transfer_body.bits.write_grams(jetton_amount)  # jetton amount
        transfer_body.bits.write_address(None)  # from_address
        transfer_body.bits.write_address(None)  # response_address
        transfer_body.bits.write_grams(0)  # forward amount
        transfer_body.bits.write_bit(0)  # forward_payload in this slice, not separate cell

        body.refs.append(transfer_body)
        return body

    def create_change_admin_body(self, new_admin_address: Address, query_id: int = 0) -> Cell:
        body = Cell()
        body.bits.write_uint(3, 32)  # OP
        body.bits.write_uint(query_id, 64)  # query_id
        body.bits.write_address(new_admin_address)
        return body

    def create_edit_content_body(self, jetton_content_uri: str, query_id: int = 0) -> Cell:
        body = Cell()
        body.bits.write_uint(4, 32)  # OP
        body.bits.write_uint(query_id, 64)  # query_id
        body.refs.append(create_offchain_uri_cell(jetton_content_uri))
        return body

