Docker image for Produce & Publish Server + Speedata Publisher
==============================================================

Clean build
-----------

.. code::

    make build-clean

Standard build
--------------

.. code::

    make build


Run
---

It is possible to use the container for storing the temporary files (container
will grow over time) or you specify an external spool directory using the
`--volume` option when you run the Docker image. The usage of an external spool directory
is recommended in order to access the logfile `gunicorn.log` easily in case of error
or for debugging purposes.

The `-p|--port` option is need to expose the REST API endpoint to the Docker host.

.. code::

    run docker -p 6543:6543 --volume /my/local/var/folder:/pp-server/var zopyx/pp-server-speedata 


Access
------

Access the Produce & Publish server on http://localhost:6543
