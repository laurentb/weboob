#!/usr/bin/env python
import sys
from weboob.tools.browser import StandardBrowser

print StandardBrowser()._certhash(sys.argv[1])
