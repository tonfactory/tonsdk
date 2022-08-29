

from ... import Contract
from ....boc import Cell


class NFTSale(Contract):
    code = 'B5EE9C7241020A010001B4000114FF00F4A413F4BCF2C80B01020120020302014804050004F2300202CD0607002FA03859DA89A1F481F481F481F401A861A1F401F481F4006101F7D00E8698180B8D8492F82707D201876A2687D207D207D207D006A18116BA4E10159C71D991B1B2990E382C92F837028916382F970FA01698FC1080289C6C8895D7970FAE99F98FD2018201A642802E78B2801E78B00E78B00FD016664F6AA701363804C9B081B2299823878027003698FE99F9810E000C92F857010C0801F5D41081DCD650029285029185F7970E101E87D007D207D0018384008646582A804E78B28B9D090D0A85AD08A500AFD010AE5B564B8FD80384008646582AC678B2803FD010B65B564B8FD80384008646582A802E78B00FD0109E5B564B8FD80381041082FE61E8A10C00C646582A802E78B117D010A65B509E58F8A40900C8C0029A3110471036454012F004E032363704C0038E4782103B9ACA0015BEF2E1C95312C70559C705B1F2E1CA702082105FCC3D14218010C8CB055006CF1622FA0215CB6A14CB1F14CB3F21CF1601CF16CA0021FA02CA00C98100A0FB00E05F06840FF2F0002ACB3F22CF1658CF16CA0021FA02CA00C98100A0FB00AECABAD1'

    def __init__(self, **kwargs):
        self.code = kwargs.get('code') or self.code
        kwargs["code"] = Cell.one_from_boc(self.code)
        super().__init__(**kwargs)

    def create_data_cell(self) -> Cell:
        cell = Cell()
        cell.bits.write_address(self.options['marketplace_address'])
        cell.bits.write_address(self.options['nft_address'])
        cell.bits.write_address(None)  # nft_owner_address
        cell.bits.write_grams(self.options['full_price'])

        fees_cell = Cell()
        fees_cell.bits.write_coins(self.options['marketplace_fee'])
        fees_cell.bits.write_address(self.options['royalty_address'])
        fees_cell.bits.write_coins(self.options['royalty_amount'])
        cell.refs.append(fees_cell)
        return cell

    def create_cancel_body(self, query_id: int = 0) -> Cell:
        cell = Cell()
        cell.bits.write_uint(3, 32)  # cancel OP-code
        cell.bits.write_uint(query_id, 64)
        return cell


