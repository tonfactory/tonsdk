from .wordlist import wordlist
from hashlib import pbkdf2_hmac
from typing import List, Optional, Tuple
import math, hashlib, hmac

PBKDF_ITERATIONS = 100000

def lpad(string, pad_string, length):
    while len(string) < length:
        string = pad_string + string
    return string

def bytes_to_bits(byte_array):
    res = ''
    for byte in byte_array:
        x = byte
        res += lpad(bin(x)[2:], '0', 8)
    return res

def bytes_to_mnemonic_indexes(src: bytes, words_count: int = 24):
    bits = bytes_to_bits(src)
    indexes = []
    for i in range(words_count):
        sl = bits[i * 11: i * 11 + 11]
        indexes.append(int(sl, 2))
    return indexes

def bytes_to_mnemonics(src: bytes, words_count: int = 24):
    mnemonics = bytes_to_mnemonic_indexes(src, words_count)
    res = [wordlist[m] for m in mnemonics]
    return res

def is_basic_seed(entropy: str | bytes) -> bool:
    seed = pbkdf2_hmac("sha512", entropy, 'TON seed version'.encode('utf-8'), max(1, math.floor(PBKDF_ITERATIONS / 256)))
    return seed[0] == 0

def mnemonic_to_entropy(mnemo_words: List[str], password: Optional[str] = None):
    sign = hmac.new((" ".join(mnemo_words)).encode('utf-8'), bytes(0), hashlib.sha512).digest()
    return sign

def normalize_mnemonic(src: List[str]) -> list:
    return list(map(lambda v: v.lower().strip(), src))

def is_password_seed(entropy: str | bytes) -> bool:
    seed = pbkdf2_hmac("sha512", entropy, 'TON fastseed version', 1, 64)
    return seed[0] == 1

def is_password_needed(mnemonic_array: List[str]):
    passless_entropy = mnemonic_to_entropy(mnemonic_array)
    return (is_password_seed(passless_entropy)) and not (is_basic_seed(passless_entropy))

def mnemonic_validate(mnemonic_array: List[str], password: Optional[str] = None):
    mnemonic_array = normalize_mnemonic(mnemonic_array)
    for word in mnemonic_array:
        if word not in wordlist:
            return False
        
        if password and len(password) > 0:
            if not is_password_needed(mnemonic_array):
                return False
    return is_basic_seed(mnemonic_to_entropy(mnemonic_array, password))

def path_for_account(network: int = 0, workchain: int = 0, account: int = 0, wallet_version: int = 0):
    # network default mainnet 0 and testnet 1
    chain = 255 if workchain == -1 else workchain
    return [44, 607, network, chain, account, wallet_version] # Last zero is reserved for alternative wallet contracts

def tg_user_id_to_account(user_id: int) -> Tuple[int, int]:
    start_limit = 0
    step = 2000000000
    network = 0
    account_id = user_id

    while start_limit <= user_id:
        start_limit += step
        network = (start_limit - step) // step * 2
        account_id = user_id - start_limit + step
    return [network, account_id]