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

from PyQt4.QtGui import QDialog, QTreeWidgetItem, QLabel, QLineEdit, QCheckBox, \
                        QMessageBox, QPixmap, QImage, QIcon, QHeaderView, \
                        QListWidgetItem, QTextDocument, QComboBox
from PyQt4.QtCore import SIGNAL, Qt, QVariant, QUrl

import re
from logging import warning

from weboob.tools.application.qt.backendcfg_ui import Ui_BackendCfg

class BackendCfg(QDialog):
    def __init__(self, weboob, caps=None, parent=None):
        QDialog.__init__(self, parent)
        self.ui = Ui_BackendCfg()
        self.ui.setupUi(self)

        self.to_unload = set()
        self.to_load = set()

        self.weboob = weboob
        self.caps = caps
        self.config_widgets = {}

        self.weboob.backends_loader.load_all()

        self.ui.configuredBackendsList.header().setResizeMode(QHeaderView.ResizeToContents)
        self.ui.configFrame.hide()

        for name, backend in self.weboob.backends_loader.loaded.iteritems():
            if not self.caps or backend.has_caps(*self.caps):
                item = QListWidgetItem(name.capitalize())

                if backend.icon_path:
                    img = QImage(backend.icon_path)
                    item.setIcon(QIcon(QPixmap.fromImage(img)))

                self.ui.backendsList.addItem(item)

        self.loadConfiguredBackendsList()

        self.connect(self.ui.configuredBackendsList, SIGNAL('itemClicked(QTreeWidgetItem *, int)'), self.configuredBackendClicked)
        self.connect(self.ui.configuredBackendsList, SIGNAL('itemChanged(QTreeWidgetItem *, int)'), self.configuredBackendEnabled)
        self.connect(self.ui.backendsList, SIGNAL('itemSelectionChanged()'), self.backendSelectionChanged)
        self.connect(self.ui.proxyBox, SIGNAL('toggled(bool)'), self.proxyEditEnabled)
        self.connect(self.ui.addButton, SIGNAL('clicked()'), self.addEvent)
        self.connect(self.ui.removeButton, SIGNAL('clicked()'), self.removeEvent)
        self.connect(self.ui.configButtonBox, SIGNAL('accepted()'), self.acceptBackend)
        self.connect(self.ui.configButtonBox, SIGNAL('rejected()'), self.rejectBackend)

    def loadConfiguredBackendsList(self):
        self.ui.configuredBackendsList.clear()
        for instance_name, name, params in self.weboob.backends_config.iter_backends():
            if name not in self.weboob.backends_loader.loaded:
                continue
            backend = self.weboob.backends_loader.loaded[name]
            if self.caps and not backend.has_caps(*self.caps):
                continue

            item = QTreeWidgetItem(None, [instance_name, name])
            item.setCheckState(0, Qt.Checked if params.get('_enabled', '1').lower() in ('1', 'y', 'true') else Qt.Unchecked)

            if backend.icon_path:
                img = QImage(backend.icon_path)
                item.setIcon(0, QIcon(QPixmap.fromImage(img)))

            self.ui.configuredBackendsList.addTopLevelItem(item)

    def configuredBackendEnabled(self, item, col):
        instname = unicode(item.text(0))
        bname = unicode(item.text(1))
        if item.checkState(0) == Qt.Checked:
            self.to_load.add(instname)
            enabled = '1'
        else:
            self.to_unload.add(instname)
            try:
                self.to_load.remove(instname)
            except KeyError:
                pass
            enabled = '0'

        self.weboob.backends_config.edit_backend(instname, bname, {'_enabled': enabled})

    def configuredBackendClicked(self, item, col):
        bname = unicode(item.text(0))

        self.editBackend(bname)

    def addEvent(self):
        self.editBackend()

    def removeEvent(self):
        item = self.ui.configuredBackendsList.currentItem()
        if not item:
            return

        bname = unicode(item.text(0))
        reply = QMessageBox.question(self, self.tr('Remove a backend'),
                                     unicode(self.tr("Are you sure you want to remove the backend '%s'?")) % bname,
                                     QMessageBox.Yes|QMessageBox.No)

        if reply != QMessageBox.Yes:
            return

        self.weboob.backends_config.remove_backend(bname)
        self.to_unload.add(bname)
        try:
            self.to_load.remove(bname)
        except KeyError:
            pass
        self.ui.configFrame.hide()
        self.loadConfiguredBackendsList()

    def editBackend(self, bname=None):
        self.ui.configFrame.show()

        if bname is not None:
            mname, params = self.weboob.backends_config.get_backend(bname)

            items = self.ui.backendsList.findItems(mname, Qt.MatchFixedString)
            if not items:
                warning('Backend not found')
            else:
                self.ui.backendsList.setCurrentItem(items[0])
                self.ui.backendsList.setEnabled(False)

            self.ui.nameEdit.setText(bname)
            self.ui.nameEdit.setEnabled(False)
            if '_proxy' in params:
                self.ui.proxyBox.setChecked(True)
                self.ui.proxyEdit.setText(params.pop('_proxy'))
            else:
                self.ui.proxyBox.setChecked(False)
                self.ui.proxyEdit.clear()

            params.pop('_enabled', None)

            for key, value in params.iteritems():
                l, widget = self.config_widgets[key]
                if isinstance(widget, QLineEdit):
                    widget.setText(unicode(value))
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(value.lower() in ('1', 'true', 'yes', 'on'))
                elif isinstance(widget, QComboBox):
                    for i in xrange(widget.count()):
                        if unicode(widget.itemData(i).toString()) == value:
                            widget.setCurrentIndex(i)
                            break
                else:
                    warning('Unknown type field "%s": %s', key, widget)
        else:
            self.ui.nameEdit.clear()
            self.ui.nameEdit.setEnabled(True)
            self.ui.proxyBox.setChecked(False)
            self.ui.proxyEdit.clear()
            self.ui.backendsList.setEnabled(True)
            self.ui.backendsList.setCurrentRow(-1)

    def acceptBackend(self):
        bname = unicode(self.ui.nameEdit.text())
        selection = self.ui.backendsList.selectedItems()

        if not selection:
            QMessageBox.critical(self, self.tr('Unable to add a configured backend'),
                                       self.tr('Please select a backend'))
            return

        backend = self.weboob.backends_loader.loaded[unicode(selection[0].text()).lower()]

        params = {}
        missing = []

        if not bname:
            missing.append(self.tr('Name'))

        if self.ui.proxyBox.isChecked():
            params['_proxy'] = unicode(self.ui.proxyEdit.text())
            if not params['_proxy']:
                missing.append(self.tr('Proxy'))

        for key, field in backend.config.iteritems():
            label, value = self.config_widgets[key]

            if isinstance(value, QLineEdit):
                params[key] = unicode(value.text())
            elif isinstance(value, QCheckBox):
                params[key] = '1' if value.isChecked() else '0'
            elif isinstance(value, QComboBox):
                params[key] = unicode(value.itemData(value.currentIndex()).toString())
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

        self.weboob.backends_config.add_backend(bname, backend.name, params, edit=not self.ui.nameEdit.isEnabled())
        self.to_load.add(bname)
        self.ui.configFrame.hide()

        self.loadConfiguredBackendsList()

    def rejectBackend(self):
        self.ui.configFrame.hide()

    def backendSelectionChanged(self):
        for key, (label, value) in self.config_widgets.iteritems():
            label.hide()
            value.hide()
            self.ui.configLayout.removeWidget(label)
            self.ui.configLayout.removeWidget(value)
            label.deleteLater()
            value.deleteLater()
        self.config_widgets = {}
        self.ui.backendInfo.clear()

        selection = self.ui.backendsList.selectedItems()
        if not selection:
            return

        backend = self.weboob.backends_loader.loaded[unicode(selection[0].text()).lower()]

        if backend.icon_path:
            img = QImage(backend.icon_path)
            self.ui.backendInfo.document().addResource(QTextDocument.ImageResource, QUrl('mydata://logo.png'), QVariant(img))

        self.ui.backendInfo.setText(unicode(self.tr(
                                   '<h1>%s Backend %s</h1>'
                                   '<b>Version</b>: %s<br />'
                                   '<b>Maintainer</b>: %s<br />'
                                   '<b>License</b>: %s<br />'
                                   '<b>Description</b>: %s<br />'
                                   '<b>Capabilities</b>: %s<br />'))
                                   % ('<img src="mydata://logo.png" />' if backend.icon_path else '',
                                      backend.name.capitalize(),
                                      backend.version,
                                      backend.maintainer.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'),
                                      backend.license,
                                      backend.description,
                                      ', '.join([cap.__name__ for cap in backend.iter_caps()])))

        for key, field in backend.config.iteritems():
            label = QLabel(u'%s:' % field.description)
            if isinstance(field.default, bool):
                value = QCheckBox()
                if field.default:
                    value.setChecked(True)
            elif field.choices:
                value = QComboBox()
                for k, l in (field.choices.iteritems() if isinstance(field.choices, dict) else ((k,k) for k in field.choices)):
                    value.addItem(l, QVariant(k))
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

    def run(self):
        self.exec_()

        ret = (len(self.to_load) > 0 or len(self.to_unload) > 0)

        self.weboob.unload_backends(self.to_unload)
        self.weboob.load_configured_backends(names=self.to_load)

        return ret
