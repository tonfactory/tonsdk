import codecs
import json
from typing import Dict, Optional


class ToncenterWrongResult(Exception):
    def __init__(self, code):
        self.code = code


class ToncenterClient:
    def __init__(self, base_url: str, api_key: Optional[str]):
        self.base_url = base_url
        self.api_key = api_key

    def raw_send_message(self, serialized_boc):
        serialized_boc = codecs.decode(codecs.encode(
            serialized_boc, "base64"), 'utf-8').replace("\n", '')

        return {
            "func": self.__post_request,
            "args": [self.base_url + "sendBoc"],
            "kwargs": {"data": {"boc": serialized_boc}}
        }

    def raw_run_method(self, address, method, stack_data, output_layout=None):
        return {
            "func": self.__post_request,
            "args": [self.base_url + "runGetMethod"],
            "kwargs": {"data": {"address": address, "method": method, "stack": stack_data}}
        }

    def raw_get_account_state(self, prepared_address: str):
        return {
            "func": self.__jsonrpc_request,
            "args": ["getAddressInformation"],
            "kwargs": {"params": {"address": prepared_address}}
        }

    async def __post_request(self, session, url, data):
        async with session.post(url, data=json.dumps(data), headers=self.__headers()) as resp:
            return await self.__parse_response(resp)

    async def __jsonrpc_request(self, session, method: str, params: Dict, id: str = "1", jsonrpc: str = "2.0"):
        payload = {
            "id": id,
            "jsonrpc": jsonrpc,
            "method": method,
            "params": params,
        }

        async with session.post(self.base_url + "jsonRPC", json=payload, headers=self.__headers()) as resp:
            return await self.__parse_response(resp)

    def __headers(self):
        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json',
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        return headers

    async def __parse_response(self, resp):
        try:
            resp = await resp.json()
        except Exception:  # TODO: catch correct exceptions
            raise ToncenterWrongResult(resp.status)

        if not resp['ok']:
            raise ToncenterWrongResult(resp['code'])

        return resp['result']
