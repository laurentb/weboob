# -*- coding: utf-8 -*-

# Copyright(C) 2008-2011  Romain Bignon
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


from weboob.backends.aum.pages.base import PageBase
from weboob.backends.aum.exceptions import AdopteWait
from time import sleep

class WaitPage(PageBase):

    def on_loaded(self):
        raise AdopteWait()

    def check(self):
        result = self.browser.openurl('http://www.adopteunmec.com/fajax_checkEnter.php?anticache=0.46168455299380795').read()
        return result == 'Ok'

    def process_wait(self):
        while not self.check():
            sleep(10)

        self.browser.location('/home.php')

