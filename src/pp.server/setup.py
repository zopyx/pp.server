import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()

requires = [
    'pyramid',
    'pyramid_debugtoolbar',
    'pyramid_xmlrpc',
    'waitress',
    'sqlalchemy',
    'celery',
    'flower',
    'pastescript',
    'waitress',
    'plac',
    ]

tests_require = [
    'webtest',
]

setup(name='pp.server',
      version='0.1.5',
      description='pp.server - Produce & Publish Server',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='Andreas Jung',
      author_email='info@zopyx.com',
      url='http://pypi.python.org/pypi/pp.server',
      keywords='web pyramid pylons',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=tests_require,
      test_suite="pp.server",
      extras_require={
          'testing': tests_require,
      },
      entry_points="""\
      [paste.app_factory]
      main = pp.server:main
      [console_scripts]
      service-client = pp.server.scripts.service_client:main
      worker = pp.server.scripts.worker:main
      """,
      )
