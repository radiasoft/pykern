import sys


def istextfile(fileobj, blocksize=512):
    """ Uses heuristics to guess whether the given file is text or binary,
        by reading a single block of bytes from the file.
        If more than 30% of the chars in the block are non-text, or there
        are NUL ('\x00') bytes in the block, assume this is a binary file.
    """
    def _int2byte(x):
        return bytes((x,))

    _text_characters = (
        b''.join(_int2byte(i) for i in range(32, 127)) +
        b'\n\r\t\f\b')

    block = fileobj.read(blocksize)
    if b'\x00' in block:
        # Files with null bytes are binary
        return False
    elif not block:
        # An empty file is considered a valid text file
        return True

    # Use translate's 'deletechars' argument to efficiently remove all
    # occurrences of _text_characters from the block
    nontext = block.translate(None, _text_characters)
    return float(len(nontext)) / len(block) <= 0.30


if __name__ == "__main__":
    with open('text-data-example.dat', 'rb') as f:
        print(istextfile(f))
    with open('binary-data-example.dat', 'rb') as f:
        print(istextfile(f))
