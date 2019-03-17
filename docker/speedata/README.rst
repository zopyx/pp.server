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
`--volume` option when you run the Docker image. The exported volume name is
`/pp-server/var`.  The usage of an external spool directory is recommended in
order to access the logfile `gunicorn.log` easily in case of error or for
debugging purposes.

The `-p|--port` option is need to expose the REST API endpoint to the Docker host.

.. code::

    docker run -p 6543:6543 --volume /my/local/var/folder:/pp-server/var zopyx/pp-server-speedata 

The output should be like this::

    latest: Pulling from zopyx/pp-server-speedata
    2ec1fbfd44b7: Pull complete
    6e1685b014c5: Pull complete
    dbcba25ba0b5: Pull complete
    f1458f3f6f08: Pull complete
    b61fefd0e5b6: Pull complete
    7b49d48f271b: Pull complete
    Digest: sha256:77cfe295e921d4bd71a6c7641556edcc0f383546ff9ae2f24a88df3f70c27f01
    Status: Downloaded newer image for zopyx/pp-server-speedata:latest
    2019-03-11 07:23:58 circus[1] [INFO] Starting master on pid 1
    2019-03-11 07:23:58 circus[1] [INFO] Arbiter now waiting for commands
    2019-03-11 07:23:58 circus[1] [INFO] gunicorn started
    [2019-03-11 07:23:58 +0000] [10] [INFO] Starting gunicorn 19.9.0
    [2019-03-11 07:23:58 +0000] [10] [INFO] Listening at: http://0.0.0.0:6543 (10)
    [2019-03-11 07:23:58 +0000] [10] [INFO] Using worker: sync
    [2019-03-11 07:23:58 +0000] [13] [INFO] Booting worker with pid: 13
    [2019-03-11 07:23:58 +0000] [14] [INFO] Booting worker with pid: 14
    2019-03-11 07:23:58,863 INFO  [root:35][MainThread] Installed: publisher
    2019-03-11 07:23:58,863 INFO  [root:39][MainThread] Remote execution enabled: False
    2019-03-11 07:23:58,867 INFO  [root:35][MainThread] Installed: publisher
    2019-03-11 07:23:58,867 INFO  [root:39][MainThread] Remote execution enabled: False


Access
------

Access the Produce & Publish server on http://localhost:6543
