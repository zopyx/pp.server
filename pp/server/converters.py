################################################################
# pp.server - Produce & Publish Server
# (C) 2021, ZOPYX,  Tuebingen, Germany
################################################################

import os
import zipfile

from pp.server import util

CONVERTERS = {
    "prince": {
        "cmd": "prince",
        "version": "prince --version",
        "convert": 'prince {cmd_options} -v "{source_html}" -o "{target_filename}"',},
    "pdfreactor.sh": {
        "cmd": "pdfreactor.sh",
        "version": "pdfreactor.sh --version",
        "convert": 'pdfreactor.sh  "{source_html}"  "{target_filename}"',},
    "pdfreactor": {
        "cmd":
        "pdfreactor.py",
        "version":
        "pdfreactor.py --version",
        "convert":
        'pdfreactor.py {cmd_options} --addLinks --addBookmarks --logLevel debug -i "{source_html}" -o "{target_filename}"',
        "convert_docker":
        'pdfreactor.py {cmd_options} --addLinks --addBookmarks --logLevel debug -i "{source_docker_html}" -o "{target_filename}"',
    },
    "antennahouse": {
        "cmd": "run.sh",
        "version": "run.sh -v",
        "convert": 'run.sh {cmd_options} -d "{source_html}" -o "{target_filename}"',},
    "weasyprint": {
        "cmd": "weasyprint",
        "version": "weasyprint --version",
        "convert": 'weasyprint {cmd_options} "{source_html}" "{target_filename}"',},
    "typesetsh": {
        "cmd": "typeset.sh.phar",
        "version": "typeset.sh.phar --version",
        "convert": 'typeset.sh.phar -vv render:html --allow-local / -rx "{source_html}" "{target_filename}"',},
    "pagedjs": {
        "cmd": "pagedjs-cli",
        "version": "pagedjs-cli --version",
        "convert": 'pagedjs-cli -t 10000 "{source_html}" -o "{target_filename}"',},
    "wkhtmltopdf": {
        "cmd": "wkhtmltopdf",
        "version": "wkhtmltopdf --version",
        "convert": 'wkhtmltopdf {cmd_options} "{source_html}" "{target_filename}"',},
    "speedata": {
        "cmd": "sp",
        "version": "sp --version",
        "convert":
        'sp --jobname out --timeout 30 --runs 2 --wd "{work_dir}" --outputdir "{work_dir}/out" {cmd_options}',},
    "calibre": {
        "cmd": "ebook-convert",
        "version": "ebook-convert --version",
        "convert": 'ebook-convert "{source_html}" "{target_filename}" {cmd_options}',},
    "vivliostyle": {
        "cmd": "vivliostyle",
        "version": "vivliostyle --version",
        "convert": 'vivliostyle build --output "{target_filename}" "{cmd_options}" "{source_html}"',},
    "versatype": {
        "cmd": "versatype-formatter",
        "version": "versatype-formatter --version",
        "convert": 'versatype-formatter "{source_html}" --output "{target_filename}" "{cmd_options}"',},}


async def convert_pdf(work_dir, work_file, converter, logger, cmd_options, source_filename="index.html"):
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

    if not has_converter(converter):
        return dict(status=9999, output=u'Unknown converter "{}"'.format(converter))

    converter_config = CONVERTERS[converter]

    if converter == "pdfreactor" and "PP_PDFREACTOR_DOCKER" in os.environ:
        # PDFreactor running on Docker requires special trickery
        # We assume that the /docs volume of the PDFreactor container is mounted into the local
        # filesystem.
        cmd = converter_config["convert_docker"]
        parts = work_dir.split("/")
        source_docker_html = "file:///docs/{}/index.html".format(parts[-1])
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
        )

    logger("CMD: {}".format(cmd))
    result = await util.run(cmd)
    status = result["status"]
    output = result["stdout"] + result["stderr"]

    logger("STATUS: {}".format(result["status"]))
    logger("OUTPUT")
    logger(output)

    return dict(status=status, output=output, filename=target_filename)
