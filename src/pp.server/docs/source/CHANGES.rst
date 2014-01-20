0.4.3 (20.01.2014)
------------------
- implemented automatic queue cleanup after one day

0.4.2 (18.01.2014)
------------------
- URL fix in index.pt related to virtual hosting

0.4.1 (13.01.2014)
------------------
- show Python version and converters on index.pt
- authorization support added

0.4.0 (17.10.2013)
------------------
- Python 3.3 support
- Pyramid 1.5 support

0.3.5 (05.10.2013)
------------------
- added 'cmd_options' to pdf and unoconv API 
  methods for specifying arbitary command line parameters
  for the external converters

0.3.4 (05.10.2013)
------------------
- added 'cleanup' API 

0.3.3 (05.10.2013)
------------------
- added 'version' and 'converter' API methods

0.3.2 (04.10.2013)
------------------
- added support EPUB conversion using ``Calibre``

0.3.1 (03.10.2013)
------------------
- updated documentation 

0.3.0 (14.07.2013)
------------------
- unoconv conversion now returns a ZIP archive
  (e.g. a HTML file + extracted images)

0.2.7 (06.07.2013)
------------------
- added support for Phantom.js converter

0.2.5 (05.07.2013)
------------------
- better detecting of prince and pdfreactor binaries

0.2.2 (05.07.2013)
------------------
- updated the documentation
- minor cleanup 

0.2.1 (04.07.2013)
------------------
- re-added poll API

0.2.0 (03.07.2013)
------------------
- converted XML-RPC api to REST api

0.1.9 (01.07.2013)
------------------
- monkeypatch pyramid_xmlrpc.parse_xmlrpc_request in order
  to by-pass its stupid DOS request body check

0.1.7 (29.06.2013)
------------------
- more tests
- fixes
- updated documentation

0.1.5 (27.06.2013)
------------------
- test for synchronous operations
- fixes

0.1.0 (24.06.2013)
------------------
- initial release
