BIT_NUMBER_SIZE = 10  # 10 bit
SHIFT_SIZE = 13  # 13 bit
MAX_BIT_NUMBER = 1022
MAX_SHIFT = 8191  # 2^13 = 8192


class HighloadQueryId:
    def __init__(self) -> None:
        """
        Initializes a HighloadQueryId instance with default values

        :ivar _shift: Internal state for shift (bigint) [0 .. 8191]
        :ivar _bit_number: Internal state for bit number (bigint) [0 .. 1022]
        """
        self._shift = 0
        self._bit_number = 0

    @classmethod
    def from_shift_and_bit_number(
        cls, shift: int, bit_number: int
    ) -> "HighloadQueryId":
        """
        Creates a new HighloadQueryId object with specified shift and bit number

        :param shift: The shift value (int)
        :param bit_number: The bit number value (int)
        :return: A new instance of HighloadQueryId
        :raises ValueError: If the shift or bit number is out of valid range
        """
        if not (0 <= shift <= MAX_SHIFT):
            raise ValueError("invalid shift")
        if not (0 <= bit_number <= MAX_BIT_NUMBER):
            raise ValueError("invalid bitnumber")

        q = cls()
        q._shift = shift
        q._bit_number = bit_number
        return q

    def get_next(self) -> "HighloadQueryId":
        """
        Calculates the next HighloadQueryId based on the current state

        :return: HighloadQueryId representing the next ID
        :raises ValueError: If the current ID is at the maximum capacity
        """
        new_bit_number = self._bit_number + 1
        new_shift = self._shift

        if new_shift == MAX_SHIFT and new_bit_number >= (MAX_BIT_NUMBER - 1):
            # we left one queryId for emergency withdraw
            raise ValueError("Overload")

        if new_bit_number > MAX_BIT_NUMBER:
            new_bit_number = 0
            new_shift += 1
            if new_shift > MAX_SHIFT:
                raise ValueError("Overload")

        return self.from_shift_and_bit_number(
            new_shift, new_bit_number
        )

    def has_next(self) -> bool:
        """
        Checks if there is a next HighloadQueryId available

        :return: True if there is a next ID available, False otherwise
        """
        # we left one queryId for emergency withdraw
        is_end = (
            self._bit_number >= (MAX_BIT_NUMBER - 1)
            and self._shift == MAX_SHIFT
        )
        return not is_end

    @property
    def shift(self) -> int:
        """
        Gets the current shift value

        :return: The current shift value (int)
        """
        return self._shift

    @property
    def bit_number(self) -> int:
        """
        Gets the current bit number value

        :return: The current bit number value (int)
        """
        return self._bit_number

    @property
    def query_id(self) -> int:
        """
        Computes the query ID based on the current shift and bit number

        :return: The computed query ID (int)
        """
        return (self._shift << BIT_NUMBER_SIZE) + self._bit_number

    @classmethod
    def from_query_id(cls, query_id: int) -> "HighloadQueryId":
        """
        Creates a new HighloadQueryId object from a given query ID

        :param query_id: The query ID to parse (int)
        :return: A new instance of HighloadQueryId
        """
        shift = query_id >> BIT_NUMBER_SIZE
        bit_number = query_id & 1023
        return cls.from_shift_and_bit_number(shift, bit_number)

    @classmethod
    def from_seqno(cls, i: int) -> "HighloadQueryId":
        """
        Creates a HighloadQueryId from a sequence number

        :param i: The sequence number (int)
        :return: A new HighloadQueryId
        """
        shift = i // 1023
        bit_number = i % 1023
        return cls.from_shift_and_bit_number(shift, bit_number)

    def to_seqno(self) -> int:
        """
        Converts the current HighloadQueryId to a sequence number

        :return: The sequence number (int)
        """
        return self._bit_number + self._shift * 1023