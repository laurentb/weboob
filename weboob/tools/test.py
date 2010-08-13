# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

from unittest import TestCase
from nose.plugins.skip import SkipTest
from weboob.core import Weboob


__all__ = ['TestCase', 'BackendTest']

class BackendTest(TestCase):
    BACKEND = None

    def __init__(self, *args, **kwargs):
        TestCase.__init__(self, *args, **kwargs)

        self.backend = None
        self.weboob = Weboob()

        if self.weboob.load_configured_backends(modules=[self.BACKEND]):
            self.backend = self.weboob.backend_instances.values()[0]

    def run(self, result):
        if not self.backend:
            result.startTest(self)
            result.stopTest(self)
            raise SkipTest()

        return TestCase.run(self, result)
