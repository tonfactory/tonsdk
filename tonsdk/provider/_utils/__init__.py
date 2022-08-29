import base64

from .._exceptions import ResponseError
from ...boc import Cell


def parse_object(obj):
    type_name = obj['@type']

    if type_name in ["tvm.list", "tvm.tuple"]:
        return [parse_object(o) for o in obj["elements"]]  # ?
    elif type_name == "tvm.stackEntryTuple":
        return parse_object(obj["tuple"])
    elif type_name == "tvm.stackEntryNumber":
        return parse_object(obj["number"])
    elif type_name == "tvm.numberDecimal":
        raise Exception("Implement me pls")
    else:
        raise Exception(f"Unknown type: {type_name}")


def parse_response_stack(pair):
    type_name = pair[0]
    val = pair[1]

    if type_name == "num":
        return int(val.replace('/0x/', ''), 16)
    elif type_name in ["list", "tuple"]:
        return parse_object(val)
    elif type_name == "cell":
        content_bytes = base64.b64decode(val)
        return Cell.one_from_boc(content_bytes)
    else:
        raise Exception(f"Unknown type: {type_name}")


def parse_response(response):
    if response["exit_code"] not in [0, 1]:
        raise ResponseError("Error response", response["exit_code"])

    arr = [parse_response_stack(pair) for pair in response["stack"]]

    return arr[0] if len(arr) == 1 else arr
