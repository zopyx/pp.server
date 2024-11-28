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


from pp.server import util
from pp.server.logger import LOG

CONVERTERS = {
    "prince": {
        "cmd": "prince",
        "version": "prince --version",
        "convert": 'prince {cmd_options} -v "{source_html}" -o "{target_filename}"',
    },
    "pdfreactor-legacy": {
        "cmd": "pdfreactor.py",
        "version": "pdfreactor.py --version",
        "convert": 'pdfreactor.py {cmd_options} --addLinks --addBookmarks --logLevel debug -i "{source_html}" -o "{target_filename}"',
        "convert_docker": 'pdfreactor.py {cmd_options} --addLinks --addBookmarks --logLevel debug -i "{source_docker_html}" -o "{target_filename}"',
    },
    "pdfreactor": {
        "cmd": "pdfreactor.py",
        "version": "pdfreactor.py --version",
        "convert": 'pdfreactor.py {cmd_options} --log-level DEBUG -v -i "{source_html}" -o "{target_filename}" --base-url "{base_url}"',
        "convert_docker": 'pdfreactor.py {cmd_options} --log-level DEBUG -v -i "{source_docker_html}" -o "{target_filename}"',
    },
    "antennahouse": {
        "cmd": "run.sh",
        "version": "run.sh -v",
        "convert": 'run.sh {cmd_options} -d "{source_html}" -o "{target_filename}"',
    },
    "weasyprint": {
        "cmd": "weasyprint",
        "version": "weasyprint --version",
        "convert": 'weasyprint {cmd_options} "{source_html}" "{target_filename}"',
    },
    "typesetsh": {
        "cmd": "typeset.sh.phar",
        "version": "typeset.sh.phar --version",
        "convert": 'typeset.sh.phar -vv render:html --allow-local / -rx "{source_html}" "{target_filename}"',
    },
    "pagedjs": {
        "cmd": "pagedjs-cli",
        "version": "pagedjs-cli --version",
        "convert": 'pagedjs-cli -t 10000 "{source_html}" -o "{target_filename}"',
    },
    "wkhtmltopdf": {
        "cmd": "wkhtmltopdf",
        "version": "wkhtmltopdf --version",
        "convert": 'wkhtmltopdf {cmd_options} "{source_html}" "{target_filename}"',
    },
    "speedata": {
        "cmd": "sp",
        "version": "sp --version",
        "convert": 'sp --jobname out --timeout 30 --runs 2 --wd "{work_dir}" --outputdir "{work_dir}/out" {cmd_options}',
    },
    "calibre": {
        "cmd": "ebook-convert",
        "version": "ebook-convert --version",
        "convert": 'ebook-convert "{source_html}" "{target_filename}" {cmd_options}',
    },
    "vivliostyle": {
        "cmd": "vivliostyle",
        "version": "vivliostyle --version",
        "convert": 'vivliostyle build --output "{target_filename}" "{source_html}"',
    },
    "versatype": {
        "cmd": "versatype-formatter",
        "version": "versatype-formatter --version",
        "convert": 'versatype-formatter "{source_html}" --output "{target_filename}" "{cmd_options}"',
    },
}


def load_resource(package, resource_name):
    data = pkgutil.get_data(package, resource_name)
    return data


async def convert_pdf(
    work_dir, work_file, converter, logger, cmd_options, source_filename="index.html",
):
    """Converter a given ZIP file
    containing input files (HTML + XML) and asset files
    to PDF.
    """

    # avoid circular import
    from pp.server.registry import has_converter

    # unzip archive first
    zf = zipfile.ZipFile(work_file)
    for name in zf.namelist():
        filename = os.path.join(work_dir, name)
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        with open(filename, "wb") as fp:
            fp.write(zf.read(name))

    source_html = os.path.join(work_dir, source_filename)

    if converter == "calibre":
        target_filename = os.path.join(work_dir, "out", "out.epub")
    else:
        target_filename = os.path.join(work_dir, "out", "out.pdf")

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
            target_filename=target_filename,
            source_docker_html=source_docker_html,
        )
    else:
        cmd = converter_config["convert"]
        cmd = cmd.format(
            cmd_options=cmd_options,
            work_dir=work_dir,
            target_filename=target_filename,
            source_html=source_html,
            base_url=base_url,
        )

    logger(f"CMD: {cmd}")
    result = await util.run(cmd)
    status = result["status"]
    output = result["stdout"] + result["stderr"]

    logger(f"STATUS: {result['status']}")
    logger("OUTPUT")
    logger(output)

    return dict(status=status, output=output, filename=target_filename)


async def selftest(converter: str) -> bytes:
    """Converter self test"""

    # created work directory
    work_dir = tempfile.mktemp()

    # copy HTML sample from test_data directory
    resource_root = importlib.util.find_spec("pp.server.test_data").origin
    resource_dir = Path(resource_root).parent / "html"
    source_html = str(Path(work_dir) / "index.html")
    target_filename = os.path.join(work_dir, "out.pdf")
    # required for PDFreactor 12+
    base_url = f"file://{work_dir}/"

    if converter == "calibre":
        target_filename = os.path.join(work_dir, "out.epub")
    elif converter == "speedata":
        source_html = str(Path(work_dir) / "index.xml")
        resource_dir = Path(resource_root).parent / "speedata"

    shutil.copytree(resource_dir, work_dir)

    converter_config = CONVERTERS[converter]

    cmd = converter_config["convert"]
    cmd = cmd.format(
        cmd_options="",
        work_dir=work_dir,
        target_filename=target_filename,
        source_html=source_html,
        base_url=base_url,
    )

    LOG.info(f"CMD: {cmd}")
    result = await util.run(cmd)
    output = result["stdout"] + result["stderr"]

    LOG.info(f"STATUS: {result['status']}")
    LOG.info("OUTPUT")
    LOG.info(output)

    # return PDF data as bytes
    with open(target_filename, "rb") as fp:
        pdf_data = fp.read()

    shutil.rmtree(work_dir)
    return pdf_data
