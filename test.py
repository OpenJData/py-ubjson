# Copyright (c) 2015, V. Termanis, Iotic Labs Ltd.
# All rights reserved.
# Licensed under 2-clause BSD license - see LICENSE file for details.

from sys import version_info
from io import BytesIO
from unittest import TestCase
from pprint import pformat
from decimal import Decimal
from struct import pack
from collections import OrderedDict

from ubjson.compat import u
from ubjson import dump as ubjdump, dumpb as ubjdumpb, loadb as ubjloadb, EncoderException, DecoderException

# Not imported from ubjson.markers since cannot access them directly if compiled with cython

# Value types
TYPE_NONE = b'\x00'
TYPE_NULL = b'Z'
TYPE_BOOL_TRUE = b'T'
TYPE_BOOL_FALSE = b'F'
TYPE_INT8 = b'i'
TYPE_UINT8 = b'U'
TYPE_INT16 = b'I'
TYPE_INT32 = b'l'
TYPE_INT64 = b'L'
TYPE_FLOAT32 = b'd'
TYPE_FLOAT64 = b'D'
TYPE_HIGH_PREC = b'H'
TYPE_CHAR = b'C'
TYPE_STRING = b'S'

# Container delimiters
OBJECT_START = b'{'
OBJECT_END = b'}'
ARRAY_START = b'['
ARRAY_END = b']'

# Optional container parameters
CONTAINER_TYPE = b'$'
CONTAINER_COUNT = b'#'

PY2 = version_info[0] < 3


class TestEncodeDecode(TestCase):

    @staticmethod
    def __formatInOut(obj, encoded):
        return '\nInput:\n%s\nOutput (%d):\n%s' % (pformat(obj), len(encoded), encoded)

    if PY2:  # pragma: no cover
        def typeCheck(self, actual, expected):
            self.assertEqual(actual, expected)
    else:
        def typeCheck(self, actual, expected):
            self.assertEqual(actual, ord(expected))

    def checkEncDec(self, obj,
                    # total length of encoded object
                    length=None,
                    # total length is at least the given number of bytes
                    lengthGreaterOrEqual=False,
                    # approximate comparison (e.g. for float)
                    equalDelta=None,
                    # type marker expected at start of encoded output
                    expectedType=None,
                    # additional arguments to pass to encoder
                    **kwargs):
        """Black-box test to check whether the provided object is the same once encoded and subsequently decoded."""
        encoded = ubjdumpb(obj, **kwargs)
        if expectedType is not None:
            self.typeCheck(encoded[0], expectedType)
        if length is not None:
            assertFunc = self.assertGreaterEqual if lengthGreaterOrEqual else self.assertEqual
            assertFunc(len(encoded), length, self.__formatInOut(obj, encoded))
        if equalDelta is not None:
            self.assertAlmostEqual(ubjloadb(encoded), obj, delta=equalDelta, msg=self.__formatInOut(obj, encoded))
        else:
            self.assertEqual(ubjloadb(encoded), obj, self.__formatInOut(obj, encoded))

    def test_noData(self):
        with self.assertRaises(DecoderException):
            ubjloadb(b'')

    def test_trailingInput(self):
        self.assertEqual(ubjloadb(TYPE_BOOL_TRUE * 10), True)

    def test_invalidMarker(self):
        with self.assertRaises(DecoderException):
            ubjloadb(b'A')

    def test_bool(self):
        self.assertEqual(ubjdumpb(True), TYPE_BOOL_TRUE)
        self.assertEqual(ubjdumpb(False), TYPE_BOOL_FALSE)
        self.checkEncDec(True, 1)
        self.checkEncDec(False, 1)

    def test_null(self):
        self.assertEqual(ubjdumpb(None), TYPE_NULL)
        self.checkEncDec(None, 1)

    def test_char(self):
        self.assertEqual(ubjdumpb(u('a')), TYPE_CHAR + 'a'.encode('utf-8'))
        # no char, char invalid utf-8
        for suffix in (b'', b'\xfe'):
            with self.assertRaises(DecoderException):
                ubjloadb(TYPE_CHAR + suffix)
        for char in (u('a'), u('\0'), u('~')):
            self.checkEncDec(char, 2)

    def test_string(self):
        self.assertEqual(ubjdumpb(u('ab')), TYPE_STRING + TYPE_UINT8 + b'\x02' + 'ab'.encode('utf-8'))
        self.checkEncDec(u(''), 3)
        # invalid string size, string too short, string invalid utf-8
        for suffix in (b'\x81', b'\x01', b'\x01' + b'\xfe'):
            with self.assertRaises(DecoderException):
                ubjloadb(TYPE_STRING + TYPE_INT8 + suffix)
        # Note: In Python 2 plain str type is encoded as byte array
        for string in ('some ascii', u('\u00a9 with extended\u2122'), u('long string') * 100):
            self.checkEncDec(string, 4, lengthGreaterOrEqual=True)

    def test_int(self):
        self.assertEqual(ubjdumpb(Decimal(-1.5)),
                         TYPE_HIGH_PREC + TYPE_UINT8 + b'\x04' + '-1.5'.encode('utf-8'))
        # insufficient length
        with self.assertRaises(DecoderException):
            ubjloadb(TYPE_INT16 + b'\x01')

        for type_, value, totalSize in (
                (TYPE_UINT8, 0, 2),
                (TYPE_UINT8, 255, 2),
                (TYPE_INT8, -128, 2),
                (TYPE_INT16, -32768, 3),
                (TYPE_INT16, 32767, 3),
                (TYPE_INT32, 2147483647, 5),
                (TYPE_INT32, -2147483648, 5),
                (TYPE_INT64, 9223372036854775807, 9),
                (TYPE_INT64, -9223372036854775808, 9),
                # HIGH_PREC (marker + length marker + length + value)
                (TYPE_HIGH_PREC, 9223372036854775808, 22),
                (TYPE_HIGH_PREC, -9223372036854775809, 23),
                (TYPE_HIGH_PREC, 9999999999999999999999999999999999999, 40)):
            self.checkEncDec(value, totalSize, expectedType=type_)

    def test_highPrecision(self):
        self.assertEqual(ubjdumpb(Decimal(-1.5)),
                         TYPE_HIGH_PREC + TYPE_UINT8 + b'\x04' + '-1.5'.encode('utf-8'))
        # insufficient length, invalid utf-8, invalid decimal value
        for suffix in (b'n', b'\xfe\xfe', b'na'):
            with self.assertRaises(DecoderException):
                ubjloadb(TYPE_HIGH_PREC + TYPE_UINT8 + b'\x02' + suffix)

        self.checkEncDec(1.8e315)
        for value in (
                0.0,
                2.5,
                'inf',
                '-inf',
                10e30,
                -1.2345e67890):
            # minimum length because: marker + length marker + length + value
            self.checkEncDec(Decimal(value), 4, lengthGreaterOrEqual=True)
        # cannot compare equality, so test separately
        self.assertTrue(ubjloadb(ubjdumpb(Decimal('nan'))).is_nan())  # pylint: disable=no-member

    def test_float(self):
        # insufficient length
        for fType in (TYPE_FLOAT32, TYPE_FLOAT64):
            with self.assertRaises(DecoderException):
                ubjloadb(fType + b'\x01')
        for type_, value, totalSize in (
                (TYPE_FLOAT32, 0.0, 5),
                (TYPE_FLOAT32, 1.18e-38, 5),
                (TYPE_FLOAT32, 3.4e38, 5),
                (TYPE_FLOAT64, 2.23e-308, 9),
                (TYPE_FLOAT64, 1.8e307, 9)):
            self.checkEncDec(value, totalSize, equalDelta=(0.0001 * abs(value)), expectedType=type_)

    def test_array(self):
        for sequence in list, tuple:
            self.assertEqual(ubjdumpb(sequence()), ARRAY_START + ARRAY_END)
        self.assertEqual(ubjdumpb((None,), container_count=True), (ARRAY_START + CONTAINER_COUNT + TYPE_UINT8 +
                                                                   b'\x01' + TYPE_NULL))
        obj = [123,
               1.25,
               Decimal('10e15'),
               'a',
               'here is a string',
               None,
               True,
               False,
               [[1, 2], 3, [4, 5, 6], 7],
               {'a dict': 456}]
        for opts in ({'container_count': False}, {'container_count': True}):
            self.checkEncDec(obj, **opts)

    def test_bytes(self):
        # insufficient length
        with self.assertRaises(DecoderException):
            ubjloadb(ARRAY_START + CONTAINER_TYPE + TYPE_UINT8 + CONTAINER_COUNT + TYPE_UINT8 + b'\x02' + b'\x01')
        self.checkEncDec(b'')
        self.checkEncDec(b'\x01' * 4)
        self.assertEqual(ubjloadb(ubjdumpb(b'\x04' * 4), no_bytes=True), [4] * 4)

    def test_container_fixed(self):
        rawStart = ARRAY_START + CONTAINER_TYPE + TYPE_INT8 + CONTAINER_COUNT + TYPE_UINT8
        self.assertEqual(ubjloadb(rawStart + b'\x00'), [])
        # fixed-type + count
        self.assertEqual(ubjloadb(ARRAY_START + CONTAINER_TYPE + TYPE_NULL + CONTAINER_COUNT + TYPE_UINT8 + b'\x05'),
                         [None] * 5)
        self.assertEqual(ubjloadb(rawStart + b'\x03' + (b'\x01' * 3)), [1, 1, 1])
        # invalid type
        with self.assertRaises(DecoderException):
            ubjloadb(ARRAY_START + CONTAINER_TYPE + b'\x01')
        # type without count
        with self.assertRaises(DecoderException):
            ubjloadb(ARRAY_START + CONTAINER_TYPE + TYPE_INT8 + b'\x01')

        rawStart = OBJECT_START + CONTAINER_TYPE + TYPE_INT8 + CONTAINER_COUNT + TYPE_UINT8
        self.assertEqual(ubjloadb(rawStart + b'\x00'), {})
        self.assertEqual(ubjloadb(rawStart + b'\x03' + (TYPE_UINT8 + b'\x02' + b'aa' + b'\x01' +
                                                        TYPE_UINT8 + b'\x02' + b'bb' + b'\x02' +
                                                        TYPE_UINT8 + b'\x02' + b'cc' + b'\x03')),
                         {'aa': 1, 'bb': 2, 'cc': 3})
        # fixed type + count
        self.assertEqual(ubjloadb(OBJECT_START + CONTAINER_TYPE + TYPE_NULL + CONTAINER_COUNT + TYPE_UINT8 + b'\x02' +
                                  TYPE_UINT8 + b'\x02' + b'aa' + TYPE_UINT8 + b'\x02' + b'bb'),
                         {'aa': None, 'bb': None})

    def test_object(self):
        self.assertEqual(ubjdumpb({}), OBJECT_START + OBJECT_END)
        self.assertEqual(ubjdumpb({'a': None}, container_count=True), (OBJECT_START + CONTAINER_COUNT + TYPE_UINT8 +
                                                                       b'\x01' + TYPE_UINT8 + b'\x01' +
                                                                       'a'.encode('utf-8') + TYPE_NULL))
        self.checkEncDec({})
        with self.assertRaises(EncoderException):
            ubjdumpb({123: 'non-string key'})
        with self.assertRaises(EncoderException):
            ubjdumpb({'fish': type(list)})
        # invalid key size type
        with self.assertRaises(DecoderException):
            ubjloadb(OBJECT_START + TYPE_NULL)
        # invalid key size, key too short, key invalid utf-8, no value
        for suffix in (b'\x81', b'\x01', b'\x01' + b'\xfe', b'\x0101'):
            with self.assertRaises(DecoderException):
                ubjloadb(OBJECT_START + TYPE_INT8 + suffix)
        self.checkEncDec({'longkey1' * 65: 1})
        self.checkEncDec({'longkey2' * 4096: 1})

        obj = {'int': 123,
               'longint': 9223372036854775807,
               'float': 1.25,
               'hp': Decimal('10e15'),
               'char': 'a',
               'str': 'here is a string',
               'unicode': u('\u00a9 with extended\u2122'),
               u('\u00a9 with extended\u2122'): 'unicode-key',
               'null': None,
               'true': True,
               'false': False,
               'array': [1, 2, 3],
               'bytes_array': b'1234',
               'object': {'another one': 456, 'yet another': {'abc': True}}}
        for opts in ({'container_count': False}, {'container_count': True}):
            self.checkEncDec(obj, **opts)

        # dictionary key sorting
        obj1 = OrderedDict.fromkeys('abc')
        obj2 = OrderedDict.fromkeys('cba')
        self.assertNotEqual(ubjdumpb(obj1), ubjdumpb(obj2))
        self.assertEqual(ubjdumpb(obj1, sort_keys=True), ubjdumpb(obj2, sort_keys=True))

    def test_circular(self):
        sequence = [1, 2, 3]
        sequence.append(sequence)
        mapping = {'a': 1, 'b': 2}
        mapping['c'] = mapping

        for container in (sequence, mapping):
            with self.assertRaises(EncoderException):
                ubjdumpb(container)

        # Refering to the same container multiple times is valid however
        sequence = [1, 2, 3]
        mapping = {'a': 1, 'b': 2}
        self.checkEncDec([sequence, mapping, sequence, mapping])

    def test_unencodable(self):
        with self.assertRaises(EncoderException):
            ubjdumpb(type(None))

    def test_decoder_fuzz(self):
        for start, end, fmt in ((0, pow(2, 8), '>B'), (pow(2, 8), pow(2, 16), '>H')):
            for i in range(start, end):
                try:
                    ubjloadb(pack(fmt, i))
                except DecoderException:
                    pass
                except Exception as e:  # pragma: no cover  pylint: disable=broad-except
                    self.fail('Unexpected failure: %s' % e)

    def test_fp(self):
        obj = {"a": 123, "b": 456}
        output = BytesIO()
        ubjdump({"a": 123, "b": 456}, output)
        self.assertEqual(ubjloadb(output.getvalue()), obj)