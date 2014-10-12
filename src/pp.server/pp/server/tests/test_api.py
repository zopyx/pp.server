################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX,  Tuebingen, Germany
################################################################

import os
import base64
import json
import unittest
import zipfile
import tempfile
import zipfile
from pyramid import testing


class Base(unittest.TestCase):

    def setUp(self):
        from pp.server import main
        from webtest import TestApp
        app = main({})
        self.config = testing.setUp()
        self.testapp = TestApp(app)

class PDFTests(Base):

    def test_index(self):
        result = self.testapp.get('/', status=200)
        assert '<title>Produce &amp; Publish Server</title> ' in result

    def test_princexml(self):
        self._convert_pdf('princexml')

    def test_pdfreactor(self):
        self._convert_pdf('pdfreactor')

    def test_unknown_converter(self):
        self._convert_pdf('does.not.exist', expected='ERROR')

    def _convert_pdf(self, converter, expected='OK'):

        # Generate ZIP file with sample data first
        index_html = os.path.join(os.path.dirname(__file__), 'index.html')
        zip_name = tempfile.mktemp(suffix='.zip')
        zf = zipfile.ZipFile(zip_name, 'w')
        zf.write(index_html, 'index.html')
        zf.close()
        with open(zip_name, 'rb') as fp:
            zip_data = fp.read()
        os.unlink(zip_name)

        params = dict(converter=converter)
        upload_files = [('file', 'in.zip', zip_data)]
        result = self.testapp.post('/api/1/pdf', params, upload_files=upload_files, status=200)
        params = json.loads(result.body)

        if expected == 'OK':
            assert params['status'] == 'OK'
            assert 'output' in params
            pdf_data = base64.decodestring(params['data'])
            assert pdf_data.startswith('%PDF-1.4')
        else:
            assert params['status'] == 'ERROR'
            assert 'Unknown converter' in params['output']

class Unoconvtests(Base):

    def _unoconv(self, input_file, format, expected='OK'):

        docx_fname = os.path.join(os.path.dirname(__file__), input_file)
        with open(docx_fname, 'rb') as fp:
            docx_data = fp.read()

        params = dict(filename=input_file, output_format=format)
        upload_files = [('file', input_file, docx_data)]
        result = self.testapp.post('/api/1/unoconv', params, upload_files=upload_files, status=200)
        params = json.loads(result.body)

        if expected == 'OK':
            assert params['status'] == 'OK'
            assert 'output' in params
            zip_name = tempfile.mktemp(suffix='.zip')
            with open(zip_name, 'wb') as fp:
                zip_data = base64.decodestring(params['data'])
                fp.write(zip_data)

            with zipfile.ZipFile(zip_name, 'r') as zf:
                for name in zf.namelist():
                    base, ext = os.path.splitext(name)
                    if ext in ('.pdf', '.html'):
                        data = zf.read(name)
                        os.unlink(zip_name)
                        return data
        else:
            assert params['status'] == 'ERROR'
            assert 'is not known to unoconv' in params['output']
    
    def test_docx2pdf(self):
        pdf_data = self._unoconv('test.docx', 'pdf')
        assert pdf_data.startswith('%PDF-1.4')

    def test_docx2html(self):
        html_data = self._unoconv('test.docx', 'html')
        assert html_data.startswith('<!DOCTYPE')

    def test_docx2unknown(self):
        self._unoconv('test.docx', 'unknown', expected='ERROR')
