import codecs
import json
import random
import time

from tvm_valuetypes import render_tvm_stack

from ._wrapper import SyncTonLibWrapper
from .._utils import CtypesStdoutCapture, TonLibWrongResult


class SyncTonlibClient:
    def __init__(self, config, keystore, cdll_path=None, verbosity=0):
        self.ton_config = config
        self.keystore = keystore
        self.cdll_path = cdll_path
        self.verbosity = verbosity

    def init(self):
        wrapper = SyncTonLibWrapper(self.cdll_path)
        self.tonlib_wrapper = wrapper

        one_liteserver = self.ton_config['liteservers'][random.randrange(0, len(self.ton_config['liteservers']))]
        self.ton_config['liteservers'] = [one_liteserver]

        with CtypesStdoutCapture():
            change_verbosity_level_query = {
                '@type': 'setLogVerbosityLevel',
                'new_verbosity_level': self.verbosity
            }

            keystore_obj = {
                '@type': 'keyStoreTypeDirectory',
                'directory': self.keystore
            }

            init_tonlib_query = {
                '@type': 'init',
                'options': {
                    '@type': 'options',
                    'config': {
                        '@type': 'config',
                        'config': json.dumps(self.ton_config),
                        'use_callbacks_for_network': False,
                        'blockchain_name': '',
                        'ignore_cache': False
                    },
                    'keystore_type': keystore_obj
                }
            }

            queries_order = {}
            for i, query in enumerate([change_verbosity_level_query, init_tonlib_query]):
                query_idx = self.__execute(query)
                queries_order[query_idx] = i

            results = self.read_results(queries_order)

        return results[1]

    def read_result(self, query_idx, read_timeout=None):
        return self.read_results({query_idx: 0}, read_timeout)[0]

    def read_results(self, queries_order, read_timeout=None):
        read_timeout = read_timeout if read_timeout else time.time() + 5
        results = [None] * len(queries_order)
        while queries_order:
            if time.time() >= read_timeout:
                raise TimeoutError("Tonlib queries took too long!")

            result = None
            try:
                result = self.tonlib_wrapper.receive()
            except Exception as e:  # FIXME: handle exceptions (TimeOutError?)
                raise

            if result and isinstance(result, dict) and ("@extra" in result) and (result["@extra"] in queries_order):
                query_order = queries_order[result["@extra"]]
                results[query_order] = result
                queries_order.pop(result["@extra"])

        return results

    def raw_get_account_state(self, prepared_address: str):
        request = {
            '@type': 'raw.getAccountState',
            'account_address': {
                'account_address': prepared_address
            }
        }

        return self.__execute(request)

    def raw_send_message(self, serialized_boc):
        serialized_boc = codecs.decode(codecs.encode(
            serialized_boc, "base64"), 'utf-8').replace("\n", '')
        request = {
            '@type': 'raw.sendMessage',
            'body': serialized_boc
        }

        return self.__execute(request)

    def raw_run_method(self, address, method, stack_data, output_layout=None):
        stack_data = render_tvm_stack(stack_data)
        if isinstance(method, int):
            method = {'@type': 'smc.methodIdNumber', 'number': method}
        else:
            method = {'@type': 'smc.methodIdName', 'name': str(method)}
        contract_id = self._load_contract(address)
        request = {
            '@type': 'smc.runGetMethod',
            'id': contract_id,
            'method': method,
            'stack': stack_data
        }

        return self.__execute(request)

    def _load_contract(self, address):
        request = {
            '@type': 'smc.load',
            'account_address': {
                'account_address': address
            }
        }
        result = self.read_result(self.__execute(request))
        if result.get('@type', 'error') == 'error':
            raise TonLibWrongResult("smc.load failed", result)

        return result["id"]

    def __execute(self, query) -> str:
        extra_id = "%s:%s" % (time.time(), random.random())
        query["@extra"] = extra_id

        self.tonlib_wrapper.send(query)

        return extra_id
