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

from PyQt4.QtGui import QDialog, QTreeWidgetItem, QLabel, QFormLayout, \
                        QMessageBox, QPixmap, QImage, QIcon, QHeaderView, \
                        QListWidgetItem, QTextDocument, QVBoxLayout, \
                        QDialogButtonBox
from PyQt4.QtCore import SIGNAL, Qt, QVariant, QUrl

from logging import warning

from weboob.capabilities.account import ICapAccount, Account, AccountRegisterError
from weboob.tools.application.qt.backendcfg_ui import Ui_BackendCfg
from weboob.tools.ordereddict import OrderedDict
from .qt import QtValue

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

        # This attribute is set when itemChanged it called, because when
        # a backend is enabled/disabled, we don't want to display its config
        # frame, and the itemClicked event is always emit just after a
        # itemChanged event.
        # is_enabling is a counter to prevent race conditions.
        self.is_enabling = 0

        self.weboob.modules_loader.load_all()

        self.ui.configuredBackendsList.header().setResizeMode(QHeaderView.ResizeToContents)
        self.ui.configFrame.hide()

        for name, backend in self.weboob.modules_loader.loaded.iteritems():
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
        self.connect(self.ui.registerButton, SIGNAL('clicked()'), self.registerEvent)
        self.connect(self.ui.configButtonBox, SIGNAL('accepted()'), self.acceptBackend)
        self.connect(self.ui.configButtonBox, SIGNAL('rejected()'), self.rejectBackend)

    def loadConfiguredBackendsList(self):
        self.ui.configuredBackendsList.clear()
        for instance_name, name, params in self.weboob.backends_config.iter_backends():
            backend = self.weboob.modules_loader.get_or_load_module(name)
            if not backend or self.caps and not backend.has_caps(*self.caps):
                continue

            item = QTreeWidgetItem(None, [instance_name, name])
            item.setCheckState(0, Qt.Checked if params.get('_enabled', '1').lower() in ('1', 'y', 'true') else Qt.Unchecked)

            if backend.icon_path:
                img = QImage(backend.icon_path)
                item.setIcon(0, QIcon(QPixmap.fromImage(img)))

            self.ui.configuredBackendsList.addTopLevelItem(item)

    def configuredBackendEnabled(self, item, col):
        self.is_enabling += 1

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
        if self.is_enabling:
            self.is_enabling -= 1
            return

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
        self.ui.registerButton.hide()
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
                try:
                    l, widget = self.config_widgets[key]
                except KeyError:
                    warning('Key "%s" is not found' % key)
                else:
                    widget.set_data(value)
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

        backend = self.weboob.modules_loader.get_or_load_module(unicode(selection[0].text()).lower())

        if not backend:
            QMessageBox.critical(self, self.tr('Unable to add a configured backend'),
                                       self.tr('The selected backend does not exist.'))
            return

        params = {}

        if not bname:
            QMessageBox.critical(self, self.tr('Missing field'),
                                       self.tr('Please specify a backend name'))
            return

        if self.ui.proxyBox.isChecked():
            params['_proxy'] = unicode(self.ui.proxyEdit.text())
            if not params['_proxy']:
                QMessageBox.critical(self, self.tr('Missing field'),
                                           self.tr('Please specify a proxy URL'))
                return

        for key, field in backend.config.iteritems():
            label, qtvalue = self.config_widgets[key]

            try:
                value = qtvalue.get_value()
            except ValueError, e:
                QMessageBox.critical(self,
                                     self.tr('Invalid value'),
                                     unicode(self.tr('Invalid value for field "%s":<br /><br />%s')) % (field.label, e))
                return

            params[key] = value.value

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

        backend = self.weboob.modules_loader.loaded[unicode(selection[0].text()).lower()]

        if backend.icon_path:
            img = QImage(backend.icon_path)
            self.ui.backendInfo.document().addResource(QTextDocument.ImageResource, QUrl('mydata://logo.png'), QVariant(img))

        self.ui.backendInfo.setText(unicode(self.tr(
                                   '<h1>%s Backend %s</h1>'
                                   '<b>Version</b>: %s<br />'
                                   '<b>Maintainer</b>: %s<br />'
                                   '<b>License</b>: %s<br />'
                                   '%s'
                                   '<b>Description</b>: %s<br />'
                                   '<b>Capabilities</b>: %s<br />'))
                                   % ('<img src="mydata://logo.png" />' if backend.icon_path else '',
                                      backend.name.capitalize(),
                                      backend.version,
                                      backend.maintainer.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'),
                                      backend.license,
                                      (unicode(self.tr('<b>Website</b>: %s<br />')) % backend.website) if backend.website else '',
                                      backend.description,
                                      ', '.join([cap.__name__ for cap in backend.iter_caps()])))

        if backend.has_caps(ICapAccount) and self.ui.nameEdit.isEnabled():
            self.ui.registerButton.show()
        else:
            self.ui.registerButton.hide()

        for key, field in backend.config.iteritems():
            label = QLabel(u'%s:' % field.label)
            value = QtValue(field)
            self.ui.configLayout.addRow(label, value)
            self.config_widgets[key] = (label, value)

    def proxyEditEnabled(self, state):
        self.ui.proxyEdit.setEnabled(state)

    def registerEvent(self):
        selection = self.ui.backendsList.selectedItems()
        if not selection:
            return

        backend = self.weboob.modules_loader.get_or_load_module(unicode(selection[0].text()).lower())

        if not backend:
            return

        dialog = QDialog(self)
        vbox = QVBoxLayout(dialog)
        if backend.website:
            website = 'on the website <b>%s</b>' % backend.website
        else:
            website = 'with the backend <b>%s</b>' % backend.name
        vbox.addWidget(QLabel('To create an account %s, please give these informations:' % website))
        formlayout = QFormLayout()
        props_widgets = OrderedDict()
        for key, prop in backend.klass.ACCOUNT_REGISTER_PROPERTIES.iteritems():
            widget = QtValue(prop)
            formlayout.addRow(QLabel(u'%s:' % prop.label), widget)
            props_widgets[prop.id] = widget

        vbox.addLayout(formlayout)
        buttonBox = QDialogButtonBox(dialog)
        buttonBox.setStandardButtons(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        self.connect(buttonBox, SIGNAL("accepted()"), dialog.accept)
        self.connect(buttonBox, SIGNAL("rejected()"), dialog.reject)
        vbox.addWidget(buttonBox)

        end = False
        while not end:
            end = True
            if dialog.exec_():
                account = Account()
                account.properties = {}
                for key, widget in props_widgets.iteritems():
                    try:
                        v = widget.get_value()
                    except ValueError, e:
                        QMessageBox.critical(self,
                                             self.tr('Invalid value'),
                                             unicode(self.tr('Invalid value for field "%s":<br /><br />%s')) % (key, e))
                        end = False
                        break
                    else:
                        account.properties[key] = v
                if end:
                    try:
                        backend.klass.register_account(account)
                    except AccountRegisterError, e:
                        QMessageBox.critical(self,
                                             self.tr('Error during register'),
                                             unicode(self.tr('Unable to register account %s:<br /><br />%s')) % (website, e))
                        end = False
                    else:
                        for key, value in account.properties.iteritems():
                            if key in self.config_widgets:
                                self.config_widgets[key][1].set_data(value.value)

    def run(self):
        self.exec_()

        ret = (len(self.to_load) > 0 or len(self.to_unload) > 0)

        self.weboob.unload_backends(self.to_unload)
        self.weboob.load_backends(names=self.to_load)

        return ret
