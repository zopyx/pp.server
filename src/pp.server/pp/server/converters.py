################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX Ltd, Tuebingen, Germany
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

calibre = None
if util.which('ebook-convert'):
    calibre = 'ebook-convert'

unoconv = None
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

    with open(os.path.join(work_dir, 'out', 'output.txt'), 'wb') as fp:
        fp.write(cmd + '\n')
        fp.write(output + '\n')
    with open(os.path.join(work_dir, 'out', 'done'), 'wb') as fp:
        fp.write('done')

    return dict(status=status,
                output=output,
                out_directory=out_directory)


def pdf(work_dir, work_file, converter, cmd_options):
    """ Converter a given ZIP file
        containing input files (HTML + XML) and asset files
        to PDF.
    """

    # unzip archive first
    zf = zipfile.ZipFile(work_file)
    for name in zf.namelist():
        filename = os.path.join(work_dir, name)
        with open(filename, 'wb') as fp:
            fp.write(zf.read(name))

    source_html = os.path.join(work_dir, 'index.html')

    if converter == 'calibre':
        target_filename = os.path.join(work_dir, 'out', 'out.epub')
    else:
        target_filename = os.path.join(work_dir, 'out', 'out.pdf')

    if converter == 'princexml':
        if not princexml:
            raise RuntimeError('"prince" not found')
        cmd = '{} {} -v "{}" "{}"'.format(princexml, cmd_options, source_html, target_filename) 

    elif converter == 'pdfreactor':
        if not pdfreactor:
            raise RuntimeError('"pdfreactor" not found')
        cmd = '{} {} -a links -a bookmarks --addlog -v debug "{}" "{}"'.format(pdfreactor, cmd_options, source_html, target_filename) 

    elif converter == 'phantomjs':
        if not phantomjs:
            raise RuntimeError('"phantomjs" not found')
        rasterize = pkg_resources.resource_filename('pp.server', 'scripts/rasterize.js')
        cmd = '{} {} --debug false "{}" "{}" "{}" A4'.format(phantomjs, cmd_options, rasterize, source_html, target_filename) 

    elif converter == 'calibre':
        if not calibre:
            raise RuntimeError('"calibre" not found')
        cmd = '{} "{}" "{}" {}'.format(calibre, source_html, target_filename, cmd_options)

    else:
        return dict(status=9999,
                    output=u'Unknown converter "{}"'.format(converter))

    status, output = util.runcmd(cmd)

    with open(os.path.join(work_dir, 'out', 'output.txt'), 'w') as fp:
        fp.write(cmd + '\n')
        fp.write(output + '\n')
    with open(os.path.join(work_dir, 'out', 'done'), 'w') as fp:
        fp.write('done')

    return dict(status=status,
                output=output,
                filename=target_filename)
