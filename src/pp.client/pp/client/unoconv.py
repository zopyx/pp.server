""" XMLRPC client to access the unoconv API of the Produce & Publish server """

import os
import plac
import xmlrpclib

@plac.annotations(
    input_filename=('Source file to be converted', 'positional'),
    format=('Output format (default=pdf)', 'option', 'f'),
    output=('Write converted file to custom filename', 'option', 'o'),
    server_url=('URL of Produce & Publish XMLRPC API)', 'option', 's'),
    async=('Perform conversion asynchronously)', 'flag', 'a'),
    verbose=('Verbose mode)', 'flag', 'v'),
)
def unoconv(input_filename, 
           format='pdf', 
           output='',
           async=False, 
           server_url='http://localhost:6543/api',
           verbose=False):

    def log(s):
        if verbose:
            print s

    server = xmlrpclib.ServerProxy(server_url)
    result = server.unoconv(os.path.basename(input_filename),
                            xmlrpclib.Binary(open(input_filename, 'rb').read()),
                            format,
                            async)
    if async:
        log(result)
    else:
        if result['status'] == 'OK':
            if not output:
                base, ext = os.path.splitext(input_filename)
                output= base + '.' + format
            with open(output, 'wb') as fp:
                fp.write(result['data'].data)
            log('Output filename: {}'.format(output))
        else:
            log('An error occured')
            log('Output:')
            log(result['output'])

    return result

def main():
    plac.call(unoconv)

if __name__ == '__main__':
    main()
