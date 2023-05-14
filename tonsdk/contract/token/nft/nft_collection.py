from math import floor
from typing import List, Tuple

from .nft_utils import create_offchain_uri_cell, serialize_uri
from ... import Contract
from ....boc import Cell, DictBuilder
from ....utils import Address


class NFTCollection(Contract):
    code = 'B5EE9C724102140100021F000114FF00F4A413F4BCF2C80B0102016202030202CD04050201200E0F04E7D10638048ADF000E8698180B8D848ADF07D201800E98FE99FF6A2687D20699FEA6A6A184108349E9CA829405D47141BAF8280E8410854658056B84008646582A802E78B127D010A65B509E58FE59F80E78B64C0207D80701B28B9E382F970C892E000F18112E001718112E001F181181981E0024060708090201200A0B00603502D33F5313BBF2E1925313BA01FA00D43028103459F0068E1201A44343C85005CF1613CB3FCCCCCCC9ED54925F05E200A6357003D4308E378040F4966FA5208E2906A4208100FABE93F2C18FDE81019321A05325BBF2F402FA00D43022544B30F00623BA9302A402DE04926C21E2B3E6303250444313C85005CF1613CB3FCCCCCCC9ED54002C323401FA40304144C85005CF1613CB3FCCCCCCC9ED54003C8E15D4D43010344130C85005CF1613CB3FCCCCCCC9ED54E05F04840FF2F00201200C0D003D45AF0047021F005778018C8CB0558CF165004FA0213CB6B12CCCCC971FB008002D007232CFFE0A33C5B25C083232C044FD003D0032C03260001B3E401D3232C084B281F2FFF2742002012010110025BC82DF6A2687D20699FEA6A6A182DE86A182C40043B8B5D31ED44D0FA40D33FD4D4D43010245F04D0D431D430D071C8CB0701CF16CCC980201201213002FB5DAFDA89A1F481A67FA9A9A860D883A1A61FA61FF480610002DB4F47DA89A1F481A67FA9A9A86028BE09E008E003E00B01A500C6E'

    def __init__(self, **kwargs):
        self.code = kwargs.get('code') or self.code
        kwargs["code"] = Cell.one_from_boc(self.code)
        super().__init__(**kwargs)
        self.options['royalty_base'] = self.options.get('royalty_base', 1000)
        self.options['royalty_factor'] = floor(self.options.get('royalty', 0) * self.options['royalty_base'])


    def create_content_cell(self, params) -> Cell:
        collection_content_cell = create_offchain_uri_cell(params['collection_content_uri'])
        common_content_cell = Cell()
        common_content_cell.bits.write_bytes(serialize_uri(params['nft_item_content_base_uri']))
        content_cell = Cell()
        content_cell.refs.append(collection_content_cell)
        content_cell.refs.append(common_content_cell)
        return content_cell


    def create_royalty_cell(self, params) -> Cell:
        royalty_cell = Cell()
        royalty_cell.bits.write_uint(params['royalty_factor'], 16)
        royalty_cell.bits.write_uint(params['royalty_base'], 16)
        royalty_cell.bits.write_address(params['royalty_address'])
        return royalty_cell


    def create_data_cell(self) -> Cell:
        cell = Cell()
        cell.bits.write_address(self.options['owner_address'])
        cell.bits.write_uint(0, 64)  # next_item_index
        cell.refs.append(self.create_content_cell(self.options))
        cell.refs.append(Cell.one_from_boc(self.options['nft_item_code_hex']))
        cell.refs.append(self.create_royalty_cell(self.options))
        return cell

    def create_mint_body(
            self, item_index: int, new_owner_address: Address,
            item_content_uri: str, amount: int = 50000000, query_id: int = 0
    ) -> Cell:
        body = Cell()
        body.bits.write_uint(1, 32)
        body.bits.write_uint(query_id, 64)
        body.bits.write_uint(item_index, 64)
        body.bits.write_grams(amount)
        content_cell = Cell()
        content_cell.bits.write_address(new_owner_address)
        uri_content = Cell()
        uri_content.bits.write_bytes(serialize_uri(item_content_uri))
        content_cell.refs.append(uri_content)
        body.refs.append(content_cell)
        return body
    
    def create_batch_mint_body(
            self, from_item_index: int,
            contents_and_owners: List[Tuple[str, Address]],
            amount_per_one: int = 50000000, query_id: int = 0
    ) -> Cell:
        body = Cell()
        body.bits.write_uint(2, 32)
        body.bits.write_uint(query_id, 64)
        deploy_list = DictBuilder(64)
        for i, (item_content_uri, new_owner_address) in \
                enumerate(contents_and_owners):
            item = Cell()
            item.bits.write_grams(amount_per_one)
            content = Cell()
            content.bits.write_address(new_owner_address)
            uri_content = Cell()
            uri_content.bits.write_bytes(serialize_uri(item_content_uri))
            content.refs.append(uri_content)
            item.refs.append(content)
            deploy_list.store_cell(i + from_item_index, item)
        body.refs.append(deploy_list.end_dict())
        return body

    def create_get_royalty_params_body(self, query_id: int = 0) -> Cell:
        body = Cell()
        body.bits.write_uint(0x693d3950, 32)  # OP
        body.bits.write_uint(query_id, 64)  # query_id
        return body

    def create_change_owner_body(self, new_owner_address: Address, query_id: int = 0) -> Cell:
        body = Cell()
        body.bits.write_uint(3, 32)  # OP
        body.bits.write_uint(query_id, 64)  # query_id
        body.bits.write_address(new_owner_address)
        return body

    def create_edit_content_body(self, params) -> Cell:
        if params['royalty'] > 1:
            raise Exception('royalty must be less than 1')

        body = Cell()
        body.bits.write_uint(4, 32)  # OP
        body.bits.write_uint(params.get('query_id', 0), 64)  # query_id
        body.refs.append(self.create_content_cell(params))
        body.refs.append(self.create_royalty_cell(params))
        return body


