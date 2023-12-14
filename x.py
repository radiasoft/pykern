import sys
import pykern.pkio


# def is_binary(filename):
#     """
#     https://eli.thegreenplace.net/2011/10/19/perls-guess-if-file-is-text-or-binary-implemented-in-python

#     Uses heuristics to guess whether the given file is text or binary,
#         by reading a single block of bytes from the file.
#         If more than 30% of the chars in the block are non-text, or there
#         are NUL ('\x00') bytes in the block, assume this is a binary file.
#     """
#     def _int2byte(x):
#         return bytes((x,))

#     with open(filename, 'rb') as f:
#         block = f.read(512)
#         if not block:
#             # An empty file is considered a valid text file
#             return False
#         try:
#             block.decode('utf-8')
#             print("passed utf-8")
#             return False
#         except UnicodeDecodeError:
#             _text_characters = (
#                 b''.join(_int2byte(i) for i in range(32, 127)) +
#                 b'\n\r\t\f\b')

#             if b'\x00' in block:
#                 # Files with null bytes are binary
#                 return True

#             # Use translate's 'deletechars' argument to efficiently remove all
#             # occurrences of _text_characters from the block
#             nontext = block.translate(None, _text_characters)
#             return float(len(nontext)) / len(block) > 0.30


if __name__ == "__main__":
    print(pykern.pkio.is_binary('empty.dat'))
    print(pykern.pkio.is_binary('text-data-example.dat'))
    print(pykern.pkio.is_binary('binary-data-example.dat'))

