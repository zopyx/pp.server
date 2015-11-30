#!/usr/bin/env python

import os
import sys
import subprocess

argv = sys.argv[1:]

pdfreactor_path = os.environ.get('PDFREACTOR_PATH', '/opt/PDFreactor8')
bin_path = os.path.join(pdfreactor_path, 'bin', 'pdfreactor.py') 
if not os.path.exists(bin_path):
    raise RuntimeError('No PDFreactor 8 script found at {}'.format(bin_path))

exec_path = '"{}" "{}" {}'.format(sys.executable, bin_path, ' '.join(argv))
st, output = subprocess.getstatusoutput(exec_path)
print(output)
sys.exit(st)
