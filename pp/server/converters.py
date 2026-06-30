"""PDF/EPUB conversion orchestration and converter configuration.

Loads converter definitions from ``config.toml``, manages ZIP extraction
with path traversal protection and resource limits, and provides the
core ``convert_pdf`` and ``selftest`` async functions used by the API routes.
"""

import importlib.util
import os
import pkgutil
import shutil
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore[import-not-found, no-redef]  # ty: ignore

from pp.server import util
from pp.server.logger import LOG
from pp.server.util import parse_cmd_options

# ---------------------------------------------------------------------------
# Configurable resource limits (overridable via environment variables)
# ---------------------------------------------------------------------------
# Maximum size of the base64-decoded ZIP payload (bytes)
_MAX_ZIP_SIZE = int(os.environ.get("PP_MAX_ZIP_SIZE", str(100 * 1024 * 1024)))  # 100 MB
# Maximum number of entries in a ZIP archive
_MAX_ZIP_ENTRIES = int(os.environ.get("PP_MAX_ZIP_ENTRIES", "1000"))
# Maximum total uncompressed size across all ZIP entries (bytes)
_MAX_ZIP_TOTAL_UNCOMPRESSED = int(
    os.environ.get("PP_MAX_ZIP_TOTAL_UNCOMPRESSED", str(500 * 1024 * 1024))  # 500 MB
)
# Maximum uncompressed size for a single ZIP entry (bytes)
_MAX_ZIP_FILE_SIZE = int(
    os.environ.get("PP_MAX_ZIP_FILE_SIZE", str(100 * 1024 * 1024))  # 100 MB
)
# Maximum path length for extracted entries
_MAX_ZIP_PATH_LENGTH = int(os.environ.get("PP_MAX_ZIP_PATH_LENGTH", "255"))
# Conversion subprocess timeout (seconds)
_CONVERSION_TIMEOUT = int(
    os.environ.get("PP_CONVERSION_TIMEOUT_SECONDS", "300")
)  # 5 minutes

# Extra environment variables to pass to converter subprocesses
_CONVERTER_EXTRA_ENV = os.environ.get("PP_CONVERTER_EXTRA_ENV", "")
_CONVERTER_EXTRA_ENV_SET = (
    set(_CONVERTER_EXTRA_ENV.split(",")) if _CONVERTER_EXTRA_ENV else set()
)


def load_config() -> dict[str, Any]:
    """Load converter configuration from ``config.toml``.

    Returns:
        Dictionary with a ``converters`` key mapping converter names
        to their command definitions. Returns an empty dict on error.
    """
    config_path = Path(__file__).parent / "config.toml"
    try:
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        LOG.error(f"Configuration file not found: {config_path}")
        return {"converters": {}}
    except Exception as e:
        LOG.error(f"Error loading configuration: {e}")
        return {"converters": {}}


# Load converters from config file
config = load_config()
CONVERTERS = config.get("converters", {})


# ---------------------------------------------------------------------------
# ZIP resource limit helpers
# ---------------------------------------------------------------------------


class ZipLimitError(Exception):
    """Raised when a ZIP archive violates a configured resource limit."""

    def __init__(self, message: str, code: str = "payload_too_large") -> None:
        self.code = code
        super().__init__(message)


class ZipValidationError(Exception):
    """Raised when a ZIP archive contains unsafe or malformed entries."""


def _validate_zip_resources(zf: zipfile.ZipFile, payload_size: int) -> None:
    """Validate a ZIP archive against configured resource limits.

    Checks are performed in order of cheapest-to-most-expensive to fail
    fast on clearly invalid archives.

    Args:
        zf: Opened ZIP file handle.
        payload_size: Size of the decoded ZIP payload in bytes.

    Raises:
        ZipLimitError: If any resource limit is exceeded.
    """
    if payload_size > _MAX_ZIP_SIZE:
        raise ZipLimitError(
            f"ZIP payload size {payload_size} exceeds limit {_MAX_ZIP_SIZE} bytes",
            code="payload_too_large",
        )

    infolist = zf.infolist()

    if len(infolist) > _MAX_ZIP_ENTRIES:
        raise ZipLimitError(
            f"ZIP contains {len(infolist)} entries, exceeds "
            f"limit of {_MAX_ZIP_ENTRIES}",
            code="too_many_entries",
        )

    total_uncompressed = 0
    info: zipfile.ZipInfo
    for info in infolist:
        if info.file_size > _MAX_ZIP_FILE_SIZE:
            raise ZipLimitError(
                f"ZIP entry {info.filename!r} has uncompressed size "
                f"{info.file_size} which exceeds limit "
                f"{_MAX_ZIP_FILE_SIZE} bytes",
                code="entry_too_large",
            )
        if len(info.filename) > _MAX_ZIP_PATH_LENGTH:
            raise ZipLimitError(
                f"ZIP entry path length {len(info.filename)} exceeds "
                f"limit of {_MAX_ZIP_PATH_LENGTH} chars: {info.filename!r}",
                code="path_too_long",
            )
        total_uncompressed += info.file_size

    if total_uncompressed > _MAX_ZIP_TOTAL_UNCOMPRESSED:
        raise ZipLimitError(
            f"ZIP total uncompressed size {total_uncompressed} exceeds "
            f"limit {_MAX_ZIP_TOTAL_UNCOMPRESSED} bytes",
            code="total_uncompressed_too_large",
        )


# ---------------------------------------------------------------------------
# ZIP extraction with safety
# ---------------------------------------------------------------------------


def _extract_safely(zf: zipfile.ZipFile, work_dir: Path) -> None:
    """Extract ZIP entries safely, preventing directory traversal.

    Rejects entries whose resolved path falls outside the target
    ``work_dir``, blocking attacks like ``../../etc/passwd``.

    Args:
        zf: Opened ZIP file handle.
        work_dir: Directory to extract into.
    """
    work_dir_resolved = work_dir.resolve()
    actual_total = 0
    for info in zf.infolist():
        name = info.filename
        target = (work_dir / name).resolve()
        is_within = str(target).startswith(str(work_dir_resolved) + "/") or (
            target == work_dir_resolved
        )
        if not is_within:
            raise ZipValidationError(f"ZIP entry escapes extraction directory: {name}")
        if name.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            actual_file_size = 0
            with zf.open(info) as src, target.open("wb") as dst:
                while chunk := src.read(1024 * 1024):
                    actual_file_size += len(chunk)
                    actual_total += len(chunk)
                    if actual_file_size > _MAX_ZIP_FILE_SIZE:
                        raise ZipLimitError(
                            f"ZIP entry {name!r} extracted size exceeds "
                            f"limit {_MAX_ZIP_FILE_SIZE} bytes",
                            code="entry_too_large",
                        )
                    if actual_total > _MAX_ZIP_TOTAL_UNCOMPRESSED:
                        raise ZipLimitError(
                            f"ZIP extracted size exceeds total limit "
                            f"{_MAX_ZIP_TOTAL_UNCOMPRESSED} bytes",
                            code="total_uncompressed_too_large",
                        )
                    dst.write(chunk)


# ---------------------------------------------------------------------------
# Argv building helpers
# ---------------------------------------------------------------------------


def _build_convert_argv(
    convert_args: list[str],
    cmd_option_tokens: list[str],
    **fmt_kwargs: str,
) -> list[str]:
    """Build an argv list from a converter template.

    The special placeholder ``{cmd_options}`` is expanded into the
    individual tokens from *cmd_option_tokens*. Other placeholders
    (e.g. ``{source_html}``, ``{target_filename}``) are replaced
    via ``str.format()``.

    Args:
        convert_args: Template argv list from converter config.
        cmd_option_tokens: User-supplied option tokens (from
            :func:`util.parse_cmd_options`).
        **fmt_kwargs: Values for non-command-option placeholders.

    Returns:
        Completed argv list suitable for :func:`util.run`.
    """
    argv: list[str] = []
    for arg in convert_args:
        if arg == "{cmd_options}":
            argv.extend(cmd_option_tokens)
        else:
            argv.append(arg.format(**fmt_kwargs))
    return argv


# ---------------------------------------------------------------------------
# Resource loading
# ---------------------------------------------------------------------------


def load_resource(package: str, resource_name: str) -> bytes:
    """Load a package resource as bytes.

    See :func:`pp.server.templates.load_resource` for details.
    """
    data = pkgutil.get_data(package, resource_name)  # type: ignore[name-defined]
    assert data is not None, f"Resource {package}/{resource_name} not found"
    return data


# ---------------------------------------------------------------------------
# Core conversion
# ---------------------------------------------------------------------------


async def convert_pdf(
    work_dir: str,
    work_file: str,
    converter: str,
    logger: Callable[[str], None],
    cmd_options: str,
    source_filename: str = "index.html",
) -> dict[str, Any]:
    """Convert a ZIP archive to PDF/EPUB using the specified converter.

    Unpacks the ZIP into a working directory, validates resource limits,
    runs the converter command via ``create_subprocess_exec`` (no shell),
    and returns the result.

    Args:
        work_dir: Temporary working directory path.
        work_file: Path to the uploaded ZIP file.
        converter: Name of the converter to use (must be in CONVERTERS).
        logger: Callback for per-conversion log messages.
        cmd_options: Additional command-line options (parsed with
            :func:`util.parse_cmd_options`).
        source_filename: Entry point HTML (or XML) file in the ZIP.

    Returns:
        Dictionary with ``status`` (exit code or 9999 for unknown converter),
        ``output`` (combined stdout+stderr), and ``filename`` (output path).
    """
    # Avoid circular import
    from pp.server.registry import has_converter

    # Check converter availability early
    if not has_converter(converter):
        return dict(
            status=9999,
            output=f'Unknown converter "{converter}"',
            filename="",
        )

    # Parse and validate cmd_options
    cmd_option_tokens = parse_cmd_options(cmd_options)

    # Unzip archive with resource limits
    work_dir_path = Path(work_dir)
    zf = zipfile.ZipFile(work_file)
    payload_size = Path(work_file).stat().st_size

    try:
        _validate_zip_resources(zf, payload_size)
        _extract_safely(zf, work_dir_path)
    except ZipLimitError as e:
        zf.close()
        LOG.warning(f"ZIP resource limit exceeded: {e}")
        return dict(status=9989, output=str(e), filename="")
    except (ZipValidationError, zipfile.BadZipFile) as e:
        zf.close()
        LOG.warning(f"ZIP validation failed: {e}")
        return dict(status=9988, output=str(e), filename="")

    zf.close()

    source_html = work_dir_path / source_filename

    if converter == "calibre":
        target_filename = work_dir_path / "out" / "out.epub"
    else:
        target_filename = work_dir_path / "out" / "out.pdf"

    # Required for PDFreactor 12+
    base_url = f"file://{work_dir}/"

    converter_config = CONVERTERS[converter]

    # Determine which args template to use (docker variant or standard)
    is_docker = converter == "pdfreactor" and "PP_PDFREACTOR_DOCKER" in os.environ

    if is_docker:
        docker_args_key = "convert_docker_args"
        if docker_args_key not in converter_config:
            msg = f"Converter {converter!r} has no argv docker command configured"
            LOG.error(msg)
            return dict(status=9998, output=msg, filename="")
        parts = work_dir.split("/")
        source_docker_html = f"file:///docs/{parts[-1]}/index.html"
        argv = _build_convert_argv(
            converter_config[docker_args_key],
            cmd_option_tokens,
            target_filename=str(target_filename),
            source_docker_html=source_docker_html,
        )
    else:
        args_key = "convert_args"
        if args_key not in converter_config:
            msg = f"Converter {converter!r} has no argv command configured"
            LOG.error(msg)
            return dict(status=9998, output=msg, filename="")
        argv = _build_convert_argv(
            converter_config[args_key],
            cmd_option_tokens,
            source_html=str(source_html),
            target_filename=str(target_filename),
            work_dir=str(work_dir_path),
            base_url=base_url,
        )

    # Run via argv (no shell)
    extra_env: dict[str, str] = {}
    if "PP_PDFREACTOR_DOCKER" in os.environ:
        extra_env["PP_PDFREACTOR_DOCKER"] = os.environ["PP_PDFREACTOR_DOCKER"]
    for env_name in _CONVERTER_EXTRA_ENV_SET:
        if env_name in os.environ:
            extra_env[env_name] = os.environ[env_name]

    logger(f"CMD: {' '.join(str(a) for a in argv)}")

    try:
        result = await util.run(
            argv,
            cwd=str(work_dir_path),
            timeout=_CONVERSION_TIMEOUT,
            extra_env=extra_env if extra_env else None,
        )
    except TimeoutError:
        msg = f"Conversion timed out after {_CONVERSION_TIMEOUT}s"
        logger(msg)
        LOG.warning(msg)
        return dict(status=9997, output=msg, filename="")

    _log_and_return(result, logger)
    return _format_result(result, str(target_filename))


def _log_and_return(result: dict[str, Any], logger: Callable[[str], None]) -> None:
    """Log conversion result via the job logger."""
    status = result["status"]
    output = str(result.get("stdout", "") or "") + str(result.get("stderr", "") or "")
    logger(f"STATUS: {status}")
    logger("OUTPUT")
    logger(output)


def _format_result(result: dict[str, Any], target_filename: str) -> dict[str, Any]:
    """Normalize a raw run() result into the conversion result dict."""
    status = result["status"]
    output = str(result.get("stdout", "") or "") + str(result.get("stderr", "") or "")
    return dict(status=status, output=output, filename=target_filename)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


async def selftest(converter: str) -> bytes:
    """Run a self-test for the given converter.

    Creates a temporary directory, copies sample HTML content,
    runs the converter, and returns the generated PDF (or EPUB
    for Calibre) as bytes.

    Args:
        converter: Name of the converter to test.

    Returns:
        Raw PDF or EPUB bytes.

    Raises:
        AssertionError: If test data resources are not found.
        FileNotFoundError: If the converter binary or output is missing.
        OSError: On filesystem-level errors during the test.
    """
    work_dir = Path(tempfile.mkdtemp(prefix="pp-server-selftest-"))
    try:
        # copy HTML sample from test_data directory
        resource_root = importlib.util.find_spec("pp.server.test_data")
        assert resource_root is not None and resource_root.origin is not None, (
            "pp.server.test_data spec not found"
        )
        resource_dir = Path(resource_root.origin).parent / "html"
        source_html = work_dir / "index.html"
        target_filename = work_dir / "out.pdf"
        # required for PDFreactor 12+
        base_url = f"file://{work_dir}/"

        if converter == "calibre":
            target_filename = work_dir / "out.epub"
        elif converter == "speedata":
            source_html = work_dir / "index.xml"
            resource_dir = Path(resource_root.origin).parent / "speedata"

        shutil.copytree(str(resource_dir), str(work_dir), dirs_exist_ok=True)

        converter_config = CONVERTERS[converter]

        args_key = "convert_args"
        if args_key not in converter_config:
            msg = f"Converter {converter!r} has no argv command configured"
            raise RuntimeError(msg)
        argv = _build_convert_argv(
            converter_config[args_key],
            [],  # no cmd_options for selftest
            source_html=str(source_html),
            target_filename=str(target_filename),
            work_dir=str(work_dir),
            base_url=base_url,
        )
        LOG.info(f"CMD: {' '.join(str(a) for a in argv)}")
        result = await util.run(argv, cwd=str(work_dir), timeout=_CONVERSION_TIMEOUT)

        output = str(result.get("stdout", "") or "") + str(
            result.get("stderr", "") or ""
        )
        LOG.info(f"STATUS: {result['status']}")
        LOG.info("OUTPUT")
        LOG.info(output)

        # return PDF data as bytes
        pdf_data = Path(target_filename).read_bytes()
        return pdf_data
    finally:
        # Cleanup temp directory on success or failure
        shutil.rmtree(str(work_dir), ignore_errors=True)
