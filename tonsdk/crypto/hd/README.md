# Derivation path

```python
def path_for_account(network: int, workchain: int == 0, account: int, wallet_version: int == 0):
    # network default mainnet 0 and testnet 1
    chain = 255 if worckchain === -1 else 0
    return [44, 607, network, chain, account, wallet_version] # Last zero is reserved for alternative wallet contracts
```
We propose to use user's id in telegram for creating personal wallets in centralized apps.
For creating a tree of accounts we will use user's telegram id. At the fact that id's value can be much more bigger than HARDENED_OFFSET (0x80000000 in hex, 2147483647 in decimal)
we estimate it multiple of 2000000000 and add 2 to ```network```:

```python
def tg_user_id_to_account(userid: int) -> Tuple[int, int]:
    start_limit = 0
    step = 2000000000
    network = 0
    account_id = user_id

    while start_limit <= user_id:
        start_limit += step
        network = (start_limit - step) // step * 2
        account_id = user_id - start_limit + step
    return [network, account_id]
```