# https://github.com/vergl4s/ethereum-mnemonic-utils/blob/master/mnemonic_utils.py
import math
import os
from hashlib import pbkdf2_hmac

from ._settings import PBKDF_ITERATIONS


def get_secure_random_number(min_v, max_v):
    range_betw = max_v - min_v
    bits_needed = math.ceil(math.log2(range_betw))
    if bits_needed > 53:
        raise Exception("Range is too large")

    bytes_needed = math.ceil(bits_needed / 8)
    mask = math.pow(2, bits_needed) - 1

    while True:
        res = os.urandom(bits_needed)
        power = (bytes_needed - 1) * 8
        number_val = 0
        for i in range(bytes_needed):
            number_val += res[i] * math.pow(2, power)
            power -= 8
        number_val = int(number_val) & int(mask)
        if number_val >= range_betw:
            continue

        return min_v + number_val


def is_basic_seed(entropy):
    seed = pbkdf2_hmac("sha512", entropy, 'TON seed version'.encode(
        'utf-8'), max(1, math.floor(PBKDF_ITERATIONS / 256)))
    return seed[0] == 0
