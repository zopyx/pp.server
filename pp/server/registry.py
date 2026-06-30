"""Converter registry — detect and manage available PDF converters.

Scans the system PATH for known converter binaries and maintains
a registry of which converters are available. Provides async
version detection for all registered converters.
"""

import asyncio
from typing import Any

from pp.server.converters import CONVERTERS
from pp.server.logger import LOG
from pp.server.util import run, which

REGISTRY: dict[str, bool] = {}


def _register_converters() -> None:
    """Register all converters found in the configuration.

    Iterates over ``CONVERTERS`` and calls :func:`register_converter`
    for each one, checking if the binary is present in the system PATH.
    """
    for converter, converter_config in CONVERTERS.items():
        register_converter(converter, converter_config["cmd"])


def register_converter(converter_name: str, converter_cmd: str) -> None:
    """Check if a converter binary is available and register its status.

    Looks for the binary in the system PATH, and as a fallback in a
    ``bin/`` subdirectory named after the converter.

    Args:
        converter_name: Logical name (e.g. ``prince``, ``weasyprint``).
        converter_cmd: Binary name to search for (e.g. ``prince``).
    """
    REGISTRY[converter_name] = False
    if which(converter_cmd) or which(f"bin/{converter_name}"):
        REGISTRY[converter_name] = True
    if REGISTRY[converter_name]:
        LOG.info(f"Converter {converter_name} registered")


def available_converters() -> list[str]:
    """Return alphabetically sorted names of all available converters.

    Returns:
        List of converter names whose binaries were found in PATH.
    """
    return sorted([c for c in REGISTRY if REGISTRY[c]])


def has_converter(converter_name: str) -> bool:
    """Check if a specific converter is registered and available.

    Args:
        converter_name: Converter name to check.

    Returns:
        True if the converter binary was found.
    """
    return converter_name in available_converters()


def get_converter_registry() -> dict[str, bool]:
    """Return the raw converter registry dictionary.

    Returns:
        Mapping of converter name to availability status.
    """
    return REGISTRY


async def converter_versions() -> dict[str, str]:
    """Run ``--version`` for every registered converter in parallel.

    Executes all version commands concurrently using ``asyncio.gather``.
    Converters whose version command fails (non-zero exit or exception)
    are reported as ``n/a``.

    Returns:
        Dictionary mapping converter name to version string or ``n/a``.
    """

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
    """Print list of available converters to stdout.

    Useful for manual inspection::

        python -m pp.server.registry
    """
    _register_converters()
    print(available_converters())


if __name__ == "__main__":
    main()
