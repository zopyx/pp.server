################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX,  Tuebingen, Germany
################################################################

import os
import json
import zipfile
import pkg_resources
import pyramid.threadlocal
from pyramid.settings import asbool

from pp.server import util


pdfreactor = None
if util.which("pdfreactor"):
    pdfreactor = "pdfreactor"
elif os.path.exists("bin/pdfreactor"):
    pdfreactor = "bin/pdfreactor"

pdfreactor8 = None
if util.which("pdfreactor.py"):
    pdfreactor8 = "pdfreactor.py"
elif os.path.exists("bin/pdfreactor.py"):
    pdfreactor8 = "bin/pdfreactor.py"

wkhtmltopdf = None
if util.which("wkhtmltopdf"):
    wkhtmltopdf = "wkhtmltopdf"
elif os.path.exists("bin/wkhtmltopdf"):
    wkhtmltopdf = "bin/wkhtmltopdf"

princexml = None
if util.which("prince"):
    princexml = "prince"
elif os.path.exists("bin/prince"):
    princexml = "bin/prince"

phantomjs = None
if util.which("phantomjs"):
    phantomjs = "phantomjs"
elif os.path.exists("bin/phantomjs"):
    phantomjs = "bin/phantomjs"

publisher = None
if util.which("sp"):
    publisher = "sp"
elif os.path.exists("bin/sp"):
    publisher = "bin/sp"

weasyprint = None
if util.which("weasyprint"):
    weasyprint = "weasyprint"

vivlio = None
if util.which("vivliostyle-formatter"):
    vivlio = "vivliostyle-formatter"

versatype = None
if util.which("versatype-converter"):
    versatype = "versatype-converter"

antennahouse = None
if util.which("run.sh"):
    antennahouse = "run.sh"

calibre = None
if util.which("ebook-convert"):
    calibre = "ebook-convert"

unoconv_bin = None
if util.which("unoconv"):
    unoconv_bin = "unoconv"


def unoconv(work_dir, input_filename, output_format, cmd_options):
    """ Convert ``input_filename`` using ``unoconv`` to
        the new target format.
    """

    base, ext = os.path.splitext(input_filename)
    out_directory = os.path.join(work_dir, "out")
    cmd = '{} {} -f "{}" -o "{}" "{}"'.format(
        unoconv_bin, cmd_options, output_format, out_directory, input_filename
    )
    status, output = util.runcmd(cmd)

    with open(os.path.join(work_dir, "out", "output.txt"), "w") as fp:
        fp.write(cmd + "\n")
        fp.write(output + "\n")
    with open(os.path.join(work_dir, "out", "done"), "w") as fp:
        fp.write("done")

    return dict(status=status, output=output, out_directory=out_directory)


def pdf(
    work_dir, work_file, converter, logger, cmd_options, source_filename="index.html"
):
    """ Converter a given ZIP file
        containing input files (HTML + XML) and asset files
        to PDF.
    """

    # unzip archive first
    zf = zipfile.ZipFile(work_file)
    for name in zf.namelist():
        filename = os.path.join(work_dir, name)
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        with open(filename, "wb") as fp:
            fp.write(zf.read(name))

    # check for project.json
    json_fn = os.path.join(work_dir, "project.json")
    project_data = None
    if os.path.exists(json_fn):
        with open(json_fn, "rb") as fp:
            project_data = json.load(fp)

    cmd_output = ""
    if project_data:
        execute_on = project_data.get("execute_on", "client")
        if execute_on == "server":
            settings = pyramid.threadlocal.get_current_registry().settings
            remote_exec = asbool(settings.get("remote_execution", "false"))
            if not remote_exec:
                raise RuntimeError(
                    "Remote execution is disabled (set remote_execution=true in [app:main])"
                )

            converter = project_data.get("converter")
            cmd = project_data.get("command")
            cmd = 'cd "{work_dir}"; {cmd}  2>&1'.format(
                work_dir=work_dir, cmd=cmd)
            status, cmd_output = util.runcmd(cmd)
            if status != 0:
                raise RuntimeError(
                    "{cmd} failed with exit code {status}".format(
                        cmd=cmd, status=status
                    )
                )

    source_html = os.path.join(work_dir, source_filename)

    if converter == "calibre":
        target_filename = os.path.join(work_dir, "out", "out.epub")
    else:
        target_filename = os.path.join(work_dir, "out", "out.pdf")

    if converter == "princexml":
        if not princexml:
            return dict(status=9999, output=u"PrinceXML not installed")
        cmd = '{} {} -v "{}" -o "{}"'.format(
            princexml, cmd_options, source_html, target_filename
        )

    elif converter == "pdfreactor":
        if not pdfreactor:
            return dict(status=9999, output=u"PDFreactor not installed")
        cmd = '{} {} -a links -a bookmarks -v debug "{}" "{}"'.format(
            pdfreactor, cmd_options, source_html, target_filename
        )

    elif converter == "pdfreactor8":

        if not pdfreactor8:
            return dict(status=9999, output=u"PDFreactor 8 not installed")
        if 'PP_PDFREACTOR_DOCKER' in os.environ:
            # for using PDFreactor under Docker we need to rewrite the source URI
            parts = work_dir.split('/')
            source_docker_html = 'file:///docs/{}/index.html'.format(parts[-1])
            cmd = '{} {} --addLinks --addBookmarks --logLevel debug -i "{}" -o "{}"'.format(
                pdfreactor8, cmd_options, source_docker_html, target_filename
            )
        else:
            cmd = '{} {} --addLinks --addBookmarks --logLevel debug -i "{}" -o "{}"'.format(
                pdfreactor8, cmd_options, source_html, target_filename
            )

    elif converter == "wkhtmltopdf":
        if not wkhtmltopdf:
            return dict(status=9999, output=u"wkhtmltopdf not installed")
        cmd = '{} {} "{}" "{}"'.format(
            wkhtmltopdf, cmd_options, source_html, target_filename
        )

    elif converter == "publisher":
        if not publisher:
            return dict(status=9999, output=u"Speedata Publisher not installed")
        cmd = '{} --jobname out --timeout 30 --runs 2 --wd "{}" --outputdir "{}/out" {}'.format(
            publisher, work_dir, work_dir, cmd_options
        )

    elif converter == "phantomjs":
        if not phantomjs:
            return dict(status=9999, output=u"PhantomJS not installed")
        rasterize = pkg_resources.resource_filename(
            "pp.server", "scripts/rasterize.js")
        cmd = '{} {} --debug false "{}" "{}" "{}" A4'.format(
            phantomjs, cmd_options, rasterize, source_html, target_filename
        )

    elif converter == "weasyprint":
        if not weasyprint:
            return dict(status=9999, output=u"weasyprint not installed")
        cmd = '{} {} "{}" "{}"'.format(
            weasyprint, cmd_options, source_html, target_filename
        )

    elif converter == "calibre":
        if not calibre:
            return dict(status=9999, output=u"Calibre not installed")
        cmd = '{} "{}" "{}" {}'.format(
            calibre, source_html, target_filename, cmd_options
        )

    elif converter == "vivliostyle":
        out_directory = os.path.join(work_dir, "out")
        out_filename = "out.pdf"
        if not vivlio:
            return dict(status=9999, output=u"Vivliostyle not installed")
        cmd = '{} "{}" --output "{}/{}" "{}"'.format(
            vivlio, source_html, out_directory, out_filename, cmd_options
        )
    elif converter == "versatype":
        out_directory = os.path.join(work_dir, "out")
        out_filename = "out.pdf"
        if not versatype:
            return dict(status=9999, output=u"Versatype not installed")
        cmd = '{} "{}" --output "{}/{}" "{}"'.format(
            versatype, source_html, out_directory, out_filename, cmd_options
        )
    elif converter == "antennahouse":
        out_directory = os.path.join(work_dir, "out")
        out_filename = "out.pdf"
        if not antennahouse:
            return dict(status=9999, output=u"Antennahouse not installed")
        cmd = '{} {} -d "{}" -o "{}/{}"'.format(
            antennahouse, cmd_options, source_html, out_directory, out_filename
        )

    else:
        return dict(status=9999, output=u'Unknown converter "{}"'.format(converter))

    logger("CMD: {}".format(cmd))

    status, output = util.runcmd(cmd)
    if converter == "publisher":
        status = 0

    logger("STATUS: {}".format(status))
    logger("OUTPUT")
    logger(output)

    return dict(status=status, output=cmd_output + output, filename=target_filename)
