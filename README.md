# Some usage examples

Create boc to send to the toncenter API

```python
from tonsdk.contract.wallet import WalletVersionEnum, Wallets

wallet_workchain = 0
wallet_version = WalletVersionEnum.v3r2
wallet_mnemonics = ["my", "24", "mnemo", ..., "words"] 

_mnemonics, _pub_k, _priv_k, wallet = Wallets.from_mnemonics(wallet_mnemonics, wallet_version, wallet_workchain)
query = wallet.create_init_external_message()
base64_boc = bytes_to_b64str(query["message"].to_boc(False))
```
