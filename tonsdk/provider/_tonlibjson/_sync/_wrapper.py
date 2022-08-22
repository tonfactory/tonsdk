import json
from ctypes import CDLL, c_void_p, c_char_p, c_double

from .._utils import get_tonlib_cdll_path


class SyncTonLibWrapper:
    def __init__(self, cdll_path=None):
        cdll_path = get_tonlib_cdll_path() if not cdll_path else cdll_path
        tonlib = CDLL(cdll_path)

        tonlib_json_client_create = tonlib.tonlib_client_json_create
        tonlib_json_client_create.restype = c_void_p
        tonlib_json_client_create.argtypes = []

        tonlib_json_client_destroy = tonlib.tonlib_client_json_destroy
        tonlib_json_client_destroy.restype = None
        tonlib_json_client_destroy.argtypes = [c_void_p]
        self.__tonlib_json_client_destroy = tonlib_json_client_destroy

        tonlib_json_client_receive = tonlib.tonlib_client_json_receive
        tonlib_json_client_receive.restype = c_char_p
        tonlib_json_client_receive.argtypes = [c_void_p, c_double]
        self.__tonlib_json_client_receive = tonlib_json_client_receive

        tonlib_json_client_send = tonlib.tonlib_client_json_send
        tonlib_json_client_send.restype = None
        tonlib_json_client_send.argtypes = [c_void_p, c_char_p]
        self.__tonlib_json_client_send = tonlib_json_client_send

        try:
            self._client = tonlib_json_client_create()
        except Exception:  # FIXME
            raise

    def __del__(self):
        try:
            if hasattr(self, '__tonlib_json_client_destroy'):
                self.__tonlib_json_client_destroy(self._client)
        except Exception:  # FIXME
            raise

    def send(self, query):
        query = json.dumps(query).encode('utf-8')

        try:
            self.__tonlib_json_client_send(self._client, query)
        except Exception:  # FIXME
            raise

    def receive(self, timeout=4):
        result = None
        try:
            result = self.__tonlib_json_client_receive(
                self._client, timeout)
        except Exception:  # FIXME
            raise

        if result:
            result = json.loads(result.decode('utf-8'))
        return result
