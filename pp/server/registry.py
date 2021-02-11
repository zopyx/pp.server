# -*- coding: utf-8 -*-


import os

from pp.server.util import which

REGISTRY = dict()


def _register_converters():
    """ Register all known converters """

    register_converter("pdfreactor", "pdfreactor.py")
    register_converter("prince", "prince")
    register_converter("phantomjs", "phantomjs")
    register_converter("speedata", "sp")
    register_converter("weasyprint", "weasyprint")
    register_converter("vivliostyle", "vivliostyle-formatter")
    register_converter("versatype", "versatype-converter")
    register_converter("antennahouse", "run.sh")
    register_converter("calibre", "ebook-convert")
    register_converter("typesetsh", "typeset.sh.phar")
    register_converter("pagedjs", "pagedjs-cli")


def register_converter(converter_name: str, converter_cmd: str):
    """Check if particular converter can be find through its `converter_cmd`
    directly in the $PATH or some `bin/` path.
    """

    if which(converter_cmd):
        REGISTRY[converter_name] = True
    elif which(f"bin/{converter_name}"):
        REGISTRY[converter_name] = True


def available_converters() -> [str]:
    """ Return list of available converter names """
    return list(REGISTRY.keys())


def has_converter(converter_name: str) -> bool:
    """ Check if a given converter name is registered """
    return converter_name in available_converters


def get_converter_registry():
    """ Return the converter registry """
    return REGISTRY


def main():
    _register_converters()
    print(available_converters())


if __name__ == "__main__":
    main()