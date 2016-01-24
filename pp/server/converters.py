################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX,  Tuebingen, Germany
################################################################

import os
import zipfile
import pkg_resources
from pp.server import util


pdfreactor = None
if util.which('pdfreactor'):
    pdfreactor = 'pdfreactor'
elif os.path.exists('bin/pdfreactor'):
    pdfreactor = 'bin/pdfreactor'

pdfreactor8 = None
if util.which('pdfreactor8'):
    pdfreactor8 = 'pdfreactor8'
elif os.path.exists('bin/pdfreactor8'):
    pdfreactor8 = 'bin/pdfreactor8'

wkhtmltopdf= None
if util.which('wkhtmltopdf'):
    wkhtmltopdf = 'wkhtmltopdf'
elif os.path.exists('bin/wkhtmltopdf'):
    wkhtmltopdf = 'bin/wkhtmltopdf'
    
princexml = None
if util.which('prince'):
    princexml = 'prince'
elif os.path.exists('bin/prince'):
    princexml = 'bin/prince'

phantomjs = None
if util.which('phantomjs'):
    phantomjs = 'phantomjs'
elif os.path.exists('bin/phantomjs'):
    phantomjs = 'bin/phantomjs'

publisher = None
if util.which('sp'):
    publisher = 'sp'
elif os.path.exists('bin/sp'):
    publisher = 'bin/sp'

vivlio = None
if util.which('vivliostyle-formatter'):
    vivlio = 'vivliostyle-formatter'

antennahouse = None
if util.which('run.sh'):
    antennahouse = 'run.sh'

calibre = None
if util.which('ebook-convert'):
    calibre = 'ebook-convert'

unoconv_bin = None
if util.which('unoconv'):
    unoconv_bin = 'unoconv'


def unoconv(work_dir, input_filename, output_format, cmd_options):
    """ Convert ``input_filename`` using ``unoconv`` to
        the new target format.
    """

    base, ext = os.path.splitext(input_filename)
    out_directory = os.path.join(work_dir, 'out')
    cmd = '{} {} -f "{}" -o "{}" "{}"'.format(unoconv_bin, cmd_options, output_format, out_directory, input_filename)
    status, output = util.runcmd(cmd)

    with open(os.path.join(work_dir, 'out', 'output.txt'), 'w') as fp:
        fp.write(cmd + '\n')
        fp.write(output + '\n')
    with open(os.path.join(work_dir, 'out', 'done'), 'w') as fp:
        fp.write('done')

    return dict(status=status,
                output=output,
                out_directory=out_directory)


def pdf(work_dir, work_file, converter, cmd_options, source_filename='index.html'):
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
        with open(filename, 'wb') as fp:
            fp.write(zf.read(name))

    source_html = os.path.join(work_dir, source_filename)

    if converter == 'calibre':
        target_filename = os.path.join(work_dir, 'out', 'out.epub')
    else:
        target_filename = os.path.join(work_dir, 'out', 'out.pdf')

    if converter == 'princexml':
        if not princexml:
            return dict(status=9999,
                        output=u'PrinceXML not installed')
        cmd = '{} {} -v "{}" "{}"'.format(princexml, cmd_options, source_html, target_filename) 

    elif converter == 'pdfreactor':
        if not pdfreactor:
            return dict(status=9999,
                        output=u'PDFreactor not installed')
        cmd = '{} {} -a links -a bookmarks -v debug "{}" "{}"'.format(pdfreactor, cmd_options, source_html, target_filename) 

    elif converter == 'pdfreactor8':
        if not pdfreactor8:
            return dict(status=9999,
                        output=u'PDFreactor 8 not installed')
        cmd = '{} {} --addLinks --addBookmarks --logLevel debug -i "{}" -o "{}"'.format(pdfreactor8, cmd_options, source_html, target_filename) 

    elif converter == 'wkhtmltopdf':
        if not wkhtmltopdf:
            return dict(status=9999,
                        output=u'wkhtmltopdf not installed')
        cmd = '{} {} "{}" "{}"'.format(wkhtmltopdf, cmd_options, source_html, target_filename) 

    elif converter == 'publisher':
        if not publisher:
            return dict(status=9999,
                        output=u'Speedata Publisher not installed')
        cmd = '{} --jobname out --wd "{}" --outputdir "{}/out"'.format(publisher, work_dir, work_dir, cmd_options) 

    elif converter == 'phantomjs':
        if not phantomjs:
            return dict(status=9999,
                        output=u'PhantomJS not installed')
        rasterize = pkg_resources.resource_filename('pp.server', 'scripts/rasterize.js')
        cmd = '{} {} --debug false "{}" "{}" "{}" A4'.format(phantomjs, cmd_options, rasterize, source_html, target_filename) 

    elif converter == 'calibre':
        if not calibre:
            return dict(status=9999,
                        output=u'Calibre not installed')
        cmd = '{} "{}" "{}" {}'.format(calibre, source_html, target_filename, cmd_options)

    elif converter == 'vivliostyle':
        out_directory = os.path.join(work_dir, 'out')
        out_filename = 'out.pdf'
        if not vivlio:
            return dict(status=9999,
                        output=u'Vivliostyle not installed')
        cmd = '{} "{}" --output "{}/{}" "{}"'.format(vivlio, source_html, out_directory, out_filename, cmd_options)
    elif converter == 'antennahouse':
        out_directory = os.path.join(work_dir, 'out')
        out_filename = 'out.pdf'
        if not antennahouse:
            return dict(status=9999,
                        output=u'Antennahouse not installed')
        cmd = '{} {} -d "{}" -o "{}/{}"'.format(antennahouse, cmd_options, source_html, out_directory, out_filename)

    else:
        return dict(status=9999,
                    output=u'Unknown converter "{}"'.format(converter))

    status, output = util.runcmd(cmd)

    with open(os.path.join(work_dir, 'out', 'output.txt'), 'w', encoding='utf8') as fp:
        fp.write(cmd + '\n')
        fp.write(output + '\n')
    with open(os.path.join(work_dir, 'out', 'done'), 'w') as fp:
        fp.write('done')

    return dict(status=status,
                output=output,
                filename=target_filename)
