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

from PyQt4.QtGui import QWidget
from PyQt4.QtCore import SIGNAL

from weboob.tools.application.qt import QtMainWindow
from weboob.tools.application.qt.backendcfg import BackendCfg
from weboob.capabilities.dating import ICapDating

try:
    from weboob.applications.qboobmsg.messages_manager import MessagesManager
    HAVE_BOOBMSG = True
except ImportError:
    HAVE_BOOBMSG = False

from .ui.main_window_ui import Ui_MainWindow
from .status import AccountsStatus
from .contacts import ContactsWidget

class MainWindow(QtMainWindow):
    def __init__(self, config, weboob, parent=None):
        QtMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.config = config
        self.weboob = weboob

        self.loaded_tabs = {}

        self.ui.tabWidget.addTab(AccountsStatus(self.weboob), self.tr('Status'))
        if HAVE_BOOBMSG:
            self.ui.tabWidget.addTab(MessagesManager(self.weboob), self.tr('Messages'))
        self.ui.tabWidget.addTab(ContactsWidget(self.weboob), self.tr('Contacts'))
        self.ui.tabWidget.addTab(QWidget(), self.tr('Calendar'))

        self.connect(self.ui.actionBackends, SIGNAL("triggered()"), self.backendsConfig)
        self.connect(self.ui.tabWidget, SIGNAL('currentChanged(int)'), self.tabChanged)

    def backendsConfig(self):
        bckndcfg = BackendCfg(self.weboob, (ICapDating,), self)
        bckndcfg.show()

    def tabChanged(self, i):
        widget = self.ui.tabWidget.currentWidget()

        if hasattr(widget, 'load') and not i in self.loaded_tabs:
            widget.load()
            self.loaded_tabs[i] = True
