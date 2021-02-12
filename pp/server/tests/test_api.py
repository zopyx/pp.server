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

from fastapi.testclient import TestClient

from pp.server.server import app

client = TestClient(app)

class PDFTests(unittest.TestCase):

    def test_index(self):
        result = client.get('/')
        assert result.status_code == 200
        assert '2021' in result.text

    def test_has_converter(self):
        result = client.get('/converter?converter_name=prince')
        assert result.status_code == 200
        assert result.json() == dict(has_converter=True)

    def test_has_converter(self2):
        result = client.get('/converter?converter_name=dummy')
        assert result.status_code == 200
        assert result.json() == dict(has_converter=False)

    def test_prince(self):
        self._convert_pdf("prince")

    def test_weasyprint(self):
        self._convert_pdf("weasyprint")

    def test_antennahouse(self):
        self._convert_pdf("antennahouse")

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

        params = dict(converter=converter, cmd_options=" ", data=base64.encodebytes(zip_data))
        upload_files = [('file', 'in.zip', zip_data)]
        result = client.post('/convert', params)
        params = result.json()

        if expected == 'OK':
            assert params['status'] == 'OK'
            assert 'output' in params
            pdf_data = base64.decodebytes(params['data'].encode("ascii"))
            assert pdf_data.startswith(b'%PDF-1.')
        else:
            assert params['status'] == 'ERROR'
            assert 'Unknown converter' in params['output']

