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


def unoconv(work_dir, input_filename, output_format):
    """ Convert ``input_filename`` using ``unoconv`` to
        the new target format.
    """

    base, ext = os.path.splitext(input_filename)
    out_directory = os.path.join(work_dir, 'out')
    cmd = 'unoconv -f "{}" -o "{}" "{}"'.format(output_format, out_directory, input_filename)
    status, output = util.runcmd(cmd)

    with open(os.path.join(work_dir, 'out', 'output.txt'), 'wb') as fp:
        fp.write(cmd + '\n')
        fp.write(output + '\n')
    with open(os.path.join(work_dir, 'out', 'done'), 'wb') as fp:
        fp.write('done')

    return dict(status=status,
                output=output,
                out_directory=out_directory)


def pdf(work_dir, work_file, converter):
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
    target_pdf = os.path.join(work_dir, 'out', 'out.pdf')

    if converter == 'princexml':
        if not princexml:
            raise RuntimeError('prince not found')
        cmd = '{} -v "{}" "{}"'.format(princexml, source_html, target_pdf) 

    elif converter == 'pdfreactor':
        if not pdfreactor:
            raise RuntimeError('pdfreactor not found')
        cmd = '{} -v debug "{}" "{}"'.format(pdfreactor, source_html, target_pdf) 

    elif converter == 'phantomjs':
        if not phantomjs:
            raise RuntimeError('phantomjs not found')
        rasterize = pkg_resources.resource_filename('pp.server', 'scripts/rasterize.js')
        cmd = '{} --debug false "{}" "{}" "{}" A4'.format(phantomjs, rasterize, source_html, target_pdf) 

    else:
        return dict(status=9999,
                    output=u'Unknown converter "{}"'.format(converter))

    status, output = util. runcmd(cmd)

    with open(os.path.join(work_dir, 'out', 'output.txt'), 'wb') as fp:
        fp.write(cmd + '\n')
        fp.write(output + '\n')
    with open(os.path.join(work_dir, 'out', 'done'), 'wb') as fp:
        fp.write('done')

    return dict(status=status,
                output=output,
                filename=target_pdf)
