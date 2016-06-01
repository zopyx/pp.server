import os
import sys

if sys.version_info[:2] not in ((3,3), (3,4), (3,5), (3,6)):
    raise RuntimeError('pp.server requires Python 3.3 or higher')

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'docs', 'source', 'README.rst')).read()
CHANGES = open(os.path.join(here, 'docs', 'source', 'CHANGES.rst')).read()

requires = [
    'pyramid',
    'pyramid_chameleon',
    'waitress',
    'sqlalchemy',
    'celery',
    'flower',
    'waitress',
    'plac',
    'pp.client-python'
    ]

tests_require = [
    'webtest',
]

setup(name='pp.server',
      version='0.7.10',
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
      keywords='web pyramid pdf unoconv conversion princexml pdfreactor',
      packages=find_packages(),
      namespace_packages=['pp'],
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=tests_require,
      test_suite="pp.server",
      extras_require={
          'testing': tests_require,
      },
      entry_points="""\
      [console_scripts]
      unoconv = pp.server.unoconv:main
      pdfreactor8=pp.server.pdfreactor8:main
      [paste.app_factory]
      main = pp.server:main
      """,
      )

