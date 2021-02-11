# -*- coding: utf-8 -*-


import os
from pdb import Pdb

from pp.server.util import which
from pp.server.util import runcmd

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

    if REGISTRY["prince"]:
        status, output = runcmd("prince --version")
        result["prince"] = output if status == 0 else "n/a"

    if REGISTRY["pdfreactor"]:
        status, output = runcmd("pdfreactor.py --version")
        result["pdfreactor"] = output if status == 0 else "n/a"

    if REGISTRY["phantomjs"]:
        status, output = runcmd("phantomjs --version")
        result["phantomjs"] = output if status == 0 else "n/a"

    if REGISTRY["calibre"]:
        status, output = runcmd("ebook-convert --version")
        result["calibre"] = output if status == 0 else "n/a"

    if REGISTRY["vivliostyle"]:
        status, output = runcmd("vivliostyle-formatter --version".format(vivlio))
        result["vivliostyle"] = output if status == 0 else "n/a"

    if REGISTRY["versatype"]:
        status, output = runcmd("versatype-formatter --version")
        result["versatype"] = output if status == 0 else "n/a"

    if REGISTRY["antennahouse"]:
        status, output = runcmd("run.sh -v")
        result["antennahouse"] = output if status == 0 else "n/a"

    if REGISTRY["speedata"]:
        status, output = runcmd("sp --version")
        result["publisher"] = output if status == 0 else "n/a"

    if REGISTRY["weasyprint"]:
        status, output = runcmd("weasyprint --version")
        result["weasyprint"] = output if status == 0 else "n/a"

    if REGISTRY["pagedjs"]:
        status, output = runcmd("pagedjs-cli --version")
        result["pagedjs-cli"] = output if status == 0 else "n/a"

    if REGISTRY["typesetsh"]:
        status, output = runcmd("typeset.sh.phar --version")
        result["typeset.sh"] = output if status == 0 else "n/a"

    return result


def main():
    _register_converters()
    print(available_converters())


if __name__ == "__main__":
    main()