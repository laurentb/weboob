# -*- coding: utf-8 -*-

# Copyright(C) 2011  Clément Schreiner
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

from weboob.tools.application.qt import QtApplication
from weboob.capabilities.content import ICapContent

from .main_window import MainWindow

class QWebContentEdit(QtApplication):
    APPNAME = 'qwebcontentedit'
    VERSION = '0.7.1'
    COPYRIGHT = u'Copyright(C) 2011 Clément Schreiner'
    DESCRIPTION = 'Qt application allowing to manage contents of various websites.'
    CAPS = ICapContent

    def main(self, argv):
        self.load_backends(ICapContent, storage=self.create_storage())
        self.main_window = MainWindow(self.config, self.weboob)
        self.main_window.show()
        return self.weboob.loop()


