import asyncio
import functools
import json
import logging
import random
import time
import traceback
from ctypes import CDLL, c_void_p, c_char_p, c_double

from .._utils import get_tonlib_cdll_path

logger = logging.getLogger(__name__)


# class TonLib for single liteserver
class AsyncTonLibJsonWrapper:
    def __init__(self, loop, ls_index, cdll_path=None, verbose=0):
        cdll_path = get_tonlib_cdll_path() if not cdll_path else cdll_path
        tonlib = CDLL(cdll_path)

        tonlib_json_client_create = tonlib.tonlib_client_json_create
        tonlib_json_client_create.restype = c_void_p
        tonlib_json_client_create.argtypes = []
        try:
            self._client = tonlib_json_client_create()
        except Exception:
            asyncio.ensure_future(self.restart(), loop=loop)

        tonlib_json_client_receive = tonlib.tonlib_client_json_receive
        tonlib_json_client_receive.restype = c_char_p
        tonlib_json_client_receive.argtypes = [c_void_p, c_double]
        self._tonlib_json_client_receive = tonlib_json_client_receive

        tonlib_json_client_send = tonlib.tonlib_client_json_send
        tonlib_json_client_send.restype = None
        tonlib_json_client_send.argtypes = [c_void_p, c_char_p]
        self._tonlib_json_client_send = tonlib_json_client_send

        tonlib_json_client_execute = tonlib.tonlib_client_json_execute
        tonlib_json_client_execute.restype = c_char_p
        tonlib_json_client_execute.argtypes = [c_void_p, c_char_p]
        self._tonlib_json_client_execute = tonlib_json_client_execute

        tonlib_json_client_destroy = tonlib.tonlib_client_json_destroy
        tonlib_json_client_destroy.restype = None
        tonlib_json_client_destroy.argtypes = [c_void_p]
        self._tonlib_json_client_destroy = tonlib_json_client_destroy

        self.futures = {}
        self.loop = loop
        self.ls_index = ls_index
        self.read_results_task = asyncio.ensure_future(
            self.read_results(), loop=self.loop)
        self.del_expired_futures_task = asyncio.ensure_future(
            self.del_expired_futures_loop(), loop=self.loop)
        self.shutdown_state = False  # False, "started", "finished"
        self.request_num = 0
        self.verbose = verbose

        self.max_requests = None
        self.max_restarts = None

    def __del__(self):
        try:
            self._tonlib_json_client_destroy(self._client)
        except Exception:
            logger.error(f'Traceback: {traceback.format_exc()}')
            asyncio.ensure_future(self.restart(), loop=self.loop)

    def send(self, query):
        query = json.dumps(query).encode('utf-8')
        try:
            self._tonlib_json_client_send(self._client, query)
        except Exception:
            asyncio.ensure_future(self.restart(), loop=self.loop)

    async def restart(self):
        if not self.shutdown_state:
            self.shutdown_state = "started"
            asyncio.ensure_future(self.restart_hook(
                self.max_restarts), loop=self.loop)

    def receive(self, timeout=10):
        result = None
        try:
            result = self._tonlib_json_client_receive(
                self._client, timeout)  # time.sleep # asyncio.sleep
        except Exception:
            asyncio.ensure_future(self.restart(), loop=self.loop)
        if result:
            result = json.loads(result.decode('utf-8'))
        return result

    def set_restart_hook(self, hook, max_requests=None, max_restarts=None):
        self.max_requests = max_requests
        self.max_restarts = max_restarts
        self.restart_hook = hook

    def execute(self, query, timeout=10):
        query_type = query.get('@type', '?')

        extra_id = "%s:%s:%s" % (
            time.time()+timeout, self.ls_index, random.random())
        query["@extra"] = extra_id

        self.loop.run_in_executor(None, lambda: self.send(query))

        future_result = self.loop.create_future()
        self.futures[extra_id] = future_result

        self.request_num += 1

        if self.max_requests and self.max_requests < self.request_num:
            asyncio.ensure_future(self.restart(), loop=self.loop)

        return future_result

    @property
    def _is_finishing(self):
        return (not len(self.futures)) and (self.shutdown_state in ["started", "finished"])

    async def read_results(self):
        timeout = 3
        delta = 5
        receive_func = functools.partial(self.receive, timeout)

        while not self._is_finishing:
            result = None
            try:
                result = await asyncio.wait_for(self.loop.run_in_executor(None, receive_func), timeout=timeout + delta)
            except asyncio.TimeoutError:
                logger.critical(f"Tonlib #{self.ls_index:03d} Stuck!")
                asyncio.ensure_future(self.restart(), loop=self.loop)
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.critical(f"Tonlib #{self.ls_index:03d} crashed!")
                asyncio.ensure_future(self.restart(), loop=self.loop)
                await asyncio.sleep(0.05)

            # return result
            if result and isinstance(result, dict) and ("@extra" in result) and (result["@extra"] in self.futures):
                try:
                    if not self.futures[result["@extra"]].done():
                        self.futures[result["@extra"]].set_result(result)
                        self.futures.pop(result["@extra"])
                except Exception as e:
                    logger.error(
                        f'Tonlib #{self.ls_index:03d} receiving result exception: {e}')
        self.shutdown_state = "finished"

    async def del_expired_futures_loop(self):
        while not self._is_finishing:
            await self.cancel_futures()
            await asyncio.sleep(0.05)

    async def cancel_futures(self, cancel_all=False):
        now = time.time()
        to_del = []
        for i in self.futures:
            if float(i.split(":")[0]) <= now or cancel_all:
                to_del.append(i)
        for i in to_del:
            i.cancel()
            self.futures.pop(i)
