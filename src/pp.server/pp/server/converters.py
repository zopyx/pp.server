import os
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
