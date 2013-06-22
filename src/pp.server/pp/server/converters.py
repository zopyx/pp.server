################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX Ltd, Tuebingen, Germany
################################################################

import os
import zlib
import zipfile
from pp.server import util

def unoconv(input_filename, output_format):
    """ Convert ``input_filename`` using ``unoconv`` to
        the new target format.
    """

    base, ext = os.path.splitext(input_filename)
    dest_filename = base + '.' + output_format
    cmd = 'unoconv -f "{}" "{}"'.format(output_format, input_filename)
    status, output = util.runcmd(cmd)
    return dict(status=status,
                output=output,
                filename=dest_filename)


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
    target_pdf = os.path.join(work_dir, 'out.pdf')

    if converter == 'princexml':
        cmd = 'prince -v "{}" "{}"'.format(source_html, target_pdf) 
    elif converter == 'pdfreactor':
        cmd = 'pdfreactor -v debug "{}" "{}"'.format(source_html, target_pdf) 
    else:
        raise NotImplementedError('No support for converter "{}"'.format(converter))

    status, output = util. runcmd(cmd)
    return dict(status=status,
                output=output,
                filename=target_pdf)
