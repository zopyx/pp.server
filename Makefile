sdist:
	rm -fr dist/*
	bin/python setup.py sdist

release:
	bin/pip install jarn.mkrelease
	bin/mkrelease -p -d pypi

docs:
	cd docs; make html

upload-docs:
	bin/python setup.py upload_docs --upload-dir docs/build/html

test-install: sdist
	rm -fr /tmp/pp.server
	virtualenv-3.4 /tmp/pp.server
	ls dist
	find dist -name pp.server-\* -exec cp {} /tmp/pp.server.tgz \;
	/tmp/pp.server/bin/pip install /tmp/pp.server.tgz
	cp development.ini /tmp/development.ini
	/tmp/pp.server/bin/pserve /tmp/development.ini
