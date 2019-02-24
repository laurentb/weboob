# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


from weboob.capabilities.messages import CapMessages
from weboob.tools.application.qt5 import QtApplication

from .main_window import MainWindow


class QBoobMsg(QtApplication):
    APPNAME = 'qboobmsg'
    VERSION = '1.5'
    COPYRIGHT = 'Copyright(C) 2010-YEAR Romain Bignon'
    DESCRIPTION = "Qt application allowing to read messages on various websites and reply to them."
    SHORT_DESCRIPTION = "send and receive message threads"
    CAPS = CapMessages

    def main(self, argv):
        self.load_backends(CapMessages, storage=self.create_storage())

        main_window = MainWindow(self.config, self.weboob)
        main_window.show()
        return self.weboob.loop()
