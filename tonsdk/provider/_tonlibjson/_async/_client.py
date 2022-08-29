import asyncio
import codecs
import json
import logging
import random
from copy import deepcopy
from pathlib import Path

from tvm_valuetypes import render_tvm_stack, deserialize_boc

from ._wrapper import AsyncTonLibJsonWrapper
from .._utils import b64str_to_hex, hex_to_b64str, hash_to_hex, CtypesStdoutCapture, TonLibWrongResult
from ..._address import prepare_address, detect_address

logger = logging.getLogger(__name__)


class AsyncTonlibClient:
    def __init__(self,
                 config,
                 keystore,
                 loop,
                 cdll_path=None,
                 verbosity_level=0):
        self.ls_index = random.randrange(0, len(config['liteservers']))
        self.config = config
        self.keystore = keystore
        self.cdll_path = cdll_path
        self.loop = loop
        self.verbosity_level = verbosity_level
        self.max_parallel_requests = config['liteservers'][0].get(
            "max_parallel_requests", 50)

        self.semaphore = None
        self.tonlib_wrapper = None
        self.loaded_contracts_num = None

    @property
    def local_config(self):
        local = deepcopy(self.config)
        local['liteservers'] = [local['liteservers'][self.ls_index]]
        return local

    async def reconnect(self, max_restarts=None):
        if max_restarts is not None:
            max_restarts -= 1
        if max_restarts is None or max_restarts >= 0:
            await self.init(max_restarts)
            logger.info(
                f'Client #{self.ls_index:03d} reconnected (max_restarts: {max_restarts})')
        else:
            logger.info(
                'Client #{self.ls_index:03d} has no reconnect attempts left')
            self.tonlib_wrapper = None

    async def init(self, max_restarts=None):
        """
        TL Spec
            init options:options = options.Info;
            options config:config keystore_type:KeyStoreType = Options;

            keyStoreTypeDirectory directory:string = KeyStoreType;
            config config:string blockchain_name:string use_callbacks_for_network:Bool ignore_cache:Bool = Config;

        :param ip: IPv4 address in dotted notation or signed int32
        :param port: IPv4 TCP port
        :param key: base64 pub key of liteserver node
        :return: None
        """
        self.semaphore = asyncio.Semaphore(self.max_parallel_requests)

        self.loaded_contracts_num = 0
        wrapper = AsyncTonLibJsonWrapper(self.loop, self.ls_index, self.cdll_path)
        keystore_obj = {
            '@type': 'keyStoreTypeDirectory',
            'directory': self.keystore
        }
        # create keystore
        Path(self.keystore).mkdir(parents=True, exist_ok=True)

        request = {
            '@type': 'init',
            'options': {
                '@type': 'options',
                'config': {
                    '@type': 'config',
                    'config': json.dumps(self.local_config),
                    'use_callbacks_for_network': False,
                    'blockchain_name': '',
                    'ignore_cache': False
                },
                'keystore_type': keystore_obj
            }
        }
        self.tonlib_wrapper = wrapper
        with CtypesStdoutCapture():
            # set verbosity level
            await self.set_verbosity_level(self.verbosity_level)

        # set confog
        init_result = await self.tonlib_wrapper.execute(request)
        self.tonlib_wrapper.set_restart_hook(
            hook=self.reconnect, max_requests=1024, max_restarts=max_restarts)

        logger.info(F"TonLib #{self.ls_index:03d} inited successfully")

        return init_result

    async def set_verbosity_level(self, level):
        request = {
            '@type': 'setLogVerbosityLevel',
            'new_verbosity_level': level
        }
        return await self.tonlib_wrapper.execute(request)

    async def raw_get_transactions(self, account_address: str, from_transaction_lt: str, from_transaction_hash: str):
        """
        TL Spec:
            raw.getTransactions account_address:accountAddress from_transaction_id:internal.transactionId = raw.Transactions;
            accountAddress account_address:string = AccountAddress;
            internal.transactionId lt:int64 hash:bytes = internal.TransactionId;
        :param account_address: str with raw or user friendly address
        :param from_transaction_lt: from transaction lt
        :param from_transaction_hash: from transaction hash in HEX representation
        :return: dict as
            {
                '@type': 'raw.transactions',
                'transactions': list[dict as {
                    '@type': 'raw.transaction',
                    'utime': int,
                    'data': str,
                    'transaction_id': internal.transactionId,
                    'fee': str,
                    'in_msg': dict as {
                        '@type': 'raw.message',
                        'source': str,
                        'destination': str,
                        'value': str,
                        'message': str
                    },
                    'out_msgs': list[dict as raw.message]
                }],
                'previous_transaction_id': internal.transactionId
            }
        """
        account_address = prepare_address(account_address)
        from_transaction_hash = hex_to_b64str(from_transaction_hash)

        request = {
            '@type': 'raw.getTransactions',
            'account_address': {
                'account_address': account_address,
            },
            'from_transaction_id': {
                '@type': 'internal.transactionId',
                'lt': from_transaction_lt,
                'hash': from_transaction_hash
            }
        }
        return await self.tonlib_wrapper.execute(request)

    async def raw_get_account_state(self, address: str):
        """
        TL Spec:
            raw.getAccountState account_address:accountAddress = raw.AccountState;
            accountAddress account_address:string = AccountAddress;
        :param address: str with raw or user friendly address
        :return: dict as
            {
                '@type': 'raw.accountState',
                'balance': str,
                'code': str,
                'data': str,
                'last_transaction_id': internal.transactionId,
                'sync_utime': int
            }
        """
        account_address = prepare_address(
            address)  # TODO: understand why this is not used
        request = {
            '@type': 'raw.getAccountState',
            'account_address': {
                'account_address': address
            }
        }

        return await self.tonlib_wrapper.execute(request)

    async def generic_get_account_state(self, address: str):
        # TODO: understand why this is not used
        account_address = prepare_address(address)
        request = {
            '@type': 'getAccountState',
            'account_address': {
                'account_address': address
            }
        }
        return await self.tonlib_wrapper.execute(request)

    async def _load_contract(self, address):
        # TODO: understand why this is not used
        account_address = prepare_address(address)
        request = {
            '@type': 'smc.load',
            'account_address': {
                'account_address': address
            }
        }
        result = await self.tonlib_wrapper.execute(request)
        if result.get('@type', 'error') == 'error':
            raise TonLibWrongResult("smc.load failed", result)
        self.loaded_contracts_num += 1
        return result["id"]

    async def raw_run_method(self, address, method, stack_data, output_layout=None):
        """
          For numeric data only
          TL Spec:
            smc.runGetMethod id:int53 method:smc.MethodId stack:vector<tvm.StackEntry> = smc.RunResult;

          smc.methodIdNumber number:int32 = smc.MethodId;
          smc.methodIdName name:string = smc.MethodId;

          tvm.slice bytes:string = tvm.Slice;
          tvm.cell bytes:string = tvm.Cell;
          tvm.numberDecimal number:string = tvm.Number;
          tvm.tuple elements:vector<tvm.StackEntry> = tvm.Tuple;
          tvm.list elements:vector<tvm.StackEntry> = tvm.List;

          tvm.stackEntrySlice slice:tvm.slice = tvm.StackEntry;
          tvm.stackEntryCell cell:tvm.cell = tvm.StackEntry;
          tvm.stackEntryNumber number:tvm.Number = tvm.StackEntry;
          tvm.stackEntryTuple tuple:tvm.Tuple = tvm.StackEntry;
          tvm.stackEntryList list:tvm.List = tvm.StackEntry;
          tvm.stackEntryUnsupported = tvm.StackEntry;

          smc.runResult gas_used:int53 stack:vector<tvm.StackEntry> exit_code:int32 = smc.RunResult;
        """
        stack_data = render_tvm_stack(stack_data)
        if isinstance(method, int):
            method = {'@type': 'smc.methodIdNumber', 'number': method}
        else:
            method = {'@type': 'smc.methodIdName', 'name': str(method)}
        contract_id = await self._load_contract(address)
        request = {
            '@type': 'smc.runGetMethod',
            'id': contract_id,
            'method': method,
            'stack': stack_data
        }

        return await self.tonlib_wrapper.execute(request)

    async def raw_send_message(self, serialized_boc):
        """
          raw.sendMessage body:bytes = Ok;

          :param serialized_boc: bytes, serialized bag of cell
        """
        serialized_boc = codecs.decode(codecs.encode(
            serialized_boc, "base64"), 'utf-8').replace("\n", '')
        request = {
            '@type': 'raw.sendMessage',
            'body': serialized_boc
        }
        return await self.tonlib_wrapper.execute(request)

    async def _raw_create_query(self, destination, body, init_code=b'', init_data=b''):
        """
          raw.createQuery destination:accountAddress init_code:bytes init_data:bytes body:bytes = query.Info;

          query.info id:int53 valid_until:int53 body_hash:bytes  = query.Info;

        """
        init_code = codecs.decode(codecs.encode(
            init_code, "base64"), 'utf-8').replace("\n", '')
        init_data = codecs.decode(codecs.encode(
            init_data, "base64"), 'utf-8').replace("\n", '')
        body = codecs.decode(codecs.encode(body, "base64"),
                             'utf-8').replace("\n", '')
        destination = prepare_address(destination)
        request = {
            '@type': 'raw.createQuery',
            'body': body,
            'init_code': init_code,
            'init_data': init_data,
            'destination': {
                'account_address': destination
            }
        }
        result = await self.tonlib_wrapper.execute(request)
        if result.get('@type', 'error') == 'error':
            raise TonLibWrongResult("raw.createQuery failed", result)
        return result

    async def _raw_send_query(self, query_info):
        """
          query.send id:int53 = Ok;
        """
        request = {
            '@type': 'query.send',
            'id': query_info['id']
        }
        return await self.tonlib_wrapper.execute(request)

    async def raw_create_and_send_query(self, destination, body, init_code=b'', init_data=b''):
        query_info = await self._raw_create_query(destination, body, init_code, init_data)
        return self._raw_send_query(query_info)

    async def raw_create_and_send_message(self, destination, body, initial_account_state=b''):
        # Very close to raw_create_and_send_query, but StateInit should be generated outside
        """
          raw.createAndSendMessage destination:accountAddress initial_account_state:bytes data:bytes = Ok;

        """
        initial_account_state = codecs.decode(codecs.encode(
            initial_account_state, "base64"), 'utf-8').replace("\n", '')
        body = codecs.decode(codecs.encode(body, "base64"),
                             'utf-8').replace("\n", '')
        destination = prepare_address(destination)
        request = {
            '@type': 'raw.createAndSendMessage',
            'destination': {
                'account_address': destination
            },
            'initial_account_state': initial_account_state,
            'data': body
        }
        return await self.tonlib_wrapper.execute(request)

    async def raw_estimate_fees(self, destination, body, init_code=b'', init_data=b'', ignore_chksig=True):
        query_info = await self._raw_create_query(destination, body, init_code, init_data)
        request = {
            '@type': 'query.estimateFees',
            'id': query_info['id'],
            'ignore_chksig': ignore_chksig
        }
        return await self.tonlib_wrapper.execute(request)

    async def raw_get_block_transactions(self, fullblock, count, after_tx):
        request = {
            '@type': 'blocks.getTransactions',
            'id': fullblock,
            'mode': 7 if not after_tx else 7+128,
            'count': count,
            'after': after_tx
        }
        return await self.tonlib_wrapper.execute(request)

    async def raw_get_block_transactions_ext(self, fullblock, count, after_tx):
        request = {
            '@type': 'blocks.getTransactionsExt',
            'id': fullblock,
            'mode': 7 if not after_tx else 7+128,
            'count': count,
            'after': after_tx
        }
        return await self.tonlib_wrapper.execute(request)

    async def get_transactions(self, account,
                               from_transaction_lt=None,
                               from_transaction_hash=None,
                               to_transaction_lt=0,
                               limit=10,
                               decode_messages=True,
                               *args, **kwargs):
        """
         Return all transactions between from_transaction_lt and to_transaction_lt
         if to_transaction_lt and to_transaction_hash are not defined returns all transactions
         if from_transaction_lt and from_transaction_hash are not defined checks last
        """
        if from_transaction_hash:
            from_transaction_hash = hash_to_hex(from_transaction_hash)
        if (from_transaction_lt == None) or (from_transaction_hash == None):
            addr = await self.raw_get_account_state(account)
            if '@type' in addr and addr['@type'] == "error":
                addr = await self.raw_get_account_state(account)
            if '@type' in addr and addr['@type'] == "error":
                raise TonLibWrongResult("raw.getAccountState failed", addr)
            try:
                from_transaction_lt, from_transaction_hash = int(
                    addr["last_transaction_id"]["lt"]), b64str_to_hex(addr["last_transaction_id"]["hash"])
            except KeyError:
                raise TonLibWrongResult(
                    "Can't get last_transaction_id data", addr)
        reach_lt = False
        all_transactions = []
        current_lt, curret_hash = from_transaction_lt, from_transaction_hash
        while (not reach_lt) and (len(all_transactions) < limit):
            raw_transactions = await self.raw_get_transactions(account, current_lt, curret_hash)
            if(raw_transactions['@type']) == 'error':
                break
                # TODO probably we should chenge get_transactions API
                # if 'message' in raw_transactions['message']:
                #  raise Exception(raw_transactions['message'])
                # else:
                #  raise Exception("Can't get transactions")
            transactions, next = raw_transactions['transactions'], raw_transactions.get(
                "previous_transaction_id", None)
            for t in transactions:
                tlt = int(t['transaction_id']['lt'])
                if tlt <= to_transaction_lt:
                    reach_lt = True
                    break
                all_transactions.append(t)
            if next:
                current_lt, curret_hash = int(
                    next["lt"]), b64str_to_hex(next["hash"])
            else:
                break
            if current_lt == 0:
                break

        all_transactions = all_transactions[:limit]
        for t in all_transactions:
            try:
                if "in_msg" in t:
                    if "source" in t["in_msg"]:
                        t["in_msg"]["source"] = t["in_msg"]["source"]["account_address"]
                    if "destination" in t["in_msg"]:
                        t["in_msg"]["destination"] = t["in_msg"]["destination"]["account_address"]
                    if decode_messages:
                        try:
                            if "msg_data" in t["in_msg"]:
                                dcd = ""
                                if t["in_msg"]["msg_data"]["@type"] == "msg.dataRaw":
                                    msg_cell_boc = codecs.decode(codecs.encode(
                                        t["in_msg"]["msg_data"]["body"], 'utf8'), 'base64')
                                    message_cell = deserialize_boc(
                                        msg_cell_boc)
                                    dcd = message_cell.data.data.tobytes()
                                    t["in_msg"]["message"] = codecs.decode(
                                        codecs.encode(dcd, 'base64'), "utf8")
                                elif t["in_msg"]["msg_data"]["@type"] == "msg.dataText":
                                    dcd = codecs.encode(
                                        t["in_msg"]["msg_data"]["text"], 'utf8')
                                    t["in_msg"]["message"] = codecs.decode(
                                        codecs.decode(dcd, 'base64'), "utf8")
                        except Exception as e:
                            t["in_msg"]["message"] = ""
                            logger.warning(
                                f"in_msg message decoding exception: {e}")
                if "out_msgs" in t:
                    for o in t["out_msgs"]:
                        if "source" in o:
                            o["source"] = o["source"]["account_address"]
                        if "destination" in o:
                            o["destination"] = o["destination"]["account_address"]
                        if decode_messages:
                            try:
                                if "msg_data" in o:
                                    dcd = ""
                                    if o["msg_data"]["@type"] == "msg.dataRaw":
                                        msg_cell_boc = codecs.decode(codecs.encode(
                                            o["msg_data"]["body"], 'utf8'), 'base64')
                                        message_cell = deserialize_boc(
                                            msg_cell_boc)
                                        dcd = message_cell.data.data.tobytes()
                                        o["message"] = codecs.decode(
                                            codecs.encode(dcd, 'base64'), "utf8")
                                    elif o["msg_data"]["@type"] == "msg.dataText":
                                        dcd = codecs.encode(
                                            o["msg_data"]["text"], 'utf8')
                                        o["message"] = codecs.decode(
                                            codecs.decode(dcd, 'base64'), "utf8")
                            except Exception as e:
                                o["message"] = ""
                                logger.warning(
                                    f"out_msg message decoding exception: {e}")
            except Exception as e:
                logger.error(f"getTransaction exception: {e}")
        return all_transactions

    async def get_masterchain_info(self, *args, **kwargs):
        request = {
            '@type': 'blocks.getMasterchainInfo'
        }
        result = await self.tonlib_wrapper.execute(request)
        if result.get('@type', 'error') == 'error':
            raise TonLibWrongResult("blocks.getMasterchainInfo failed", result)
        return result

    async def lookup_block(self, workchain, shard, seqno=None, lt=None, unixtime=None, *args, **kwargs):
        assert seqno or lt or unixtime, "Seqno, LT or unixtime should be defined"
        mode = 0
        if seqno:
            mode += 1
        if lt:
            mode += 2
        if unixtime:
            mode += 4
        request = {
            '@type': 'blocks.lookupBlock',
            'mode': mode,
            'id': {
                '@type': 'ton.blockId',
                'workchain': workchain,
                'shard': shard,
                'seqno': seqno
            },
            'lt': lt,
            'utime': unixtime
        }
        return await self.tonlib_wrapper.execute(request)

    async def get_shards(self, master_seqno=None, lt=None, unixtime=None, *args, **kwargs):
        assert master_seqno or lt or unixtime, "Seqno, LT or unixtime should be defined"
        wc, shard = -1, -9223372036854775808
        fullblock = await self.lookup_block(wc, shard, master_seqno, lt, unixtime)
        request = {
            '@type': 'blocks.getShards',
            'id': fullblock
        }
        return await self.tonlib_wrapper.execute(request)

    async def get_block_transactions(self, workchain, shard, seqno, count, root_hash=None, file_hash=None, after_lt=None, after_hash=None, *args, **kwargs):
        if root_hash and file_hash:
            fullblock = {
                '@type': 'ton.blockIdExt',
                'workchain': workchain,
                'shard': shard,
                'seqno': seqno,
                'root_hash': root_hash,
                'file_hash': file_hash
            }
        else:
            fullblock = await self.lookup_block(workchain, shard, seqno)
            if fullblock.get('@type', 'error') == 'error':
                return fullblock
        after_tx = {
            '@type': 'blocks.accountTransactionId',
            'account': after_hash if after_hash else 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=',
            'lt': after_lt if after_lt else 0
        }
        total_result = {}
        incomplete = True

        while incomplete:
            result = await self.raw_get_block_transactions(fullblock, count, after_tx)
            if(result['@type']) == 'error':
                result = await self.raw_get_block_transactions(fullblock, count, after_tx)
            if(result['@type']) == 'error':
                raise TonLibWrongResult('Can\'t get blockTransactions', result)
            if not total_result:
                total_result = result
            else:
                total_result["transactions"] += result["transactions"]
                total_result["incomplete"] = result["incomplete"]
            incomplete = result["incomplete"]
            if incomplete:
                after_tx['account'] = result["transactions"][-1]["account"]
                after_tx['lt'] = result["transactions"][-1]["lt"]

        # TODO automatically check incompleteness and download all txes
        for tx in total_result["transactions"]:
            try:
                tx["account"] = "%d:%s" % (
                    result["id"]["workchain"], b64str_to_hex(tx["account"]))
            except:
                pass
        return total_result

    async def get_block_transactions_ext(self,
                                         workchain,
                                         shard,
                                         seqno,
                                         count,
                                         root_hash=None,
                                         file_hash=None,
                                         after_lt=None,
                                         after_hash=None,
                                         *args, **kwargs):
        if root_hash and file_hash:
            fullblock = {
                '@type': 'ton.blockIdExt',
                'workchain': workchain,
                'shard': shard,
                'seqno': seqno,
                'root_hash': root_hash,
                'file_hash': file_hash
            }
        else:
            fullblock = await self.lookup_block(workchain, shard, seqno)
            if fullblock.get('@type', 'error') == 'error':
                return fullblock
        after_tx = {
            '@type': 'blocks.accountTransactionId',
            'account': after_hash if after_hash else 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=',
            'lt': after_lt if after_lt else 0
        }
        total_result = {}
        incomplete = True

        while incomplete:
            result = await self.raw_get_block_transactions_ext(fullblock, count, after_tx)
            if(result['@type']) == 'error':
                result = await self.raw_get_block_transactions_ext(fullblock, count, after_tx)
            if(result['@type']) == 'error':
                raise TonLibWrongResult('Can\'t get blockTransactions', result)
            if not total_result:
                total_result = result
            else:
                total_result["transactions"] += result["transactions"]
                total_result["incomplete"] = result["incomplete"]
            incomplete = result["incomplete"]
            if incomplete:
                account_friendly = result["transactions"][-1]["address"]["account_address"]
                hex_without_workchain = detect_address(account_friendly)[
                    'raw_form'].split(':')[1]
                after = hex_to_b64str(hex_without_workchain)
                after_tx['account'] = after
                after_tx['lt'] = result["transactions"][-1]["transaction_id"]["lt"]

        for tx in total_result["transactions"]:
            try:
                account_friendly = tx["address"]["account_address"]
                hex_without_workchain = detect_address(account_friendly)[
                    'raw_form'].split(':')[1]
                tx["account"] = "%d:%s" % (
                    result["id"]["workchain"], hex_without_workchain)
            except:
                pass
        return total_result

    async def get_block_header(self, workchain, shard, seqno, root_hash=None, file_hash=None, *args, **kwargs):
        if root_hash and file_hash:
            fullblock = {
                '@type': 'ton.blockIdExt',
                'workchain': workchain,
                'shard': shard,
                'seqno': seqno,
                'root_hash': root_hash,
                'file_hash': file_hash
            }
        else:
            fullblock = await self.lookup_block(workchain, shard, seqno)
            if fullblock.get('@type', 'error') == 'error':
                return fullblock
        request = {
            '@type': 'blocks.getBlockHeader',
            'id': fullblock
        }
        return await self.tonlib_wrapper.execute(request)

    async def try_locate_tx_by_incoming_message(self, source, destination, creation_lt, *args, **kwargs):
        src = detect_address(source)
        dest = detect_address(destination)
        workchain = dest["raw_form"].split(":")[0]
        shards = await self.get_shards(lt=int(creation_lt))

        for shard_data in shards['shards']:
            shardchain = shard_data['shard']
            for b in range(3):
                block = await self.lookup_block(workchain, shardchain, lt=int(creation_lt) + b * 1000000)
                txs = await self.get_block_transactions(workchain,
                                                        shardchain,
                                                        block["seqno"],
                                                        count=40,
                                                        root_hash=block["root_hash"],
                                                        file_hash=block["file_hash"])
                candidate = tuple()
                count = 0
                for tx in txs["transactions"]:
                    if tx["account"] == dest["raw_form"]:
                        count += 1
                        if not candidate or candidate[1] < int(tx["lt"]):
                            candidate = tx["hash"], int(tx["lt"])
                if candidate:
                    txses = await self.get_transactions(destination,
                                                        from_transaction_lt=candidate[1],
                                                        from_transaction_hash=b64str_to_hex(
                                                            candidate[0]),
                                                        limit=max(count, 10))
                    for tx in txses:
                        try:
                            in_msg = tx["in_msg"]
                            tx_source = in_msg["source"]
                            if len(tx_source) and detect_address(tx_source)["raw_form"] == src["raw_form"]:
                                if int(in_msg["created_lt"]) == int(creation_lt):
                                    return tx
                        except KeyError:
                            pass
        raise Exception("Tx not found")

    async def try_locate_tx_by_outcoming_message(self, source, destination, creation_lt, *args, **kwargs):
        src = detect_address(source)
        dest = detect_address(destination)
        workchain = src["raw_form"].split(":")[0]
        shards = await self.get_shards(lt=int(creation_lt))

        for shard_data in shards['shards']:
            shardchain = shard_data['shard']
            block = await self.lookup_block(workchain, shardchain, lt=int(creation_lt))
            txses = await self.get_block_transactions(workchain,
                                                      shardchain,
                                                      block["seqno"],
                                                      count=40,
                                                      root_hash=block["root_hash"],
                                                      file_hash=block["file_hash"])
            candidate = tuple()
            count = 0
            for tx in txses["transactions"]:
                if tx["account"] == src["raw_form"]:
                    count += 1
                    if not candidate or candidate[1] < int(tx["lt"]):
                        candidate = tx["hash"], int(tx["lt"])
            if candidate:
                txses = await self.get_transactions(source,
                                                    from_transaction_lt=candidate[1],
                                                    from_transaction_hash=b64str_to_hex(
                                                        candidate[0]),
                                                    limit=max(count, 10))
                for tx in txses:
                    try:
                        for msg in tx["out_msgs"]:
                            if detect_address(msg["destination"])["raw_form"] == dest["raw_form"]:
                                if int(msg["created_lt"]) == int(creation_lt):
                                    return tx
                    except KeyError:
                        pass
        raise Exception("Tx not found")
