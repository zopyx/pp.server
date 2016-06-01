0.7.10 (2016/06/01)
------------------
- updated to Pyramid 1.7

0.7.7 (2016/01/24)
------------------
- updated support for latest Vivliostyle formatter
- added support for Antennahouse Formatter

0.7.6 (2015/11/30)
------------------
- support for PDFreactor 8

0.7.5 (2015/11/18)
------------------
- fixed race condition while creating directories

0.7.4 (2015/11/14)
------------------
- support for nested uploaded ZIP files

0.7.3 (2015/11/14)
------------------
- support for Vivliostyle Formatter

0.7.2 (2015/04/20)
------------------
- merged https://bitbucket.org/ajung/pp.server/pull-request/1/
  (improper check for wkhtmltopdf)
- merged https://bitbucket.org/ajung/pp.server/pull-request/2/
  (fix for async operations)

0.7.1 (2015/03/13)
------------------
- unicode fix in runcmd()

0.7.0 (2015/02/15)
------------------

- 0.6.x was completely badly packaged
- changed repo structure

0.6.1 (2015/02/02)
------------------
- add /api/converter-versions to webservice API

0.6.0 (2015/01/26)
------------------
- dropped Python 2.X support, Python 3.3 or higher 
  is now a mandatory requirement

0.5.5 (2015/01/23)
------------------
- UTF8 handling fix

0.5.3 (2014/11/23)
------------------
- support for WKHTMLTOPDF

0.5.2 (2014/11/19)
------------------
- support for Speedata Publisher 

0.5.1 (2014/10/12)
------------------
- improved error handling

0.5.0 (2014/10/12)
------------------
- official Python 3.3/3.4 support 

0.4.7 (25.09.2014)
------------------
- fixed documentation bug

0.4.6 (22.08.2014)
------------------
- removed PDFreactor --addlog option

0.4.5 (22.08.2014)
------------------
- added supplementary commandline options to pdfreactor commandline call

0.4.4 (24.01.2014)
------------------
- minor typos fixed

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
