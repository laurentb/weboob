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

from PyQt4.QtGui import QDialog, QTableWidgetItem, QLabel, QLineEdit, QCheckBox, QMessageBox
from PyQt4.QtCore import SIGNAL, Qt

import re
from logging import warning

from weboob.tools.application.qt.backendcfg_ui import Ui_BackendCfg

class BackendCfg(QDialog):
    def __init__(self, weboob, caps=None, parent=None):
        QDialog.__init__(self, parent)
        self.ui = Ui_BackendCfg()
        self.ui.setupUi(self)

        self.weboob = weboob
        self.caps = caps
        self.config_widgets = {}

        self.weboob.modules_loader.load()

        self.ui.configFrame.hide()

        for name, module in self.weboob.modules_loader.modules.iteritems():
            if not self.caps or module.has_caps(*self.caps):
                self.ui.modulesList.addItem(name.capitalize())

        self.loadBackendsList()

        self.connect(self.ui.backendsList, SIGNAL('cellClicked(int, int)'), self.backendClicked)
        self.connect(self.ui.modulesList, SIGNAL('itemSelectionChanged()'), self.modulesSelectionChanged)
        self.connect(self.ui.proxyBox, SIGNAL('toggled(bool)'), self.proxyEditEnabled)
        self.connect(self.ui.addButton, SIGNAL('clicked()'), self.addEvent)
        self.connect(self.ui.removeButton, SIGNAL('clicked()'), self.removeEvent)
        self.connect(self.ui.configButtonBox, SIGNAL('accepted()'), self.acceptBackend)
        self.connect(self.ui.configButtonBox, SIGNAL('rejected()'), self.rejectBackend)

    def loadBackendsList(self):
        self.ui.backendsList.clearContents()
        for instance_name, name, params in self.weboob.backends_config.iter_backends():
            self.ui.backendsList.insertRow(0)
            self.ui.backendsList.setItem(0, 0, QTableWidgetItem(instance_name))
            self.ui.backendsList.setItem(0, 1, QTableWidgetItem(name))

    def closeEvent(self, event):
        event.accept()

    def backendClicked(self, row, col):
        bname = unicode(self.ui.backendsList.item(row, 0).text())

        self.editBackend(bname)

    def addEvent(self):
        self.editBackend()

    def removeEvent(self):
        item = self.ui.backendsList.currentItem()
        if not item:
            return

        bname = unicode(self.ui.backendsList.item(item.row(), 0).text())
        reply = QMessageBox.question(self, self.tr('Remove a backend'),
                                     unicode(self.tr("Are you sure you want to remove the backend '%s'?")) % bname,
                                     QMessageBox.Yes|QMessageBox.No)

        if reply != QMessageBox.Yes:
            return

        self.weboob.backends_config.remove_backend(bname)
        self.loadBackendsList()

    def editBackend(self, bname=None):
        self.ui.configFrame.show()

        if bname is not None:
            mname, params = self.weboob.backends_config.get_backend(bname)

            items = self.ui.modulesList.findItems(mname, Qt.MatchFixedString)
            if not items:
                print 'Module not found'
            else:
                self.ui.modulesList.setCurrentItem(items[0])
                self.ui.modulesList.setEnabled(False)

            self.ui.nameEdit.setText(bname)
            self.ui.nameEdit.setEnabled(False)
            if '_proxy' in params:
                self.ui.proxyBox.setChecked(True)
                self.ui.proxyEdit.setText(params.pop('_proxy'))
            else:
                self.ui.proxyBox.setChecked(False)
                self.ui.proxyEdit.clear()

            for key, value in params.iteritems():
                l, widget = self.config_widgets[key]
                if isinstance(widget, QLineEdit):
                    widget.setText(unicode(value))
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(value.lower() in ('1', 'true', 'yes', 'on'))
                else:
                    warning('Unknown type field "%s": %s', key, widget)
        else:
            self.ui.nameEdit.clear()
            self.ui.nameEdit.setEnabled(True)
            self.ui.proxyBox.setChecked(False)
            self.ui.proxyEdit.clear()
            self.ui.modulesList.setEnabled(True)
            self.ui.modulesList.setCurrentRow(-1)

    def acceptBackend(self):
        bname = unicode(self.ui.nameEdit.text())
        selection = self.ui.modulesList.selectedItems()

        if not selection:
            QMessageBox.critical(self, self.tr('Unable to add a backend'),
                                       self.tr('Please select a module'))
            return

        module = self.weboob.modules_loader.modules[unicode(selection[0].text()).lower()]

        params = {}
        missing = []

        if not bname:
            missing.append(self.tr('Name'))

        if self.ui.proxyBox.isChecked():
            params['_proxy'] = unicode(self.ui.proxyEdit.text())
            if not params['_proxy']:
                missing.append(self.tr('Proxy'))

        for key, field in module.get_config().iteritems():
            label, value = self.config_widgets[key]

            if isinstance(value, QLineEdit):
                params[key] = unicode(value.text())
            elif isinstance(value, QCheckBox):
                params[key] = '1' if value.isChecked() else '0'
            else:
                warning('Unknown type field "%s": %s', key, value)

            if not params[key]:
                params[key] = field.default

            if not params[key]:
                missing.append(field.description)
            elif field.regexp and not re.match(field.regexp, params[key]):
                QMessageBox.critical(self,
                                     self.tr('Invalid value'),
                                     unicode(self.tr('Invalid value for field "%s":\n\n%s')) % (field.description, params[key]))
                return

        if missing:
            QMessageBox.critical(self,
                                 self.tr('Missing fields'),
                                 unicode(self.tr('Please set a value in this fields:\n%s')) % ('\n'.join(['- %s' % s for s in missing])))
            return

        self.weboob.backends_config.add_backend(bname, module.get_name(), params, edit=not self.ui.nameEdit.isEnabled())
        self.ui.configFrame.hide()

        self.loadBackendsList()

    def rejectBackend(self):
        self.ui.configFrame.hide()

    def modulesSelectionChanged(self):
        for key, (label, value) in self.config_widgets.iteritems():
            label.hide()
            value.hide()
            self.ui.configLayout.removeWidget(label)
            self.ui.configLayout.removeWidget(value)
        self.config_widgets.clear()
        self.ui.moduleInfo.clear()

        selection = self.ui.modulesList.selectedItems()
        if not selection:
            return

        module = self.weboob.modules_loader.modules[unicode(selection[0].text()).lower()]
        self.ui.moduleInfo.setText(unicode(self.tr(
                                   '<h1>Module %s</h1>'
                                   '<b>Version</b>: %s<br />'
                                   '<b>Maintainer</b>: %s<br />'
                                   '<b>License</b>: %s<br />'
                                   '<b>Description</b>: %s<br />'
                                   '<b>Capabilities</b>: %s<br />'))
                                   % (module.get_name().capitalize(),
                                      module.get_version(),
                                      module.get_maintainer().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'),
                                      module.get_license(),
                                      module.get_description(),
                                      ', '.join([cap.__name__ for cap in module.iter_caps()])))

        for key, field in module.get_config().iteritems():
            label = QLabel(u'%s:' % field.description)
            if isinstance(field.default, bool):
                value = QCheckBox()
                if field.default:
                    value.setChecked(True)
            else:
                value = QLineEdit()
                if field.default is not None:
                    value.setText(unicode(field.default))
                if field.is_masked:
                    value.setEchoMode(value.Password)
            self.ui.configLayout.addRow(label, value)
            self.config_widgets[key] = (label, value)

    def proxyEditEnabled(self, state):
        self.ui.proxyEdit.setEnabled(state)

if __name__ == '__main__':
    from PyQt4.QtGui import QApplication
    from weboob import Weboob
    import sys

    app = QApplication(sys.argv)
    weboob = Weboob()
    weboob.load_backends()

    dlg = BackendCfg(weboob)
    dlg.show()
    app.exec_()
