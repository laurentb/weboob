# -*- coding: utf-8 -*-

# Copyright(C) 2011  Clément Schreiner
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

from weboob.tools.application.qt5 import QtApplication
from weboob.capabilities.content import CapContent

from .main_window import MainWindow


class QWebContentEdit(QtApplication):
    APPNAME = 'qwebcontentedit'
    VERSION = '1.5'
    COPYRIGHT = u'Copyright(C) 2011-2014 Clément Schreiner'
    DESCRIPTION = "Qt application allowing to manage content of various websites."
    SHORT_DESCRIPTION = "manage websites content"
    CAPS = CapContent

    def main(self, argv):
        self.load_backends(CapContent, storage=self.create_storage())
        main_window = MainWindow(self.config, self.weboob, self)
        main_window.show()
        return self.weboob.loop()
