""" XMLRPC client to access the unoconv API of the Produce & Publish server """

import os
import plac
import time
import xmlrpclib
import zipfile
import zlib
import tempfile

def makeZipFromDirectory(directory):
    """ Generate a ZIP file from a directory containing all its
        contents. Returns the filename of the generated ZIP file.
    """

    directory = os.path.abspath(directory)
    zip_filename = tempfile.mktemp()
    ZF = zipfile.ZipFile(zip_filename, 'w')
    for dirname, dirnames, filenames in os.walk(directory):
        for fname in filenames:
            arcname = os.path.join(dirname, fname).replace(directory + os.path.sep, '')
            fullname = os.path.abspath(os.path.join(dirname, fname))
            ZF.write(fullname, arcname)
    ZF.close()
    return zip_filename

@plac.annotations(
    source_directory=('Source directory containing content and assets to be converted', 'positional'),
    converter=('PDF converter to be used (princexml, pdfreactor)', 'option', 'c'),
    output=('Write result ZIP to given .zip filename', 'option', 'o'),
    server_url=('URL of Produce & Publish XMLRPC API)', 'option', 's'),
    async=('Perform conversion asynchronously)', 'flag', 'a'),
    verbose=('Verbose mode', 'flag', 'v'),
)
def main_(source_directory,
          converter='princexml', 
          output='',
          async=False, 
          server_url='http://localhost:6543/api',
          verbose=False):

    def log(s):
        if verbose:
            print s

    zip_filename = makeZipFromDirectory(source_directory)
    server = xmlrpclib.ServerProxy(server_url)
    result = server.pdf(xmlrpclib.Binary(open(zip_filename, 'rb').read()),
                        converter,
                        async)

    os.unlink(zip_filename)

    if async:
        log(result)
        job_id = result['id']
        running = True
        while running:
            time.sleep(1)
            print 'polling'
            result = server.poll(job_id)
            if result['done']:
                running = False
                if result['status'] == 0:
                    output_filename = 'out.pdf'
                    with open(output_filename, 'wb') as fp:
                        if result['compression'] == 'zlib':
                            fp.write(zlib.decompress(result['data'].data))
                        else:
                            fp.write(result['data'].data)
                    print 'Done', output_filename
                elif result['status'] == -1:
                    print 'Error'
                    

    else:
        if result['status'] == 'OK':
            if not output:
                base, ext = os.path.splitext(zip_filename)
                output= base + '.pdf'
            with open(output, 'wb') as fp:
                if result['compression'] == 'zlib':
                    fp.write(zlib.decompress(result['data'].data))
                else:
                    fp.write(result['data'].data)
            log('Output filename: {}'.format(output))
        else:
            log('An error occured')
            log('Output:')
            log(result['output'])

    return result
    
def main():
    plac.call(main_)

if __name__ == '__main__':
    main()
