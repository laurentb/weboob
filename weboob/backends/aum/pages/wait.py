# -*- coding: utf-8 -*-

"""
Copyright(C) 2008-2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

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
        while not self.check(self):
            sleep(10)

        self.browser.location('/home.php')

