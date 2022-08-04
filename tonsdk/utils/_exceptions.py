from .._exceptions import TonSdkException


class InvalidAddressError(TonSdkException):
    default_detail = 'Invalid address error.'
