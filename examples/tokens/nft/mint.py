from tonsdk.contract.token.nft import NFTCollection, NFTItem
from tonsdk.contract import Address
from tonsdk.utils import to_nano, bytes_to_b64str
from tonsdk.contract.wallet import Wallets, WalletVersionEnum


def create_collection():
    royalty_base = 1000
    royalty_factor = 55

    #  royalty in percents = royalty_factor / royalty_base

    collection = NFTCollection(royalty_base=royalty_base,
                               royalty=royalty_factor,
                               royalty_address=Address('royalty address'),
                               owner_address=Address('collection owner address'),
                               collection_content_uri='https://s.getgems.io/nft/b/c/62fba50217c3fe3cbaad9e7f/meta.json',
                               nft_item_content_base_uri='https://s.getgems.io/nft/b/c/62fba50217c3fe3cbaad9e7f/',
                               nft_item_code_hex=NFTItem.code)

    return collection


def create_nft_mint_body():
    collection = create_collection()

    nft_item_index = 0
    # in most collections with offchain metadata individual item content uri = item_index/meta.json

    body = collection.create_mint_body(item_index=nft_item_index,
                                       new_owner_address=Address('owner address'),
                                       item_content_uri=f'{nft_item_index}/meta.json',
                                       amount=to_nano(0.02, 'ton'))

    return body


def create_batch_nft_mint_body():
    collection = create_collection()

    contents_and_owners = []

    from_item_index = 1
    to_item_index = 11

    for i in range(from_item_index, to_item_index + 1):
        contents_and_owners.append(
            (f'{i}/meta.json', Address('owner address'))
        )

    body = collection.create_batch_mint_body(from_item_index=from_item_index,
                                             contents_and_owners=contents_and_owners,
                                             amount_per_one=to_nano(0.01, 'ton'))
    return body


"""your wallet mnemonics"""
mnemonics = ['always', 'crystal', 'grab', 'glance', 'cause', 'dismiss', 'answer', 'expose', 'once', 'session',
             'tunnel', 'topic', 'defense', 'such', 'army', 'smile', 'exhibit', 'misery', 'runway', 'tone', 'want',
             'primary', 'piano', 'language']

mnemonics, pub_k, priv_k, wallet = Wallets.from_mnemonics(mnemonics=mnemonics, version=WalletVersionEnum.v3r2,
                                                          workchain=0)

"""deploy collection"""
collection = create_collection()
collection_state_init = collection.create_state_init()['state_init']

query = wallet.create_transfer_message(to_addr=collection.address.to_string(),
                                       amount=to_nano(0.02, 'ton'),
                                       state_init=collection_state_init,
                                       seqno=int('wallet seqno'))


"""mint nft"""
body = create_nft_mint_body()
collection = create_collection()

query = wallet.create_transfer_message(to_addr=collection.address.to_string(),
                                       amount=to_nano(0.04, 'ton'),
                                       seqno=int('wallet seqno'),
                                       payload=body)


"""mint batch of nfts"""
body = create_batch_nft_mint_body()
collection = create_collection()

query = wallet.create_transfer_message(to_addr=collection.address.to_string(),
                                       amount=to_nano(0.04, 'ton'),
                                       seqno=int('wallet seqno'),
                                       payload=body)


"""then send boc to blockchain"""
boc = bytes_to_b64str(query["message"].to_boc(False))
