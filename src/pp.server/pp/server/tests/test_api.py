################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX Ltd, Tuebingen, Germany
################################################################

import os
import base64
import xmlrpclib
import unittest
import zipfile
import tempfile
from pyramid import testing


class ViewIntegrationTests(unittest.TestCase):

    def setUp(self):
        from pp.server import main
        from webtest import TestApp
        app = main({})
        self.config = testing.setUp()
        self.testapp = TestApp(app)

    def test_my_view(self):
        result = self.testapp.get('/', status=200)
        assert 'Produce &amp; Publish Webservice' in result
