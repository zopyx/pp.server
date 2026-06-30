################################################################
# pp.server - Produce & Publish Server
# (C) 2021, ZOPYX,  Tuebingen, Germany
################################################################
"""Package-wide logger singleton.

Provides a pre-configured Loguru logger instance imported as ``LOG``
throughout the application. Configure via Loguru's standard methods
(e.g. ``LOG.add("file.log")``).
"""

from loguru import logger as LOG  # noqa
