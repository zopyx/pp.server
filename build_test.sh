#!/bin/bash

export PATH=\
/opt/buildout.python/bin:\
$PATH:

if [[ "$1" = "python-2.6" ]]
then
    python_version=2.6
fi

if [[ "$1" = "python-2.7" ]]
then
    python_version=2.7
fi

virtualenv-$python_version .
bin/python bootstrap.py
bin/buildout
bin/py.test src/pp.server --junitxml=jenkins.xml

