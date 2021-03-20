# -*- coding: utf-8 -*-

################################################################
# pp.server - Produce & Publish Server
# (C) 2021, ZOPYX,  Tuebingen, Germany
################################################################

import os
import asyncio

from pp.server.util import which
from pp.server.util import run
from pp.server.logger import LOG
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
    if REGISTRY[converter_name]:
        LOG.info(f"Converter {converter_name} registered")


def available_converters() -> [str]:
    """ Return list of available converter names """
    return sorted(list([c for c in REGISTRY if REGISTRY[c]]))


def has_converter(converter_name: str) -> bool:
    """ Check if a given converter name is registered """
    return converter_name in available_converters()


def get_converter_registry():
    """ Return the converter registry """
    return REGISTRY


async def converter_versions():
    """ Run the --version command for every registered converter """

    async def execute_cmd(converter, cmd, future):
        result = await run(cmd)
        future.set_result(dict(result=result, converter=converter))

    loop = asyncio.get_event_loop()

    tasks = []
    futures = []
    for converter in available_converters():
        converter_config = CONVERTERS[converter]
        future = asyncio.Future()
        futures.append(future)
        task = loop.create_task(execute_cmd(converter, converter_config["version"], future))
        tasks.append(task)

    await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)

    versions = dict()
    for f in futures:
        result = f.result()
        converter = result["converter"]
        status = result["result"]["status"]
        output = result["result"]["stdout"] + result["result"]["stderr"]
        versions[converter] = output if status == 0 else "n/a"

    return versions


def main():
    _register_converters()
    print(available_converters())


if __name__ == "__main__":
    main()
