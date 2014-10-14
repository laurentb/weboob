# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon, Laurent Bachelier
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

import sys
from random import choice
from unittest import TestCase

from weboob.core import Weboob

# This is what nose does for Python 2.6 and lower compatibility
# We do the same so nose becomes optional
try:
    from unittest.case import SkipTest
except:
    from nose.plugins.skip import SkipTest


__all__ = ['BackendTest', 'SkipTest']


class BackendTest(TestCase):
    MODULE = None

    def __init__(self, *args, **kwargs):
        TestCase.__init__(self, *args, **kwargs)

        self.backends = {}
        self.backend_instance = None
        self.backend = None
        self.weboob = Weboob()

        if self.weboob.load_backends(modules=[self.MODULE]):
            # provide the tests with all available backends
            self.backends = self.weboob.backend_instances
            # chose one backend (enough for most tests)
            self.backend_instance = choice(self.backends.keys())
            self.backend = self.backends[self.backend_instance]

    def run(self, result):
        """
        Call the parent run() for each backend instance.
        Skip the test if we have no backends.
        """
        # This is a hack to fix an issue with nosetests running
        # with many tests. The default is 1000.
        sys.setrecursionlimit(10000)
        try:
            if not len(self.backends):
                result.startTest(self)
                result.stopTest(self)
                raise SkipTest('No backends configured for this module.')
            TestCase.run(self, result)
        finally:
            self.weboob.deinit()

    def shortDescription(self):
        """
        Generate a description with the backend instance name.
        """
        # do not use TestCase.shortDescription as it returns None
        return '%s [%s]' % (str(self), self.backend_instance)
