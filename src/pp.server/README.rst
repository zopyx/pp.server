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

Requirements
------------

* Python 2.6, 2.7 (no Python 3 support)

Installation
------------

- create an ``virtualenv`` environment (Python 2.6 or 2.7) - either within your
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
    use = egg:pp..server#app
    reload_templates = true
    debug_authorization = false
    debug_notfound = false

    [server:main]
    use = egg:Paste#http
    host = 127.0.0.1
    port = 6543

- start the server (in foreground)::

    bin/pserve server.ini 

- or start it in background::

    bin/pserve server.ini  --daemon

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

