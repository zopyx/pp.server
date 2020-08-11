################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX,  Tuebingen, Germany
################################################################

import os
import sys
import base64
import time
import pkg_resources
import functools
import shutil
import tempfile
import zipfile
import datetime
from pyramid.view import view_config

from pp.server.logger import LOG
from pp.server import converters
from pp.server import util

queue_dir = os.path.join(os.getcwd(), "var", "queue")
queue_dir = os.environ.get('PP_SPOOL_DIRECTORY', queue_dir)
if not os.path.exists(queue_dir):
    try:
        os.makedirs(queue_dir)
    except FileExistsError:
        pass

print('PP_SPOOL_DIRECTORY:', queue_dir)


QUEUE_CLEANUP_TIME = 24 * 60 * 60  # 1 day


def new_converter_id(converter):
    """ New converter id based on timestamp + converter name """
    return datetime.datetime.now().strftime("%Y%m%dT%H%M%S.%f") + "-" + converter


def converter_log(work_dir, msg):
    """ Logging per conversion (by work dir) """
    converter_logfile = os.path.join(work_dir, "converter.log")
    msg = datetime.datetime.now().strftime("%Y%m%dT%H%M%S") + " " + msg
    with open(converter_logfile, "a") as fp:
        try:
            fp.write(msg + "\n")
        except UnicodeError:
            fp.write(msg.encode("ascii", "replace").decode(
                "ascii", "replace") + "\n")


class WebViews(object):
    def __init__(self, request):
        self.request = request

    @view_config(route_name="home", renderer="index.pt", request_method="GET")
    def index(self):
        version = pkg_resources.require("pp.server")[0].version
        return dict(
            version=version,
            python_version=sys.version,
            converter_versions=self.converter_versions(),
        )

    @view_config(route_name="version", renderer="json", request_method="GET")
    def version(self):
        version = pkg_resources.require("pp.server")[0].version
        return dict(version=version, module="pp.server")

    @view_config(
        route_name="available_converters", renderer="json", request_method="GET"
    )
    def available_converters(self):
        from pp.server.converters import princexml
        from pp.server.converters import pdfreactor
        from pp.server.converters import pdfreactor8
        from pp.server.converters import phantomjs
        from pp.server.converters import calibre
        from pp.server.converters import unoconv_bin
        from pp.server.converters import publisher
        from pp.server.converters import wkhtmltopdf
        from pp.server.converters import vivlio
        from pp.server.converters import versatype
        from pp.server.converters import antennahouse
        from pp.server.converters import weasyprint

        return dict(
            princexml=princexml is not None,
            pdfreactor=pdfreactor is not None,
            pdfreactor8=pdfreactor8 is not None,
            phantomjs=phantomjs is not None,
            calibre=calibre is not None,
            unoconv=unoconv_bin is not None,
            wkhtmltopdf=wkhtmltopdf is not None,
            vivliostyle=vivlio is not None,
            versatype=versatype is not None,
            weasyprint=weasyprint is not None,
            antennahouse=antennahouse is not None,
            publisher=publisher is not None,
        )

    @view_config(route_name="converter_versions", renderer="json", request_method="GET")
    def converter_versions(self):
        from pp.server.converters import princexml
        from pp.server.converters import pdfreactor
        from pp.server.converters import pdfreactor8
        from pp.server.converters import phantomjs
        from pp.server.converters import calibre
        from pp.server.converters import unoconv_bin
        from pp.server.converters import publisher
        from pp.server.converters import wkhtmltopdf
        from pp.server.converters import vivlio
        from pp.server.converters import versatype
        from pp.server.converters import antennahouse
        from pp.server.converters import weasyprint

        result = dict()

        if princexml:
            status, output = util.runcmd("{} --version".format(princexml))
            result["princexml"] = output if status == 0 else "n/a"

        if pdfreactor:
            status, output = util.runcmd("{} --version".format(pdfreactor))
            result["pdfreactor"] = output if status == 1 else "n/a"

        if phantomjs:
            status, output = util.runcmd("{} --version".format(phantomjs))
            result["phantomjs"] = output if status == 0 else "n/a"

        if pdfreactor8:
            status, output = util.runcmd("{} --version".format(pdfreactor8))
            result["pdfreactor8"] = output if status == 0 else "n/a"

        if wkhtmltopdf:
            status, output = util.runcmd("{} --version".format(wkhtmltopdf))
            result["wkhtmltopdf"] = output if status == 0 else "n/a"

        if calibre:
            status, output = util.runcmd(
                "{} -convert --version".format(calibre))
            result["calibre"] = output if status == 0 else "n/a"

        if unoconv_bin:
            status, output = util.runcmd("{} --version".format(unoconv_bin))
            result["unoconv"] = output if status == 0 else "n/a"

        if vivlio:
            status, output = util.runcmd("{} --version".format(vivlio))
            result["vivliostyle"] = output if status == 0 else "n/a"

        if versatype:
            status, output = util.runcmd("{} --version".format(versatype))
            result["versatype"] = output if status == 0 else "n/a"

        if antennahouse:
            status, output = util.runcmd("{} -v".format(antennahouse))
            result["antennahouse"] = output if status == 0 else "n/a"

        if publisher:
            status, output = util.runcmd("{} --version".format(publisher))
            result["publisher"] = output if status == 0 else "n/a"

        if weasyprint:
            status, output = util.runcmd("{} --version".format(weasyprint))
            result["weasyprint"] = output if status == 0 else "n/a"

        return result

    @view_config(route_name="cleanup", renderer="json", request_method="GET")
    def cleanup_queue(self):

        if not os.path.exists(queue_dir):
            os.makedirs(queue_dir)

        try:
            lc = self.request.registry.settings["last_cleanup"]
        except (KeyError, AttributeError):
            lc = time.time() - 3600 * 24 * 10
            pass

        now = time.time()
        if now - lc < QUEUE_CLEANUP_TIME:
            return
        removed = 0
        for dirname in os.listdir(queue_dir):
            fullname = os.path.join(queue_dir, dirname)
            mtime = os.path.getmtime(fullname)
            if now - mtime > QUEUE_CLEANUP_TIME:
                LOG.debug("Cleanup: {}".format(fullname))
                if os.path.isdir(fullname):
                    shutil.rmtree(fullname)
                elif os.path.isfile(fullname):
                    os.unlink(fullname)
                removed += 1
        self.request.registry.settings["last_cleanup"] = time.time()
        return dict(directories_removed=removed)

    @view_config(route_name="unoconv_api_1", request_method="POST", renderer="json")
    def unoconv(self):
        """ Convert office formats using ``unoconv`` """

        self.cleanup_queue()

        params = self.request.params
        input_filename = params["filename"]
        input_data = params["file"].file.read()
        output_format = params.get("output_format", "pdf")
        cmd_options = params.get("cmd_options", "")

        new_id = new_converter_id("unoconv")
        work_dir = os.path.join(queue_dir, new_id)
        os.mkdir(work_dir)
        os.mkdir(os.path.join(work_dir, "out"))
        work_file = os.path.join(work_dir, os.path.basename(input_filename))
        with open(work_file, "wb") as fp:
            fp.write(input_data)

        log = functools.partial(converter_log, work_dir)

        ts = time.time()
        log("START: unoconv({}, {}, {})".format(
            new_id, work_file, output_format))
        result = converters.unoconv(
            work_dir, work_file, output_format, cmd_options)
        duration = time.time() - ts
        log("END : unoconv({} {} sec): {}".format(
            new_id, duration, result["status"]))
        if result["status"] == 0:  # OK
            out_directory = result["out_directory"]
            zip_name = tempfile.mktemp()
            zip_out = zipfile.ZipFile(zip_name, "w")
            for fn in os.listdir(out_directory):
                if fn in ("done", "output.txt"):
                    continue
                zip_out.write(os.path.join(out_directory, fn), fn)
            zip_out.close()
            bin_data = base64.encodestring(open(zip_name, "rb").read())
            os.unlink(zip_name)
            return dict(status="OK", data=bin_data, output=result["output"])
        else:  # error
            return dict(status="ERROR", output=result["output"])

    @view_config(route_name="pdf_api_1", request_method="POST", renderer="json")
    def pdf(self):

        self.cleanup_queue()

        params = self.request.params
        zip_data = params["file"].file.read()
        converter = params.get("converter", "princexml")
        cmd_options = params.get("cmd_options", "")

        new_id = new_converter_id(converter)
        work_dir = os.path.join(queue_dir, new_id)
        out_dir = os.path.join(work_dir, "out")
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        work_file = os.path.join(work_dir, "in.zip")
        with open(work_file, "wb") as fp:
            fp.write(zip_data)

        log = functools.partial(converter_log, work_dir)

        ts = time.time()
        msg = "START: pdf({}, {}, {})".format(new_id, work_file, converter)
        log(msg)
        LOG.info(msg)

        result = converters.pdf(work_dir, work_file,
                                converter, log, cmd_options)

        duration = time.time() - ts
        msg = "END : pdf({} {} sec): {}".format(
            new_id, duration, result["status"])
        log(msg)
        LOG.info(msg)

        output = result["output"]
        if result["status"] == 0:  # OK
            pdf_data = open(result["filename"], "rb").read()
            pdf_data = base64.encodestring(pdf_data).decode("ascii")
            return dict(status="OK", data=pdf_data, output=output)
        else:  # error
            return dict(status="ERROR", output=output)
