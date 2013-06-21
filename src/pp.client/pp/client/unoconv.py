""" XMLRPC client to access the unoconv API of the Produce & Publish server """

import os
import plac
import xmlrpclib

def main_(input_filename, 
          output_format='pdf', 
          output_filename=None,
          async=False, 
          server_url='http://localhost:6543/api'):

    server = xmlrpclib.ServerProxy(server_url)
    result = server.unoconv(os.path.basename(input_filename),
                            xmlrpclib.Binary(open(input_filename, 'rb').read()),
                            output_format,
                            async)

    if result['status'] == 'OK':
        if not output_filename:
            base, ext = os.path.splitext(input_filename)
            output_filename = base + '.' + output_format
        with open(output_filename, 'wb') as fp:
            fp.write(result['data'].data)
        print 'Output filename: {}'.format(output_filename)
    else:
        print 'An error occured'
        print 'Output:'
        print result['output']
    
def main():
    plac.call(main_)

if __name__ == '__main__':
    main()
