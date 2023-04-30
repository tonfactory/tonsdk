from tonsdk.crypto import mnemonic_new
from tonsdk.contract.wallet import Wallets, WalletVersionEnum
from tonsdk.utils import to_nano, bytes_to_b64str


mnemonics = ['broken', 'decade', 'unit', 'bird', 'enrich', 'great', 'nurse', 'offer', 'rescue',
             'sound', 'pole', 'true', 'dignity', 'buyer', 'provide', 'boil', 'connect', 'universe',
             'model', 'add', 'obtain', 'hire', 'gift', 'swim']
#  mnemonics = mnemonic_new()
version = WalletVersionEnum.v3r2
wc = 0

mnemonics, pub_k, priv_k, wallet = Wallets.from_mnemonics(mnemonics=mnemonics, version=version, workchain=wc)


"""to external deploy"""
boc = wallet.create_init_external_message()


"""to internal deploy"""
query = my_wallet.create_transfer_message(to_addr=new_wallet.address.to_string(),
                                  amount=to_nano(0.02, 'ton'),
                                  state_init=new_wallet.create_state_init()['state_init'],
                                  seqno=int('wallet seqno'))


"""transfer"""
query = wallet.create_transfer_message(to_addr='destination address',
                                  amount=to_nano(float('amount to transfer'), 'ton'),
                                  payload='message',
                                  seqno=int('wallet seqno'))


"""then send boc to blockchain"""
boc = bytes_to_b64str(query["message"].to_boc(False))
