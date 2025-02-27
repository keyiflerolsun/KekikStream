# ! https://github.com/keyiflerolsun/Kekik-cloudstream/blob/master/FilmMakinesi/src/main/kotlin/com/keyiflerolsun/CloseLoadUnpacker.kt

import re

packed_extract_regex = re.compile(
    r"\}\('(.*)',\s*(\d+),\s*(\d+),\s*'(.*?)'\.split\('\|'\)",
    re.IGNORECASE | re.MULTILINE
)

unpack_replace_regex = re.compile(
    r"\b\w+\b",
    re.IGNORECASE | re.MULTILINE
)

class Unbaser:
    ALPHABET = {
        52: "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOP",
        54: "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQR",
        62: "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        95: " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
    }

    def __init__(self, base: int):
        self.base = base

        if base > 62:
            self.selector = 95
        elif base > 54:
            self.selector = 62
        elif base > 52:
            self.selector = 54
        else:
            self.selector = 52

        self.dict = {char: idx for idx, char in enumerate(Unbaser.ALPHABET[self.selector])}
    
    def unbase(self, value: str) -> int:
        if 2 <= self.base <= 36:
            try:
                return int(value, self.base)
            except ValueError:
                return 0
        else:
            result = 0

            for index, c in enumerate(reversed(value)):
                digit  = self.dict.get(c, 0)
                result += digit * (self.base ** index)

            return result

def unpack(script_block: str) -> str:
    match = packed_extract_regex.search(script_block)
    if not match:
        raise ValueError("Packed script not found")

    payload, radix_str, count_str, symtab_str = match.groups()

    radix  = int(radix_str)
    count  = int(count_str)
    symtab = symtab_str.split('|')

    if len(symtab) != count:
        raise ValueError("there is an error in the packed script")

    unbaser = Unbaser(radix)

    def replacer(match_obj):
        word        = match_obj.group(0)
        index       = unbaser.unbase(word)
        replacement = symtab[index] if index < len(symtab) else word

        return replacement or word

    return unpack_replace_regex.sub(replacer, payload)