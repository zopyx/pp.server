# -*- coding: utf-8 -*-

import os
from pdb import Pdb

from pp.server.util import which
from pp.server.util import runcmd
from pp.server.converters import CONVERTERS

REGISTRY = dict()


def _register_converters():
    """ Register all known converters """

    for converter, converter_config in CONVERTERS.items():
        register_converter(converter, converter_config["cmd"])


def register_converter(converter_name: str, converter_cmd: str):
    """Check if particular converter can be find through its `converter_cmd`
    directly in the $PATH or some `bin/` path.
    """

    REGISTRY[converter_name] = False
    if which(converter_cmd):
        REGISTRY[converter_name] = True
    elif which(f"bin/{converter_name}"):
        REGISTRY[converter_name] = True


def available_converters() -> [str]:
    """ Return list of available converter names """
    return sorted(list([c for c in REGISTRY if REGISTRY[c]]))


def has_converter(converter_name: str) -> bool:
    """ Check if a given converter name is registered """
    return converter_name in available_converters()


def get_converter_registry():
    """ Return the converter registry """
    return REGISTRY


def converter_versions():

    result = dict()

    for converter in available_converters():
        converter_config = CONVERTERS[converter]
        status, output = runcmd(converter_config["version"])
        result[converter] = output if status == 0 else "n/a"

    return result


def main():
    _register_converters()
    print(available_converters())


if __name__ == "__main__":
    main()
