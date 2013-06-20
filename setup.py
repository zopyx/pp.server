import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    'pyramid',
    'pyramid_debugtoolbar',
    'waitress',
    'pymongo',
    'requests',
    'cssselect',
    'celery',
    'flower',
    'plac',
    ]

setup(name='pp.server',
      version='0.1',
      description='pp.server',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='web pyramid pylons',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      test_suite="ppserver",
      entry_points="""\
      [paste.app_factory]
      main = ppserver:main
      [console_scripts]
      service-client = ppserver.scripts.service_client:main
      worker = ppserver.scripts.worker:main
      """,
      )
