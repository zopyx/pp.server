################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX Ltd, Tuebingen, Germany
################################################################

import os
import xmlrpclib
import unittest
import zipfile
import tempfile
import zipfile
import zlib
from pyramid import testing


class ViewIntegrationTests(unittest.TestCase):

    def setUp(self):
        from pp.server import main
        from webtest import TestApp
        app = main({})
        self.config = testing.setUp()
        self.testapp = TestApp(app)

    def test_index(self):
        result = self.testapp.get('/', status=200)
        assert 'Produce &amp; Publish Webservice' in result

    def test_princexml(self):
        self._convert_pdf('princexml')

    def test_pdfreactor(self):
        self._convert_pdf('pdfreactor')

    def _convert_pdf(self, converter):

        index_html = os.path.join(os.path.dirname(__file__), 'index.html')
        zip_name = tempfile.mktemp(suffix='.zip')
        zf = zipfile.ZipFile(zip_name, 'w')
        zf.write(index_html, 'index.html')
        zf.close()
        with open(zip_name, 'rb') as fp:
            zip_data = fp.read()
        os.unlink(zip_name)

        params = (xmlrpclib.Binary(zip_data), converter)
        xml = xmlrpclib.dumps(params, 'pdf')

        result = self.testapp.post('/api', xml, status=200)
        params, methodname = xmlrpclib.loads(result.body)
        params = params[0]
        assert params['status'] == 'OK'
        assert 'output' in params
        assert params['compression'] == 'zlib'
        pdf_data = zlib.decompress(params['data'].data)
        assert pdf_data.startswith('%PDF-1.4')
