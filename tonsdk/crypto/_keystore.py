import os
from hashlib import pbkdf2_hmac
from typing import Tuple

from nacl.bindings import crypto_box_seed_keypair


def generate_keystore_key(password: str, salt: bytes) -> Tuple[bytes, bytes]:
    """
    :rtype: (bytes(public_key), bytes(secret_key))
    """
    secret = pbkdf2_hmac("sha512", password.encode('utf-8'), salt, 400_000, 32)
    return crypto_box_seed_keypair(secret)


def generate_new_keystore(password: str, version: int = 1):
    salt = os.urandom(32)
    pub_k, _ = generate_keystore_key(password, salt)

    return {"version": version, "salt": salt.hex(), "public_key": pub_k.hex()}
