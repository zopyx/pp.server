pp.server - Produce & Publish Server
====================================

``pp.server`` is a Pyramid based server implementation and implements the
server side functionality of the Produce & Publish platform.  It is known as
the ``Produce & Publish Server``.

The Produce & Publish Server provided web service APIs for converting
HTML/XML + assets to PDF using one of the following external PDF converters:

- PrinceXML (www.princexml.com)
- PDFreactor (www.realobjects.com)

In addition the Produce & Publish server provides a simple conversion
API for converting format A to B (as supported through LibreOffice
or OpenOffice). The conversion is build on top of ``unoconv```.

The web service provides both synchronous and asynchronous operations.

Requirements
------------

* 2.7 (no Python 3 support, no support for older Python versions)

Installation
------------

- create an ``virtualenv`` environment (Python 2.7) - either within your
  current (empty) directory or by letting virtualenv create one for you.
  (``easy_install virtualenv`` if ``virtualenv`` is not available on your
  system)::

    virtualenv --no-site-packages .

  or:: 

    virtualenv --no-site-packages pp.server

- install the Produce & Publish server::

    bin/easy_install pp.server

- create a ``server.ini`` configuration file (and change it according to your needs)::

    [DEFAULT]
    debug = true

    [app:main]
    use = egg:pp.server
    reload_templates = true
    debug_authorization = false
    debug_notfound = false

    [server:main]
    use = egg:waitress#main
    host = 127.0.0.1
    port = 6543

- start the server (in foreground)::

    bin/pserve server.ini 

- or start it in background::

    bin/pserve server.ini  --daemon

API documentation
-----------------

All API methods are available through a REST api
following API URL endpoint::

    http://host:port/api/1/<command>

With the default server configuration this translates to::

    http://localhost:6543/api/1/pdf

    or

    http://localhost:6543/api/1/unoconv


PDF conversion API
##################

Remember that all converters use HTML or XML as input for the conversion. All
input data (HTML/XML, images, stylesheets, fonts etc.) must be stored in ZIP
archive. The filename of the content **must** be named ``index.html``.

You have to ``POST`` the data to the 

    http://host:port/api/1/pdf

with the following parameters:


- ``file`` - the zip archive base64 encoded

- ``converter`` - a string that determines the the PDF
  converter to be used (either ``princexml`` or ``pdfreactor``)

- ``async`` - asynchronous ("1") or synchronous conversion ("0", default)


Returns:

The API returns its result as JSON structure with the following key-value
pairs:

- ``status`` - either ``OK`` or ``ERROR``

- ``data``- the generated PDF file encoded as base64 encoded byte string

- ``output`` - the conversion transcript (output of the converter run)


Source code
-----------

https://bitbucket.org/ajung/pp.server

Bug tracker
-----------

https://bitbucket.org/ajung/pp.server/issues?

Support
-------

Support for Produce & Publish Server is currently only available on a project
basis.

License
-------
``pp.server`` is published under the GNU Public License V2 (GPL 2).

Contact
-------

| ZOPYX Limited
| Hundskapfklinge 33
| D-72074 Tuebingen, Germany
| info@zopyx.com
| www.zopyx.com

