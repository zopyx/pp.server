""" XMLRPC client to access the unoconv API of the Produce & Publish server """

import os
import plac
import xmlrpclib
@plac.annotations(
    input_filename=('Source file to be converted', 'positional'),
    format=('Output format (default=pdf)', 'option'),
    filename=('Write converted file to custom filename)', 'option'),
    server_url=('URL of Produce & Publish XMLRPC API)', 'option'),
)
def main_(input_filename, 
          format='pdf', 
          filename=None,
          async=False, 
          server_url='http://localhost:6543/api'):

    server = xmlrpclib.ServerProxy(server_url)
    result = server.unoconv(os.path.basename(input_filename),
                            xmlrpclib.Binary(open(input_filename, 'rb').read()),
                            format,
                            async)

    if result['status'] == 'OK':
        if not filename:
            base, ext = os.path.splitext(input_filename)
            filename = base + '.' + format
        with open(filename, 'wb') as fp:
            fp.write(result['data'].data)
        print 'Output filename: {}'.format(filename)
    else:
        print 'An error occured'
        print 'Output:'
        print result['output']
    
def main():
    plac.call(main_)

if __name__ == '__main__':
    main()
