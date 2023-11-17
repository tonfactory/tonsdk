from typing import List, Optional, Tuple
import math, hmac
from hashlib import pbkdf2_hmac
from .utils import bytes_to_mnemonics, mnemonic_validate
from .._settings import PBKDF_ITERATIONS

HARDENED_OFFSET = 0x80000000
MNEMONICS_SEED = 'TON Mnemonics HD seed'

def mnemonic_from_random_seed(seed: bytes, words_count: int = 24, password: Optional[str] = None):
    bytes_length = math.ceil(words_count * 11 / 8)
    current_seed = seed
    while True:
        entropy = pbkdf2_hmac('sha512', current_seed, 'TON mnemonic seed', max(1, math.floor(PBKDF_ITERATIONS / 256)), bytes_length)
        mnemonics = bytes_to_mnemonics(entropy, words_count)
        if mnemonic_validate(mnemonics, password):
            return mnemonics
        current_seed = entropy

def get_mnemonics_master_key_from_seed(seed: bytes) -> Tuple[bytes, bytes]:
    I = hmac(MNEMONICS_SEED, seed)
    IL = I[:32]
    IR = I[32:]
    return [IL, IR]

def derive_mnemonic_hardened_key(parent: Tuple[bytes, bytes], index: int) -> Tuple[bytes, bytes]:
    if index >= HARDENED_OFFSET:
        raise ValueError('Key index must be less than offset')

    index_buffer = bytearray(4)
    index_buffer.append(index + HARDENED_OFFSET, 0)
    data = b'\x00' + parent[0] + index_buffer

    I = hmac(parent[1], data)
    IL = I[:32]
    IR = I[32:]
    return [IL, IR]

def derive_mnemonics_path(seed: bytes, path: List[int], words_count: int = 24, password: Optional[str] = None):
    state = get_mnemonics_master_key_from_seed(seed)
    remaining = path.copy()
    while len(remaining) > 0:
        index = remaining[0]
        remaining = remaining[1:]
        state = derive_mnemonic_hardened_key(state, index)

    return mnemonic_from_random_seed(state[0], words_count, password)