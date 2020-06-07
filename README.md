# Binary JData for Python - a lightweight binary JSON format

- Copyright: (C) Qianqian Fang (2020) <q.fang at neu.edu>
- Copyright: (C) Iotic Labs Ltd. (2019) <vilnis.termanis at iotic-labs.com>
- License: Apache License, Version 2.0
- Version: 0.2
- URL: https://github.com/fangq/pybj


This is a Python v3.2+ (and 2.7+) [Binary JData](http://openjdata.org) based on 
the [Draft-1](Binary_JData_Specification.md) specification.

## Installing / packaging
```shell
## To get from PyPI
pip3 install bjdata

## To only build extension modules inline (e.g. in repository)
python3 setup.py build_ext -i

## To build & install globally
python3 setup.py install

## To skip building of extensions when installing (or building)
PYBJDATA_NO_EXTENSION=1 python3 setup.py install
```

**Notes**

- The extension module is not required but provide a significant speed boost.
- The above can also be run with v2.7+
- At run time, one can check whether compiled version is in use via the 
_bjdata.EXTENSION_ENABLED_ boolean


## Usage
It's meant to behave very much like Python's built-in 
[JSON module](https://docs.python.org/3/library/json.html), e.g.:
```python
import bjdata as bj

encoded = bj.dumpb({u'a': 1})

decoded = bj.loadb(encoded)
```
**Note**: Only unicode strings in Python 2 will be encoded as strings, plain *str* 
will be encoded as a byte array.


## Documentation
```python
import bjdata
help(bjdata.dump)
help(bjdata.load)
```

## Command-line utility
This converts between JSON and BJData formats:
```shell
python3 -mbjdata
USAGE: bjdata (fromjson|tojson) (INFILE|-) [OUTFILE]
```


## Tests

### Static
This library has been checked using [flake8](https://pypi.python.org/pypi/flake8) 
and [pylint](http://www.pylint.org), using a modified configuration - 
see _pylint.rc_ and _flake8.cfg_.

### Unit
```shell
python3 -mvenv py
. py/bin/activate
pip install -U pip setuptools
pip install -e .[dev]

./coverage_test.sh
```
**Note**: See `coverage_test.sh` for additional requirements.


## Limitations
- The **No-Op** type is only supported by the decoder. (This should arguably be 
  a protocol-level rather than serialisation-level option.) Specifically, it is 
  **only** allowed to occur at the start or between elements of a container and 
  **only** inside un-typed containers. (In a typed container it is impossible to 
  tell the difference between an encoded element and a No-Op.)
- Strongly-typed containers are only supported by the decoder (apart from for 
  **bytes**/**bytearray**) and not for No-Op.
- Encoder/decoder extensions are not supported at this time.


## Acknowledgement

This package was modified based on the py-ubjson package developed by
[Iotic Labs Ltd.](https://www.iotics.com/) 
Project URL: https://github.com/Iotic-Labs/py-ubjson

The major changes were focused on supporting the Binary JData Specification 
[Draft 1](Binary_JData_Specification.md) - an extended Universal Binary JSON 
(UBJSON) Specification Draft-12 by adding the below new features:

* BJData adds 4 new numeric data types: `uint16 [u]`, `uint32 [m]`, `uint64 [M]` 
  and `float16 [h]`
* BJData supports an optimized ND array container
* BJData does not convert NaN/Inf/-Inf to `null`
