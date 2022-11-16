
def find_common_prefix(src):
    # Corner cases
    if len(src) == 0:
        return ''
    if len(src) == 1:
        return src[0]

    # Searching for prefix
    _sorted = sorted(src)
    size = 0
    for i, e in enumerate(_sorted[0]):
        if e == _sorted[-1][i]:
            size += 1
        else:
            break

    return _sorted[0][:size]

