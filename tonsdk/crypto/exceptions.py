from .._exceptions import TonSdkException


class InvalidMnemonicsError(TonSdkException):
    default_detail = "Invalid mnemonics error."
