# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Veyssier
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


from weboob.capabilities.recipe import CapRecipe
from weboob.tools.application.qt5 import QtApplication

from .main_window import MainWindow


class QCookboob(QtApplication):
    APPNAME = 'qcookboob'
    VERSION = '1.5'
    COPYRIGHT = 'Copyright(C) 2013-2014 Julien Veyssier'
    DESCRIPTION = "Qt application allowing to search recipes."
    SHORT_DESCRIPTION = "search recipes"
    CAPS = CapRecipe
    CONFIG = {'settings': {'backend': '',
                           'maxresultsnumber': '10'
                           }
              }

    def main(self, argv):
        self.load_backends([CapRecipe])
        self.load_config()

        main_window = MainWindow(self.config, self.weboob, self)
        main_window.show()
        return self.weboob.loop()
