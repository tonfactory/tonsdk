
class TonSdkException(Exception):
    """
    Base class for tonsdk exceptions.
    Subclasses should provide `.default_detail` properties.
    """
    default_detail = 'TonSdk error.'

    def __init__(self, detail=None):
        self.detail = self.default_detail if detail is None else detail

    def __str__(self):
        return str(self.detail)
