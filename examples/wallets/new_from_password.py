from tonsdk.crypto import mnemonic_from_password
from tonsdk.contract.wallet import Wallets, WalletVersionEnum


password = "secretWalletPassword"
mnemonics = mnemonic_from_password(password, words_count=24)  # Will create the same mnemonics for the same password
version = WalletVersionEnum.v3r2
wc = 0

mnemonics, pub_k, priv_k, wallet = Wallets.from_mnemonics(mnemonics=mnemonics, version=version, workchain=wc)
