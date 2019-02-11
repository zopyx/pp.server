pp.server - Produce & Publish Server
====================================

``pp.server`` is a Pyramid based server implementation and implements the
server side functionality of the Produce & Publish platform.  It is known as
the ``Produce & Publish Server``.

The Produce & Publish Server provided web service APIs for converting
HTML/XML + assets to PDF using one of the following external PDF converters:

- PrinceXML (www.princexml.com, commercial)
- PDFreactor (www.realobjects.com, commercial)
- PhantomJS (free, unsupported)  
- Speedata Publisher (www.speedata.de, open-source, experimental support)
- WKHTMLTOPDF (www.wkhtmltopdf.org, open-source, experimental support)
- Vivliostyle Formatter (www.vivliostyle.com, commercial, experimental support)
- VersaType Formatter (www.trim-marks.com, commercial, experimental support)
- Antennahouse 6.6 (www.antennahouse.com, commercial)
- Weasyprint (free, unsupported)

In addition there is experimental support for generating EPUB documents
using ``Calibre`` (www.calibre.org, open-source).

In addition the Produce & Publish server provides a simple conversion
API for converting format A to B (as supported through LibreOffice
or OpenOffice). The conversion is build on top of ``unoconv``.

The web service provides only synchronous operation.

Requirements
------------

- Python 3.6 or higher, no support for Python 2.x

- the external binaries 

  - PrinceXML: ``prince``, 
  - PDFreactor up to version 7: ``pdfreactor``,  
  - PDFreactor version 8 or higher: ``pdfreactor.py``,  
  - Unoconv: ``unoconv`` 
  - Speedata Publisher: ``sp``
  - Calibre: ``ebook-convert``
  - WKHTMLTOPDF: ``wkhtmltopdf``    
  - Vivliostyle: ``vivliostyle-formatter``    
  - VersaType : ``versatype-converter``    
  - Weasyprint: ``weasyprint``    
  - Antennahouse: ``run.sh``    

  must be in the $PATH. Please refer to the installation documentation
  of the individual products.

Installation
------------

- create a Python 3  virtual environment using::

    python3 -m venv pp.server

- install the Produce & Publish server::

    bin/pip install pp.server

- create a ``server.ini`` configuration file (and change it according to your needs)::

    [DEFAULT]
    debug = true

    [app:main]
    use = egg:pp.server
    reload_templates = true
    debug_authorization = false
    debug_notfound = false

    [server:main]
    use = egg:gunicorn#main
    host = 0.0.0.0
    port = 6543



    [loggers]
    keys = root, myproject

    [handlers]
    keys = console, logfile

    [formatters]
    keys = generic, form01

    [formatter_form01]
    format = %(asctime)s %(levelname)-5.5s [%(name)s:%(lineno)s][%(threadName)s] %(message)s
    datefmt=
    class=logging.Formatter

    [logger_root]
    level = INFO
    handlers = console, logfile

    [logger_myproject]
    level = DEBUG
    handlers =
    qualname = myproject


    [handler_console]
    class = StreamHandler
    args = (sys.stderr,)
    level = NOTSET
    formatter = form01

    [handler_logfile]
    class = FileHandler
    level = INFO
    formatter = form01
    args=('var/gunicorn.log', 'w')

    [formatter_generic]
    format = %(asctime)s %(levelname)-5.5s [%(name)s:%(lineno)s][%(threadName)s] %(message)s

- create a ``circusd.ini`` configuration file (and change it according to your needs)::

    [watcher:gunicorn]
    cmd = bin/gunicorn --paste server.ini

    [env:gunicorn]
    PATH = $PATH
    TZ = $TZ

 
- both configuration files can be created automatically using the helper script::

    bin/pp-server-templates

- start the server (in foreground)::

    bin/gunicorn --paste server.ini 

- or start it in background::

    bin/circusd circusd.ini  --daemon

Converter requirements
----------------------

For the PDF conversion the related converter binaries or scripts
must be included in the ``$PATH`` of your server.

- ``prince`` for PrinceXML

- ``pdfreactor`` for PDFreactor 7

- ``pdfreactor8`` for PDFreactor 8 or higher

- ``phantomjs`` for PhantomJS

- ``wkhtmltopdf`` for WKHTMLToPDF

- ``ebook-convert`` for Calibre

- ``sp`` for the Speedata Publisher

- ``vivliostyle`` for the Vivliostyle formatter

- ``versatype`` for the Versatype converter

- ``weasyprint`` for Weasyprint

- ``antennahouse`` for the Antennahouse

API documentation
-----------------

All API methods are available through a REST api
following API URL endpoint::

    http://host:port/api/1/<command>

With the default server configuration this translates to::

    http://localhost:6543/api/1/pdf

    or

    http://localhost:6543/api/1/unoconv

Environment variables
+++++++++++++++++++++

`pp.server` uses the `var` folder of the installation directory by default as
temporary folder for conversion data. Set the environment variable `PP_SPOOL_DIRECTORY` 
if you need different spool directory instead. 

If you run PDFreactor 10 or higher under Docker then you must set the environment
variable `PP_PDFREACTOR_DOCKER=1` in order to generated a proper `file:///docs/...`
URI for `pdfreactor.py`.


PDF conversion API
++++++++++++++++++

Remember that all converters use HTML or XML as input for the conversion. All
input data (HTML/XML, images, stylesheets, fonts etc.) must be stored in ZIP
archive. The filename of the content **must** be named ``index.html``.

You have to ``POST`` the data to the 

    http://host:port/api/1/pdf

with the following parameters:


- ``file`` - the ZIP archive (multi/part encoding)

- ``converter`` - a string that determines the the PDF
  converter to be used (either ``princexml``, ``pdfreactor``, ``phantomjs``, ``vivliostyle``, ``versatype``, 
  or ``calibre`` for generating EPUB content)

- ``cmd_options`` - an optional string of command line parameters added 
  as given to the calls of the externals converters


Returns:

The API returns its result as JSON structure with the following key-value
pairs:

- ``status`` - either ``OK`` or ``ERROR``

- ``data``- the generated PDF file encoded as base64 encoded byte string

- ``output`` - the conversion transcript (output of the converter run)

  
Unoconv conversion API
++++++++++++++++++++++

The unoconv web service wraps the OpenOffice/LibreOffice server mode
in order to perform document conversion (mainly used in the Produce & Publish
world for convertering DOC(X) documents to HTML/XML).

Remember that all converters use HTML or XML as input for the conversion. All
input data (HTML/XML, images, stylesheets, fonts etc.) must be stored in ZIP
archive. The filename of the content **must** be named ``index.html``.

You have to ``POST`` the data to the 

    http://host:port/api/1/unoconv

with the following parameters:


- ``file`` - the source files (multi/part encoding)

- ``cmd_options`` - an optional string of command line parameters added 
  as given to the ``unoconv`` calls

Returns:

The API returns its result as JSON structure with the following key-value
pairs:

- ``status`` - either ``OK`` or ``ERROR``

- ``data`` - the converted output files as ZIP archive (e.g.
  a DOCX file containing images will be converted to a HTML file
  plus the list of extract image files)

- ``output`` - the conversion transcript (output of the converter run)

Introspection API methods
+++++++++++++++++++++++++

Produce & Publish server version:

    http://host:port/api/version

returns:

    {"version": "0.3.2", "module": "pp.server"}
   
Installed/available converters:

    http://host:port/api/converters

returns:

    {"unoconv": true, "pdfreactor": true, "phantomjs": false, "calibre": true, "princexml": true}


Versions of installed converter:

    http://host:port/api/converter-versions

returns:

    {'princexml': 'Version x.y', 'pdfreactor: 'Version a.b.c', ...}


Other API methods
+++++++++++++++++

Cleanup of the queue directory (removes conversion data older than one day)

    http://host:port/api/cleanup

returns:

    {"directories_removed": 22}


Advanced installation issues
----------------------------

Installation of PDFreactor using zc.buildout
++++++++++++++++++++++++++++++++++++++++++++

- https://bitbucket.org/ajung/pp.server/raw/master/pdfreactor.cfg

Installation of PrinceXML using zc.buildout
+++++++++++++++++++++++++++++++++++++++++++

- https://bitbucket.org/ajung/pp.server/raw/master/princexml.cfg

- https://bitbucket.org/ajung/pp.server/raw/master/circus-app.ini

Source code
-----------

https://bitbucket.org/ajung/pp.server

Bug tracker
-----------

https://bitbucket.org/ajung/pp.server/issues

Support
-------

Support for Produce & Publish Server is currently only available on a project
basis.

License
-------
``pp.server`` is published under the GNU Public License V2 (GPL 2).

Contact
-------

| ZOPYX 
| Hundskapfklinge 33
| D-72074 Tuebingen, Germany
| info@zopyx.com
| www.zopyx.com
| www.produce-and-publish.info
