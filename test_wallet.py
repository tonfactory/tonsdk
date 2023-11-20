from tonsdk.crypto import mnemonic_new, mnemonic_is_valid, mnemonic_to_hd_seed
from tonsdk.crypto.hd import mnemonic_validate, derive_mnemonics_path
from tonsdk.contract.wallet import Wallets, WalletVersionEnum
from tonsdk.utils import to_nano, bytes_to_b64str

mnemonics = [
  'squeeze', 'afford',  'brother',
  'era',     'remain',  'upper',
  'region',  'goat',    'dog',
  'gain',    'ketchup', 'drip',
  'honey',   'coil',    'interest',
  'walk',    'merit',   'hidden',
  'real',    'puzzle',  'toward',
  'penalty', 'answer',  'meat'
]
#  mnemonics = mnemonic_new()
version = WalletVersionEnum.v4r2
wc = 0

mnemonics, pub_k, priv_k, wallet = Wallets.from_mnemonics(mnemonics=mnemonics, version=version, workchain=wc)


print("mnemonics", mnemonics)
print("pub_k", pub_k)
print("priv_k", priv_k)
print("wallet", wallet.address.to_string(True, True, True))

root_mnemonic = [
        "stock", "spin", "miss",
        "term", "actual", "auto",
        "ozone", "mass", "labor",
        "middle", "grab", "task",
        "cool", "tenant", "close",
        "invest", "common", "hire",
        "aware", "valley", "scene",
        "seven", "observe", "trend"
    ]
root_seed = 'aWyXi7Singg64DJfwlU9JRfZsFMRSgQfJamUOSZl8ggllunSb8ocgqL/ydbxrrfEQP22p3SFn3lzbEv4dnJbng=='
path_0 = [0]
mnemonics_path_0 = [
            'crush', 'guitar', 'depth',
            'metal', 'social', 'pause',
            'angle', 'spread', 'real',
            'sphere', 'garbage', 'crime',
            'device', 'ostrich', 'keep',
            'embody', 'fire', 'plug',
            'water', 'stand', 'execute',
            'race', 'cattle', 'capable'
        ]

path_10 = [0, 10, 1000000000],
mnemonics_path_0_10 = [
            'venture', 'december', 'exile',
            'shell', 'venture', 'chaos',
            'edge', 'fiber', 'core',
            'woman', 'glance', 'length',
            'token', 'sunset', 'cost',
            'ankle', 'bird', 'pudding',
            'power', 'minimum', 'conduct',
            'release', 'easy', 'giraffe'
        ]

root_hd_seed_from_mnemonic = bytes_to_b64str(mnemonic_to_hd_seed(root_mnemonic))
print("seed", root_hd_seed_from_mnemonic)
print("mnemonic_to_hd_seed Equal root_seed", root_seed == root_hd_seed_from_mnemonic)


derive_mnemonics_path_0 = derive_mnemonics_path(seed=root_hd_seed_from_mnemonic.encode("utf-8"), path=path_0)
print("deriveMnemonicsPath", derive_mnemonics_path_0)
print("deriveMnemonicsPath_0 Equal mnemonics_path_0", derive_mnemonics_path_0 == mnemonics_path_0)


"""to external deploy"""
# boc = wallet.create_init_external_message()


"""to internal deploy"""
# query = my_wallet.create_transfer_message(to_addr=new_wallet.address.to_string(),
#                                   amount=to_nano(0.02, 'ton'),
#                                   state_init=new_wallet.create_state_init()['state_init'],
#                                   seqno=int('wallet seqno'))


"""transfer"""
# query = wallet.create_transfer_message(to_addr='destination address',
#                                   amount=to_nano(float('amount to transfer'), 'ton'),
#                                   payload='message',
#                                   seqno=int('wallet seqno'))


"""then send boc to blockchain"""
# boc = bytes_to_b64str(query["message"].to_boc(False))
