import asyncio
import base64
import codecs
import functools
import json
import os
import platform
import struct
from functools import wraps
from pathlib import Path


class TonLibWrongResult(Exception):
    def __init__(self, description, result={}):
        self.description = description
        self.result = result

    def __str__(self):
        return f"{self.description} - unexpected lite server response:\n\t{json.dumps(self.result)}"


def get_tonlib_cdll_path():
    platform_name = platform.system().lower()
    if platform_name == 'linux':
        lib_name = 'linux_libtonlibjson.so'
    elif platform_name == 'darwin':
        lib_name = 'macos_libtonlibjson.dylib'
    else:
        raise OSError("Your operating system is not supported yet")

    return os.path.join(
        Path(__file__).resolve().parent, 'distlib', lib_name)


def get_tonlib_config_path(ton_network):
    return os.path.join(
        Path(__file__).resolve().parent, 'distlib', 'config', f'{ton_network}.json')


class CtypesStdoutCapture:
    def __enter__(self):
        self._pipe_out, self._pipe_in = os.pipe()
        self._err_pipe_out, self._err_pipe_in = os.pipe()
        self._stdout = os.dup(1)
        self._stderr = os.dup(2)
        # replace stdout with our write pipe
        os.dup2(self._pipe_in, 1)
        os.dup2(self._err_pipe_in, 2)

        return self

    def __exit__(self, *args):
        # put stdout back in place
        os.dup2(self._stdout, 1)
        os.dup2(self._stderr, 2)


def b64str_to_bytes(b64str):
    b64bytes = codecs.encode(b64str, "utf8")
    return codecs.decode(b64bytes, "base64")


def b64str_to_hex(b64str):
    _bytes = b64str_to_bytes(b64str)
    _hex = codecs.encode(_bytes, "hex")
    return codecs.decode(_hex, "utf8")


def hex_to_b64str(x):
    return codecs.encode(codecs.decode(x, 'hex'), 'base64').decode().replace("\n", "")


def hash_to_hex(b64_or_hex_hash):
    """
    Detect encoding of transactions hash and if necessary convert it to hex.
    """
    if len(b64_or_hex_hash) == 44:
        # Hash is base64
        return b64str_to_hex(b64_or_hex_hash)
    if len(b64_or_hex_hash) == 64:
        # Hash is hex
        return b64_or_hex_hash
    raise ValueError("Invalid hash")


def pubkey_b64_to_hex(b64_key):
    """
    Convert tonlib's pubkey in format f'I{"H"*16}' i.e. prefix:key to upperhex filename as it stored in keystore
    :param b64_key: base64 encoded 36 bytes of public key
    :return:
    """
    bin_key = base64.b64decode(b64_key)
    words = 18
    ints_key = struct.unpack(f'{"H"*words}', bin_key)
    key = [x.to_bytes(2, byteorder='little') for x in ints_key]
    key = b''.join(key)
    key = [((x & 0x0F) << 4 | (x & 0xF0) >> 4).to_bytes(
        1, byteorder='little') for x in key]
    name = b''.join(key)
    return name.hex().upper()


def parallelize(f):
    @functools.wraps(f)
    def wrapper(self, *args, **kwds):
        if self._style == 'futures':
            return self._executor.submit(f, self, *args, **kwds)
        if self._style == 'asyncio':
            loop = asyncio.get_event_loop()
            return loop.run_in_executor(self._executor, functools.partial(f, self, *args, **kwds))
        raise RuntimeError(self._style)
    return wrapper


def coro_result(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def userfriendly_to_raw(address):
    k = base64.urlsafe_b64decode(address)[1:34]
    workchain_id = struct.unpack('b', k[:1])[0]
    key = k[1:].hex().upper()
    return f'{workchain_id}:{key}'


def str_b64encode(s):
    return base64.b64encode(s.encode('utf-8')).decode('utf-8') if s and isinstance(s, str) else None


# repeat
def retry_async(repeats=3, last_archval=False, raise_error=True):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = None
            exception = None
            for i in range(repeats):
                try:
                    kwargs_loc = kwargs.copy()
                    if i == repeats - 1 and last_archval:
                        kwargs_loc['archival'] = True
                    result = await func(*args, **kwargs_loc)
                    exception = None
                except Exception as ee:
                    exception = ee
            if exception is not None and raise_error:
                raise exception
            return result
        # end def
        return wrapper
    return decorator
