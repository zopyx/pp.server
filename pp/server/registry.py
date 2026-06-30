################################################################
# pp.server - Produce & Publish Server
# (C) 2021, ZOPYX,  Tuebingen, Germany
################################################################

import asyncio
from typing import Any

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
    if which(converter_cmd) or which(f"bin/{converter_name}"):
        REGISTRY[converter_name] = True
    if REGISTRY[converter_name]:
        LOG.info(f"Converter {converter_name} registered")


def available_converters() -> list[str]:
    """Return list of available converter names"""
    return sorted([c for c in REGISTRY if REGISTRY[c]])


def has_converter(converter_name: str) -> bool:
    """Check if a given converter name is registered"""
    return converter_name in available_converters()


def get_converter_registry() -> dict[str, bool]:
    """Return the converter registry"""
    return REGISTRY


async def converter_versions() -> dict[str, str]:
    """Run the --version command for every registered converter"""

    async def execute_cmd(converter: str, cmd: str) -> dict[str, Any]:
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

    versions: dict[str, str] = {}
    for conv_result in results:
        if isinstance(conv_result, BaseException):
            LOG.warning(f"Converter version check failed: {conv_result}")
            continue  # Skip failed converters

        conv_name: str = conv_result["converter"]
        status_val: int | None = conv_result["result"]["status"]
        stdout_val = str(conv_result["result"].get("stdout", "") or "")
        stderr_val = str(conv_result["result"].get("stderr", "") or "")
        output = (stdout_val + stderr_val).strip()
        versions[conv_name] = output if status_val == 0 else "n/a"

    return versions


def main() -> None:
    _register_converters()
    print(available_converters())


if __name__ == "__main__":
    main()
