Docker image for Produce & Publish Server + Speedata Publisher
==============================================================

Build
-----

::

    docker build -t pp-server-speedata .

Run
---

::

    docker run -p 8000:8000 --volume /my/local/var/folder:/pp-server/var pp-server-speedata

The server listens on port 8000 (hypercorn, HTTP/2 capable).
Access the REST API at http://localhost:8000.
Interactive API docs: http://localhost:8000/docs.
