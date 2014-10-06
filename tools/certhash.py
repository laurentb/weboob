#!/usr/bin/env python
from __future__ import print_function
import sys
from weboob.tools.browser import StandardBrowser

print(StandardBrowser()._certhash(sys.argv[1]))
