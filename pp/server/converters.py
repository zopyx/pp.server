################################################################
# pp.server - Produce & Publish Server
# (C) 2021, ZOPYX,  Tuebingen, Germany
################################################################

import os
import shutil
import tempfile
import zipfile
from pathlib import Path
import importlib.util
import pkgutil
from typing import Dict, Any, Callable

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # fallback for older Python versions

from pp.server import util
from pp.server.logger import LOG


def load_config() -> Dict[str, Any]:
    """Load configuration from config.toml file."""
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


def load_resource(package: str, resource_name: str) -> bytes:
    data = pkgutil.get_data(package, resource_name)
    return data


async def convert_pdf(
    work_dir: str,
    work_file: str,
    converter: str,
    logger: Callable[[str], None],
    cmd_options: str,
    source_filename: str = "index.html",
) -> Dict[str, Any]:
    """Converter a given ZIP file
    containing input files (HTML + XML) and asset files
    to PDF.
    """

    # avoid circular import
    from pp.server.registry import has_converter

    # unzip archive first
    work_dir_path = Path(work_dir)
    zf = zipfile.ZipFile(work_file)
    for name in zf.namelist():
        filename = work_dir_path / name
        filename.parent.mkdir(parents=True, exist_ok=True)
        filename.write_bytes(zf.read(name))

    source_html = work_dir_path / source_filename

    if converter == "calibre":
        target_filename = work_dir_path / "out" / "out.epub"
    else:
        target_filename = work_dir_path / "out" / "out.pdf"

    # required for PDFreactor 12+
    base_url = f"file://{work_dir}/"

    if not has_converter(converter):
        return dict(status=9999, output=f'Unknown converter "{converter}"')

    converter_config = CONVERTERS[converter]

    if converter == "pdfreactor" and "PP_PDFREACTOR_DOCKER" in os.environ:
        # PDFreactor running on Docker requires special trickery
        # We assume that the /docs volume of the PDFreactor container is mounted into the local
        # filesystem.
        cmd = converter_config["convert_docker"]
        parts = work_dir.split("/")
        source_docker_html = f"file:///docs/{parts[-1]}/index.html"
        cmd = cmd.format(
            cmd_options=cmd_options,
            target_filename=str(target_filename),
            source_docker_html=source_docker_html,
        )
    else:
        cmd = converter_config["convert"]
        cmd = cmd.format(
            cmd_options=cmd_options,
            work_dir=str(work_dir_path),
            target_filename=str(target_filename),
            source_html=str(source_html),
            base_url=base_url,
        )

    logger(f"CMD: {cmd}")
    result = await util.run(cmd)
    status = result["status"]
    output = result["stdout"] + result["stderr"]

    logger(f"STATUS: {result['status']}")
    logger("OUTPUT")
    logger(output)

    return dict(status=status, output=output, filename=str(target_filename))


async def selftest(converter: str) -> bytes:
    """Converter self test"""

    # created work directory
    work_dir = Path(tempfile.mktemp())

    # copy HTML sample from test_data directory
    resource_root = importlib.util.find_spec("pp.server.test_data").origin
    resource_dir = Path(resource_root).parent / "html"
    source_html = work_dir / "index.html"
    target_filename = work_dir / "out.pdf"
    # required for PDFreactor 12+
    base_url = f"file://{work_dir}/"

    if converter == "calibre":
        target_filename = work_dir / "out.epub"
    elif converter == "speedata":
        source_html = work_dir / "index.xml"
        resource_dir = Path(resource_root).parent / "speedata"

    shutil.copytree(str(resource_dir), str(work_dir))

    converter_config = CONVERTERS[converter]

    cmd = converter_config["convert"]
    cmd = cmd.format(
        cmd_options="",
        work_dir=str(work_dir),
        target_filename=str(target_filename),
        source_html=str(source_html),
        base_url=base_url,
    )

    LOG.info(f"CMD: {cmd}")
    result = await util.run(cmd)
    output = result["stdout"] + result["stderr"]

    LOG.info(f"STATUS: {result['status']}")
    LOG.info("OUTPUT")
    LOG.info(output)

    # return PDF data as bytes
    pdf_data = Path(target_filename).read_bytes()

    shutil.rmtree(str(work_dir))
    return pdf_data
