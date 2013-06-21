""" Commandline client """

import plac
import xmlrpclib

def main_(input_filename, output_format='pdf', async=False):
    print 'main'

    server = xmlrpclib.ServerProxy('http://localhost:6543/unoconv')
    server.unoconv(xmlrpclib.Binary(open(input_filename, 'rb').read()),
                   output_format,
                   async)

def main():
    plac.call(main_)

if __name__ == '__main__':
    main()
