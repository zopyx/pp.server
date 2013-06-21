""" Commandline client """

import os
import plac
import xmlrpclib

def main_(input_filename, output_format='pdf', async=False):
    print 'main'

    server = xmlrpclib.ServerProxy('http://localhost:6543/api')
    result = server.unoconv(os.path.basename(input_filename),
                            xmlrpclib.Binary(open(input_filename, 'rb').read()),
                            output_format,
                            async)

    print result
    
def main():
    plac.call(main_)

if __name__ == '__main__':
    main()
