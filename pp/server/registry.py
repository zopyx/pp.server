################################################################
# pp.server - Produce & Publish Server
# (C) 2021, ZOPYX,  Tuebingen, Germany
################################################################

import asyncio
from typing import Dict, List, Any

from pp.server.converters import CONVERTERS
from pp.server.logger import LOG
from pp.server.util import run, which

REGISTRY = dict()


def _register_converters() -> None:
    """Register all known converters"""

    for converter, converter_config in CONVERTERS.items():
        register_converter(converter, converter_config["cmd"])


def register_converter(converter_name: str, converter_cmd: str) -> None:
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


def available_converters() -> List[str]:
    """Return list of available converter names"""
    return sorted(list([c for c in REGISTRY if REGISTRY[c]]))


def has_converter(converter_name: str) -> bool:
    """Check if a given converter name is registered"""
    return converter_name in available_converters()


def get_converter_registry() -> Dict[str, bool]:
    """Return the converter registry"""
    return REGISTRY


async def converter_versions() -> Dict[str, str]:
    """Run the --version command for every registered converter"""

    async def execute_cmd(converter: str, cmd: str) -> Dict[str, Any]:
        result = await run(cmd)
        return dict(result=result, converter=converter)

    # Create tasks for all converters
    tasks = []
    for converter in available_converters():
        converter_config = CONVERTERS[converter]
        task = execute_cmd(converter, converter_config["version"])
        tasks.append(task)

    # Run all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    versions = dict()
    for result in results:
        if isinstance(result, Exception):
            continue  # Skip failed converters

        converter = result["converter"]
        status = result["result"]["status"]
        output = result["result"]["stdout"] + result["result"]["stderr"]
        output = output.strip()
        versions[converter] = output if status == 0 else "n/a"

    return versions


def main() -> None:
    _register_converters()
    print(available_converters())


if __name__ == "__main__":
    main()
